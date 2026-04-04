"""
Predefined simulation scenarios covering every market condition and wallet size.

Each Scenario fully specifies starting capital, market model, bot config,
and what outcome to measure. Run any single scenario or the full batch.

The Scenario class here is richer than engine.Scenario — it carries market
model references, expected-outcome flags, and human-readable tags that the
runner uses to wire up a SimBot and the metrics layer uses to contextualise
issues.  The runner converts a Scenario into an engine.Scenario before
passing it to SimBot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Union

from simulation.market import (
    PRESET_MODELS,
    CompositeModel,
    PriceModel,
    RegimeSwitching,
    SuddenCrash,
    SuddenPump,
    TrendedWalk,
)


# ---------------------------------------------------------------------------
# Scenario dataclass
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """Configuration for one simulation run.

    Carries everything the runner needs: capital, market model, bot config
    overrides, and expected-outcome flags for issue detection.
    """

    name: str
    description: str

    # --- Capital ---
    starting_xch: float
    starting_cat: float

    # --- Market ---
    price_model: Union[str, PriceModel]
    """Either a key into PRESET_MODELS (str) or a PriceModel instance."""
    starting_price: float
    n_ticks: int
    loop_seconds: int = 60
    """Virtual seconds per tick (used when converting ticks to hours)."""

    # --- Bot config overrides ---
    spread_bps: float = 500.0
    requote_bps: float = 200.0
    max_position_xch: float = 5.0

    # --- Tier config ---
    tier_enabled: bool = True
    n_inner: int = 2
    n_mid: int = 2
    n_outer: int = 1
    n_extreme: int = 1
    inner_mult: float = 2.0
    mid_mult: float = 1.0
    outer_mult: float = 0.45
    extreme_mult: float = 0.15
    base_size_xch: float = 0.1

    # --- Pool depth ---
    pool_depth_xch: float = 200.0

    # --- Expected outcomes ---
    tags: List[str] = field(default_factory=list)
    expect_cb_trips: bool = False
    expect_cat_drain: bool = False
    expect_xch_drain: bool = False

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    def get_price_model(self) -> PriceModel:
        """Resolve price_model to a PriceModel instance."""
        if isinstance(self.price_model, str):
            return PRESET_MODELS[self.price_model]
        return self.price_model

    def inner_size_xch(self) -> float:
        """XCH per inner-tier offer."""
        return self.base_size_xch * self.inner_mult

    def mid_size_xch(self) -> float:
        """XCH per mid-tier offer."""
        return self.base_size_xch * self.mid_mult

    def outer_size_xch(self) -> float:
        """XCH per outer-tier offer."""
        return self.base_size_xch * self.outer_mult

    def extreme_size_xch(self) -> float:
        """XCH per extreme-tier offer."""
        return self.base_size_xch * self.extreme_mult


# ---------------------------------------------------------------------------
# Helper — build composite up-then-down model
# ---------------------------------------------------------------------------

def _up_then_down(up_ticks: int, down_ticks: int) -> CompositeModel:
    """Build an uptrend-then-downtrend composite model."""
    return CompositeModel([
        (TrendedWalk(drift_pct_per_tick=0.002, volatility_pct_per_tick=0.004), up_ticks),
        (TrendedWalk(drift_pct_per_tick=-0.002, volatility_pct_per_tick=0.004), down_ticks),
    ])


def _high_freq_regime() -> RegimeSwitching:
    """Regime-switching model with short regime windows (stress test)."""
    return RegimeSwitching(low_vol=0.003, high_vol=0.020, regime_length_ticks=20)


# ---------------------------------------------------------------------------
# All scenario definitions
# ---------------------------------------------------------------------------

ALL_SCENARIOS: List[Scenario] = [

    # -----------------------------------------------------------------------
    # Micro wallet (1 XCH / 500 CAT)
    # -----------------------------------------------------------------------

    Scenario(
        name="micro_quiet",
        description="Micro wallet in a dead market — tests stagnation handling.",
        starting_xch=1.0,
        starting_cat=500.0,
        price_model="dead",
        starting_price=0.001,
        n_ticks=200,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=0.5,
        base_size_xch=0.05,
        tags=["micro", "quiet"],
    ),

    Scenario(
        name="micro_active",
        description="Micro wallet in a normal random-walk market.",
        starting_xch=1.0,
        starting_cat=500.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=200,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=0.5,
        base_size_xch=0.05,
        tags=["micro", "active"],
    ),

    Scenario(
        name="micro_crash",
        description="Micro wallet hit by a 40% crash — tests CB and CAT drain.",
        starting_xch=1.0,
        starting_cat=500.0,
        price_model="crash",
        starting_price=0.001,
        n_ticks=200,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=0.5,
        base_size_xch=0.05,
        tags=["micro", "crash"],
        expect_cb_trips=True,
    ),

    # -----------------------------------------------------------------------
    # Small wallet (5 XCH / 2000 CAT)
    # -----------------------------------------------------------------------

    Scenario(
        name="small_quiet",
        description="Small wallet in a dead market.",
        starting_xch=5.0,
        starting_cat=2000.0,
        price_model="dead",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=2.0,
        base_size_xch=0.1,
        tags=["small", "quiet"],
    ),

    Scenario(
        name="small_active",
        description="Small wallet in a normal random-walk market.",
        starting_xch=5.0,
        starting_cat=2000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=2.0,
        base_size_xch=0.1,
        tags=["small", "active"],
    ),

    Scenario(
        name="small_volatile",
        description="Small wallet under regime-switching volatility.",
        starting_xch=5.0,
        starting_cat=2000.0,
        price_model="regime_switching",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=2.0,
        base_size_xch=0.1,
        tags=["small", "volatile"],
    ),

    Scenario(
        name="small_trend_up",
        description="Small wallet in a sustained uptrend.",
        starting_xch=5.0,
        starting_cat=2000.0,
        price_model="uptrend",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=2.0,
        base_size_xch=0.1,
        tags=["small", "trend"],
    ),

    Scenario(
        name="small_trend_down",
        description="Small wallet in a sustained downtrend.",
        starting_xch=5.0,
        starting_cat=2000.0,
        price_model="downtrend",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=2.0,
        base_size_xch=0.1,
        tags=["small", "trend"],
        expect_cb_trips=True,
    ),

    # -----------------------------------------------------------------------
    # Medium wallet (20 XCH / 8000 CAT)
    # -----------------------------------------------------------------------

    Scenario(
        name="medium_quiet",
        description="Medium wallet in a dead market.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model="dead",
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["medium", "quiet"],
    ),

    Scenario(
        name="medium_active",
        description="Medium wallet in a normal random-walk market.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["medium", "active"],
    ),

    Scenario(
        name="medium_volatile",
        description="Medium wallet under regime-switching volatility.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model="regime_switching",
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["medium", "volatile"],
    ),

    Scenario(
        name="medium_pump_dump",
        description="Medium wallet hit by a pump-and-dump event.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model="pump_and_dump",
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["medium", "pump_dump"],
        expect_cb_trips=True,
        expect_cat_drain=True,
    ),

    # -----------------------------------------------------------------------
    # Large wallet (100 XCH / 40000 CAT)
    # -----------------------------------------------------------------------

    Scenario(
        name="large_active",
        description="Large wallet in a normal random-walk market.",
        starting_xch=100.0,
        starting_cat=40000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=20.0,
        base_size_xch=0.5,
        pool_depth_xch=200.0,
        tags=["large", "active"],
    ),

    Scenario(
        name="large_volatile",
        description="Large wallet under regime-switching volatility.",
        starting_xch=100.0,
        starting_cat=40000.0,
        price_model="regime_switching",
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=20.0,
        base_size_xch=0.5,
        pool_depth_xch=200.0,
        tags=["large", "volatile"],
    ),

    Scenario(
        name="large_shallow_pool",
        description="Large wallet in a random-walk market with a shallow pool (80 XCH depth).",
        starting_xch=100.0,
        starting_cat=40000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=20.0,
        base_size_xch=0.5,
        pool_depth_xch=80.0,
        tags=["large", "shallow_pool"],
    ),

    # -----------------------------------------------------------------------
    # Whale wallet (500 XCH / 200000 CAT)
    # -----------------------------------------------------------------------

    Scenario(
        name="whale_active",
        description="Whale wallet in a normal market — tests capital deployment efficiency.",
        starting_xch=500.0,
        starting_cat=200000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=50.0,
        base_size_xch=1.0,
        pool_depth_xch=200.0,
        tags=["whale", "active"],
    ),

    Scenario(
        name="whale_pool_dominated",
        description="Whale wallet larger than the pool — tests position-limit behaviour.",
        starting_xch=500.0,
        starting_cat=200000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=50.0,
        base_size_xch=1.0,
        pool_depth_xch=100.0,
        tags=["whale", "pool_dominated"],
        expect_cb_trips=True,
    ),

    # -----------------------------------------------------------------------
    # Edge cases
    # -----------------------------------------------------------------------

    Scenario(
        name="cat_drain",
        description="Severely CAT-limited wallet — should exhaust CAT supply quickly.",
        starting_xch=10.0,
        starting_cat=100.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=200,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.1,
        tags=["edge_case", "cat_drain"],
        expect_cat_drain=True,
    ),

    Scenario(
        name="xch_drain",
        description="Severely XCH-limited wallet — tests XCH exhaustion path.",
        starting_xch=0.5,
        starting_cat=5000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=200,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=0.3,
        base_size_xch=0.02,
        tags=["edge_case", "xch_drain"],
        expect_xch_drain=True,
    ),

    Scenario(
        name="extreme_crash_recovery",
        description="50% crash followed by a slow recovery over 600 ticks.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model=CompositeModel([
            (TrendedWalk(drift_pct_per_tick=0.0, volatility_pct_per_tick=0.004), 150),
            (SuddenCrash(
                crash_tick_fraction=0.0,
                crash_pct=0.50,
                crash_duration=10,
                recovery_pct_per_tick=0.003,
                pre_volatility=0.004,
            ), 450),
        ]),
        starting_price=0.001,
        n_ticks=600,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["edge_case", "crash", "recovery"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="extreme_pump",
        description="80% pump over 400 ticks — tests sell-side CB and CAT accumulation.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model=SuddenPump(
            pump_tick_fraction=0.2,
            pump_pct=0.80,
            pump_duration=8,
            decay_pct_per_tick=0.001,
            pre_volatility=0.004,
        ),
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["edge_case", "pump"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="extreme_pump_dump",
        description="Full pump-and-dump cycle over 600 ticks.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model="pump_and_dump",
        starting_price=0.001,
        n_ticks=600,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["edge_case", "pump_dump"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="liquidity_crisis",
        description="Volatility spike (liquidity crisis) mid-run — tests CB recovery.",
        starting_xch=20.0,
        starting_cat=8000.0,
        price_model="liquidity_crisis",
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.2,
        tags=["edge_case", "liquidity_crisis"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="tight_spread",
        description="100 bps spread — tests fill rate and P&L under thin margin.",
        starting_xch=10.0,
        starting_cat=4000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=100,
        requote_bps=50,
        max_position_xch=5.0,
        base_size_xch=0.1,
        tags=["edge_case", "tight_spread"],
    ),

    Scenario(
        name="wide_spread",
        description="2000 bps spread — tests whether offers fill at all.",
        starting_xch=10.0,
        starting_cat=4000.0,
        price_model="random_walk",
        starting_price=0.001,
        n_ticks=300,
        spread_bps=2000,
        requote_bps=800,
        max_position_xch=5.0,
        base_size_xch=0.1,
        tags=["edge_case", "wide_spread"],
    ),

    Scenario(
        name="stepped_price",
        description="Stepped/illiquid price model — tests fill logic on discrete jumps.",
        starting_xch=10.0,
        starting_cat=4000.0,
        price_model="stepped",
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.1,
        tags=["edge_case", "stepped"],
    ),

    # -----------------------------------------------------------------------
    # Stress tests
    # -----------------------------------------------------------------------

    Scenario(
        name="stress_high_vol_small",
        description="Small wallet under high-frequency regime switching for 1000 ticks.",
        starting_xch=2.0,
        starting_cat=1000.0,
        price_model=_high_freq_regime(),
        starting_price=0.001,
        n_ticks=1000,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=1.0,
        base_size_xch=0.05,
        tags=["stress", "high_vol", "small"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="stress_high_vol_large",
        description="Large wallet under high-frequency regime switching for 1000 ticks.",
        starting_xch=50.0,
        starting_cat=20000.0,
        price_model=_high_freq_regime(),
        starting_price=0.001,
        n_ticks=1000,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=15.0,
        base_size_xch=0.3,
        tags=["stress", "high_vol", "large"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="stress_sustained_trend",
        description="200-tick uptrend then 300-tick downtrend — full directional stress.",
        starting_xch=10.0,
        starting_cat=4000.0,
        price_model=_up_then_down(200, 300),
        starting_price=0.001,
        n_ticks=500,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=5.0,
        base_size_xch=0.1,
        tags=["stress", "trend"],
        expect_cb_trips=True,
    ),

    Scenario(
        name="stress_position_limit",
        description="Tight CB (1 XCH max position) against a strong downtrend.",
        starting_xch=10.0,
        starting_cat=4000.0,
        price_model="downtrend",
        starting_price=0.001,
        n_ticks=400,
        spread_bps=500,
        requote_bps=200,
        max_position_xch=1.0,
        base_size_xch=0.1,
        tags=["stress", "position_limit"],
        expect_cb_trips=True,
    ),
]


# ---------------------------------------------------------------------------
# Lookup map
# ---------------------------------------------------------------------------

SCENARIO_MAP: Dict[str, Scenario] = {s.name: s for s in ALL_SCENARIOS}
