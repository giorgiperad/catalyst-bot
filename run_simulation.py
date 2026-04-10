"""
Simulation Runner — Virtual Trading Environment

Runs the bot's market-making logic against synthetic or historical price data
without touching the real wallet, network, or database.

Usage:
    python run_simulation.py                          # Run all scenarios
    python run_simulation.py --scenario medium_active # Run one scenario
    python run_simulation.py --list                   # List all scenarios
    python run_simulation.py --replay bot.db          # Replay real bot database
    python run_simulation.py --replay export.json     # Replay JSON log export
    python run_simulation.py --quick                  # Run 5 key scenarios fast
    python run_simulation.py --stress                 # Run stress tests only
    python run_simulation.py --output results.csv     # Export results to CSV
    python run_simulation.py --scenario medium_active --detail  # Detailed output
    python run_simulation.py --mock                   # Fake run (no imports needed)
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Scenario registry — canonical list used by --list, --quick, --stress
# ---------------------------------------------------------------------------

# Each entry:  (name, description, tags)
ALL_SCENARIO_NAMES: List[Tuple[str, str, List[str]]] = [
    # Active trading, moderate size
    ("small_active",       "Small wallet, active market",            ["active"]),
    ("small_quiet",        "Small wallet, quiet market",             ["quiet"]),
    ("medium_active",      "Medium wallet, active market",           ["active"]),
    ("medium_quiet",       "Medium wallet, quiet market",            ["quiet"]),
    ("large_active",       "Large wallet, active market",            ["active"]),
    ("large_quiet",        "Large wallet, quiet market",             ["quiet"]),
    # Stress and edge cases
    ("medium_crash",       "Medium wallet, sudden 50% crash",        ["stress"]),
    ("large_volatile",     "Large wallet, high volatility",          ["stress"]),
    ("cat_drain",          "CAT balance drains to zero",             ["stress"]),
    ("xch_drain",          "XCH balance drains to zero",             ["stress"]),
    ("stress_position_limit", "Position limit hit repeatedly",       ["stress"]),
    ("stress_cb_storm",    "CB trips on every other tick",           ["stress"]),
    ("stress_requote",     "Requote threshold hammered by noise",     ["stress"]),
    # Price models
    ("trend_up",           "Steady upward trend",                    ["trend"]),
    ("trend_down",         "Steady downward trend",                  ["trend"]),
    ("mean_revert",        "Mean-reverting price process",           ["trend"]),
    ("flash_crash",        "Price drops 30% then recovers",         ["edge"]),
    ("pump_dump",          "Pump then dump pattern",                  ["edge"]),
    # Tight/wide spread variants
    ("tight_spread",       "Spread 200bps — very tight",             ["spread"]),
    ("wide_spread",        "Spread 2000bps — very wide",             ["spread"]),
    ("medium_tight",       "Medium wallet, 400bps spread",           ["spread"]),
    # Coin prep / wallet edge cases
    ("coin_starved",       "Wallet with very few coins",             ["wallet"]),
    ("coin_rich",          "Wallet with many small coins",           ["wallet"]),
    # Multi-tier
    ("inner_only",         "Only inner tier active",                 ["tier"]),
    ("outer_only",         "Only outer/extreme tiers active",        ["tier"]),
    ("full_ladder",        "All 4 tiers, large wallet",              ["tier"]),
    # Misc
    ("zero_cat",           "Start with no CAT balance",              ["edge"]),
    ("zero_xch",           "Start with no XCH balance",             ["edge"]),
    ("minimal",            "Smallest possible configuration",        ["edge"]),
    ("default",            "Default scenario from Scenario()",       ["basic"]),
]

# The 5 scenarios used for --quick
QUICK_SCENARIOS = [
    "small_active",
    "medium_crash",
    "large_volatile",
    "cat_drain",
    "stress_position_limit",
]

STRESS_TAGS = {"stress", "edge"}


# ---------------------------------------------------------------------------
# Scenario builder — constructs a Scenario from a name string
# ---------------------------------------------------------------------------

def _build_scenario(name: str, Scenario):
    """Construct a Scenario object from a preset name.

    This function encodes all the scenario-specific config decisions.
    Every scenario name in ALL_SCENARIO_NAMES must be handled here.

    Args:
        name: Scenario name string.
        Scenario: The Scenario class from simulation.engine.

    Returns:
        A populated Scenario instance.
    """
    # Base defaults — overridden below per scenario
    kw = dict(
        spread_bps=800.0,
        requote_bps=150.0,
        n_inner=3, n_mid=3, n_outer=2, n_extreme=1,
        inner_size_xch=1.0, mid_size_xch=0.5,
        outer_size_xch=0.25, extreme_size_xch=0.1,
        starting_xch=10.0, starting_cat=5000.0,
        xch_coin_size=0.5, cat_coin_size_tokens=500.0,
        xch_reserve=0.03, cat_reserve=0.0,
        max_position_xch=5.0,
        cat_decimals=3,
        name=name,
    )

    if name == "small_active":
        kw.update(starting_xch=2.0, starting_cat=1000.0,
                  n_inner=2, n_mid=2, inner_size_xch=0.3, mid_size_xch=0.2)
    elif name == "small_quiet":
        kw.update(starting_xch=2.0, starting_cat=1000.0,
                  n_inner=2, n_mid=2, spread_bps=1000.0)
    elif name == "medium_active":
        pass  # base defaults are medium-active
    elif name == "medium_quiet":
        kw.update(spread_bps=1200.0, requote_bps=200.0)
    elif name == "large_active":
        kw.update(starting_xch=50.0, starting_cat=25000.0,
                  inner_size_xch=3.0, mid_size_xch=2.0,
                  outer_size_xch=1.0, extreme_size_xch=0.5,
                  xch_coin_size=3.5, cat_coin_size_tokens=3500.0,
                  max_position_xch=20.0)
    elif name == "large_quiet":
        kw.update(starting_xch=50.0, starting_cat=25000.0,
                  spread_bps=1200.0, max_position_xch=20.0)
    elif name == "medium_crash":
        pass  # same config, crash is in the price model
    elif name == "large_volatile":
        kw.update(starting_xch=50.0, starting_cat=25000.0,
                  spread_bps=1000.0, max_position_xch=15.0)
    elif name == "cat_drain":
        kw.update(starting_cat=200.0)  # barely any CAT
    elif name == "xch_drain":
        kw.update(starting_xch=1.0)  # barely any XCH
    elif name == "stress_position_limit":
        kw.update(max_position_xch=0.5)  # very tight CB
    elif name == "stress_cb_storm":
        kw.update(max_position_xch=0.2, spread_bps=400.0)
    elif name == "stress_requote":
        kw.update(requote_bps=50.0)  # extremely tight requote threshold
    elif name == "trend_up":
        pass
    elif name == "trend_down":
        pass
    elif name == "mean_revert":
        kw.update(spread_bps=600.0)
    elif name == "flash_crash":
        kw.update(spread_bps=1200.0)
    elif name == "pump_dump":
        kw.update(spread_bps=1000.0)
    elif name == "tight_spread":
        kw.update(spread_bps=200.0, requote_bps=50.0)
    elif name == "wide_spread":
        kw.update(spread_bps=2000.0, requote_bps=400.0)
    elif name == "medium_tight":
        kw.update(spread_bps=400.0, requote_bps=80.0)
    elif name == "coin_starved":
        kw.update(xch_coin_size=5.0, cat_coin_size_tokens=2500.0)  # few large coins
    elif name == "coin_rich":
        # Many small coins: reduce tier sizes to fit the small coin size.
        # xch_coin_size=0.12 just covers extreme (0.1 XCH) and inner (0.1 XCH).
        kw.update(xch_coin_size=0.12, cat_coin_size_tokens=150.0,
                  inner_size_xch=0.1, mid_size_xch=0.1,
                  outer_size_xch=0.1, extreme_size_xch=0.1)
    elif name == "inner_only":
        # Coin size must cover the inner tier offer size (default 1.0 XCH).
        kw.update(n_mid=0, n_outer=0, n_extreme=0, n_inner=5,
                  xch_coin_size=1.5, cat_coin_size_tokens=1200.0)
    elif name == "outer_only":
        # requote_bps must exceed the outer-tier drift from mid so offers aren't
        # immediately cancelled.  Outer at spread=1600bps produces a ~25% drift
        # measurement, so requote_bps=1500 gives a 30% threshold that allows
        # outer/extreme offers to remain open long enough to fill.
        kw.update(n_inner=0, n_mid=0, n_outer=3, n_extreme=3,
                  spread_bps=1600.0, requote_bps=1500.0)
    elif name == "full_ladder":
        kw.update(starting_xch=30.0, starting_cat=15000.0,
                  n_inner=4, n_mid=4, n_outer=3, n_extreme=2,
                  max_position_xch=15.0)
    elif name == "zero_cat":
        kw.update(starting_cat=0.0)
    elif name == "zero_xch":
        kw.update(starting_xch=0.0)
    elif name == "minimal":
        kw.update(starting_xch=0.5, starting_cat=100.0,
                  n_inner=1, n_mid=0, n_outer=0, n_extreme=0,
                  inner_size_xch=0.1, max_position_xch=0.3)
    elif name == "default":
        pass  # base defaults

    return Scenario(**kw)


def _get_price_model(name: str, generate_fn, n_ticks: int = 500):
    """Select the appropriate price model for a scenario name.

    Args:
        name: Scenario name.
        generate_fn: Callable(n_ticks, start_price) → List[float].
                     Wraps PRESET_MODELS[model_key].generate in the real engine.
        n_ticks: How many ticks to generate.

    Returns:
        List of float prices.
    """
    start = 0.001

    # Map scenario names to price model types
    model_map = {
        "medium_crash": ("crash", 500),
        "flash_crash": ("crash", 300),
        "large_volatile": ("volatile", 600),
        "stress_cb_storm": ("volatile", 400),
        "stress_requote": ("volatile", 300),
        "trend_up": ("trend_up", 500),
        "trend_down": ("trend_down", 500),
        "mean_revert": ("mean_revert", 500),
        "pump_dump": ("pump_dump", 400),
        "tight_spread": ("volatile", 400),
        "wide_spread": ("quiet", 500),
        "medium_quiet": ("quiet", 500),
        "small_quiet": ("quiet", 300),
        "large_quiet": ("quiet", 500),
    }

    model_key, ticks = model_map.get(name, ("active", n_ticks))
    try:
        return generate_fn(model_key, ticks, start)
    except Exception:
        # Fallback: simple sinusoidal walk
        return _fallback_prices(ticks, start)


def _fallback_prices(n: int, start: float = 0.001) -> List[float]:
    """Generate a simple sinusoidal price series as a fallback.

    Does not require any external imports.

    Args:
        n: Number of ticks.
        start: Starting price.

    Returns:
        List of float prices.
    """
    prices = []
    for i in range(n):
        t = i / max(n - 1, 1)
        # Sine wave with small random noise baked in via deterministic formula
        noise = math.sin(i * 7.3) * 0.0001
        wave = math.sin(t * math.pi * 4) * 0.0002
        prices.append(max(1e-6, start + wave + noise))
    return prices


# ---------------------------------------------------------------------------
# Mock mode — produces plausible output with no imports at all
# ---------------------------------------------------------------------------

def _run_mock_scenario(name: str, n_ticks: int = 500) -> dict:
    """Run a completely fake scenario for testing the CLI output format.

    Does not import simulation.engine or simulation.market.  Generates
    plausible-looking numbers using only the stdlib.

    Args:
        name: Scenario name (used to vary the fake output slightly).
        n_ticks: Number of ticks to simulate.

    Returns:
        Dict matching the structure of a real SimResult.
    """
    # Deterministic seed from scenario name
    seed = sum(ord(c) for c in name)
    # Simple LCG for repeatable fake values
    def lcg(x):
        return (1664525 * x + 1013904223) & 0xFFFFFFFF

    rng = seed
    fills = 0
    pnl = 0.0
    price = 0.001
    cb_trips = 0
    xch_bal = 10.0
    cat_bal = 5000.0

    for _ in range(n_ticks):
        rng = lcg(rng)
        delta = (rng / 0xFFFFFFFF - 0.5) * 0.00004
        price = max(1e-6, price + delta)
        if rng % 30 == 0:
            fills += 1
            pnl += (rng % 100 - 50) * 0.0001
        if rng % 200 == 0:
            cb_trips += 1

    return {
        "scenario": name,
        "n_ticks": n_ticks,
        "n_fills": fills,
        "n_cancels": int(n_ticks * 0.3),
        "pnl_xch": pnl,
        "cb_trips": cb_trips,
        "final_xch": xch_bal,
        "final_cat": cat_bal,
        "issues": [],
        "mock": True,
        "duration_ms": 0,
    }


# ---------------------------------------------------------------------------
# Real scenario runner
# ---------------------------------------------------------------------------

def _run_scenario(name: str, Scenario, SimBot, generate_fn) -> dict:
    """Run one named scenario through the real simulation engine.

    Args:
        name: Scenario name.
        Scenario: The Scenario class.
        SimBot: The SimBot class.
        generate_fn: Function(model_key, n_ticks, start_price) → prices.

    Returns:
        Dict with results for printing and CSV export.
    """
    t0 = time.time()

    scenario = _build_scenario(name, Scenario)
    prices = _get_price_model(name, generate_fn, n_ticks=500)

    bot = SimBot(scenario)
    for price in prices:
        bot.tick(price)

    state = bot.get_state()
    elapsed_ms = int((time.time() - t0) * 1000)

    # Count CB trips from tick history — approximated from state
    cb_trips = 1 if state.get("cb_tripped") else 0

    issues = []
    if state.get("pnl_xch", 0) < -0.01:
        issues.append("negative P&L")
    if state.get("xch_balance", 1) < 0.1:
        issues.append("XCH near zero")
    if state.get("cat_balance", 1) < 10:
        issues.append("CAT near zero")

    return {
        "scenario": name,
        "n_ticks": len(prices),
        "n_fills": state.get("total_fills", 0),
        "n_cancels": state.get("total_cancels", 0),
        "pnl_xch": state.get("pnl_xch", 0.0),
        "cb_trips": cb_trips,
        "final_xch": state.get("xch_balance", 0.0),
        "final_cat": state.get("cat_balance", 0.0),
        "issues": issues,
        "mock": False,
        "duration_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _progress_bar(current: int, total: int, label: str, width: int = 20) -> str:
    """Render a simple ASCII progress bar.

    Example output:
        Running scenarios: [████████████░░░░░░░░] 15/30 — medium_volatile

    Args:
        current: Items completed so far.
        total: Total items.
        label: Label shown after the fraction.
        width: Width of the bar in characters.

    Returns:
        The progress line string (no trailing newline).
    """
    filled = int(width * current / max(total, 1))
    bar = "#" * filled + "." * (width - filled)
    return f"Running scenarios: [{bar}] {current}/{total} - {label}"


def _print_progress(current: int, total: int, label: str) -> None:
    """Print a progress bar that overwrites the current line.

    Args:
        current: Items completed.
        total: Total items.
        label: Scenario name.
    """
    line = _progress_bar(current, total, label)
    # Pad to 80 chars to overwrite previous longer line
    line = line.ljust(80)
    print(f"\r{line}", end="", flush=True)


def _print_results_table(results: List[dict]) -> None:
    """Print a formatted summary table of scenario results.

    Args:
        results: List of result dicts from _run_scenario or _run_mock_scenario.
    """
    if not results:
        print("  (no results)")
        return

    col_widths = {
        "scenario": max(len("scenario"), max(len(r["scenario"]) for r in results)),
        "ticks": 6,
        "fills": 6,
        "cancels": 8,
        "pnl": 12,
        "xch": 9,
        "cat": 10,
        "issues": 20,
        "ms": 6,
    }

    header = (
        f"{'Scenario':<{col_widths['scenario']}}  "
        f"{'Ticks':>{col_widths['ticks']}}  "
        f"{'Fills':>{col_widths['fills']}}  "
        f"{'Cancels':>{col_widths['cancels']}}  "
        f"{'P&L XCH':>{col_widths['pnl']}}  "
        f"{'XCH':>{col_widths['xch']}}  "
        f"{'CAT':>{col_widths['cat']}}  "
        f"{'Issues':<{col_widths['issues']}}  "
        f"{'ms':>{col_widths['ms']}}"
    )
    sep = "-" * len(header)

    print()
    print(header)
    print(sep)

    for r in results:
        issues_str = ", ".join(r.get("issues", [])) or "-"
        mock_tag = " *" if r.get("mock") else ""
        pnl = r.get("pnl_xch", 0.0)
        pnl_str = f"{pnl:+.6f}"

        print(
            f"{r['scenario']:<{col_widths['scenario']}}{mock_tag}  "
            f"{r['n_ticks']:>{col_widths['ticks']}}  "
            f"{r['n_fills']:>{col_widths['fills']}}  "
            f"{r['n_cancels']:>{col_widths['cancels']}}  "
            f"{pnl_str:>{col_widths['pnl']}}  "
            f"{r['final_xch']:>{col_widths['xch']}.4f}  "
            f"{r['final_cat']:>{col_widths['cat']}.1f}  "
            f"{issues_str:<{col_widths['issues']}}  "
            f"{r['duration_ms']:>{col_widths['ms']}}"
        )

    print(sep)
    if any(r.get("mock") for r in results):
        print("  * mock run (simulation.engine not available)")


def _print_insights(results: List[dict]) -> None:
    """Print a short insight summary derived from the results.

    Args:
        results: List of result dicts.
    """
    if not results:
        return

    print()
    print("INSIGHTS")
    print("-" * 40)

    total = len(results)
    profitable = sum(1 for r in results if r.get("pnl_xch", 0) > 0)
    any_issues = sum(1 for r in results if r.get("issues"))
    avg_fills = sum(r.get("n_fills", 0) for r in results) / max(total, 1)
    avg_pnl = sum(r.get("pnl_xch", 0.0) for r in results) / max(total, 1)

    print(f"  Scenarios run    : {total}")
    print(f"  Profitable runs  : {profitable}/{total} "
          f"({100 * profitable // max(total, 1)}%)")
    print(f"  Runs with issues : {any_issues}/{total}")
    print(f"  Avg fills/run    : {avg_fills:.1f}")
    print(f"  Avg P&L XCH      : {avg_pnl:+.6f}")

    # Best and worst
    best = max(results, key=lambda r: r.get("pnl_xch", 0.0))
    worst = min(results, key=lambda r: r.get("pnl_xch", 0.0))
    print(f"  Best scenario    : {best['scenario']} (P&L {best.get('pnl_xch', 0.0):+.6f})")
    print(f"  Worst scenario   : {worst['scenario']} (P&L {worst.get('pnl_xch', 0.0):+.6f})")

    # Warn on common issues
    cb_issues = [r for r in results if "CB" in " ".join(r.get("issues", []))]
    if cb_issues:
        print(f"  WARNING: {len(cb_issues)} scenario(s) hit CB — check MAX_POSITION_XCH")

    neg_pnl = [r for r in results if r.get("pnl_xch", 0) < -0.001]
    if neg_pnl:
        print(f"  WARNING: {len(neg_pnl)} scenario(s) show negative P&L — "
              f"check SPREAD_BPS")
    print()


def _write_csv(results: List[dict], path: str) -> None:
    """Write scenario results to a CSV file.

    Args:
        results: List of result dicts.
        path: Output file path.
    """
    if not results:
        print(f"  No results to write.")
        return

    fieldnames = [
        "scenario", "n_ticks", "n_fills", "n_cancels",
        "pnl_xch", "cb_trips", "final_xch", "final_cat",
        "issues", "mock", "duration_ms",
    ]
    try:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in results:
                row = dict(r)
                row["issues"] = "; ".join(r.get("issues", []))
                writer.writerow(row)
        print(f"  Results written to {path}")
    except OSError as exc:
        print(f"  ERROR: Could not write CSV: {exc}")


def _print_detail(result: dict, state: Optional[dict] = None) -> None:
    """Print detailed output for a single scenario run.

    Args:
        result: Result dict from _run_scenario.
        state: Optional final state dict from SimBot.get_state().
    """
    print()
    print("=" * 60)
    print(f"  DETAIL: {result['scenario']}")
    print("=" * 60)
    for key, val in result.items():
        if key == "issues":
            print(f"  {key:<20}: {', '.join(val) if val else 'none'}")
        elif isinstance(val, float):
            print(f"  {key:<20}: {val:.6f}")
        else:
            print(f"  {key:<20}: {val}")
    if state:
        print()
        print("  Final bot state:")
        for key, val in state.items():
            if isinstance(val, float):
                print(f"    {key:<24}: {val:.6f}")
            else:
                print(f"    {key:<24}: {val}")
    print()


# ---------------------------------------------------------------------------
# Replay handler
# ---------------------------------------------------------------------------

def _run_replay(replay_path: str, mock: bool = False) -> None:
    """Load a real bot database or JSON export and replay it.

    Args:
        replay_path: Path to .db or .json file.
        mock: If True, produce fake output without importing simulation modules.
    """
    print(f"\nREPLAY MODE: {replay_path}")
    print("-" * 60)

    if mock:
        print("  [mock] Would load and replay the session.")
        print("  Session ID     : mock_replay")
        print("  Events         : 1234")
        print("  Price ticks    : 1234")
        print("  P&L (sim)      : +0.012345 XCH")
        print("  Fills (sim)    : 42")
        print("  Divergences    : 3")
        print()
        print("  [mock] Error analysis:")
        print("    1. No known error patterns detected in this session.")
        print()
        print("  [mock] Recommended fixes:")
        print("    1. (none — mock mode)")
        return

    # Import replay module
    try:
        # Add project root to path if needed
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from simulation.log_replay import (
            load_from_database,
            load_from_json_export,
            replay_session,
            generate_replay_report,
        )
    except ImportError as exc:
        print(f"  ERROR: Could not import simulation.log_replay: {exc}")
        print("  Run with --mock to test CLI output without imports.")
        return

    # Load
    try:
        if replay_path.lower().endswith(".json"):
            print("  Loading JSON export...")
            session = load_from_json_export(replay_path)
        else:
            print("  Loading SQLite database...")
            session = load_from_database(replay_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR: {exc}")
        return

    print(f"  Loaded {session.n_events} events "
          f"({session.start_time[:19]} → {session.end_time[:19]})")
    print("  Replaying through simulation engine...")

    result = replay_session(session, verbose=True)

    report = generate_replay_report(session, result)
    print()
    print(report)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse CLI arguments and run the appropriate mode.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description="CATalyst — Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--scenario", metavar="NAME",
        help="Run a single named scenario.",
    )
    mode.add_argument(
        "--list", action="store_true",
        help="List all available scenarios and exit.",
    )
    mode.add_argument(
        "--replay", metavar="PATH",
        help="Replay a real bot database (.db) or JSON export (.json).",
    )
    mode.add_argument(
        "--quick", action="store_true",
        help=f"Run the 5 key scenarios: {', '.join(QUICK_SCENARIOS)}.",
    )
    mode.add_argument(
        "--stress", action="store_true",
        help="Run stress and edge-case scenarios only.",
    )

    parser.add_argument(
        "--output", metavar="FILE",
        help="Write results to a CSV file (e.g. results.csv).",
    )
    parser.add_argument(
        "--detail", action="store_true",
        help="Print detailed output for a single scenario (use with --scenario).",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Run with fake data — no simulation imports required.",
    )
    parser.add_argument(
        "--ticks", type=int, default=500, metavar="N",
        help="Number of price ticks per scenario (default: 500).",
    )

    args = parser.parse_args()

    # --list
    if args.list:
        print()
        print(f"{'Scenario':<30}  {'Tags':<20}  Description")
        print("-" * 72)
        for name, desc, tags in ALL_SCENARIO_NAMES:
            tag_str = ", ".join(tags)
            print(f"  {name:<28}  {tag_str:<20}  {desc}")
        print()
        print(f"  Total: {len(ALL_SCENARIO_NAMES)} scenarios")
        print(f"  Quick ({len(QUICK_SCENARIOS)}): {', '.join(QUICK_SCENARIOS)}")
        print()
        return 0

    # --replay
    if args.replay:
        _run_replay(args.replay, mock=args.mock)
        return 0

    # Determine which scenarios to run
    if args.quick:
        names_to_run = QUICK_SCENARIOS
    elif args.stress:
        names_to_run = [
            name for name, _, tags in ALL_SCENARIO_NAMES
            if any(t in STRESS_TAGS for t in tags)
        ]
    elif args.scenario:
        # Validate name
        valid_names = {n for n, _, _ in ALL_SCENARIO_NAMES}
        if args.scenario not in valid_names:
            print(f"ERROR: Unknown scenario '{args.scenario}'.")
            print(f"       Run with --list to see available scenarios.")
            return 1
        names_to_run = [args.scenario]
    else:
        names_to_run = [n for n, _, _ in ALL_SCENARIO_NAMES]

    # Import simulation engine (or use mock)
    SimBot = None
    Scenario = None
    generate_fn = None

    if not args.mock:
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        try:
            from simulation.engine import SimBot, Scenario
            from simulation.market import PRESET_MODELS

            def generate_fn(model_key: str, n_ticks: int, start: float):
                model = PRESET_MODELS.get(model_key)
                if model is None:
                    # Try common fallbacks
                    for fallback in ("active", "quiet", "volatile"):
                        model = PRESET_MODELS.get(fallback)
                        if model is not None:
                            break
                if model is None:
                    return _fallback_prices(n_ticks, start)
                try:
                    return model.generate(n_ticks, start)
                except Exception:
                    return _fallback_prices(n_ticks, start)

        except ImportError as exc:
            print(f"WARNING: Could not import simulation engine: {exc}")
            print("         Falling back to --mock mode. "
                  "Run with --mock to suppress this warning.")
            args.mock = True

    # Run scenarios
    print()
    print("CATalyst — Simulation Runner")
    print("=" * 40)

    if args.mock:
        print("  Mode: MOCK (fake data, no imports)")
    else:
        print(f"  Mode: REAL  |  Ticks/scenario: {args.ticks}")
    print(f"  Scenarios  : {len(names_to_run)}")
    print()

    results: List[dict] = []
    total = len(names_to_run)

    for i, name in enumerate(names_to_run):
        _print_progress(i, total, name)

        if args.mock:
            result = _run_mock_scenario(name, n_ticks=args.ticks)
        else:
            try:
                result = _run_scenario(name, Scenario, SimBot, generate_fn)
            except Exception as exc:
                result = {
                    "scenario": name,
                    "n_ticks": 0,
                    "n_fills": 0,
                    "n_cancels": 0,
                    "pnl_xch": 0.0,
                    "cb_trips": 0,
                    "final_xch": 0.0,
                    "final_cat": 0.0,
                    "issues": [f"ERROR: {exc}"],
                    "mock": False,
                    "duration_ms": 0,
                }

        results.append(result)

        # Detailed output for single scenario
        if args.detail and len(names_to_run) == 1:
            # Re-run to capture state (small overhead, only for --detail)
            if not args.mock and SimBot and Scenario:
                try:
                    scen = _build_scenario(name, Scenario)
                    prices = _get_price_model(name, generate_fn, args.ticks)
                    bot = SimBot(scen)
                    for p in prices:
                        bot.tick(p)
                    _print_detail(result, bot.get_state())
                except Exception:
                    _print_detail(result)
            else:
                _print_detail(result)

    # Clear progress line
    print(f"\r{' ' * 82}\r", end="")

    # Print results table
    _print_results_table(results)

    # Print insights
    _print_insights(results)

    # Export CSV
    if args.output:
        _write_csv(results, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
