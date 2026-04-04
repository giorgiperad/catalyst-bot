"""
Simulation report generation.

Produces console tables, CSV exports, JSON exports, and an
'insights' summary that maps simulation findings to real bot fixes.
"""

from __future__ import annotations

import csv
import json
import os
from typing import List

from simulation.metrics import SimResult
from simulation.runner import aggregate_issues


# ---------------------------------------------------------------------------
# Column widths and helpers
# ---------------------------------------------------------------------------

_COL_SCENARIO = 32
_COL_PNL = 8
_COL_FILLS = 7
_COL_DEAD = 7
_COL_CB = 8
_COL_ISSUES = 6

_SEPARATOR = (
    "-" * _COL_SCENARIO
    + "-+-"
    + "-" * _COL_PNL
    + "-+-"
    + "-" * _COL_FILLS
    + "-+-"
    + "-" * _COL_DEAD
    + "-+-"
    + "-" * _COL_CB
    + "-+-"
    + "-" * _COL_ISSUES
)


def _trunc(text: str, width: int) -> str:
    """Truncate or right-pad a string to exactly width characters."""
    if len(text) > width:
        return text[: width - 1] + "..."
    return text.ljust(width)


def _fmt_pnl(pnl_pct: float) -> str:
    """Format P&L percentage with sign, right-aligned."""
    sign = "+" if pnl_pct >= 0 else ""
    return f"{sign}{pnl_pct:.2f}%".rjust(_COL_PNL)


def _worst_flag(result: SimResult, all_results: List[SimResult]) -> str:
    """Return '!' if this result is in the bottom 20% by PnL, else ' '."""
    if len(all_results) < 5:
        return " "
    sorted_pnl = sorted(r.pnl_pct for r in all_results)
    threshold = sorted_pnl[max(0, len(sorted_pnl) // 5)]
    return "!" if result.pnl_pct <= threshold else " "


# ---------------------------------------------------------------------------
# print_summary_table
# ---------------------------------------------------------------------------

def print_summary_table(results: List[SimResult]) -> None:
    """Print a formatted ASCII table of all scenario results.

    Columns: Scenario | P&L% | Fills | Dead% | CB trips | Issues

    Worst performers (bottom 20% by P&L) are flagged with '!' in the
    leftmost position.

    Args:
        results: List of SimResult to display.
    """
    if not results:
        print("No results to display.")
        return

    header = (
        _trunc("Scenario", _COL_SCENARIO)
        + " | "
        + "P&L %".rjust(_COL_PNL)
        + " | "
        + "Fills".rjust(_COL_FILLS)
        + " | "
        + "Dead%".rjust(_COL_DEAD)
        + " | "
        + "CB trips".rjust(_COL_CB)
        + " | "
        + "Issues".rjust(_COL_ISSUES)
    )

    print()
    print(" " + header)
    print(" " + _SEPARATOR)

    for r in results:
        flag = _worst_flag(r, results)
        row = (
            flag
            + _trunc(r.scenario_name, _COL_SCENARIO)
            + " | "
            + _fmt_pnl(r.pnl_pct)
            + " | "
            + str(r.total_fills).rjust(_COL_FILLS)
            + " | "
            + f"{r.dead_pct:.0f}%".rjust(_COL_DEAD)
            + " | "
            + str(r.cb_trips).rjust(_COL_CB)
            + " | "
            + str(len(r.issues)).rjust(_COL_ISSUES)
        )
        print(row)

    print(" " + _SEPARATOR)
    print(f"  {len(results)} scenarios total. '!' = bottom 20% by P&L.\n")


# ---------------------------------------------------------------------------
# print_insights
# ---------------------------------------------------------------------------

# Mapping from issue pattern prefix to suggested fix
_FIX_MAP = {
    "Bot spent": "Reduce requote cooldown or increase coin prep count",
    "Circuit breaker occupied": "Widen position limit or spread for this volatility regime",
    "Heavily one-sided fills": "Adjust spread asymmetry or review position limit direction",
    "Capturing only": "Increase requote_bps threshold so offers survive longer",
    "Coin prep triggered": "Increase fee pool reserve or coin split target count",
    "Max drawdown": "Widen position limits or increase spread for extreme moves",
    "CAT nearly exhausted": "Add CAT reserve buffer or reduce sell offer depth",
    "XCH nearly exhausted": "Add XCH reserve buffer or reduce buy offer depth",
    "Extremely high fill rate": "Check spread config -- may be too tight",
    "Low capital deployment": "Increase tier counts (n_inner/n_mid) for this wallet size",
    "Profitable scenario": "No fix needed -- this config works",
    "Losing scenario": "Investigate fill asymmetry, spread vs volatility ratio",
    "SCENARIO FAILED": "Check scenario config for errors",
}


def _match_fix(pattern: str) -> str:
    """Return a fix hint for a given issue pattern prefix."""
    for key, fix in _FIX_MAP.items():
        if pattern.startswith(key):
            return fix
    return "Review scenario output for details"


def print_insights(results: List[SimResult]) -> None:
    """Print a consolidated insight box across all scenario runs.

    Groups issues by type, counts frequency, and suggests specific fixes.

    Example output::

        +=== SIMULATION INSIGHTS ===========================================+
        | 3/30 scenarios: Bot spent >20% time with no active offers         |
        |   -> Affected: micro_crash, xch_drain, stress_position_limit       |
        |   -> Fix: Reduce requote cooldown or increase coin prep count       |
        +===================================================================+

    Args:
        results: List of SimResult from one or more batch runs.
    """
    if not results:
        print("No results to analyse.")
        return

    aggregated = aggregate_issues(results)
    total = len(results)
    box_width = 70

    # Filter out the 'Profitable scenario' positive findings for the issues count
    problems = {k: v for k, v in aggregated.items() if not k.startswith("Profitable")}
    positives = {k: v for k, v in aggregated.items() if k.startswith("Profitable")}

    print()
    print("+" + "=" * (box_width - 2) + "+")
    title = " SIMULATION INSIGHTS "
    pad_l = (box_width - 2 - len(title)) // 2
    pad_r = box_width - 2 - len(title) - pad_l
    print("|" + " " * pad_l + title + " " * pad_r + "|")
    print("+" + "=" * (box_width - 2) + "+")

    if not aggregated:
        line = "  No issues detected across all scenarios."
        print("|" + line.ljust(box_width - 2) + "|")
    else:
        for pattern, data in aggregated.items():
            count = data["count"]
            scenarios = data["scenarios"]
            fix = _match_fix(pattern)

            # Headline
            headline = f"  {count}/{total} scenarios: {pattern}"
            print("|" + _box_line(headline, box_width) + "|")

            # Affected scenarios (wrapped to two lines max)
            affected_str = ", ".join(scenarios)
            affected_line = f"    -> Affected: {affected_str}"
            for chunk in _wrap_line(affected_line, box_width - 4):
                print("|  " + chunk.ljust(box_width - 4) + "  |")

            # Fix suggestion
            fix_line = f"    -> Fix: {fix}"
            for chunk in _wrap_line(fix_line, box_width - 4):
                print("|  " + chunk.ljust(box_width - 4) + "  |")

            # Blank separator between entries
            print("|" + " " * (box_width - 2) + "|")

    # Summary stats
    n_issues = sum(v["count"] for v in problems.values())
    n_pos = sum(v["count"] for v in positives.values())
    summary = f"  {n_issues} problem findings, {n_pos} profitable scenarios"
    print("+" + "=" * (box_width - 2) + "+")
    print("|" + _box_line(summary, box_width) + "|")
    print("+" + "=" * (box_width - 2) + "+")
    print()


def _box_line(text: str, box_width: int) -> str:
    """Format a line to fit inside a box of given total width."""
    inner = box_width - 2
    if len(text) > inner:
        text = text[: inner - 1] + "..."
    return text.ljust(inner)


def _wrap_line(text: str, width: int) -> List[str]:
    """Wrap text to width characters, breaking on spaces."""
    if len(text) <= width:
        return [text]
    lines: List[str] = []
    while len(text) > width:
        split_at = text[:width].rfind(" ")
        if split_at <= 0:
            split_at = width
        lines.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        lines.append(text)
    return lines


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------

def export_csv(
    results: List[SimResult],
    path: str = "simulation_results.csv",
) -> None:
    """Export all scenario results to a CSV file.

    One row per scenario.  Raw series (price, pnl, balances) are NOT
    included -- use export_json for those.

    Args:
        results: List of SimResult to export.
        path: Destination file path. Defaults to simulation_results.csv.
    """
    if not results:
        print("No results to export.")
        return

    fieldnames = [
        "scenario_name",
        "n_ticks",
        "duration_virtual_hours",
        "starting_xch",
        "starting_cat",
        "ending_xch",
        "ending_cat",
        "starting_portfolio_xch",
        "ending_portfolio_xch",
        "pnl_xch",
        "pnl_pct",
        "total_fills",
        "buy_fills",
        "sell_fills",
        "total_offers_created",
        "total_offers_cancelled",
        "fill_rate_per_hour",
        "avg_spread_captured_bps",
        "avg_capital_deployed_pct",
        "dead_ticks",
        "dead_pct",
        "max_drawdown_pct",
        "max_net_position_cat",
        "cb_trips",
        "cb_ticks",
        "coin_splits_needed",
        "n_issues",
        "issues",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = {
                "scenario_name": r.scenario_name,
                "n_ticks": r.n_ticks,
                "duration_virtual_hours": round(r.duration_virtual_hours, 4),
                "starting_xch": r.starting_xch,
                "starting_cat": r.starting_cat,
                "ending_xch": round(r.ending_xch, 6),
                "ending_cat": round(r.ending_cat, 3),
                "starting_portfolio_xch": round(r.starting_portfolio_xch, 6),
                "ending_portfolio_xch": round(r.ending_portfolio_xch, 6),
                "pnl_xch": round(r.pnl_xch, 6),
                "pnl_pct": round(r.pnl_pct, 4),
                "total_fills": r.total_fills,
                "buy_fills": r.buy_fills,
                "sell_fills": r.sell_fills,
                "total_offers_created": r.total_offers_created,
                "total_offers_cancelled": r.total_offers_cancelled,
                "fill_rate_per_hour": round(r.fill_rate_per_hour, 2),
                "avg_spread_captured_bps": round(r.avg_spread_captured_bps, 2),
                "avg_capital_deployed_pct": round(r.avg_capital_deployed_pct, 2),
                "dead_ticks": r.dead_ticks,
                "dead_pct": round(r.dead_pct, 2),
                "max_drawdown_pct": round(r.max_drawdown_pct, 4),
                "max_net_position_cat": round(r.max_net_position_cat, 3),
                "cb_trips": r.cb_trips,
                "cb_ticks": r.cb_ticks,
                "coin_splits_needed": r.coin_splits_needed,
                "n_issues": len(r.issues),
                "issues": " | ".join(r.issues),
            }
            writer.writerow(row)

    abs_path = os.path.abspath(path)
    print(f"CSV exported: {abs_path} ({len(results)} rows)")


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

def export_json(
    results: List[SimResult],
    path: str = "simulation_results.json",
) -> None:
    """Export all results to JSON, including raw price/pnl/balance series.

    Args:
        results: List of SimResult to export.
        path: Destination file path. Defaults to simulation_results.json.
    """
    if not results:
        print("No results to export.")
        return

    payload = []
    for r in results:
        payload.append({
            "scenario_name": r.scenario_name,
            "n_ticks": r.n_ticks,
            "duration_virtual_hours": r.duration_virtual_hours,
            "starting_xch": r.starting_xch,
            "starting_cat": r.starting_cat,
            "ending_xch": r.ending_xch,
            "ending_cat": r.ending_cat,
            "starting_portfolio_xch": r.starting_portfolio_xch,
            "ending_portfolio_xch": r.ending_portfolio_xch,
            "pnl_xch": r.pnl_xch,
            "pnl_pct": r.pnl_pct,
            "total_fills": r.total_fills,
            "buy_fills": r.buy_fills,
            "sell_fills": r.sell_fills,
            "total_offers_created": r.total_offers_created,
            "total_offers_cancelled": r.total_offers_cancelled,
            "fill_rate_per_hour": r.fill_rate_per_hour,
            "avg_spread_captured_bps": r.avg_spread_captured_bps,
            "avg_capital_deployed_pct": r.avg_capital_deployed_pct,
            "dead_ticks": r.dead_ticks,
            "dead_pct": r.dead_pct,
            "max_drawdown_pct": r.max_drawdown_pct,
            "max_net_position_cat": r.max_net_position_cat,
            "cb_trips": r.cb_trips,
            "cb_ticks": r.cb_ticks,
            "coin_splits_needed": r.coin_splits_needed,
            "issues": r.issues,
            "price_series": r.price_series,
            "pnl_series": r.pnl_series,
            "balance_xch_series": r.balance_xch_series,
            "balance_cat_series": r.balance_cat_series,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    abs_path = os.path.abspath(path)
    print(f"JSON exported: {abs_path} ({len(results)} scenarios)")


# ---------------------------------------------------------------------------
# print_scenario_detail
# ---------------------------------------------------------------------------

def print_scenario_detail(result: SimResult) -> None:
    """Print a detailed breakdown of a single scenario result.

    Args:
        result: The SimResult to describe.
    """
    w = 60
    divider = "-" * w

    print()
    print(f"+{divider}+")
    title = f" Scenario: {result.scenario_name} "
    print(f"|{title.center(w)}|")
    print(f"+{divider}+")

    def _row(label: str, value: str) -> None:
        line = f"  {label:<30} {value}"
        if len(line) > w:
            line = line[: w - 1] + "..."
        print(f"|{line.ljust(w)}|")

    # Duration
    _row("Ticks:", str(result.n_ticks))
    _row("Virtual hours:", f"{result.duration_virtual_hours:.1f} h")

    print(f"+{divider}+")
    print(f"|{'  Capital':^{w}}|")
    print(f"+{divider}+")

    _row("Starting XCH:", f"{result.starting_xch:.4f}")
    _row("Starting CAT:", f"{result.starting_cat:.1f}")
    _row("Ending XCH:", f"{result.ending_xch:.4f}")
    _row("Ending CAT:", f"{result.ending_cat:.1f}")
    _row("Start portfolio (XCH):", f"{result.starting_portfolio_xch:.6f}")
    _row("End portfolio (XCH):", f"{result.ending_portfolio_xch:.6f}")
    sign = "+" if result.pnl_xch >= 0 else ""
    _row("P&L (XCH):", f"{sign}{result.pnl_xch:.6f}")
    _row("P&L (%):", f"{sign}{result.pnl_pct:.4f}%")

    print(f"+{divider}+")
    print(f"|{'  Activity':^{w}}|")
    print(f"+{divider}+")

    _row("Total fills:", str(result.total_fills))
    _row("Buy fills:", str(result.buy_fills))
    _row("Sell fills:", str(result.sell_fills))
    _row("Offers created:", str(result.total_offers_created))
    _row("Offers cancelled:", str(result.total_offers_cancelled))
    _row("Fill rate (per hour):", f"{result.fill_rate_per_hour:.2f}")
    _row("Avg spread captured (bps):", f"{result.avg_spread_captured_bps:.1f}")

    print(f"+{divider}+")
    print(f"|{'  Risk':^{w}}|")
    print(f"+{divider}+")

    _row("Max drawdown:", f"{result.max_drawdown_pct:.2f}%")
    _row("Max net CAT position:", f"{result.max_net_position_cat:.1f}")
    _row("CB trips:", str(result.cb_trips))
    _row("CB ticks:", str(result.cb_ticks))
    cb_pct = (result.cb_ticks / result.n_ticks * 100) if result.n_ticks > 0 else 0.0
    _row("CB % of runtime:", f"{cb_pct:.1f}%")

    print(f"+{divider}+")
    print(f"|{'  Efficiency':^{w}}|")
    print(f"+{divider}+")

    _row("Avg capital deployed:", f"{result.avg_capital_deployed_pct:.1f}%")
    _row("Dead ticks:", str(result.dead_ticks))
    _row("Dead %:", f"{result.dead_pct:.1f}%")
    _row("Coin splits needed:", str(result.coin_splits_needed))

    if result.issues:
        print(f"+{divider}+")
        print(f"|{'  Issues':^{w}}|")
        print(f"+{divider}+")
        for issue in result.issues:
            for chunk in _wrap_detail(f"  * {issue}", w - 2):
                print(f"| {chunk.ljust(w - 2)} |")

    print(f"+{divider}+")
    print()


def _wrap_detail(text: str, width: int) -> List[str]:
    """Wrap text to fit within width characters for the detail box."""
    if len(text) <= width:
        return [text]
    lines: List[str] = []
    indent = "    "  # continuation indent
    while len(text) > width:
        split_at = text[:width].rfind(" ")
        if split_at <= 0:
            split_at = width
        lines.append(text[:split_at])
        text = indent + text[split_at:].lstrip()
    if text:
        lines.append(text)
    return lines
