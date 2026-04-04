#!/usr/bin/env python3
"""
Probe Sage offer creation methods and report the actual maker inputs used.

This script is meant to answer one question:
when we create offers in different ways, which coins does Sage actually lock?

Recommended usage:
  1. Run coin prep first so you have a clean pool of prepared trading coins.
  2. Stop the bot so wallet state is stable while this runs.
  3. Run this script from the same Python interpreter/environment as the app.

Examples:
  python probe_offer_creation_methods.py
  python probe_offer_creation_methods.py --repeat 5 --workers 1
  python probe_offer_creation_methods.py --repeat 10 --workers 5 --methods wallet_selected
  python probe_offer_creation_methods.py --methods wallet_selected,manager_selected,wallet_hints_only
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    from config import cfg
    from database import DB_PATH
    from offer_manager import OfferManager
    from wallet import (
        WALLET_ID_XCH,
        cancel_offer,
        create_offer as wallet_create_offer,
        get_owned_coins_detailed,
        get_wallet_type,
    )
except ModuleNotFoundError as exc:
    print(
        "Import failed. Run this script with the same Python interpreter the bot uses.\n"
        f"Missing module: {exc}",
        file=sys.stderr,
    )
    raise


METHODS = (
    "wallet_selected",
    "manager_selected",
    "wallet_hints_only",
    "wallet_unconstrained",
)


@dataclass
class CoinChoice:
    wallet_type: str
    coin_id: str
    amount_mojos: int
    assigned_tier: str


def norm_coin_id(value: Optional[str]) -> str:
    if not value:
        return ""
    cid = str(value).strip().lower()
    if not cid.startswith("0x"):
        cid = "0x" + cid
    return cid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Sage offer creation methods and record locked inputs."
    )
    parser.add_argument(
        "--methods",
        default="wallet_selected,manager_selected",
        help=f"Comma-separated methods to run. Available: {', '.join(METHODS)}",
    )
    parser.add_argument(
        "--assets",
        default="xch,cat",
        help="Comma-separated spend assets to test: xch, cat",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="How many offers to create per method per asset.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="How many offers to create concurrently within each method batch.",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=0,
        help="Delay between task submissions inside a method batch.",
    )
    parser.add_argument(
        "--settle-secs",
        type=float,
        default=2.0,
        help="Initial wait before checking Sage locked inputs.",
    )
    parser.add_argument(
        "--poll-count",
        type=int,
        default=8,
        help="How many times to poll Sage for exact locked inputs.",
    )
    parser.add_argument(
        "--poll-interval-secs",
        type=float,
        default=1.0,
        help="Delay between exact locked-input polls.",
    )
    parser.add_argument(
        "--post-method-settle-secs",
        type=float,
        default=3.0,
        help="Wait after each method batch so cancels can settle.",
    )
    parser.add_argument(
        "--offer-ratio",
        type=float,
        default=0.90,
        help="Spend this fraction of the selected coin amount when building selected-coin tests.",
    )
    parser.add_argument(
        "--xch-request-cat-mojos",
        type=int,
        default=100_000,
        help="Requested CAT mojos for XCH-spend test offers.",
    )
    parser.add_argument(
        "--cat-request-xch-mojos",
        type=int,
        default=100_000_000_000,
        help="Requested XCH mojos for CAT-spend test offers.",
    )
    parser.add_argument(
        "--max-time-secs",
        type=int,
        default=300,
        help="Offer expiry window used for probe offers.",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Optional output path for the JSON report.",
    )
    parser.add_argument(
        "--keep-offers",
        action="store_true",
        help="Do not cancel the created offers after inspection.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    args.methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    args.assets = [a.strip().lower() for a in args.assets.split(",") if a.strip()]

    unknown_methods = sorted(set(args.methods) - set(METHODS))
    if unknown_methods:
        raise SystemExit(f"Unknown methods: {', '.join(unknown_methods)}")

    bad_assets = sorted(set(args.assets) - {"xch", "cat"})
    if bad_assets:
        raise SystemExit(f"Unknown assets: {', '.join(bad_assets)}")

    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")
    if args.offer_ratio <= 0 or args.offer_ratio >= 1:
        raise SystemExit("--offer-ratio must be > 0 and < 1")


def get_cat_wallet_id() -> int:
    return int(cfg.CAT_WALLET_ID)


def get_spend_wallet_id(wallet_type: str) -> int:
    if wallet_type == "xch":
        return int(WALLET_ID_XCH)
    if wallet_type == "cat":
        return get_cat_wallet_id()
    raise ValueError(f"Unknown wallet_type {wallet_type}")


def pick_smallest_spare_coins(wallet_type: str, count: int) -> List[CoinChoice]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            select coin_id, amount_mojos, assigned_tier
            from coins
            where status='free'
              and designation='tier_spare'
              and wallet_type=?
            order by amount_mojos asc, coin_id asc
            limit ?
            """,
            (wallet_type, count),
        ).fetchall()
    finally:
        conn.close()

    return [
        CoinChoice(
            wallet_type=wallet_type,
            coin_id=norm_coin_id(row["coin_id"]),
            amount_mojos=int(row["amount_mojos"]),
            assigned_tier=row["assigned_tier"] or "unknown",
        )
        for row in rows
    ]


def extract_trade_id(result: Optional[dict]) -> str:
    if not isinstance(result, dict):
        return ""
    trade_id = result.get("trade_id") or result.get("offer_id") or ""
    if not trade_id:
        trade_record = result.get("trade_record") or {}
        if isinstance(trade_record, dict):
            trade_id = trade_record.get("trade_id") or trade_record.get("offer_id") or ""
    if not trade_id:
        offer_obj = result.get("offer") or {}
        if isinstance(offer_obj, dict):
            trade_id = offer_obj.get("id") or offer_obj.get("offer_id") or ""
    return str(trade_id or "")


def build_offer_dict(
    wallet_type: str,
    selected_amount_mojos: Optional[int],
    args: argparse.Namespace,
) -> Dict[str, int]:
    if wallet_type == "xch":
        spend_mojos = 1_000_000_000
        if selected_amount_mojos:
            spend_mojos = min(spend_mojos, max(1, int(selected_amount_mojos * args.offer_ratio)))
            if selected_amount_mojos > 1:
                spend_mojos = min(spend_mojos, selected_amount_mojos - 1)
        return {
            str(int(WALLET_ID_XCH)): -int(spend_mojos),
            str(int(get_cat_wallet_id())): int(args.xch_request_cat_mojos),
        }

    if wallet_type == "cat":
        spend_mojos = 8_000
        if selected_amount_mojos:
            spend_mojos = min(spend_mojos, max(1, int(selected_amount_mojos * args.offer_ratio)))
            if selected_amount_mojos > 1:
                spend_mojos = min(spend_mojos, selected_amount_mojos - 1)
        return {
            str(int(get_cat_wallet_id())): -int(spend_mojos),
            str(int(WALLET_ID_XCH)): int(args.cat_request_xch_mojos),
        }

    raise ValueError(f"Unsupported wallet_type {wallet_type}")


def get_spend_amount_mojos(offer_dict: Dict[str, int], wallet_type: str) -> int:
    wallet_id = str(get_spend_wallet_id(wallet_type))
    amount = int(offer_dict.get(wallet_id, 0))
    if amount >= 0:
        raise ValueError(f"Offer dict has no negative spend for {wallet_type}: {offer_dict}")
    return abs(amount)


def get_exact_locked_inputs(
    wallet_id: int,
    trade_id: str,
    settle_secs: float,
    poll_count: int,
    poll_interval_secs: float,
) -> List[Dict[str, int]]:
    if settle_secs > 0:
        time.sleep(settle_secs)

    for poll in range(poll_count):
        owned = get_owned_coins_detailed(wallet_id) or {}
        locked_inputs = []
        for coin_id, info in owned.items():
            offer_id = str(info.get("offer_id") or "").lower()
            if offer_id == trade_id.lower():
                locked_inputs.append(
                    {
                        "coin_id": norm_coin_id(coin_id),
                        "amount_mojos": int(info.get("amount") or 0),
                    }
                )
        if locked_inputs:
            locked_inputs.sort(key=lambda item: (item["amount_mojos"], item["coin_id"]))
            return locked_inputs
        if poll < poll_count - 1 and poll_interval_secs > 0:
            time.sleep(poll_interval_secs)
    return []


def run_wallet_create(
    wallet_type: str,
    offer_dict: Dict[str, int],
    selected_coin_id: Optional[str],
    selected_amount_mojos: Optional[int],
    args: argparse.Namespace,
    method: str,
) -> Dict:
    spend_mojos = get_spend_amount_mojos(offer_dict, wallet_type)
    kwargs = {
        "validate_only": False,
        "max_time": int(time.time()) + int(args.max_time_secs),
    }

    if method == "wallet_selected":
        kwargs["coin_ids"] = [selected_coin_id]
    elif method == "wallet_hints_only":
        kwargs["min_coin_amount"] = max(1, int(spend_mojos * 0.8))
        if selected_amount_mojos:
            kwargs["max_coin_amount"] = int(max(selected_amount_mojos, spend_mojos))
        else:
            kwargs["max_coin_amount"] = int(spend_mojos * 2.0)
    elif method == "wallet_unconstrained":
        pass
    else:
        raise ValueError(f"Unsupported direct wallet method: {method}")

    return wallet_create_offer(offer_dict, **kwargs)


def run_manager_create(
    wallet_type: str,
    offer_dict: Dict[str, int],
    selected_coin_id: str,
) -> Dict:
    manager = OfferManager()
    return manager.create_offer_with_retry(
        offer_dict=offer_dict,
        max_retries=0,
        coin_ids_enabled=True,
        selected_coin_id=selected_coin_id,
        used_coins=set(),
    )


def run_one_case(case: Dict, args: argparse.Namespace) -> Dict:
    wallet_type = case["wallet_type"]
    method = case["method"]
    selected_coin: Optional[CoinChoice] = case.get("selected_coin")
    selected_coin_id = selected_coin.coin_id if selected_coin else ""
    selected_amount_mojos = selected_coin.amount_mojos if selected_coin else None
    offer_dict = build_offer_dict(wallet_type, selected_amount_mojos, args)
    spend_amount_mojos = get_spend_amount_mojos(offer_dict, wallet_type)

    started_at = utc_now_iso()
    create_result: Optional[Dict] = None
    create_error = ""
    trade_id = ""
    locked_inputs: List[Dict[str, int]] = []
    cancel_result = None

    try:
        if method == "manager_selected":
            create_result = run_manager_create(wallet_type, offer_dict, selected_coin_id)
        else:
            create_result = run_wallet_create(
                wallet_type=wallet_type,
                offer_dict=offer_dict,
                selected_coin_id=selected_coin_id or None,
                selected_amount_mojos=selected_amount_mojos,
                args=args,
                method=method,
            )
        trade_id = extract_trade_id(create_result)
        if trade_id:
            locked_inputs = get_exact_locked_inputs(
                wallet_id=get_spend_wallet_id(wallet_type),
                trade_id=trade_id,
                settle_secs=args.settle_secs,
                poll_count=args.poll_count,
                poll_interval_secs=args.poll_interval_secs,
            )
            if not args.keep_offers:
                cancel_result = cancel_offer(trade_id, secure=False, timeout=30)
        else:
            create_error = str((create_result or {}).get("error", "missing_trade_id"))
    except Exception as exc:
        create_error = str(exc)

    locked_coin_ids = [item["coin_id"] for item in locked_inputs]
    selected_present = None
    selected_exclusive = None
    if selected_coin_id:
        normalized_selected = norm_coin_id(selected_coin_id)
        selected_present = normalized_selected in locked_coin_ids
        selected_exclusive = selected_present and len(locked_coin_ids) == 1

    extra_inputs = []
    if selected_coin_id:
        normalized_selected = norm_coin_id(selected_coin_id)
        extra_inputs = [item for item in locked_inputs if item["coin_id"] != normalized_selected]

    result = {
        "method": method,
        "wallet_type": wallet_type,
        "case_index": case["case_index"],
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "selected_coin_id": selected_coin_id,
        "selected_coin_amount_mojos": selected_amount_mojos,
        "selected_coin_tier": selected_coin.assigned_tier if selected_coin else None,
        "offer_dict": offer_dict,
        "spend_amount_mojos": spend_amount_mojos,
        "selected_covers_offer": (
            selected_amount_mojos is None or selected_amount_mojos >= spend_amount_mojos
        ),
        "create_result": create_result,
        "trade_id": trade_id,
        "locked_inputs": locked_inputs,
        "locked_input_count": len(locked_inputs),
        "selected_present": selected_present,
        "selected_exclusive": selected_exclusive,
        "extra_inputs": extra_inputs,
        "cancel_result": cancel_result,
        "create_error": create_error,
    }
    return result


def summarize(results: List[Dict]) -> List[Dict]:
    summary = {}
    for item in results:
        key = (item["method"], item["wallet_type"])
        bucket = summary.setdefault(
            key,
            {
                "method": item["method"],
                "wallet_type": item["wallet_type"],
                "cases": 0,
                "created": 0,
                "selected_present": 0,
                "selected_missing": 0,
                "selected_exclusive": 0,
                "extra_input_cases": 0,
                "wrong_single_input_cases": 0,
                "errors": 0,
            },
        )
        bucket["cases"] += 1
        if item.get("trade_id"):
            bucket["created"] += 1
        else:
            bucket["errors"] += 1

        if item.get("selected_present") is True:
            bucket["selected_present"] += 1
        elif item.get("selected_present") is False:
            bucket["selected_missing"] += 1

        if item.get("selected_exclusive") is True:
            bucket["selected_exclusive"] += 1

        if item.get("extra_inputs"):
            bucket["extra_input_cases"] += 1

        if (
            item.get("selected_coin_id")
            and item.get("locked_input_count") == 1
            and item.get("selected_present") is False
        ):
            bucket["wrong_single_input_cases"] += 1

    rows = list(summary.values())
    rows.sort(key=lambda row: (row["method"], row["wallet_type"]))
    return rows


def print_summary(summary_rows: List[Dict]) -> None:
    if not summary_rows:
        log("No results to summarize.")
        return

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    header = (
        f"{'Method':<22} {'Asset':<5} {'Cases':>5} {'Made':>5} "
        f"{'SelOK':>6} {'SelOnly':>7} {'SelMiss':>7} {'Extra':>6} "
        f"{'Wrong1':>7} {'Err':>4}"
    )
    print(header)
    print("-" * len(header))
    for row in summary_rows:
        print(
            f"{row['method']:<22} {row['wallet_type']:<5} {row['cases']:>5} "
            f"{row['created']:>5} {row['selected_present']:>6} "
            f"{row['selected_exclusive']:>7} {row['selected_missing']:>7} "
            f"{row['extra_input_cases']:>6} {row['wrong_single_input_cases']:>7} "
            f"{row['errors']:>4}"
        )
    print("=" * 100)


def default_report_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return PROJECT_DIR / f"offer_method_probe_{stamp}.json"


def main() -> int:
    args = parse_args()
    validate_args(args)

    if get_wallet_type() != "sage":
        print("This script only supports the Sage wallet backend.", file=sys.stderr)
        return 2

    selected_task_count = sum(
        args.repeat
        for method in args.methods
        if method in {"wallet_selected", "manager_selected"}
    )
    xch_selected_pool = pick_smallest_spare_coins("xch", selected_task_count)
    cat_selected_pool = pick_smallest_spare_coins("cat", selected_task_count)

    if "xch" in args.assets and len(xch_selected_pool) < selected_task_count:
        print(
            f"Need {selected_task_count} free XCH tier_spare coins, found {len(xch_selected_pool)}.",
            file=sys.stderr,
        )
        return 2
    if "cat" in args.assets and len(cat_selected_pool) < selected_task_count:
        print(
            f"Need {selected_task_count} free CAT tier_spare coins, found {len(cat_selected_pool)}.",
            file=sys.stderr,
        )
        return 2

    log("Starting offer creation probe")
    log(f"Methods: {', '.join(args.methods)}")
    log(f"Assets: {', '.join(args.assets)}")
    log(f"Repeat: {args.repeat}, Workers: {args.workers}, Pause: {args.pause_ms}ms")

    xch_cursor = 0
    cat_cursor = 0
    all_results: List[Dict] = []

    for method in args.methods:
        method_cases = []
        for wallet_type in args.assets:
            for case_index in range(args.repeat):
                selected_coin = None
                if method in {"wallet_selected", "manager_selected"}:
                    if wallet_type == "xch":
                        selected_coin = xch_selected_pool[xch_cursor]
                        xch_cursor += 1
                    else:
                        selected_coin = cat_selected_pool[cat_cursor]
                        cat_cursor += 1

                method_cases.append(
                    {
                        "method": method,
                        "wallet_type": wallet_type,
                        "case_index": case_index + 1,
                        "selected_coin": selected_coin,
                    }
                )

        log(f"Running method batch: {method} ({len(method_cases)} cases)")
        futures = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for case in method_cases:
                futures.append(executor.submit(run_one_case, case, args))
                if args.pause_ms > 0:
                    time.sleep(args.pause_ms / 1000.0)

            for future in as_completed(futures):
                result = future.result()
                all_results.append(result)
                selected_preview = (result.get("selected_coin_id") or "n/a")[:16]
                lock_count = result.get("locked_input_count", 0)
                trade_preview = (result.get("trade_id") or "no-trade")[:12]
                log(
                    f"{result['method']} {result['wallet_type']} "
                    f"case#{result['case_index']} -> {trade_preview} "
                    f"locks={lock_count} selected={selected_preview}"
                )

        if args.post_method_settle_secs > 0:
            log(
                f"Waiting {args.post_method_settle_secs:.1f}s for cancels/locks to settle "
                f"before next method..."
            )
            time.sleep(args.post_method_settle_secs)

    summary_rows = summarize(all_results)
    print_summary(summary_rows)

    report_path = Path(args.report) if args.report else default_report_path()
    report = {
        "generated_at": utc_now_iso(),
        "cwd": str(PROJECT_DIR),
        "wallet_type": get_wallet_type(),
        "args": {
            "methods": args.methods,
            "assets": args.assets,
            "repeat": args.repeat,
            "workers": args.workers,
            "pause_ms": args.pause_ms,
            "settle_secs": args.settle_secs,
            "poll_count": args.poll_count,
            "poll_interval_secs": args.poll_interval_secs,
            "post_method_settle_secs": args.post_method_settle_secs,
            "offer_ratio": args.offer_ratio,
            "xch_request_cat_mojos": args.xch_request_cat_mojos,
            "cat_request_xch_mojos": args.cat_request_xch_mojos,
            "max_time_secs": args.max_time_secs,
            "keep_offers": args.keep_offers,
        },
        "selected_coin_pool": {
            "xch": [choice.__dict__ for choice in xch_selected_pool],
            "cat": [choice.__dict__ for choice in cat_selected_pool],
        },
        "summary": summary_rows,
        "results": all_results,
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
