"""
Batch scenario runner.

Runs single or multiple scenarios, collects results, detects patterns
across runs. Can also replay real bot logs for issue reproduction.
"""

from __future__ import annotations

import traceback
from typing import Callable, Dict, List, Optional

from simulation.engine import Scenario as EngineScenario, SimBot
from simulation.metrics import MetricsCollector, SimResult
from simulation.scenarios import Scenario


# ---------------------------------------------------------------------------
# Scenario → EngineScenario bridge
# ---------------------------------------------------------------------------

def _to_engine_scenario(scenario: Scenario) -> EngineScenario:
    """Convert a simulation Scenario to an engine.Scenario for SimBot.

    Maps the richer Scenario fields onto the engine's flat config.  Tier
    sizes are computed from base_size_xch * multiplier so callers only need
    to set base_size_xch and multipliers.

    Args:
        scenario: The Scenario from scenarios.py.

    Returns:
        engine.Scenario ready to be passed to SimBot.__init__.
    """
    return EngineScenario(
        name=scenario.name,
        spread_bps=scenario.spread_bps,
        requote_bps=scenario.requote_bps,
        n_inner=scenario.n_inner if scenario.tier_enabled else 0,
        n_mid=scenario.n_mid if scenario.tier_enabled else 0,
        n_outer=scenario.n_outer if scenario.tier_enabled else 0,
        n_extreme=scenario.n_extreme if scenario.tier_enabled else 0,
        inner_size_xch=scenario.inner_size_xch(),
        mid_size_xch=scenario.mid_size_xch(),
        outer_size_xch=scenario.outer_size_xch(),
        extreme_size_xch=scenario.extreme_size_xch(),
        starting_xch=scenario.starting_xch,
        starting_cat=scenario.starting_cat,
        max_position_xch=scenario.max_position_xch,
    )


# ---------------------------------------------------------------------------
# Single scenario run
# ---------------------------------------------------------------------------

def run_scenario(scenario: Scenario, verbose: bool = False) -> SimResult:
    """Run a single scenario and return its SimResult.

    Steps:
      1. Resolve the price series from scenario.price_model.
      2. Build a SimBot using the converted engine.Scenario.
      3. Tick through all prices, recording each result.
      4. Return the aggregated SimResult.

    Args:
        scenario: The Scenario to run.
        verbose: If True, print a one-line progress indicator.

    Returns:
        SimResult with all metrics and issues populated.
    """
    if verbose:
        print(f"  Running: {scenario.name} ({scenario.n_ticks} ticks) ...", end="", flush=True)

    # 1. Generate price series
    price_model = scenario.get_price_model()
    prices = price_model.generate(scenario.n_ticks, scenario.starting_price)

    # 2. Build bot
    engine_scenario = _to_engine_scenario(scenario)
    bot = SimBot(engine_scenario)

    # 3. Collect metrics
    collector = MetricsCollector(scenario)

    for price in prices:
        tick_result = bot.tick(price)
        collector.record(tick_result, bot.get_state())

    # 4. Summarise
    result = collector.summary()

    if verbose:
        sign = "+" if result.pnl_pct >= 0 else ""
        print(f" {sign}{result.pnl_pct:.2f}% PnL, {result.total_fills} fills, "
              f"{len(result.issues)} issue(s)")

    return result


# ---------------------------------------------------------------------------
# Batch run
# ---------------------------------------------------------------------------

def run_batch(
    scenarios: List[Scenario],
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stop_on_error: bool = False,
) -> List[SimResult]:
    """Run all scenarios in sequence and return their results.

    Args:
        scenarios: List of Scenario objects to run.
        on_progress: Optional callback called as on_progress(done, total, name)
            after each scenario completes (or fails).
        stop_on_error: If True, re-raise the first exception encountered.
            If False (default), record an error result and continue.

    Returns:
        List of SimResult objects, one per scenario (same order as input).
        Failed scenarios produce a SimResult with a single error issue.
    """
    results: List[SimResult] = []
    total = len(scenarios)

    for i, scenario in enumerate(scenarios):
        try:
            result = run_scenario(scenario)
        except Exception as exc:  # noqa: BLE001
            if stop_on_error:
                raise
            # Build a minimal error result so the batch continues
            tb = traceback.format_exc()
            result = _error_result(scenario, str(exc), tb)

        results.append(result)

        if on_progress is not None:
            on_progress(i + 1, total, scenario.name)

    return results


# ---------------------------------------------------------------------------
# Run all predefined scenarios
# ---------------------------------------------------------------------------

def run_all(verbose: bool = False) -> List[SimResult]:
    """Run every predefined scenario from scenarios.ALL_SCENARIOS.

    Args:
        verbose: If True, print progress to stdout.

    Returns:
        List of SimResult, one per scenario.
    """
    from simulation.scenarios import ALL_SCENARIOS

    if verbose:
        print(f"Running {len(ALL_SCENARIOS)} scenarios ...\n")

    def _progress(done: int, total: int, name: str) -> None:
        if verbose:
            pct = done / total * 100
            print(f"  [{done}/{total} {pct:.0f}%] Completed: {name}")

    results = run_batch(ALL_SCENARIOS, on_progress=_progress if verbose else None)

    if verbose:
        print(f"\nDone. {len(results)} results collected.")

    return results


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def find_worst_scenarios(
    results: List[SimResult],
    metric: str = "pnl_pct",
    n: int = 5,
) -> List[SimResult]:
    """Return the N worst-performing scenarios by metric.

    For most metrics (pnl_pct, max_drawdown_pct) lower is worse.
    For 'max_drawdown_pct' the sign is already positive, so the highest
    values are the worst.

    Args:
        results: List of SimResult to rank.
        metric: Attribute name on SimResult to sort by.
        n: Number of worst results to return.

    Returns:
        Up to N SimResult objects, worst first.
    """
    reverse = metric in ("max_drawdown_pct", "cb_trips", "dead_pct", "coin_splits_needed")
    key_fn = lambda r: getattr(r, metric, 0.0)  # noqa: E731
    sorted_results = sorted(results, key=key_fn, reverse=reverse)
    return sorted_results[:n]


def find_best_scenarios(
    results: List[SimResult],
    metric: str = "pnl_pct",
    n: int = 5,
) -> List[SimResult]:
    """Return the N best-performing scenarios by metric.

    Args:
        results: List of SimResult to rank.
        metric: Attribute name on SimResult to sort by.
        n: Number of best results to return.

    Returns:
        Up to N SimResult objects, best first.
    """
    reverse = metric not in ("max_drawdown_pct", "cb_trips", "dead_pct", "coin_splits_needed")
    key_fn = lambda r: getattr(r, metric, 0.0)  # noqa: E731
    sorted_results = sorted(results, key=key_fn, reverse=reverse)
    return sorted_results[:n]


def aggregate_issues(results: List[SimResult]) -> Dict[str, dict]:
    """Collect all issues across runs and count their frequency.

    Issues are grouped by the first sentence (up to the first ' — ') so
    variations of the same root problem cluster together.

    Args:
        results: List of SimResult from one or more batch runs.

    Returns:
        Dict mapping issue_pattern -> {"count": int, "scenarios": List[str]}.
        Sorted by count descending.
    """
    aggregated: Dict[str, dict] = {}

    for result in results:
        for issue in result.issues:
            # Extract the category prefix (before the em-dash fix hint)
            parts = issue.split(" — ", 1)
            pattern = parts[0].strip()

            if pattern not in aggregated:
                aggregated[pattern] = {"count": 0, "scenarios": []}
            aggregated[pattern]["count"] += 1
            aggregated[pattern]["scenarios"].append(result.scenario_name)

    # Sort by frequency
    return dict(
        sorted(aggregated.items(), key=lambda kv: kv[1]["count"], reverse=True)
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _error_result(scenario: Scenario, error_msg: str, traceback_str: str) -> SimResult:
    """Build a minimal SimResult to represent a failed scenario run.

    Args:
        scenario: The scenario that failed.
        error_msg: Short error description.
        traceback_str: Full traceback string.

    Returns:
        SimResult with zero metrics and a single error issue.
    """
    return SimResult(
        scenario_name=scenario.name,
        n_ticks=0,
        duration_virtual_hours=0.0,
        starting_xch=scenario.starting_xch,
        starting_cat=scenario.starting_cat,
        ending_xch=scenario.starting_xch,
        ending_cat=scenario.starting_cat,
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
        issues=[f"SCENARIO FAILED: {error_msg}"],
        price_series=[],
        pnl_series=[],
        balance_xch_series=[],
        balance_cat_series=[],
    )
