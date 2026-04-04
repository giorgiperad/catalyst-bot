"""
Log Replay — reproduce real bot sessions from exported logs.

Two use cases:
1. User reports a bug → load their bot database → replay what happened →
   see exactly which decision went wrong and why.
2. Continuous learning → replay past sessions to measure if a proposed
   code change would have improved outcomes.

Input:  bot SQLite database path  OR  list of log dicts (from JSON export)
Output: SimResult with full timeline + annotated events + root cause analysis

Database schema (from database.py):
    events table columns: id, timestamp, event_type, severity, message, data
    data column: JSON blob (may contain mid_price, offer_price, balance, etc.)

The events table is the single source of truth for replay. We do not depend
on offers/fills tables — those may not be present in a user's export.
"""

import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LogEvent:
    """A single event from the bot's event log.

    Mirrors one row from the events table in database.py.
    The ``data`` column is stored as a JSON string in the DB and parsed here
    into a plain dict for easy inspection.
    """
    timestamp: str
    """ISO timestamp string (stored as TEXT in the events table)."""
    tick_approx: int
    """Estimated tick number derived from relative timestamp position."""
    event_type: str
    """e.g. 'offer_created', 'offer_filled', 'circuit_breaker_tripped'."""
    category: str
    """Canonical category: price / offer / fill / error / cb / wallet / system."""
    severity: str
    """'info', 'success', 'warning', or 'error' (maps to severity column)."""
    message: str
    """Human-readable description from the message column."""
    metadata: dict
    """Parsed from the data JSON blob in the DB."""


@dataclass
class ReplaySession:
    """Parsed representation of a real bot session ready for replay.

    All fields are derived from the events table alone.  Nothing here
    requires the offers or fills tables to exist.
    """
    session_id: str
    """Unique ID for this replay session (derived from DB path or 'json')."""
    start_time: str
    """ISO timestamp of the earliest event in the session."""
    end_time: str
    """ISO timestamp of the latest event in the session."""
    n_events: int
    """Total number of events loaded."""

    # Reconstructed state
    price_series: List[float]
    """Price at each approximate tick (interpolated from offer/price events)."""
    offer_events: List[LogEvent]
    """Create / cancel events."""
    error_events: List[LogEvent]
    """Events with severity='error' or event_type containing 'error'/'fail'."""
    cb_events: List[LogEvent]
    """Circuit-breaker trip and clear events."""
    fill_events: List[LogEvent]
    """Confirmed fill events."""

    # Config snapshot (from config_loaded / startup events if present)
    config_snapshot: dict
    """Best-effort reconstruction of the config that was active."""

    # Approximate wallet starting state (from wallet / balance events)
    approx_starting_xch: float
    """XCH balance at session start (0.0 if not recoverable)."""
    approx_starting_cat: float
    """CAT balance at session start (0.0 if not recoverable)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_from_database(
    db_path: str,
    start_time: str = None,
    end_time: str = None,
    session_hours: int = 24,
) -> ReplaySession:
    """Load a real bot session from its SQLite database.

    Reads the events table, orders by timestamp, and extracts:
    - Price references from offer creation events (offer_price in metadata)
    - Fill events (event_type contains 'fill' or 'filled')
    - Error events (severity = 'error' or event_type contains 'error'/'fail')
    - CB events (event_type contains 'circuit_breaker' or 'cb_')
    - Config events (event_type = 'config_loaded' or 'startup')
    - Wallet balance snapshots (event_type contains 'balance' or 'wallet')

    If start_time is not supplied, the last session_hours of events are used.

    Args:
        db_path: Absolute path to the bot SQLite database.
        start_time: ISO string — ignore events before this time.
        end_time: ISO string — ignore events after this time.
        session_hours: If start_time is None, load this many hours from the end.

    Returns:
        ReplaySession with all events parsed and categorised.

    Raises:
        FileNotFoundError: If db_path does not exist.
        ValueError: If the events table cannot be read.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    rows = []
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row

        # Determine available columns (the events table schema may vary slightly)
        cursor = conn.execute("PRAGMA table_info(events)")
        col_names = {row["name"] for row in cursor.fetchall()}

        # Build SELECT to match available columns gracefully
        select_cols = ["timestamp", "event_type", "message"]
        if "severity" in col_names:
            select_cols.append("severity")
        else:
            select_cols.append("'info' AS severity")
        if "data" in col_names:
            select_cols.append("data")
        else:
            select_cols.append("NULL AS data")

        select_sql = "SELECT " + ", ".join(select_cols) + " FROM events"

        params: List = []
        where_clauses: List[str] = []

        if start_time:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)

        if where_clauses:
            select_sql += " WHERE " + " AND ".join(where_clauses)
        elif not start_time:
            # Load the tail of the log — last session_hours of events
            # We do this by finding the max timestamp and subtracting
            max_ts_row = conn.execute(
                "SELECT MAX(timestamp) AS mt FROM events"
            ).fetchone()
            if max_ts_row and max_ts_row["mt"]:
                # Rough cutoff: subtract session_hours worth of seconds from
                # the timestamp string (works for ISO strings in SQLite)
                select_sql += (
                    " WHERE timestamp >= datetime(?, '-{} hours')".format(
                        session_hours
                    )
                )
                params.append(max_ts_row["mt"])

        select_sql += " ORDER BY timestamp ASC"

        cursor = conn.execute(select_sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except sqlite3.Error as exc:
        raise ValueError(f"Could not read events table from {db_path}: {exc}")

    session_id = os.path.basename(db_path).replace(".db", "")
    return _build_session(rows, session_id)


def load_from_json_export(json_path: str) -> ReplaySession:
    """Load a replay session from a JSON export of the events table.

    Expected format: a JSON array of objects, each with at minimum:
        timestamp, event_type, message
    Optional keys: severity, data (may be a JSON string or dict).

    Args:
        json_path: Path to the JSON file.

    Returns:
        ReplaySession parsed from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as a list of event dicts.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON export not found: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not parse JSON export: {exc}")

    if not isinstance(raw, list):
        raise ValueError("JSON export must be a list of event dicts at the top level.")

    return load_from_log_list(raw)


def load_from_log_list(events: List[dict]) -> ReplaySession:
    """Load a replay session from a list of event dicts.

    Accepts the same format as load_from_json_export — useful when a user
    pastes events directly or when they are built programmatically.

    Args:
        events: List of dicts with keys: timestamp, event_type, message,
                and optionally severity, data (string or dict).

    Returns:
        ReplaySession parsed from the list.
    """
    normalised = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        row = {
            "timestamp": str(ev.get("timestamp", "")),
            "event_type": str(ev.get("event_type", "unknown")),
            "message": str(ev.get("message", "")),
            "severity": str(ev.get("severity", "info")),
            "data": ev.get("data", None),
        }
        normalised.append(row)

    # Sort by timestamp (best-effort — strings sort lexicographically which works
    # for ISO format timestamps)
    normalised.sort(key=lambda r: r["timestamp"])
    return _build_session(normalised, "json_import")


def replay_session(session: ReplaySession, verbose: bool = True) -> dict:
    """Replay a real session through the simulation engine.

    Steps:
    1. Build a Scenario from the session's config_snapshot and balances.
    2. Use session.price_series as the price feed.
    3. Run SimBot tick-by-tick.
    4. At each tick, compare sim decisions to actual log events:
       - Did the sim create an offer when the real bot did?
       - Did the sim cancel when the real bot did?
       - Are fill timings consistent?
    5. Flag divergences as annotations in the result.
    6. Return a result dict with full timeline + divergences + issues.

    Args:
        session: Parsed ReplaySession to replay.
        verbose: Print progress dots to stdout while running.

    Returns:
        Dict with keys: ticks (list of TickResult dicts), divergences (list
        of strings), issues (list of strings), pnl_xch (float),
        n_fills (int), n_cancels (int).
    """
    # Import engine lazily — the simulation package must be on sys.path
    try:
        from simulation.engine import SimBot, Scenario
    except ImportError:
        return {
            "error": "simulation.engine not importable — check sys.path",
            "ticks": [],
            "divergences": [],
            "issues": ["simulation.engine import failed"],
            "pnl_xch": 0.0,
            "n_fills": 0,
            "n_cancels": 0,
        }

    # Build scenario from config snapshot + known balances
    scenario = _scenario_from_session(session, Scenario)

    prices = session.price_series
    if not prices:
        prices = [0.001] * 100  # Flat fallback

    bot = SimBot(scenario)

    tick_results = []
    divergences = []

    # Index actual fill events by approximate tick for comparison
    actual_fills_by_tick: Dict[int, int] = {}
    for ev in session.fill_events:
        t = ev.tick_approx
        actual_fills_by_tick[t] = actual_fills_by_tick.get(t, 0) + 1

    actual_offers_by_tick: Dict[int, int] = {}
    for ev in session.offer_events:
        if "creat" in ev.event_type.lower():
            t = ev.tick_approx
            actual_offers_by_tick[t] = actual_offers_by_tick.get(t, 0) + 1

    n_ticks = len(prices)
    dot_interval = max(1, n_ticks // 20)

    for i, price in enumerate(prices):
        if verbose and i % dot_interval == 0:
            print(".", end="", flush=True)

        result = bot.tick(price)
        tick_results.append({
            "tick": result.tick,
            "price": result.price,
            "n_fills": len(result.fills),
            "new_offers": result.new_offers,
            "cancelled": result.cancelled_offers,
            "cb_tripped": result.cb_tripped,
            "cb_side": result.cb_side,
            "xch_balance": result.xch_balance,
            "cat_balance": result.cat_balance,
            "pnl_xch": result.pnl_xch,
        })

        # Divergence: real bot created offers this tick, sim didn't
        real_offers = actual_offers_by_tick.get(i, 0)
        sim_offers = result.new_offers
        if real_offers > 0 and sim_offers == 0:
            divergences.append(
                f"Tick ~{i}: Real bot created {real_offers} offer(s) but sim "
                f"created none — possible coin shortage or CB difference."
            )
        elif real_offers == 0 and sim_offers > 3:
            divergences.append(
                f"Tick ~{i}: Sim created {sim_offers} offer(s) but real bot "
                f"created none — config may differ."
            )

        # Divergence: fills don't align
        real_fills = actual_fills_by_tick.get(i, 0)
        sim_fills = len(result.fills)
        if real_fills > 0 and sim_fills == 0 and i < len(prices) - 1:
            # Allow a 1-tick slippage before flagging
            pass
        elif real_fills == 0 and sim_fills > 2:
            divergences.append(
                f"Tick ~{i}: Sim had {sim_fills} fill(s) but real bot had none "
                f"— spread or fill model may differ."
            )

    if verbose:
        print()  # newline after progress dots

    final_state = bot.get_state()
    issues = _identify_issues(session, tick_results, final_state)

    return {
        "ticks": tick_results,
        "divergences": divergences[:50],  # Cap to avoid huge output
        "issues": issues,
        "pnl_xch": final_state.get("pnl_xch", 0.0),
        "n_fills": final_state.get("total_fills", 0),
        "n_cancels": final_state.get("total_cancels", 0),
        "final_state": final_state,
    }


def analyse_errors(session: ReplaySession) -> List[str]:
    """Scan error_events and produce a plain-English diagnosis.

    Checks for known error patterns across all events in the session,
    not just error-severity events.

    Known patterns checked:
    - wallet_unreachable / connection refused → Sage RPC connectivity issue
    - insufficient_funds / insufficient funds → coin shortage / coin prep failure
    - Requote storm → cancel+create loop (REQUOTE_COOLDOWN_SECS too short)
    - Multiple CB trips in quick succession → spread too tight for volatility
    - fill_rejected / phantom → Spacescan false positives
    - Topup events with increasing backoff → coin shortage pattern
    - Python tracebacks in message → unhandled exception
    - mass_disappearance → offers vanished without confirmed fills

    Args:
        session: The parsed ReplaySession to analyse.

    Returns:
        List of plain-English finding strings, each with timestamp, cause,
        and a recommended fix.
    """
    findings: List[str] = []
    all_events = (
        session.error_events
        + session.cb_events
        + session.offer_events
        + session.fill_events
    )
    all_events.sort(key=lambda e: e.timestamp)

    # --- Wallet connectivity ---
    wallet_errs = [
        e for e in all_events
        if _matches_any(e, ["wallet_unreachable", "connection refused",
                            "connectionrefused", "rpc error", "wallet_error",
                            "rpc_timeout"])
    ]
    if wallet_errs:
        findings.append(
            f"At {wallet_errs[0].timestamp[:19]} UTC: Wallet RPC connectivity "
            f"issue — {len(wallet_errs)} event(s) matching 'wallet_unreachable' "
            f"/ 'connection refused'.\n"
            f"  Likely cause: Sage or Chia wallet was not running or RPC port changed.\n"
            f"  Fix: Verify the wallet is running before starting the bot. Check "
            f"RPC_HOST and RPC_PORT in your .env file."
        )

    # --- Coin shortage ---
    coin_errs = [
        e for e in all_events
        if _matches_any(e, ["insufficient_funds", "insufficient funds",
                            "no_coins", "no coins", "coin_prep", "coin prep failed",
                            "topup"])
    ]
    if coin_errs:
        findings.append(
            f"At {coin_errs[0].timestamp[:19]} UTC: Coin shortage pattern — "
            f"{len(coin_errs)} event(s) matching 'insufficient funds' / 'topup'.\n"
            f"  Likely cause: Coin prep failed or topup threshold is too low.\n"
            f"  Fix: Run coin prep manually. Increase TOPUP_THRESHOLD. Check "
            f"MIN_COIN_COUNT in config."
        )

    # --- Requote storm ---
    # A requote storm is >4 cancel+create cycles within a 4-minute window
    cancel_times = [e.timestamp for e in session.offer_events
                    if "cancel" in e.event_type.lower()]
    create_times = [e.timestamp for e in session.offer_events
                    if "creat" in e.event_type.lower()]
    storm_windows = _detect_burst(cancel_times + create_times, window_secs=240, threshold=8)
    if storm_windows:
        ts = storm_windows[0]
        findings.append(
            f"At {ts[:19]} UTC: Requote storm detected — >8 cancel+create cycles "
            f"in a 4-minute window.\n"
            f"  Likely cause: REQUOTE_BPS set too tight relative to market volatility.\n"
            f"  Fix: Increase REQUOTE_COOLDOWN_SECS (try 120s) or widen REQUOTE_BPS "
            f"(try 300+)."
        )

    # --- Circuit breaker storms ---
    cb_trip_times = [e.timestamp for e in session.cb_events
                     if "trip" in e.event_type.lower() or "tripped" in e.message.lower()]
    if len(cb_trip_times) >= 3:
        findings.append(
            f"At {cb_trip_times[0][:19]} UTC: Circuit breaker tripped "
            f"{len(cb_trip_times)} time(s) during the session.\n"
            f"  Likely cause: Spread too tight for volatility — the bot is accumulating "
            f"directional position faster than it can rebalance.\n"
            f"  Fix: Increase SPREAD_BPS or reduce MAX_POSITION_XCH. Consider widening "
            f"outer/extreme tiers."
        )
    elif len(cb_trip_times) > 0:
        findings.append(
            f"Circuit breaker tripped {len(cb_trip_times)} time(s). "
            f"Position limit was hit — check SPREAD_BPS and MAX_POSITION_XCH settings."
        )

    # --- Fill rejected / phantom ---
    phantom_errs = [
        e for e in all_events
        if _matches_any(e, ["fill_rejected", "phantom", "false_positive",
                            "spacescan", "unconfirmed fill"])
    ]
    if phantom_errs:
        findings.append(
            f"At {phantom_errs[0].timestamp[:19]} UTC: {len(phantom_errs)} phantom "
            f"fill event(s) detected ('fill_rejected' / 'phantom' / 'spacescan').\n"
            f"  Likely cause: Spacescan API returning stale or incorrect fill data.\n"
            f"  Fix: This is a known issue. The bot's mass-disappearance guard (3 "
            f"confirmations) should suppress these. Check FILL_CONFIRMATION_COUNT."
        )

    # --- Topup backoff pattern ---
    topup_backoff = [
        e for e in all_events
        if _matches_any(e, ["topup_backoff", "topup_waiting", "backoff"])
    ]
    if topup_backoff:
        findings.append(
            f"At {topup_backoff[0].timestamp[:19]} UTC: Topup backoff triggered "
            f"{len(topup_backoff)} time(s).\n"
            f"  Likely cause: Repeated coin prep failures — wallet may be fragmented "
            f"or RPC intermittently unavailable.\n"
            f"  Fix: Run coin prep manually between sessions. The bot uses exponential "
            f"backoff (5 min → 60 min max)."
        )

    # --- Tracebacks / unhandled exceptions ---
    tb_events = [
        e for e in all_events
        if "traceback" in e.message.lower()
        or "exception" in e.message.lower()
        or "error:" in e.message.lower()
    ]
    if tb_events:
        # Show just the first one in full, summarise the rest
        first = tb_events[0]
        findings.append(
            f"At {first.timestamp[:19]} UTC: Unhandled exception — "
            f"{len(tb_events)} traceback/exception event(s) found.\n"
            f"  First message: {first.message[:200]}\n"
            f"  Fix: Check the full log file for the Python traceback. "
            f"This is likely a bug — report with the log attached."
        )

    # --- Mass disappearance ---
    mass_dis = [
        e for e in all_events
        if _matches_any(e, ["mass_disappearance", "offers_vanished",
                            "mass disappear"])
    ]
    if mass_dis:
        findings.append(
            f"At {mass_dis[0].timestamp[:19]} UTC: Mass disappearance guard "
            f"triggered {len(mass_dis)} time(s).\n"
            f"  Likely cause: Blockchain reorganisation, or Dexie API returned "
            f"empty offer list transiently.\n"
            f"  Fix: This is usually self-correcting. If persistent, check Dexie "
            f"API health and MASS_DISAPPEARANCE_THRESHOLD."
        )

    if not findings:
        findings.append("No known error patterns detected in this session.")

    return findings


def generate_replay_report(session: ReplaySession, result: dict) -> str:
    """Produce a full human-readable report of the replay.

    Sections:
    1. Session Summary (duration, n events, n errors)
    2. Error Analysis (from analyse_errors)
    3. Simulation Replay Results (from result['issues'])
    4. Timeline of significant events (CB trips, error spikes, fill clusters)
    5. Recommended Fixes (numbered, specific, actionable)

    Args:
        session: The parsed ReplaySession.
        result: Dict returned by replay_session().

    Returns:
        Formatted string suitable for printing or saving to a .txt file.
    """
    lines: List[str] = []
    sep = "=" * 72

    lines.append(sep)
    lines.append("  BOT SESSION REPLAY REPORT")
    lines.append(sep)

    # --- 1. Session Summary ---
    lines.append("")
    lines.append("1. SESSION SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Session ID     : {session.session_id}")
    lines.append(f"  Start time     : {session.start_time}")
    lines.append(f"  End time       : {session.end_time}")
    lines.append(f"  Total events   : {session.n_events}")
    lines.append(f"  Error events   : {len(session.error_events)}")
    lines.append(f"  CB events      : {len(session.cb_events)}")
    lines.append(f"  Fill events    : {len(session.fill_events)}")
    lines.append(f"  Offer events   : {len(session.offer_events)}")
    lines.append(f"  Price ticks    : {len(session.price_series)}")
    lines.append(f"  Approx XCH     : {session.approx_starting_xch:.4f}")
    lines.append(f"  Approx CAT     : {session.approx_starting_cat:.1f}")
    if session.config_snapshot:
        lines.append(f"  Config keys    : {', '.join(sorted(session.config_snapshot.keys())[:8])}")

    # --- 2. Error Analysis ---
    lines.append("")
    lines.append("2. ERROR ANALYSIS")
    lines.append("-" * 40)
    findings = analyse_errors(session)
    for i, finding in enumerate(findings, 1):
        lines.append(f"  [{i}] {finding}")
        lines.append("")

    # --- 3. Simulation Replay Results ---
    lines.append("3. SIMULATION REPLAY RESULTS")
    lines.append("-" * 40)
    if "error" in result:
        lines.append(f"  ERROR: {result['error']}")
    else:
        lines.append(f"  Ticks simulated : {len(result.get('ticks', []))}")
        lines.append(f"  Sim fills       : {result.get('n_fills', 0)}")
        lines.append(f"  Sim cancels     : {result.get('n_cancels', 0)}")
        lines.append(f"  Final P&L (XCH) : {result.get('pnl_xch', 0.0):+.6f}")
        divergences = result.get("divergences", [])
        if divergences:
            lines.append(f"  Divergences     : {len(divergences)}")
            for d in divergences[:5]:
                lines.append(f"    - {d}")
            if len(divergences) > 5:
                lines.append(f"    ... and {len(divergences) - 5} more.")
        else:
            lines.append("  Divergences     : None (sim aligned well with real session)")

        issues = result.get("issues", [])
        if issues:
            lines.append(f"  Issues detected :")
            for iss in issues:
                lines.append(f"    - {iss}")

    # --- 4. Timeline of Significant Events ---
    lines.append("")
    lines.append("4. TIMELINE OF SIGNIFICANT EVENTS")
    lines.append("-" * 40)
    timeline = _build_timeline(session)
    if timeline:
        for entry in timeline[:30]:
            lines.append(f"  {entry}")
    else:
        lines.append("  No significant events recorded.")

    # --- 5. Recommended Fixes ---
    lines.append("")
    lines.append("5. RECOMMENDED FIXES")
    lines.append("-" * 40)
    fixes = _generate_fixes(session, result, findings)
    if fixes:
        for i, fix in enumerate(fixes, 1):
            lines.append(f"  {i}. {fix}")
    else:
        lines.append("  No specific fixes recommended — session appears healthy.")

    lines.append("")
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_metadata(raw) -> dict:
    """Parse metadata field — handles JSON string, dict, or None.

    Args:
        raw: The raw value from the data/metadata column.

    Returns:
        A plain dict (empty dict on failure).
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _extract_price_from_event(event: LogEvent) -> Optional[float]:
    """Try to extract a price reference from any event's metadata.

    Looks for keys: mid_price, price, offer_price, bid, ask, tibet_price,
    combined_price, dexie_price in the metadata dict.  Also attempts a
    regex scan of the message string as a fallback.

    Args:
        event: The LogEvent to inspect.

    Returns:
        A positive float price if found, else None.
    """
    price_keys = [
        "mid_price", "price", "offer_price", "bid", "ask",
        "tibet_price", "combined_price", "dexie_price",
    ]
    for key in price_keys:
        val = event.metadata.get(key)
        if val is not None:
            try:
                p = float(val)
                if p > 0:
                    return p
            except (TypeError, ValueError):
                pass

    # Fallback: scan message string for price-like patterns
    # e.g. "mid=0.00123" or "price: 0.00456"
    matches = re.findall(r'(?:price|mid|bid|ask)[=:\s]+([0-9]+\.?[0-9]*(?:e[+-]?[0-9]+)?)',
                         event.message, re.IGNORECASE)
    for m in matches:
        try:
            p = float(m)
            if 0 < p < 1000:  # Sanity check: XCH/CAT prices in this range
                return p
        except ValueError:
            pass

    return None


def _interpolate_prices(
    known_prices: List[Tuple[int, float]],
    n_ticks: int,
    starting_price: float = 0.001,
) -> List[float]:
    """Fill in a price series by linear interpolation between known points.

    Args:
        known_prices: List of (tick_index, price) tuples sorted by tick index.
        n_ticks: Total number of ticks to generate.
        starting_price: Fallback price if known_prices is empty.

    Returns:
        List of float prices of length n_ticks.
    """
    if n_ticks <= 0:
        return []

    if not known_prices:
        return [starting_price] * n_ticks

    # Sort by tick index
    known_prices = sorted(known_prices, key=lambda x: x[0])

    result = [starting_price] * n_ticks

    # Fill before the first known price
    first_tick, first_price = known_prices[0]
    for i in range(min(first_tick, n_ticks)):
        result[i] = first_price

    # Linear interpolation between known points
    for k in range(len(known_prices) - 1):
        t0, p0 = known_prices[k]
        t1, p1 = known_prices[k + 1]
        t0 = max(0, min(t0, n_ticks - 1))
        t1 = max(0, min(t1, n_ticks - 1))
        if t1 <= t0:
            continue
        span = t1 - t0
        for i in range(t0, t1 + 1):
            if i >= n_ticks:
                break
            frac = (i - t0) / span
            result[i] = p0 + frac * (p1 - p0)

    # Fill after the last known price
    last_tick, last_price = known_prices[-1]
    for i in range(min(last_tick, n_ticks - 1) + 1, n_ticks):
        result[i] = last_price

    return result


def _classify_event(event_type: str, message: str, metadata: dict) -> str:
    """Map a raw event_type to a canonical category.

    Categories: price / offer / fill / error / cb / wallet / system

    Args:
        event_type: Raw event_type string from the events table.
        message: The human-readable message (used as secondary signal).
        metadata: Parsed metadata dict.

    Returns:
        One of: 'price', 'offer', 'fill', 'error', 'cb', 'wallet', 'system'.
    """
    et = event_type.lower()
    msg = message.lower()

    if any(kw in et for kw in ("circuit_breaker", "cb_", "position_limit")):
        return "cb"
    if any(kw in et for kw in ("fill", "filled", "round_trip")):
        return "fill"
    if any(kw in et for kw in ("offer_creat", "offer_cancel", "offer_post",
                               "requote", "offer_expired")):
        return "offer"
    if any(kw in et for kw in ("price", "mid_price", "tibet", "dexie_price")):
        return "price"
    if any(kw in et for kw in ("wallet", "balance", "coin", "topup", "split")):
        return "wallet"
    if any(kw in et for kw in ("error", "fail", "exception", "crash", "traceback")):
        return "error"
    if any(kw in et for kw in ("startup", "config", "shutdown", "restart")):
        return "system"

    # Fallback: check message keywords
    if any(kw in msg for kw in ("fill", "filled")):
        return "fill"
    if any(kw in msg for kw in ("offer", "cancel", "requote")):
        return "offer"
    if any(kw in msg for kw in ("error", "exception", "fail", "traceback")):
        return "error"
    if any(kw in msg for kw in ("wallet", "coin", "balance")):
        return "wallet"
    if any(kw in msg for kw in ("price", "mid")):
        return "price"

    return "system"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_session(rows: List[dict], session_id: str) -> ReplaySession:
    """Convert raw DB row dicts into a ReplaySession.

    Args:
        rows: List of dicts from the events table (sorted by timestamp).
        session_id: Identifier for the session.

    Returns:
        Populated ReplaySession.
    """
    if not rows:
        return ReplaySession(
            session_id=session_id,
            start_time="",
            end_time="",
            n_events=0,
            price_series=[],
            offer_events=[],
            error_events=[],
            cb_events=[],
            fill_events=[],
            config_snapshot={},
            approx_starting_xch=0.0,
            approx_starting_cat=0.0,
        )

    n = len(rows)
    start_time = rows[0].get("timestamp", "")
    end_time = rows[-1].get("timestamp", "")

    log_events: List[LogEvent] = []
    for idx, row in enumerate(rows):
        ts = str(row.get("timestamp", ""))
        et = str(row.get("event_type", "unknown"))
        msg = str(row.get("message", ""))
        sev = str(row.get("severity", "info"))
        meta = _parse_metadata(row.get("data"))

        category = _classify_event(et, msg, meta)
        tick_approx = idx  # Each row is treated as one approximate tick

        log_events.append(LogEvent(
            timestamp=ts,
            tick_approx=tick_approx,
            event_type=et,
            category=category,
            severity=sev,
            message=msg,
            metadata=meta,
        ))

    # Partition into sub-lists
    offer_events = [e for e in log_events if e.category == "offer"]
    error_events = [
        e for e in log_events
        if e.category == "error" or e.severity == "error"
        or any(kw in e.event_type.lower()
               for kw in ("error", "fail", "exception", "traceback"))
    ]
    cb_events = [e for e in log_events if e.category == "cb"]
    fill_events = [e for e in log_events if e.category == "fill"]

    # Reconstruct price series
    known_prices: List[Tuple[int, float]] = []
    for ev in log_events:
        p = _extract_price_from_event(ev)
        if p is not None:
            known_prices.append((ev.tick_approx, p))

    # Use number of events as tick count (1 event ≈ 1 tick for interpolation)
    price_series = _interpolate_prices(known_prices, n, starting_price=0.001)

    # Config snapshot — look for startup / config_loaded events
    config_snapshot: dict = {}
    for ev in log_events:
        if ev.event_type.lower() in ("config_loaded", "startup", "bot_start",
                                     "config_snapshot"):
            if ev.metadata:
                config_snapshot.update(ev.metadata)

    # Approximate starting balances from the earliest wallet events
    approx_xch = 0.0
    approx_cat = 0.0
    for ev in log_events[:50]:  # Only look at session start
        xch_val = ev.metadata.get("xch_balance") or ev.metadata.get("xch")
        cat_val = ev.metadata.get("cat_balance") or ev.metadata.get("cat")
        if xch_val and approx_xch == 0.0:
            try:
                approx_xch = float(xch_val)
            except (TypeError, ValueError):
                pass
        if cat_val and approx_cat == 0.0:
            try:
                approx_cat = float(cat_val)
            except (TypeError, ValueError):
                pass

    return ReplaySession(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        n_events=n,
        price_series=price_series,
        offer_events=offer_events,
        error_events=error_events,
        cb_events=cb_events,
        fill_events=fill_events,
        config_snapshot=config_snapshot,
        approx_starting_xch=approx_xch if approx_xch > 0 else 10.0,
        approx_starting_cat=approx_cat if approx_cat > 0 else 5000.0,
    )


def _scenario_from_session(session: ReplaySession, Scenario) -> object:
    """Build a Scenario object from a ReplaySession's config snapshot.

    Falls back to sensible defaults for any missing config keys.

    Args:
        session: The ReplaySession to extract config from.
        Scenario: The Scenario class (passed in to avoid circular import).

    Returns:
        A Scenario instance populated from the config snapshot.
    """
    cfg = session.config_snapshot

    def _get(key, default):
        val = cfg.get(key)
        if val is None:
            return default
        try:
            return type(default)(val)
        except (TypeError, ValueError):
            return default

    return Scenario(
        spread_bps=_get("SPREAD_BPS", 800.0),
        requote_bps=_get("REQUOTE_BPS", 150.0),
        n_inner=_get("MAX_BUY_OFFERS", 3),
        n_mid=_get("MID_OFFERS", 3),
        n_outer=_get("OUTER_OFFERS", 2),
        n_extreme=_get("EXTREME_OFFERS", 1),
        inner_size_xch=_get("INNER_SIZE_XCH", 1.0),
        mid_size_xch=_get("MID_SIZE_XCH", 0.5),
        outer_size_xch=_get("OUTER_SIZE_XCH", 0.25),
        extreme_size_xch=_get("EXTREME_SIZE_XCH", 0.1),
        starting_xch=session.approx_starting_xch,
        starting_cat=session.approx_starting_cat,
        xch_coin_size=_get("XCH_COIN_SIZE", 0.5),
        cat_coin_size_tokens=_get("CAT_COIN_SIZE", 500.0),
        xch_reserve=_get("XCH_RESERVE", 0.03),
        cat_reserve=_get("CAT_RESERVE", 0.0),
        max_position_xch=_get("MAX_POSITION_XCH", 5.0),
        cat_decimals=_get("CAT_DECIMALS", 3),
        name=f"replay_{session.session_id}",
    )


def _matches_any(event: LogEvent, keywords: List[str]) -> bool:
    """Return True if any keyword appears in the event's type or message.

    Case-insensitive.

    Args:
        event: The LogEvent to check.
        keywords: List of lowercase keyword strings.
    """
    combined = (event.event_type + " " + event.message).lower()
    return any(kw in combined for kw in keywords)


def _detect_burst(
    timestamps: List[str],
    window_secs: int = 240,
    threshold: int = 8,
) -> List[str]:
    """Find time windows with more than threshold events.

    Uses a simple sliding window over ISO timestamp strings.
    Returns the timestamp of the first event in each burst window.

    Args:
        timestamps: List of ISO timestamp strings.
        window_secs: Size of the detection window in seconds.
        threshold: Minimum events in window to count as a burst.

    Returns:
        List of ISO timestamp strings marking burst starts.
    """
    if not timestamps:
        return []

    # Convert to epoch seconds — attempt ISO parse then fall back to ordinal
    epoch_times: List[float] = []
    for ts in sorted(timestamps):
        try:
            # Python 3.7+: fromisoformat doesn't support 'Z' suffix
            clean = ts.replace("Z", "+00:00")
            from datetime import datetime as _dt
            epoch_times.append(_dt.fromisoformat(clean).timestamp())
        except (ValueError, AttributeError):
            epoch_times.append(0.0)

    epoch_times = [t for t in epoch_times if t > 0]
    if not epoch_times:
        return []

    bursts: List[str] = []
    i = 0
    while i < len(epoch_times):
        window_end = epoch_times[i] + window_secs
        count = sum(1 for t in epoch_times if epoch_times[i] <= t <= window_end)
        if count >= threshold:
            bursts.append(timestamps[i] if i < len(timestamps) else "")
            # Advance past the window
            i += count
        else:
            i += 1

    return bursts


def _build_timeline(session: ReplaySession) -> List[str]:
    """Build a compact timeline of the most significant session events.

    Selects CB trips, error spikes, and fill clusters.  At most 30 entries.

    Args:
        session: The parsed ReplaySession.

    Returns:
        List of formatted timeline strings.
    """
    timeline: List[str] = []

    for ev in session.cb_events[:10]:
        timeline.append(
            f"{ev.timestamp[:19]}  [CB]    {ev.event_type} — {ev.message[:60]}"
        )
    for ev in session.error_events[:10]:
        timeline.append(
            f"{ev.timestamp[:19]}  [ERR]   {ev.event_type} — {ev.message[:60]}"
        )

    # Fill clusters: groups of fills within 60s
    fill_ts = [ev.timestamp for ev in session.fill_events]
    fill_bursts = _detect_burst(fill_ts, window_secs=60, threshold=3)
    for ts in fill_bursts[:5]:
        count = sum(1 for ft in fill_ts
                    if ft >= ts and (ft[:16] <= ts[:16] or True))
        timeline.append(
            f"{ts[:19]}  [FILL]  Fill cluster — "
            f"{min(count, len(fill_ts))} fills near this time"
        )

    # Sort by timestamp
    timeline.sort()
    return timeline[:30]


def _identify_issues(
    session: ReplaySession,
    tick_results: List[dict],
    final_state: dict,
) -> List[str]:
    """Identify issues from the sim run in the context of the real session.

    Args:
        session: The real ReplaySession.
        tick_results: List of tick result dicts from replay_session().
        final_state: Final state dict from SimBot.get_state().

    Returns:
        List of issue strings.
    """
    issues: List[str] = []

    # CB trips in sim
    cb_ticks = [t for t in tick_results if t.get("cb_tripped")]
    if len(cb_ticks) > len(tick_results) * 0.1:
        issues.append(
            f"CB was active for {len(cb_ticks)}/{len(tick_results)} ticks "
            f"({100 * len(cb_ticks) // max(1, len(tick_results))}%) — "
            f"position limit too tight or spread too narrow."
        )

    # Wallet exhaustion
    low_xch = [t for t in tick_results if t.get("xch_balance", 1.0) < 0.1]
    if low_xch:
        issues.append(
            f"XCH balance dropped below 0.1 at tick {low_xch[0]['tick']} — "
            f"consider increasing starting capital or reducing offer sizes."
        )

    low_cat = [t for t in tick_results if t.get("cat_balance", 1.0) < 10.0]
    if low_cat:
        issues.append(
            f"CAT balance dropped below 10 at tick {low_cat[0]['tick']} — "
            f"rebalance needed or reduce sell tier sizes."
        )

    # Negative P&L
    pnl = final_state.get("pnl_xch", 0.0)
    if pnl < -0.01:
        issues.append(
            f"Simulation ended with negative P&L: {pnl:+.6f} XCH — "
            f"spread may be too tight to cover fees and slippage."
        )

    return issues


def _generate_fixes(
    session: ReplaySession,
    result: dict,
    findings: List[str],
) -> List[str]:
    """Derive actionable fix recommendations from findings and sim results.

    Args:
        session: The ReplaySession.
        result: Dict from replay_session().
        findings: Findings from analyse_errors().

    Returns:
        List of specific, actionable fix strings.
    """
    fixes: List[str] = []

    # Map finding keywords to fixes
    for finding in findings:
        fl = finding.lower()
        if "requote storm" in fl:
            fixes.append(
                "Increase REQUOTE_COOLDOWN_SECS to at least 120 seconds, "
                "or increase REQUOTE_BPS above 300 to tolerate normal volatility."
            )
        if "wallet rpc" in fl or "connectivity" in fl:
            fixes.append(
                "Ensure the Sage/Chia wallet is fully synced before starting "
                "the bot. Add a health check to startup_test.py."
            )
        if "coin shortage" in fl:
            fixes.append(
                "Run coin prep manually: set MIN_COIN_COUNT higher and "
                "trigger a topup before the session starts."
            )
        if "circuit breaker" in fl and "tripped" in fl:
            fixes.append(
                "Widen SPREAD_BPS (try doubling it) or increase "
                "MAX_POSITION_XCH to reduce CB frequency."
            )
        if "phantom" in fl or "spacescan" in fl:
            fixes.append(
                "Increase FILL_CONFIRMATION_COUNT to 3 to suppress Spacescan "
                "false positives. Already the default — check it hasn't been overridden."
            )
        if "mass disappearance" in fl:
            fixes.append(
                "Check Dexie API status during this window. If recurrent, "
                "increase MASS_DISAPPEARANCE_THRESHOLD."
            )

    # Sim-derived fixes
    issues = result.get("issues", [])
    for iss in issues:
        il = iss.lower()
        if "cb was active" in il:
            fixes.append(
                "Simulation shows CB active >10% of ticks — strongly consider "
                "widening SPREAD_BPS or reducing offer sizes."
            )
        if "xch balance" in il:
            fixes.append(
                "Sim ran out of XCH — add more capital or reduce INNER_SIZE_XCH."
            )
        if "cat balance" in il:
            fixes.append(
                "Sim ran out of CAT — rebalance the portfolio before next session."
            )
        if "negative p&l" in il:
            fixes.append(
                "Negative sim P&L — increase SPREAD_BPS to capture more per fill."
            )

    # Deduplicate while preserving order
    seen: set = set()
    unique_fixes: List[str] = []
    for f in fixes:
        key = f[:40]
        if key not in seen:
            seen.add(key)
            unique_fixes.append(f)

    return unique_fixes
