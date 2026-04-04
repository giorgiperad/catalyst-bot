"""
Simulation Engine — runs bot decision logic at tick speed against fake prices.

No Flask, no network, no sleep. Every external call is intercepted and
answered by the simulation state. Findings feed back into the real bot.

The engine faithfully reimplements the market-making loop that lives in
bot_loop.py and offer_manager.py, but in pure Python with no I/O.  This
lets you run thousands of ticks in seconds to stress-test:
  - Tier sizing and requote thresholds
  - Circuit-breaker trip/recovery
  - Coin-split triggers and wallet dry-out
  - P&L under various price models (see simulation/market.py)

Typical usage::

    from simulation.engine import SimBot, Scenario
    from simulation.market import PRESET_MODELS

    scenario = Scenario(
        spread_bps=800,
        n_inner=3, n_mid=3, n_outer=2, n_extreme=1,
        starting_xch=10.0, starting_cat=5000.0,
    )
    bot = SimBot(scenario)
    prices = PRESET_MODELS["crash"].generate(500, 0.001)
    results = [bot.tick(p) for p in prices]
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SimCoin:
    """A single simulated UTXO coin.

    Mirrors the real Chia coin model: each offer locks exactly one coin.
    Amounts are stored as mojos (integer) for XCH coins and as raw CAT
    token units (integer, scaled by CAT_DECIMALS) for CAT coins.
    """
    coin_id: str
    """Unique identifier — random hex string, not a real coin ID."""
    amount_mojos: int
    """Amount in mojos for XCH coins; raw token units for CAT coins."""
    side: str
    """'xch' or 'cat'."""
    locked: bool = False
    """True when this coin is committed to an open offer."""


@dataclass
class SimOffer:
    """A single simulated market-making offer on Dexie.

    Covers both buy offers (we bid XCH, receive CAT) and sell offers
    (we bid CAT, receive XCH).
    """
    trade_id: str
    """Unique offer identifier."""
    side: str
    """'buy' or 'sell'."""
    tier: str
    """'inner', 'mid', 'outer', or 'extreme'."""
    offer_price: float
    """Price at which this offer was posted (XCH per CAT)."""
    xch_amount: float
    """XCH committed to this offer (spent on buy; received on sell)."""
    cat_amount: float
    """CAT committed to this offer (received on buy; spent on sell)."""
    created_tick: int
    """Simulation tick at which the offer was created."""
    status: str = "open"
    """'open', 'filled', or 'cancelled'."""


@dataclass
class TickResult:
    """Summary of what happened during one bot tick.

    Returned by SimBot.tick() so the caller can log, plot, or aggregate
    metrics across a full simulation run.
    """
    tick: int
    """Current tick number (zero-indexed)."""
    price: float
    """Market price at this tick."""
    fills: List[SimOffer]
    """Offers that filled during this tick."""
    new_offers: int
    """Number of new offers posted this tick."""
    cancelled_offers: int
    """Number of stale offers cancelled this tick."""
    cb_tripped: bool
    """True if a circuit breaker is currently active."""
    cb_side: str
    """The side blocked by the circuit breaker ('buy', 'sell', or '')."""
    xch_balance: float
    """Spendable XCH balance after this tick."""
    cat_balance: float
    """Spendable CAT balance after this tick."""
    active_buy_count: int
    """Number of open buy offers after this tick."""
    active_sell_count: int
    """Number of open sell offers after this tick."""
    pnl_xch: float
    """Cumulative P&L in XCH terms (net_xch_flow + net_cat_flow * price)."""


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """Configuration for one simulation run.

    Mirrors the bot's config.py attributes (SPREAD_BPS, INNER_SIZE_XCH, etc.)
    but as plain Python floats/ints so no dotenv is needed.
    """
    # --- Spread & Pricing ---
    spread_bps: float = 800.0
    """Base spread in basis points (800 = 8%)."""
    requote_bps: float = 150.0
    """Requote threshold in basis points.  Offer is stale if price moves
    more than this fraction from the offer price (150 = 1.5%)."""

    # --- Tier counts (offers per side) ---
    n_inner: int = 3
    """Target number of inner-tier offers per side."""
    n_mid: int = 3
    """Target number of mid-tier offers per side."""
    n_outer: int = 2
    """Target number of outer-tier offers per side."""
    n_extreme: int = 1
    """Target number of extreme-tier offers per side."""

    # --- Tier sizes (XCH per offer) ---
    inner_size_xch: float = 1.0
    """XCH committed per inner-tier offer (config: INNER_SIZE_XCH)."""
    mid_size_xch: float = 0.5
    """XCH committed per mid-tier offer (config: MID_SIZE_XCH)."""
    outer_size_xch: float = 0.25
    """XCH committed per outer-tier offer (config: OUTER_SIZE_XCH)."""
    extreme_size_xch: float = 0.1
    """XCH committed per extreme-tier offer (config: EXTREME_SIZE_XCH)."""

    # --- Wallet ---
    starting_xch: float = 10.0
    """Starting XCH balance."""
    starting_cat: float = 5000.0
    """Starting CAT balance (raw tokens, not mojos)."""
    xch_coin_size: float = 0.5
    """Size of each XCH UTXO coin (XCH)."""
    cat_coin_size_tokens: float = 500.0
    """Size of each CAT UTXO coin (tokens)."""
    xch_reserve: float = 0.03
    """XCH held back from trading (config: XCH_RESERVE)."""
    cat_reserve: float = 0.0
    """CAT held back from trading (config: CAT_RESERVE)."""

    # --- Position / Circuit Breaker ---
    max_position_xch: float = 5.0
    """Maximum net position size in XCH equivalent (config: MAX_POSITION_XCH)."""

    # --- CAT decimals ---
    cat_decimals: int = 3
    """Token decimals (config: CAT_DECIMALS). Used to convert CAT↔mojos."""

    # --- Misc ---
    name: str = "default"
    """Human-readable scenario name for reporting."""


# ---------------------------------------------------------------------------
# SimWallet
# ---------------------------------------------------------------------------

class SimWallet:
    """Simulated coin wallet — manages XCH and CAT UTXOs.

    The wallet tracks a list of SimCoin objects on each side.  When an
    offer is created it locks one coin; when the offer fills or is cancelled
    that coin is unlocked (or replaced by new coins reflecting the fill).
    """

    def __init__(
        self,
        xch: float,
        cat: float,
        xch_coin_size: float = 0.5,
        cat_coin_size_tokens: float = 500.0,
        xch_reserve: float = 0.03,
        cat_reserve: float = 0.0,
    ):
        """Initialise the wallet by splitting balances into coins.

        Args:
            xch: Starting XCH balance.
            cat: Starting CAT balance (tokens).
            xch_coin_size: Target size of each XCH coin in XCH.
            cat_coin_size_tokens: Target size of each CAT coin in tokens.
            xch_reserve: XCH to keep back from trading.
            cat_reserve: CAT to keep back from trading.
        """
        self.xch_reserve = xch_reserve
        self.cat_reserve = cat_reserve
        self._xch_coin_size = xch_coin_size
        self._cat_coin_size = cat_coin_size_tokens
        # 1e12 mojos per XCH
        self._MOJOS_PER_XCH = int(1e12)
        # 1000 raw units per token at 3 decimals (10^CAT_DECIMALS)
        self._UNITS_PER_TOKEN = 1000

        self.xch_coins: List[SimCoin] = self._split_balance_xch(xch, xch_coin_size)
        self.cat_coins: List[SimCoin] = self._split_balance_cat(cat, cat_coin_size_tokens)

    # --- Balance queries ---

    def spendable_xch(self) -> float:
        """Return total unlocked XCH balance in XCH (not mojos).

        Subtracts the reserve so callers see only tradeable XCH.
        """
        total_mojos = sum(
            c.amount_mojos for c in self.xch_coins if not c.locked
        )
        return max(0.0, total_mojos / self._MOJOS_PER_XCH - self.xch_reserve)

    def spendable_cat(self) -> float:
        """Return total unlocked CAT balance in tokens.

        Subtracts the reserve so callers see only tradeable CAT.
        """
        total_units = sum(
            c.amount_mojos for c in self.cat_coins if not c.locked
        )
        return max(0.0, total_units / self._UNITS_PER_TOKEN - self.cat_reserve)

    def total_xch(self) -> float:
        """Return total XCH across all coins (locked + unlocked)."""
        return sum(c.amount_mojos for c in self.xch_coins) / self._MOJOS_PER_XCH

    def total_cat(self) -> float:
        """Return total CAT across all coins (locked + unlocked) in tokens."""
        return sum(c.amount_mojos for c in self.cat_coins) / self._UNITS_PER_TOKEN

    # --- Coin locking ---

    def lock_coin(self, side: str, amount: float) -> bool:
        """Lock one free coin whose amount covers the requested value.

        Args:
            side: 'xch' or 'cat'.
            amount: XCH amount (for side='xch') or token amount (for side='cat')
                that needs to be covered.

        Returns:
            True if a suitable coin was found and locked; False otherwise.
        """
        coins = self.xch_coins if side == "xch" else self.cat_coins
        amount_units = (
            int(amount * self._MOJOS_PER_XCH) if side == "xch"
            else int(amount * self._UNITS_PER_TOKEN)
        )
        # Find the smallest coin that covers the amount (best-fit)
        candidates = [
            c for c in coins
            if not c.locked and c.amount_mojos >= amount_units
        ]
        if not candidates:
            return False
        best = min(candidates, key=lambda c: c.amount_mojos)
        best.locked = True
        return True

    def unlock_coin(self, side: str, amount: float) -> None:
        """Release the locked coin closest to the given amount.

        Args:
            side: 'xch' or 'cat'.
            amount: The amount that was previously locked.
        """
        coins = self.xch_coins if side == "xch" else self.cat_coins
        amount_units = (
            int(amount * self._MOJOS_PER_XCH) if side == "xch"
            else int(amount * self._UNITS_PER_TOKEN)
        )
        locked = [c for c in coins if c.locked]
        if not locked:
            return
        # Unlock the coin closest in size to what was originally locked
        closest = min(locked, key=lambda c: abs(c.amount_mojos - amount_units))
        closest.locked = False

    def apply_fill(self, offer: SimOffer) -> None:
        """Update coin lists when an offer fills.

        For a buy fill: spend XCH (remove locked XCH coin), gain CAT
        (add a new unlocked CAT coin).
        For a sell fill: spend CAT (remove locked CAT coin), gain XCH
        (add a new unlocked XCH coin).

        Args:
            offer: The offer that just filled.
        """
        if offer.side == "buy":
            # Remove the locked XCH coin used for this offer
            xch_units = int(offer.xch_amount * self._MOJOS_PER_XCH)
            self._remove_locked_coin(self.xch_coins, xch_units)
            # Add gained CAT as a new coin
            cat_units = int(offer.cat_amount * self._UNITS_PER_TOKEN)
            self.cat_coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=cat_units,
                side="cat",
                locked=False,
            ))
        else:  # sell
            # Remove the locked CAT coin used for this offer
            cat_units = int(offer.cat_amount * self._UNITS_PER_TOKEN)
            self._remove_locked_coin(self.cat_coins, cat_units)
            # Add gained XCH as a new coin
            xch_units = int(offer.xch_amount * self._MOJOS_PER_XCH)
            self.xch_coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=xch_units,
                side="xch",
                locked=False,
            ))

    # --- Coin health ---

    def needs_split(self, side: str) -> bool:
        """Return True if the given side has fewer than 3 free coins.

        Args:
            side: 'xch' or 'cat'.
        """
        coins = self.xch_coins if side == "xch" else self.cat_coins
        free_count = sum(1 for c in coins if not c.locked)
        return free_count < 3

    def do_split(self, side: str, target_coins: int = 10) -> int:
        """Simulate a coin split — merge free coins and redivide.

        The largest unlocked coin is split into target_coins smaller coins
        of equal size.  This does not affect locked coins.

        Args:
            side: 'xch' or 'cat'.
            target_coins: How many coins to create from the split.

        Returns:
            Number of new coins created.
        """
        coins = self.xch_coins if side == "xch" else self.cat_coins
        free = [c for c in coins if not c.locked]
        if not free:
            return 0
        # Use the largest free coin as the source
        source = max(free, key=lambda c: c.amount_mojos)
        coins.remove(source)
        if source.amount_mojos <= 0:
            return 0
        piece = source.amount_mojos // target_coins
        if piece <= 0:
            # Re-add and abort — coin too small to split
            coins.append(source)
            return 0
        remainder = source.amount_mojos - piece * target_coins
        new_coins = []
        for i in range(target_coins):
            amt = piece + (remainder if i == 0 else 0)
            new_coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=amt,
                side=side,
                locked=False,
            ))
        coins.extend(new_coins)
        return target_coins

    # --- Private helpers ---

    def _split_balance_xch(self, xch: float, coin_size: float) -> List[SimCoin]:
        """Create XCH coins from a starting balance."""
        coins: List[SimCoin] = []
        remaining_mojos = int(xch * self._MOJOS_PER_XCH)
        coin_mojos = max(1, int(coin_size * self._MOJOS_PER_XCH))
        while remaining_mojos >= coin_mojos:
            coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=coin_mojos,
                side="xch",
            ))
            remaining_mojos -= coin_mojos
        if remaining_mojos > 0:
            coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=remaining_mojos,
                side="xch",
            ))
        return coins

    def _split_balance_cat(self, cat: float, coin_size_tokens: float) -> List[SimCoin]:
        """Create CAT coins from a starting balance."""
        coins: List[SimCoin] = []
        remaining_units = int(cat * self._UNITS_PER_TOKEN)
        coin_units = max(1, int(coin_size_tokens * self._UNITS_PER_TOKEN))
        while remaining_units >= coin_units:
            coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=coin_units,
                side="cat",
            ))
            remaining_units -= coin_units
        if remaining_units > 0:
            coins.append(SimCoin(
                coin_id=_new_id(),
                amount_mojos=remaining_units,
                side="cat",
            ))
        return coins

    def _remove_locked_coin(self, coins: List[SimCoin], target_units: int) -> None:
        """Remove the locked coin closest to target_units from coins list."""
        locked = [c for c in coins if c.locked]
        if not locked:
            return
        closest = min(locked, key=lambda c: abs(c.amount_mojos - target_units))
        coins.remove(closest)


# ---------------------------------------------------------------------------
# SimBot
# ---------------------------------------------------------------------------

# Tier distance factors — how much further from mid each tier is placed
_TIER_FACTORS: Dict[str, float] = {
    "inner": 1.0,
    "mid": 1.5,
    "outer": 2.5,
    "extreme": 4.0,
}

# Ordered from closest to mid → furthest (posting priority)
_TIER_ORDER: List[str] = ["inner", "mid", "outer", "extreme"]


class SimBot:
    """Faithful reimplementation of the bot's core market-making loop.

    Same decisions as the real bot: tier sizing, requote, circuit breakers.
    Runs without Flask / PyWebView / real network calls.

    The simulation tick cycle mirrors bot_loop.py::_run_cycle():
      1. Update mid price reference.
      2. Check fills (price crossing).
      3. Cancel stale offers (requote threshold).
      4. Check circuit breakers (position limit).
      5. Post missing offers to hit target depth.
      6. Optionally trigger coin splits if wallet runs low.
    """

    def __init__(self, scenario: 'Scenario'):
        """Initialise the simulation bot from a Scenario config.

        Args:
            scenario: Scenario dataclass holding all trading parameters.
        """
        self.scenario = scenario

        # Wallet
        self.wallet = SimWallet(
            xch=scenario.starting_xch,
            cat=scenario.starting_cat,
            xch_coin_size=scenario.xch_coin_size,
            cat_coin_size_tokens=scenario.cat_coin_size_tokens,
            xch_reserve=scenario.xch_reserve,
            cat_reserve=scenario.cat_reserve,
        )

        # Active offers (trade_id -> SimOffer)
        self.active_offers: Dict[str, SimOffer] = {}

        # Reference mid price (updated each tick)
        self.mid_price_ref: Optional[float] = None

        # Tick counter
        self.tick_count: int = 0

        # --- Circuit breaker state ---
        self.cb_tripped: bool = False
        self.cb_blocked_side: str = ""
        self.cb_reason: str = ""

        # --- Position tracking (net CAT delta from fills) ---
        # Positive = net long CAT (we've been buying more than selling)
        # Negative = net short CAT (we've been selling more than buying)
        self.net_cat_delta: float = 0.0

        # --- P&L tracking ---
        self.net_xch_flow: float = 0.0   # XCH gained (sells) minus XCH spent (buys)
        self.net_cat_flow: float = 0.0   # CAT gained (buys) minus CAT spent (sells)

        # --- Cumulative fill / cancel counters ---
        self.total_fills: int = 0
        self.total_cancels: int = 0
        self.total_new_offers: int = 0

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def tick(self, price: float) -> TickResult:
        """Run one bot cycle at the given market price.

        This is the main entry point.  Call once per simulated tick with the
        current market price.  The bot will:
          - Fill any crossed offers.
          - Cancel stale offers that need requoting.
          - Re-evaluate circuit breaker state.
          - Post new offers to reach target depth.
          - Return a TickResult summarising the tick.

        Args:
            price: Current market mid price (XCH per CAT).

        Returns:
            TickResult with a complete snapshot of this tick.
        """
        # Step 1: Update price reference
        if self.mid_price_ref is None:
            self.mid_price_ref = price
        else:
            # Slow EMA update (1% weight per tick) — same as bot's price tracker
            self.mid_price_ref = self.mid_price_ref * 0.99 + price * 0.01

        # Step 2: Check fills
        fills = self._check_fills(price)
        for offer in fills:
            offer.status = "filled"
            self.wallet.apply_fill(offer)
            del self.active_offers[offer.trade_id]
            self.total_fills += 1
            # Update P&L tracking
            if offer.side == "buy":
                self.net_xch_flow -= offer.xch_amount
                self.net_cat_flow += offer.cat_amount
                self.net_cat_delta += offer.cat_amount
            else:
                self.net_xch_flow += offer.xch_amount
                self.net_cat_flow -= offer.cat_amount
                self.net_cat_delta -= offer.cat_amount

        # Step 3: Cancel stale offers
        cancelled = self._requote_stale(price)
        self.total_cancels += cancelled

        # Step 4: Check circuit breakers
        self._check_position_limit()

        # Step 5: Post missing offers
        new_count = self._post_missing_offers(price)
        self.total_new_offers += new_count

        # Step 6: Coin splits if wallet is low
        for side in ("xch", "cat"):
            if self.wallet.needs_split(side):
                self.wallet.do_split(side)

        self.tick_count += 1

        # Compile result
        active_buy_count = sum(
            1 for o in self.active_offers.values() if o.side == "buy"
        )
        active_sell_count = sum(
            1 for o in self.active_offers.values() if o.side == "sell"
        )

        return TickResult(
            tick=self.tick_count,
            price=price,
            fills=fills,
            new_offers=new_count,
            cancelled_offers=cancelled,
            cb_tripped=self.cb_tripped,
            cb_side=self.cb_blocked_side,
            xch_balance=self.wallet.spendable_xch(),
            cat_balance=self.wallet.spendable_cat(),
            active_buy_count=active_buy_count,
            active_sell_count=active_sell_count,
            pnl_xch=self._calculate_pnl(price),
        )

    def get_state(self) -> dict:
        """Return a snapshot of current bot state for metrics and logging.

        Returns:
            Dictionary with current tick, balances, offer counts, P&L,
            circuit breaker state, and position.
        """
        active = list(self.active_offers.values())
        buy_count = sum(1 for o in active if o.side == "buy")
        sell_count = sum(1 for o in active if o.side == "sell")
        price = self.mid_price_ref or 0.0
        return {
            "tick": self.tick_count,
            "mid_price_ref": price,
            "xch_balance": self.wallet.spendable_xch(),
            "cat_balance": self.wallet.spendable_cat(),
            "total_xch": self.wallet.total_xch(),
            "total_cat": self.wallet.total_cat(),
            "active_buy_count": buy_count,
            "active_sell_count": sell_count,
            "total_active_offers": len(active),
            "net_cat_delta": self.net_cat_delta,
            "net_xch_flow": self.net_xch_flow,
            "net_cat_flow": self.net_cat_flow,
            "pnl_xch": self._calculate_pnl(price),
            "cb_tripped": self.cb_tripped,
            "cb_blocked_side": self.cb_blocked_side,
            "cb_reason": self.cb_reason,
            "total_fills": self.total_fills,
            "total_cancels": self.total_cancels,
            "total_new_offers": self.total_new_offers,
            "xch_coin_count": len(self.wallet.xch_coins),
            "cat_coin_count": len(self.wallet.cat_coins),
        }

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _check_fills(self, price: float) -> List[SimOffer]:
        """Fill any offer whose price is crossed by the current market price.

        Fill logic (taker perspective):
          Buy offer: we bid XCH for CAT.  A seller takes our offer when the
            market price falls to or below our bid.  We allow a small
            tolerance (0.5%) to model realistic fill behaviour where the
            exact mid doesn't need to cross the price exactly.
          Sell offer: we ask XCH for CAT.  A buyer takes our offer when the
            market price rises to or above our ask.  Same 0.5% tolerance.

        Args:
            price: Current market mid price.

        Returns:
            List of SimOffer objects that filled this tick.
        """
        filled: List[SimOffer] = []
        for offer in list(self.active_offers.values()):
            if offer.status != "open":
                continue
            if offer.side == "buy":
                # Fill when market price <= our bid (with 0.5% grace)
                if price <= offer.offer_price * 1.005:
                    filled.append(offer)
            else:  # sell
                # Fill when market price >= our ask (with 0.5% grace)
                if price >= offer.offer_price * 0.995:
                    filled.append(offer)
        return filled

    def _get_offer_price(self, side: str, tier: str, mid: float) -> float:
        """Calculate the posting price for a given side/tier combination.

        The half-spread is derived from scenario.spread_bps, then scaled by
        the tier's distance factor.  Inner tier sits closest to mid;
        extreme tier sits furthest away.

        Buy prices: mid * (1 - half_spread * tier_factor)
        Sell prices: mid * (1 + half_spread * tier_factor)

        Args:
            side: 'buy' or 'sell'.
            tier: 'inner', 'mid', 'outer', or 'extreme'.
            mid: Current market mid price.

        Returns:
            Offer price in XCH per CAT.
        """
        half_spread = (self.scenario.spread_bps / 10_000.0) / 2.0
        factor = _TIER_FACTORS.get(tier, 1.0)
        spread_factor = half_spread * factor
        if side == "buy":
            return mid * (1.0 - spread_factor)
        else:
            return mid * (1.0 + spread_factor)

    def _requote_stale(self, price: float) -> int:
        """Cancel offers whose price has drifted beyond the requote threshold.

        An offer is stale when:
          |current_price - offer_price| / offer_price > (requote_bps / 10000) * 2

        The factor of 2 means the threshold applies to the full spread, not
        just the half-spread.  This matches bot_loop.py's requote logic.

        Stale offers are cancelled: the locked coin is unlocked so it can be
        used for a fresh offer.

        Args:
            price: Current market mid price.

        Returns:
            Number of offers cancelled.
        """
        threshold = (self.scenario.requote_bps / 10_000.0) * 2.0
        to_cancel: List[SimOffer] = []

        for offer in list(self.active_offers.values()):
            if offer.status != "open":
                continue
            if offer.offer_price <= 0:
                continue
            drift = abs(price - offer.offer_price) / offer.offer_price
            if drift > threshold:
                to_cancel.append(offer)

        for offer in to_cancel:
            offer.status = "cancelled"
            # Return the locked coin to the free pool
            if offer.side == "buy":
                self.wallet.unlock_coin("xch", offer.xch_amount)
            else:
                self.wallet.unlock_coin("cat", offer.cat_amount)
            del self.active_offers[offer.trade_id]

        return len(to_cancel)

    def _check_position_limit(self) -> None:
        """Evaluate and update the position-limit circuit breaker.

        The circuit breaker compares net_cat_delta (in CAT) to the
        equivalent of max_position_xch at the current mid price.

        If net long (bought too much CAT): block the buy side.
        If net short (sold too much CAT): block the sell side.

        CRITICAL: The correcting side is NEVER blocked.  If we're over-long
        CAT, sell offers must continue — halting them would worsen the
        position.  This matches the architectural decision recorded in
        CLAUDE.md.

        If the position is within limits, the circuit breaker is cleared.
        """
        if self.mid_price_ref is None or self.mid_price_ref <= 0:
            return

        max_cat = self.scenario.max_position_xch / self.mid_price_ref

        if self.net_cat_delta > max_cat:
            # Over-long — block buy side, allow sell side (corrects the position)
            self.cb_tripped = True
            self.cb_blocked_side = "buy"
            self.cb_reason = (
                f"Net long {self.net_cat_delta:.1f} CAT exceeds "
                f"limit {max_cat:.1f} CAT"
            )
        elif self.net_cat_delta < -max_cat:
            # Over-short — block sell side, allow buy side (corrects the position)
            self.cb_tripped = True
            self.cb_blocked_side = "sell"
            self.cb_reason = (
                f"Net short {self.net_cat_delta:.1f} CAT exceeds "
                f"limit {-max_cat:.1f} CAT"
            )
        else:
            # Within limits — clear circuit breaker
            self.cb_tripped = False
            self.cb_blocked_side = ""
            self.cb_reason = ""

    def _post_missing_offers(self, price: float) -> int:
        """Create new offers to reach the target depth on each side.

        For each side (buy/sell) and each tier (inner, mid, outer, extreme),
        count how many open offers already exist and post enough new ones to
        reach the scenario target count.

        Respects:
          - Circuit breaker: skips blocked side entirely.
          - Wallet balance: skips if insufficient free coins on that side.

        Args:
            price: Current market mid price (used to calculate offer prices).

        Returns:
            Total number of new offers posted this tick.
        """
        new_count = 0
        target_counts = {
            "inner": (self.scenario.n_inner, self.scenario.inner_size_xch),
            "mid": (self.scenario.n_mid, self.scenario.mid_size_xch),
            "outer": (self.scenario.n_outer, self.scenario.outer_size_xch),
            "extreme": (self.scenario.n_extreme, self.scenario.extreme_size_xch),
        }

        for side in ("buy", "sell"):
            if self.cb_tripped and self.cb_blocked_side == side:
                continue  # Circuit breaker: skip blocked side

            for tier in _TIER_ORDER:
                target, xch_size = target_counts[tier]
                if target <= 0:
                    continue

                # Count existing open offers on this side/tier
                existing = sum(
                    1 for o in self.active_offers.values()
                    if o.side == side and o.tier == tier and o.status == "open"
                )
                needed = target - existing

                for _ in range(needed):
                    offer_price = self._get_offer_price(side, tier, price)
                    if offer_price <= 0:
                        continue

                    # Determine coin requirements
                    if side == "buy":
                        coin_side = "xch"
                        coin_amount = xch_size
                        # CAT amount = XCH / price
                        cat_amount = xch_size / offer_price if offer_price > 0 else 0.0
                        xch_amount = xch_size
                    else:
                        # Sell: we commit CAT, receive XCH
                        # cat_amount = xch_size / offer_price (same CAT as the buy side mirror)
                        coin_side = "cat"
                        cat_amount = xch_size / offer_price if offer_price > 0 else 0.0
                        coin_amount = cat_amount
                        xch_amount = xch_size

                    # Check if wallet has enough on the relevant side
                    if side == "buy" and self.wallet.spendable_xch() < xch_amount:
                        break  # Out of XCH — skip remaining offers on this tier
                    if side == "sell" and self.wallet.spendable_cat() < cat_amount:
                        break  # Out of CAT — skip remaining offers on this tier

                    # Lock the coin
                    locked = self.wallet.lock_coin(coin_side, coin_amount)
                    if not locked:
                        break  # No suitable coin available

                    offer = SimOffer(
                        trade_id=_new_id(),
                        side=side,
                        tier=tier,
                        offer_price=offer_price,
                        xch_amount=xch_amount,
                        cat_amount=cat_amount,
                        created_tick=self.tick_count,
                        status="open",
                    )
                    self.active_offers[offer.trade_id] = offer
                    new_count += 1

        return new_count

    def _calculate_pnl(self, current_price: float) -> float:
        """Calculate cumulative P&L in XCH terms.

        P&L formula:
          net_xch_flow: XCH received from sell fills - XCH spent on buy fills
          net_cat_flow: CAT received from buy fills - CAT spent on sell fills
          pnl = net_xch_flow + (net_cat_flow * current_price)

        This is a mark-to-market P&L: the unrealised value of the net CAT
        position is priced at the current mid.

        Args:
            current_price: Current market mid price (XCH per CAT).

        Returns:
            P&L in XCH.
        """
        cat_value = self.net_cat_flow * current_price
        return self.net_xch_flow + cat_value


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _new_id() -> str:
    """Generate a short unique ID for coins and offers.

    Returns:
        A 16-character hex string.
    """
    return uuid.uuid4().hex[:16]
