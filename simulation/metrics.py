"""
Metrics collection and analysis for simulation runs.

Tracks every tick and computes aggregate statistics for comparison
across scenarios and between simulated and real bot behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from simulation.engine import SimOffer, TickResult
    from simulation.scenarios import Scenario


# ---------------------------------------------------------------------------
# TickSnapshot
# ---------------------------------------------------------------------------

@dataclass
class TickSnapshot:
    """Complete state snapshot for one tick.

    Stored by MetricsCollector so the full run can be replayed or charted.
    """

    tick: int
    price: float
    xch_balance: float
    cat_balance: float
    active_buys: int
    active_sells: int
    fills_this_tick: List["SimOffer"]
    new_offers_this_tick: int
    cancels_this_tick: int
    cb_tripped: bool
    cb_side: str
    pnl_xch: float
    spread_captured_this_tick: float
    """Estimated spread captured this tick from fills (XCH)."""


# ---------------------------------------------------------------------------
# SimResult
# ---------------------------------------------------------------------------

@dataclass
class SimResult:
    """Complete output of one scenario run.

    All aggregate metrics are pre-computed by MetricsCollector.summary().
    Raw series are kept for charting.
    """

    scenario_name: str
    n_ticks: int
    duration_virtual_hours: float

    # --- P&L ---
    starting_xch: float
    starting_cat: float
    ending_xch: float
    ending_cat: float
    starting_portfolio_xch: float
    """starting_xch + starting_cat * starting_price"""
    ending_portfolio_xch: float
    """ending_xch + ending_cat * ending_price"""
    pnl_xch: float
    """ending_portfolio_xch - starting_portfolio_xch"""
    pnl_pct: float
    """pnl_xch / starting_portfolio_xch * 100"""

    # --- Activity ---
    total_fills: int
    buy_fills: int
    sell_fills: int
    total_offers_created: int
    total_offers_cancelled: int
    fill_rate_per_hour: float
    avg_spread_captured_bps: float
    """Average actual spread captured per filled round-trip pair, in bps."""

    # --- Capital efficiency ---
    avg_capital_deployed_pct: float
    """Average fraction of total active offer slots that were filled (0–100)."""
    dead_ticks: int
    """Ticks with zero active offers on either side."""
    dead_pct: float
    """dead_ticks / n_ticks * 100"""

    # --- Risk ---
    max_drawdown_pct: float
    """Max peak-to-trough portfolio value drop, expressed as a percentage."""
    max_net_position_cat: float
    """Peak absolute net CAT position during the run."""
    cb_trips: int
    """Number of distinct circuit-breaker activation events."""
    cb_ticks: int
    """Total ticks during which a circuit breaker was active."""

    # --- Coin management ---
    coin_splits_needed: int
    """Ticks on which the wallet triggered a coin split."""

    # --- Issues ---
    issues: List[str]
    """Plain-English findings — feed back into real bot fixes."""

    # --- Raw series (for charts) ---
    price_series: List[float]
    pnl_series: List[float]
    balance_xch_series: List[float]
    balance_cat_series: List[float]


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """Accumulates per-tick data and computes aggregate SimResult.

    Usage::

        collector = MetricsCollector(scenario)
        bot = SimBot(engine_scenario)
        for price in prices:
            result = bot.tick(price)
            collector.record(result, bot.get_state())
        sim_result = collector.summary()
    """

    def __init__(self, scenario: "Scenario") -> None:
        """Initialise the collector.

        Args:
            scenario: The Scenario being run (needed for context in summary).
        """
        self._scenario = scenario
        self.snapshots: List[TickSnapshot] = []
        self.fill_events: List[dict] = []
        self.cb_events: List[dict] = []
        self.error_events: List[dict] = []

        # Internal tracking
        self._cb_was_tripped: bool = False
        self._coin_split_ticks: int = 0
        self._prev_xch: Optional[float] = None
        self._prev_cat: Optional[float] = None

    # -----------------------------------------------------------------------
    # Public record methods
    # -----------------------------------------------------------------------

    def record(self, tick_result: "TickResult", bot_state: dict) -> None:
        """Record one tick result.

        Args:
            tick_result: The TickResult returned by SimBot.tick().
            bot_state: The dict returned by SimBot.get_state() at the same tick.
        """
        # Estimate spread captured this tick
        spread_captured = self._estimate_spread_captured(tick_result)

        snapshot = TickSnapshot(
            tick=tick_result.tick,
            price=tick_result.price,
            xch_balance=tick_result.xch_balance,
            cat_balance=tick_result.cat_balance,
            active_buys=tick_result.active_buy_count,
            active_sells=tick_result.active_sell_count,
            fills_this_tick=list(tick_result.fills),
            new_offers_this_tick=tick_result.new_offers,
            cancels_this_tick=tick_result.cancelled_offers,
            cb_tripped=tick_result.cb_tripped,
            cb_side=tick_result.cb_side,
            pnl_xch=tick_result.pnl_xch,
            spread_captured_this_tick=spread_captured,
        )
        self.snapshots.append(snapshot)

        # Track fill events
        for offer in tick_result.fills:
            self.fill_events.append({
                "tick": tick_result.tick,
                "price": tick_result.price,
                "side": offer.side,
                "tier": offer.tier,
                "offer_price": offer.offer_price,
                "xch_amount": offer.xch_amount,
                "cat_amount": offer.cat_amount,
            })

        # Track CB transitions (trip / clear)
        if tick_result.cb_tripped and not self._cb_was_tripped:
            self.cb_events.append({
                "tick": tick_result.tick,
                "event": "trip",
                "side": tick_result.cb_side,
            })
        elif not tick_result.cb_tripped and self._cb_was_tripped:
            self.cb_events.append({
                "tick": tick_result.tick,
                "event": "clear",
            })
        self._cb_was_tripped = tick_result.cb_tripped

        # Detect coin splits (spendable balance jumped upward on same side
        # without a fill on that side — proxy for a split having occurred)
        xch_now = tick_result.xch_balance
        cat_now = tick_result.cat_balance
        has_buy_fill = any(o.side == "buy" for o in tick_result.fills)
        has_sell_fill = any(o.side == "sell" for o in tick_result.fills)

        if self._prev_xch is not None:
            xch_delta = xch_now - self._prev_xch
            cat_delta = cat_now - self._prev_cat  # type: ignore[operator]
            # A coin split shows as a balance increase without a fill on that side
            if xch_delta > 0.0 and not has_sell_fill:
                self._coin_split_ticks += 1
            elif cat_delta > 0.0 and not has_buy_fill:
                self._coin_split_ticks += 1

        self._prev_xch = xch_now
        self._prev_cat = cat_now

    def record_error(
        self,
        tick: int,
        error_type: str,
        message: str,
        context: Optional[dict] = None,
    ) -> None:
        """Record an error event (used by log replay).

        Args:
            tick: Tick number at which the error occurred.
            error_type: Short category string (e.g. 'coin_lock_failed').
            message: Human-readable error description.
            context: Optional extra data dict.
        """
        self.error_events.append({
            "tick": tick,
            "error_type": error_type,
            "message": message,
            "context": context or {},
        })

    # -----------------------------------------------------------------------
    # Summary computation
    # -----------------------------------------------------------------------

    def summary(self) -> SimResult:
        """Compute all aggregate metrics and return a SimResult.

        Returns:
            SimResult with every metric populated and issues detected.
        """
        if not self.snapshots:
            return self._empty_result()

        scenario = self._scenario
        snaps = self.snapshots

        # --- Basic series ---
        price_series = [s.price for s in snaps]
        pnl_series = [s.pnl_xch for s in snaps]
        bal_xch = [s.xch_balance for s in snaps]
        bal_cat = [s.cat_balance for s in snaps]

        starting_price = price_series[0]
        ending_price = price_series[-1]

        # --- Capital ---
        starting_xch = scenario.starting_xch
        starting_cat = scenario.starting_cat
        ending_xch = snaps[-1].xch_balance
        ending_cat = snaps[-1].cat_balance

        starting_portfolio = starting_xch + starting_cat * starting_price
        ending_portfolio = ending_xch + ending_cat * ending_price
        pnl_xch = ending_portfolio - starting_portfolio
        pnl_pct = (pnl_xch / starting_portfolio * 100.0) if starting_portfolio > 0 else 0.0

        # --- Activity ---
        buy_fills = sum(1 for e in self.fill_events if e["side"] == "buy")
        sell_fills = sum(1 for e in self.fill_events if e["side"] == "sell")
        total_fills = buy_fills + sell_fills
        total_created = sum(s.new_offers_this_tick for s in snaps)
        total_cancelled = sum(s.cancels_this_tick for s in snaps)

        virtual_hours = (len(snaps) * scenario.loop_seconds) / 3600.0
        fill_rate = (total_fills / virtual_hours) if virtual_hours > 0 else 0.0

        avg_spread_bps = self._calc_avg_spread_captured_bps(scenario.starting_price)

        # --- Capital efficiency ---
        # Target total offer slots = (n_inner + n_mid + n_outer + n_extreme) * 2 sides
        total_slots = (
            scenario.n_inner + scenario.n_mid + scenario.n_outer + scenario.n_extreme
        ) * 2
        if total_slots > 0:
            deployed_fracs = [
                (s.active_buys + s.active_sells) / total_slots for s in snaps
            ]
            avg_deployed_pct = (sum(deployed_fracs) / len(deployed_fracs)) * 100.0
        else:
            avg_deployed_pct = 0.0

        dead_ticks = sum(
            1 for s in snaps if s.active_buys == 0 and s.active_sells == 0
        )
        dead_pct = (dead_ticks / len(snaps)) * 100.0 if snaps else 0.0

        # --- Risk: drawdown ---
        max_drawdown_pct = self._calc_max_drawdown(pnl_series, starting_portfolio)

        # --- Risk: net position ---
        max_net_position = self._calc_max_net_position(starting_cat, bal_cat)

        # --- CB ---
        cb_trips = sum(1 for e in self.cb_events if e["event"] == "trip")
        cb_ticks = sum(1 for s in snaps if s.cb_tripped)

        # --- Duration ---
        duration_hours = virtual_hours

        # --- Build result ---
        result = SimResult(
            scenario_name=scenario.name,
            n_ticks=len(snaps),
            duration_virtual_hours=duration_hours,
            starting_xch=starting_xch,
            starting_cat=starting_cat,
            ending_xch=ending_xch,
            ending_cat=ending_cat,
            starting_portfolio_xch=starting_portfolio,
            ending_portfolio_xch=ending_portfolio,
            pnl_xch=pnl_xch,
            pnl_pct=pnl_pct,
            total_fills=total_fills,
            buy_fills=buy_fills,
            sell_fills=sell_fills,
            total_offers_created=total_created,
            total_offers_cancelled=total_cancelled,
            fill_rate_per_hour=fill_rate,
            avg_spread_captured_bps=avg_spread_bps,
            avg_capital_deployed_pct=avg_deployed_pct,
            dead_ticks=dead_ticks,
            dead_pct=dead_pct,
            max_drawdown_pct=max_drawdown_pct,
            max_net_position_cat=max_net_position,
            cb_trips=cb_trips,
            cb_ticks=cb_ticks,
            coin_splits_needed=self._coin_split_ticks,
            issues=[],
            price_series=price_series,
            pnl_series=pnl_series,
            balance_xch_series=bal_xch,
            balance_cat_series=bal_cat,
        )

        result.issues = detect_issues(result, scenario)
        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _estimate_spread_captured(self, tick_result: "TickResult") -> float:
        """Estimate XCH spread captured this tick.

        For each fill, the spread captured is abs(offer_price - mid_price)
        * cat_amount.  We proxy mid_price with the current tick price.

        Args:
            tick_result: The current tick result.

        Returns:
            Estimated XCH value of spread captured this tick.
        """
        total = 0.0
        mid = tick_result.price
        if mid <= 0:
            return 0.0
        for offer in tick_result.fills:
            if offer.offer_price > 0 and mid > 0:
                spread = abs(offer.offer_price - mid) / mid
                total += spread * offer.xch_amount
        return total

    def _calc_avg_spread_captured_bps(self, starting_price: float) -> float:
        """Average actual spread captured per fill in basis points.

        Args:
            starting_price: The scenario starting price (used as fallback mid).

        Returns:
            Average spread captured in basis points.
        """
        if not self.fill_events:
            return 0.0
        total_bps = 0.0
        count = 0
        for ev in self.fill_events:
            mid = ev.get("price", starting_price)
            if mid > 0 and ev["offer_price"] > 0:
                bps = abs(ev["offer_price"] - mid) / mid * 10_000.0
                total_bps += bps
                count += 1
        return total_bps / count if count > 0 else 0.0

    def _calc_max_drawdown(
        self, pnl_series: List[float], starting_portfolio: float
    ) -> float:
        """Compute peak-to-trough portfolio drawdown as a percentage.

        Args:
            pnl_series: Cumulative P&L at each tick (XCH).
            starting_portfolio: Starting portfolio value in XCH.

        Returns:
            Maximum drawdown percentage (positive number).
        """
        if not pnl_series or starting_portfolio <= 0:
            return 0.0
        portfolio = [starting_portfolio + p for p in pnl_series]
        peak = portfolio[0]
        max_dd = 0.0
        for val in portfolio:
            if val > peak:
                peak = val
            if peak > 0:
                dd = (peak - val) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    def _calc_max_net_position(
        self, starting_cat: float, cat_series: List[float]
    ) -> float:
        """Return the peak absolute deviation in CAT balance from starting value.

        Args:
            starting_cat: Starting CAT balance.
            cat_series: CAT balance at each tick.

        Returns:
            Maximum absolute CAT position delta.
        """
        if not cat_series:
            return 0.0
        return max(abs(c - starting_cat) for c in cat_series)

    def _empty_result(self) -> SimResult:
        """Return a zero-filled SimResult when no ticks were recorded."""
        s = self._scenario
        return SimResult(
            scenario_name=s.name,
            n_ticks=0,
            duration_virtual_hours=0.0,
            starting_xch=s.starting_xch,
            starting_cat=s.starting_cat,
            ending_xch=s.starting_xch,
            ending_cat=s.starting_cat,
            starting_portfolio_xch=0.0,
            ending_portfolio_xch=0.0,
            pnl_xch=0.0,
            pnl_pct=0.0,
            total_fills=0,
            buy_fills=0,
            sell_fills=0,
            total_offers_created=0,
            total_offers_cancelled=0,
            fill_rate_per_hour=0.0,
            avg_spread_captured_bps=0.0,
            avg_capital_deployed_pct=0.0,
            dead_ticks=0,
            dead_pct=0.0,
            max_drawdown_pct=0.0,
            max_net_position_cat=0.0,
            cb_trips=0,
            cb_ticks=0,
            coin_splits_needed=0,
            issues=["No ticks recorded."],
            price_series=[],
            pnl_series=[],
            balance_xch_series=[],
            balance_cat_series=[],
        )


# ---------------------------------------------------------------------------
# detect_issues
# ---------------------------------------------------------------------------

def detect_issues(result: SimResult, scenario: "Scenario") -> List[str]:
    """Analyse a SimResult and produce plain-English findings.

    Each finding describes a potential problem and maps to a concrete
    bot fix.  The list is empty when everything looks healthy.

    Args:
        result: The completed SimResult.
        scenario: The Scenario that produced the result.

    Returns:
        List of plain-English issue strings.
    """
    issues: List[str] = []
    n = result.n_ticks

    # 1. Dead ticks — bot has no offers posted
    if result.dead_pct > 20.0:
        issues.append(
            f"Bot spent {result.dead_pct:.0f}% of time with no active offers"
            " — requote cooldown or coin shortage"
        )

    # 2. CB dominated runtime
    if result.cb_trips > 0 and n > 0:
        cb_pct = result.cb_ticks / n * 100.0
        if cb_pct > 30.0:
            issues.append(
                f"Circuit breaker occupied {cb_pct:.0f}% of runtime"
                " — position limit may be too tight for this market"
            )

    # 3. Heavily one-sided fills (CAT accumulation risk)
    if result.total_fills > 0:
        buy_pct = result.buy_fills / result.total_fills * 100.0
        sell_pct = result.sell_fills / result.total_fills * 100.0
        if buy_pct > 80.0:
            issues.append(
                f"Heavily one-sided fills ({buy_pct:.0f}% buys)"
                " — CAT accumulation risk. Consider tighter sell spread"
                " or higher max position"
            )
        elif sell_pct > 80.0:
            issues.append(
                f"Heavily one-sided fills ({sell_pct:.0f}% sells)"
                " — XCH accumulation risk. Consider tighter buy spread"
                " or higher max position"
            )

    # 4. Low spread capture vs posted spread
    if result.avg_spread_captured_bps > 0:
        capture_ratio = result.avg_spread_captured_bps / scenario.spread_bps
        if capture_ratio < 0.3:
            issues.append(
                f"Capturing only {result.avg_spread_captured_bps:.0f} bps"
                f" of {scenario.spread_bps:.0f} bps spread"
                " — offers being requoted before fills"
            )

    # 5. Frequent coin splits
    if n > 0 and result.coin_splits_needed > n * 0.1:
        issues.append(
            f"Coin prep triggered {result.coin_splits_needed} times"
            " — increase fee pool or coin prep multiplier"
        )

    # 6. Large drawdown
    if result.max_drawdown_pct > 15.0:
        tag_str = ", ".join(scenario.tags) if scenario.tags else "this scenario"
        issues.append(
            f"Max drawdown {result.max_drawdown_pct:.1f}%"
            f" — position limits or spread may need widening for {tag_str}"
        )

    # 7. CAT nearly exhausted
    if result.ending_cat < scenario.starting_cat * 0.1 and scenario.starting_cat > 0:
        issues.append(
            "CAT nearly exhausted"
            " — consider CAT reserve or reducing sell depth"
        )

    # 8. XCH nearly exhausted
    if result.ending_xch < scenario.starting_xch * 0.1 and scenario.starting_xch > 0:
        issues.append(
            "XCH nearly exhausted"
            " — consider XCH reserve or reducing buy depth"
        )

    # 9. Suspiciously high fill rate
    if result.fill_rate_per_hour > 100.0:
        issues.append(
            f"Extremely high fill rate {result.fill_rate_per_hour:.0f}/hr"
            " — possible config issue with spread too tight"
        )

    # 10. Low capital deployment
    if result.avg_capital_deployed_pct < 40.0:
        issues.append(
            f"Low capital deployment {result.avg_capital_deployed_pct:.0f}%"
            " — tier counts may be too low for available capital"
        )

    # 11. Profitable outcome (positive finding)
    if result.pnl_pct > 0.0:
        issues.append(
            f"Profitable scenario: +{result.pnl_pct:.2f}%"
            f" over {result.duration_virtual_hours:.1f} virtual hours"
        )

    # 12. Loss scenario
    if result.pnl_pct < -5.0:
        issues.append(
            f"Losing scenario: {result.pnl_pct:.2f}%"
            " — investigate fill asymmetry or spread vs volatility"
        )

    return issues
