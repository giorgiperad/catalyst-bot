"""
Parametric test matrix — generates 5,600 Scenario combinations.

Cross-product of:
  capital_xch : [0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]  — 8 values
  spread_bps  : [250, 500, 750, 1000, 1500]                        — 5 values
  regime      : ["quiet","moderate","active","volatile","extreme"]  — 5 values
  pattern     : ["random_walk","trend_up","trend_down","mean_revert",
                 "pump_dump","crash","stepped"]                     — 7 values
  tiers       : [1, 2, 3, 4]                                        — 4 values

Total = 8 × 5 × 5 × 7 × 4 = 5,600

Usage::

    from simulation.test_matrix import generate_matrix, generate_subset, generate_quick

    all_5600 = generate_matrix()
    subset   = generate_subset(n=500, seed=42)
    quick    = generate_quick(n=50)
    names    = get_test_names()
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

from simulation.engine import Scenario as EngineScenario
from simulation.market import (
    PRESET_MODELS,
    DeadMarket,
    LiquidityCrisis,
    MeanReverting,
    PriceModel,
    PumpAndDump,
    RandomWalk,
    RegimeSwitching,
    SteppedPrice,
    SuddenCrash,
    SuddenPump,
    TrendedWalk,
)


# ---------------------------------------------------------------------------
# Parameter axes
# ---------------------------------------------------------------------------

CAPITAL_VALUES: List[float] = [0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]

SPREAD_VALUES: List[int] = [250, 500, 750, 1000, 1500]

REGIMES: List[str] = ["quiet", "moderate", "active", "volatile", "extreme"]

PATTERNS: List[str] = [
    "random_walk",
    "trend_up",
    "trend_down",
    "mean_revert",
    "pump_dump",
    "crash",
    "stepped",
]

TIER_COUNTS: List[int] = [1, 2, 3, 4]

# Total = 8 * 5 * 5 * 7 * 4 = 5,600


# ---------------------------------------------------------------------------
# Helpers — map axes → Scenario fields
# ---------------------------------------------------------------------------

def _make_price_model(pattern: str, regime: str) -> PriceModel:
    """Return a PriceModel for the given pattern/regime combination.

    Regime modifies the volatility level; pattern determines the shape.

    Args:
        pattern: One of PATTERNS.
        regime: One of REGIMES.

    Returns:
        A PriceModel instance suitable for use in a Scenario.
    """
    # Volatility per tick mapped from regime
    vol_map = {
        "quiet": 0.002,
        "moderate": 0.005,
        "active": 0.010,
        "volatile": 0.020,
        "extreme": 0.040,
    }
    vol = vol_map.get(regime, 0.005)

    if pattern == "random_walk":
        return RandomWalk(volatility_pct_per_tick=vol)

    elif pattern == "trend_up":
        drift = vol * 0.3  # positive drift ~30% of vol
        return TrendedWalk(drift_pct_per_tick=drift, volatility_pct_per_tick=vol)

    elif pattern == "trend_down":
        drift = -vol * 0.3
        return TrendedWalk(drift_pct_per_tick=drift, volatility_pct_per_tick=vol)

    elif pattern == "mean_revert":
        speed = 0.03 if regime in ("quiet", "moderate") else 0.08
        return MeanReverting(reversion_speed=speed, volatility=vol)

    elif pattern == "pump_dump":
        return PumpAndDump(
            pump_pct=0.60 + (vol * 5.0),    # bigger pump at high vol
            dump_pct=0.55 + (vol * 4.0),
            pre_volatility=vol,
        )

    elif pattern == "crash":
        return SuddenCrash(
            crash_pct=0.30 + (vol * 3.0),   # bigger crash at high vol
            pre_volatility=vol,
        )

    elif pattern == "stepped":
        step = max(0.005, vol * 1.0)
        ticks = max(3, int(10 / (vol * 100 + 1)))
        return SteppedPrice(step_size_pct=step, ticks_per_step=ticks)

    # Fallback
    return RandomWalk(volatility_pct_per_tick=vol)


def _make_tier_config(tiers: int, capital: float) -> dict:
    """Return tier count and size fields for an EngineScenario.

    With more tiers active we spread capital thinner.
    With less capital each offer is smaller.

    Args:
        tiers: Number of tier levels to activate (1–4).
        capital: Starting XCH capital.

    Returns:
        Dict of keyword arguments for EngineScenario tier fields.
    """
    # Size each offer at a fraction of capital so the bot doesn't instantly
    # exhaust its wallet even at micro scale.
    base_size = max(0.005, min(capital * 0.04, 2.0))

    # Tier multipliers: inner is biggest, extreme is smallest
    inner_mult = 2.0
    mid_mult   = 1.0
    outer_mult = 0.45
    xtr_mult   = 0.15

    # Activate tiers progressively: 1 tier = inner only
    n_inner  = 2 if tiers >= 1 else 0
    n_mid    = 2 if tiers >= 2 else 0
    n_outer  = 1 if tiers >= 3 else 0
    n_extreme = 1 if tiers >= 4 else 0

    return {
        "n_inner":          n_inner,
        "n_mid":            n_mid,
        "n_outer":          n_outer,
        "n_extreme":        n_extreme,
        "inner_size_xch":   round(base_size * inner_mult, 6),
        "mid_size_xch":     round(base_size * mid_mult, 6),
        "outer_size_xch":   round(base_size * outer_mult, 6),
        "extreme_size_xch": round(base_size * xtr_mult, 6),
    }


def _make_wallet_config(capital: float, spread_bps: int) -> dict:
    """Derive wallet sizing from capital.

    CAT reserve is sized so we have roughly balanced starting inventory.
    We assume a price of 0.001 XCH per CAT throughout (like all scenarios).

    Args:
        capital: Starting XCH amount.
        spread_bps: Spread in basis points (affects reserve sizing).

    Returns:
        Dict of wallet fields for EngineScenario.
    """
    starting_price = 0.001
    # Aim for 1:1 value split between XCH and CAT at starting price
    starting_cat = capital / starting_price * 0.5   # half inventory in CAT

    # Coin sizes scale with capital — avoid creating thousands of tiny coins
    xch_coin_size  = max(0.01, min(capital * 0.05, 1.0))
    cat_coin_size  = max(5.0, min(starting_cat * 0.05, 500.0))

    # Reserve: minimum 0.01 XCH or 0.5% of capital, whichever is larger
    xch_reserve = max(0.01, capital * 0.005)
    # Cap reserve at 20% of capital so micro wallets can still trade
    xch_reserve = min(xch_reserve, capital * 0.20)

    return {
        "starting_xch":         capital,
        "starting_cat":         round(starting_cat, 2),
        "xch_coin_size":        round(xch_coin_size, 4),
        "cat_coin_size_tokens": round(cat_coin_size, 2),
        "xch_reserve":          round(xch_reserve, 4),
        "cat_reserve":          0.0,
    }


def _make_position_limit(capital: float) -> float:
    """Set max_position_xch as 50% of capital (symmetric around mid).

    Args:
        capital: Starting XCH.

    Returns:
        max_position_xch value.
    """
    return max(0.05, capital * 0.50)


def _requote_bps(spread_bps: int) -> float:
    """Derive a sensible requote threshold from spread.

    Set to ~60% of spread so stale offers are repriced well before the
    spread fully collapses.

    Args:
        spread_bps: Spread in basis points.

    Returns:
        requote_bps value.
    """
    return max(50.0, spread_bps * 0.60)


def _make_test_name(capital: float, spread: int, regime: str, pattern: str, tiers: int) -> str:
    """Format a canonical test name for one matrix cell.

    Args:
        capital: XCH capital.
        spread: Spread in bps.
        regime: Market regime string.
        pattern: Price pattern string.
        tiers: Number of tier levels.

    Returns:
        String like "matrix_cap0.05_sp250_reg_quiet_pat_random_walk_t1".
    """
    cap_str = f"{capital:g}"
    return f"matrix_cap{cap_str}_sp{spread}_reg_{regime}_pat_{pattern}_t{tiers}"


# ---------------------------------------------------------------------------
# MatrixScenario — Scenario wrapper used by the test matrix
# ---------------------------------------------------------------------------

@dataclass
class MatrixScenario:
    """One parametric test case from the matrix.

    Wraps engine.Scenario with metadata about what combination it represents.
    The runner can use engine_scenario() to get the EngineScenario for SimBot.
    """
    name:         str
    capital_xch:  float
    spread_bps:   int
    regime:       str
    pattern:      str
    tiers:        int
    price_model:  PriceModel
    _engine:      EngineScenario = field(repr=False)

    def engine_scenario(self) -> EngineScenario:
        """Return the EngineScenario ready for SimBot.

        Returns:
            engine.Scenario instance.
        """
        return self._engine

    def n_ticks(self) -> int:
        """Return a reasonable tick count for this scenario.

        Larger capital → more ticks (more offers to process).
        Extreme regimes → fewer ticks for speed.
        """
        base = 200
        if self.capital_xch >= 10.0:
            base = 300
        if self.regime == "extreme":
            base = int(base * 0.6)
        return base


# ---------------------------------------------------------------------------
# Matrix builder
# ---------------------------------------------------------------------------

def _build_one(
    capital: float,
    spread: int,
    regime: str,
    pattern: str,
    tiers: int,
) -> MatrixScenario:
    """Build a single MatrixScenario from the five axis values.

    Args:
        capital: Starting XCH.
        spread: Spread in basis points.
        regime: Market regime.
        pattern: Price pattern.
        tiers: Number of active tier levels.

    Returns:
        MatrixScenario with a fully populated EngineScenario.
    """
    name = _make_test_name(capital, spread, regime, pattern, tiers)
    price_model = _make_price_model(pattern, regime)
    wallet = _make_wallet_config(capital, spread)
    tier_cfg = _make_tier_config(tiers, capital)
    pos_limit = _make_position_limit(capital)
    requote = _requote_bps(spread)

    engine = EngineScenario(
        name=name,
        spread_bps=float(spread),
        requote_bps=requote,
        max_position_xch=pos_limit,
        **tier_cfg,
        **wallet,
    )

    return MatrixScenario(
        name=name,
        capital_xch=capital,
        spread_bps=spread,
        regime=regime,
        pattern=pattern,
        tiers=tiers,
        price_model=price_model,
        _engine=engine,
    )


def generate_matrix() -> List[MatrixScenario]:
    """Generate all 5,600 parametric scenarios.

    The order is deterministic: iterates capital × spread × regime × pattern × tiers.

    Returns:
        List of 5,600 MatrixScenario objects.
    """
    scenarios: List[MatrixScenario] = []
    for capital in CAPITAL_VALUES:
        for spread in SPREAD_VALUES:
            for regime in REGIMES:
                for pattern in PATTERNS:
                    for tiers in TIER_COUNTS:
                        scenarios.append(_build_one(capital, spread, regime, pattern, tiers))
    return scenarios


def generate_subset(n: int = 500, seed: int = 42) -> List[MatrixScenario]:
    """Return a reproducible random subset of the full 5,600-scenario matrix.

    Uses Python's built-in random with a fixed seed so results are stable
    across runs.

    Args:
        n: Number of scenarios to return.
        seed: Random seed for reproducibility.

    Returns:
        List of n MatrixScenario objects sampled without replacement.
    """
    rng = random.Random(seed)
    all_scenarios = generate_matrix()
    if n >= len(all_scenarios):
        return all_scenarios
    return rng.sample(all_scenarios, n)


def generate_quick(n: int = 50) -> List[MatrixScenario]:
    """Return the N most edge-covering tests from the matrix.

    Selection strategy:
    - Extreme capitals (0.05, 100.0) — both ends of the range
    - Extreme spreads (250, 1500)
    - All 5 regimes represented
    - All 7 patterns represented
    - All 4 tier counts represented
    - Fills remaining slots with the reproducible subset (seed=99)

    Args:
        n: Number of scenarios to return (default 50).

    Returns:
        List of MatrixScenario objects covering key edge cases.
    """
    seen: set = set()
    priority: List[MatrixScenario] = []

    def add(capital, spread, regime, pattern, tiers):
        key = (capital, spread, regime, pattern, tiers)
        if key not in seen:
            seen.add(key)
            priority.append(_build_one(capital, spread, regime, pattern, tiers))

    # Edge capitals × all regimes × key patterns × 1 tier
    for capital in [CAPITAL_VALUES[0], CAPITAL_VALUES[-1]]:  # 0.05, 100.0
        for regime in REGIMES:
            for pattern in ["crash", "pump_dump", "random_walk"]:
                add(capital, 500, regime, pattern, 1)

    # All spreads × medium capital × active regime × random_walk × 2 tiers
    for spread in SPREAD_VALUES:
        add(5.0, spread, "active", "random_walk", 2)

    # All patterns × medium capital × moderate regime × 500 bps × 3 tiers
    for pattern in PATTERNS:
        add(5.0, 500, "moderate", pattern, 3)

    # All tier counts × medium capital × volatile regime × crash × 1000 bps
    for tiers in TIER_COUNTS:
        add(10.0, 1000, "volatile", "crash", tiers)

    # Fill remaining with seed-stable random sample
    if len(priority) < n:
        filler = generate_subset(n=300, seed=99)
        for sc in filler:
            key = (sc.capital_xch, sc.spread_bps, sc.regime, sc.pattern, sc.tiers)
            if key not in seen:
                seen.add(key)
                priority.append(sc)
            if len(priority) >= n:
                break

    return priority[:n]


def get_test_names() -> List[str]:
    """Return the canonical name for every test in the full 5,600-scenario matrix.

    Names follow the pattern::

        matrix_cap{capital}_sp{spread}_reg_{regime}_pat_{pattern}_t{tiers}

    Returns:
        List of 5,600 test name strings.
    """
    names: List[str] = []
    for capital in CAPITAL_VALUES:
        for spread in SPREAD_VALUES:
            for regime in REGIMES:
                for pattern in PATTERNS:
                    for tiers in TIER_COUNTS:
                        names.append(_make_test_name(capital, spread, regime, pattern, tiers))
    return names


# ---------------------------------------------------------------------------
# Convenience: run a MatrixScenario through the engine
# ---------------------------------------------------------------------------

def run_matrix_scenario(ms: MatrixScenario) -> dict:
    """Run one MatrixScenario through the simulation engine and return metrics.

    Does not use simulation.runner (which expects scenarios.Scenario) —
    instead calls SimBot directly with the EngineScenario.

    Args:
        ms: MatrixScenario to run.

    Returns:
        Dict with keys: name, passed, pnl_xch, total_fills, final_xch,
        final_cat, cb_trips, n_ticks, fail_reason.
    """
    from simulation.engine import SimBot

    engine_sc = ms.engine_scenario()
    bot = SimBot(engine_sc)
    n_ticks = ms.n_ticks()

    prices = ms.price_model.generate(n_ticks, 0.001)

    cb_trips = 0
    was_tripped = False

    for price in prices:
        result = bot.tick(price)
        # Count CB trip edges (False → True transitions)
        if result.cb_tripped and not was_tripped:
            cb_trips += 1
        was_tripped = result.cb_tripped

    state = bot.get_state()
    pnl = state["pnl_xch"]
    starting_xch = engine_sc.starting_xch

    # Pass criteria:
    # 1. No Python exception (already past if we get here)
    # 2. P&L > -50% of starting capital
    max_loss = -0.5 * starting_xch
    passed = pnl >= max_loss

    fail_reason = ""
    if not passed:
        fail_reason = f"P&L {pnl:.6f} XCH < limit {max_loss:.6f} XCH"

    return {
        "name": ms.name,
        "passed": passed,
        "pnl_xch": pnl,
        "total_fills": state["total_fills"],
        "final_xch": state["xch_balance"],
        "final_cat": state["cat_balance"],
        "cb_trips": cb_trips,
        "n_ticks": n_ticks,
        "fail_reason": fail_reason,
    }
