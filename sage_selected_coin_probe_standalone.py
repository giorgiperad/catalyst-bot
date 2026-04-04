#!/usr/bin/env python3
"""
Standalone Sage selected-coin probe.

This script is intentionally self-contained so it can be shared outside this
repo. It talks directly to Sage RPC and uses only Python's standard library.

What it does:
- picks a selectable XCH coin and/or CAT coin, or uses explicit coin IDs
- creates tiny offers with coin_ids=[selected_coin_id]
- inspects owned coins for exact offer_id lock attribution
- reports whether Sage used only the selected coin, added extra same-asset
  maker inputs, or did not appear to use the selected coin
- cancels the created offers unless --keep-offers is set

It is designed to help answer:
  "If the selected maker coin already covers the maker amount, does Sage still
   add extra maker inputs?"
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"


def load_env() -> Dict[str, str]:
    env = {}
    if ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env()


def getenv(name: str, default: str = "") -> str:
    return os.getenv(name) or ENV.get(name, default)


SAGE_URL = getenv("SAGE_RPC_URL", "https://localhost:9257").rstrip("/")
SAGE_CERT = getenv("SAGE_CERT_PATH", "")
SAGE_KEY = getenv("SAGE_KEY_PATH", "")
XCH_WALLET_ID = int(getenv("CHIA_WALLET_ID_XCH", "1"))
CAT_WALLET_ID = int(getenv("CAT_WALLET_ID", "2"))
CAT_ASSET_ID = getenv("CAT_ASSET_ID", "")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def norm_coin_id(value: Optional[str]) -> str:
    if not value:
        return ""
    coin_id = str(value).strip().lower()
    if not coin_id.startswith("0x"):
        coin_id = "0x" + coin_id
    return coin_id


def make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if SAGE_CERT and SAGE_KEY:
        ctx.load_cert_chain(SAGE_CERT, SAGE_KEY)
    return ctx


SSL_CONTEXT = make_ssl_context()


def sage_rpc(method: str, payload: Optional[dict] = None, timeout: int = 15) -> dict:
    url = f"{SAGE_URL}/{method}"
    data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} HTTP {exc.code}: {body[:300]}") from exc
    except Exception as exc:
        raise RuntimeError(f"{method} failed: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone Sage selected-coin probe")
    parser.add_argument("--assets", default="xch,cat", help="Comma-separated: xch, cat")
    parser.add_argument("--repeat", type=int, default=1, help="How many times to run each asset case")
    parser.add_argument("--offer-ratio", type=float, default=0.9, help="Spend this fraction of the selected coin amount")
    parser.add_argument("--xch-request-cat-mojos", type=int, default=100_000, help="Requested CAT mojos for XCH-spend probe offers")
    parser.add_argument("--cat-request-xch-mojos", type=int, default=100_000_000_000, help="Requested XCH mojos for CAT-spend probe offers")
    parser.add_argument("--selected-xch-coin", default="", help="Explicit XCH coin ID to use")
    parser.add_argument("--selected-cat-coin", default="", help="Explicit CAT coin ID to use")
    parser.add_argument("--settle-secs", type=float, default=2.0, help="Initial wait before inspecting owned-coin locks")
    parser.add_argument("--poll-count", type=int, default=8, help="Number of owned-coin lock polls")
    parser.add_argument("--poll-interval-secs", type=float, default=1.0, help="Delay between owned-coin lock polls")
    parser.add_argument("--max-time-secs", type=int, default=300, help="Offer expiry window")
    parser.add_argument("--keep-offers", action="store_true", help="Do not cancel the created offers")
    parser.add_argument("--report", default="", help="Optional path for the JSON report")
    parser.add_argument("--verbose-coins", action="store_true", help="Print the selectable/owned coin sample before running")
    return parser.parse_args()


def get_coin_list(wallet_type: str, filter_mode: str) -> List[dict]:
    if wallet_type == "xch":
        payload = {"offset": 0, "limit": 500, "filter_mode": filter_mode}
    elif wallet_type == "cat":
        if not CAT_ASSET_ID:
            raise RuntimeError("CAT_ASSET_ID is not configured")
        payload = {
            "asset_id": CAT_ASSET_ID,
            "offset": 0,
            "limit": 500,
            "filter_mode": filter_mode,
        }
    else:
        raise ValueError(f"Unknown wallet_type {wallet_type}")

    result = sage_rpc("get_coins", payload, timeout=15)
    return result.get("coins") or result.get("records") or result.get("data") or []


def pick_selectable_coin(wallet_type: str, explicit_coin_id: str = "") -> dict:
    coins = get_coin_list(wallet_type, "selectable")
    normalized_explicit = norm_coin_id(explicit_coin_id)
    if normalized_explicit:
        for coin in coins:
            if norm_coin_id(coin.get("coin_id")) == normalized_explicit:
                return coin
        raise RuntimeError(f"Explicit {wallet_type} coin {normalized_explicit} not found in selectable coins")

    if not coins:
        raise RuntimeError(f"No selectable {wallet_type} coins found")

    coins.sort(key=lambda coin: (int(coin.get("amount") or 0), norm_coin_id(coin.get("coin_id"))))
    return coins[0]


def print_coin_sample(wallet_type: str) -> None:
    selectable = get_coin_list(wallet_type, "selectable")
    owned = get_coin_list(wallet_type, "owned")
    log(f"{wallet_type.upper()} selectable={len(selectable)} owned={len(owned)}")
    for label, coins in (("selectable", selectable[:5]), ("owned", owned[:5])):
        for coin in coins:
            log(
                f"  {wallet_type.upper()} {label}: coin_id={norm_coin_id(coin.get('coin_id'))[:20]}... "
                f"amount={int(coin.get('amount') or 0)} offer_id={str(coin.get('offer_id') or '')[:20]}"
            )


def build_offer_dict(wallet_type: str, selected_amount_mojos: int, args: argparse.Namespace) -> Dict[str, int]:
    spend_mojos = max(1, int(selected_amount_mojos * args.offer_ratio))
    if selected_amount_mojos > 1:
        spend_mojos = min(spend_mojos, selected_amount_mojos - 1)

    if wallet_type == "xch":
        return {
            str(XCH_WALLET_ID): -int(spend_mojos),
            str(CAT_WALLET_ID): int(args.xch_request_cat_mojos),
        }
    if wallet_type == "cat":
        return {
            str(CAT_WALLET_ID): -int(spend_mojos),
            str(XCH_WALLET_ID): int(args.cat_request_xch_mojos),
        }
    raise ValueError(f"Unknown wallet_type {wallet_type}")


def make_offer_payload(offer_dict: Dict[str, int], selected_coin_id: str, expires_at: int) -> dict:
    offered_assets = []
    requested_assets = []
    configured_cat = CAT_ASSET_ID.lower().replace("0x", "").strip()

    for key, amount in offer_dict.items():
        wallet_id = int(key)
        amount_int = int(amount)
        if wallet_id == XCH_WALLET_ID:
            asset_id = None
        elif wallet_id == CAT_WALLET_ID:
            asset_id = configured_cat
        else:
            raise RuntimeError(f"Unexpected wallet id {wallet_id} in offer_dict")

        target = offered_assets if amount_int < 0 else requested_assets
        target.append(
            {
                "asset_id": asset_id,
                "amount": str(abs(amount_int)),
            }
        )

    payload = {
        "offered_assets": offered_assets,
        "requested_assets": requested_assets,
        "fee": "0",
        "auto_import": True,
        "expires_at_second": int(expires_at),
        "coin_ids": [norm_coin_id(selected_coin_id).replace("0x", "")],
    }
    return payload


def extract_trade_id(result: Optional[dict]) -> str:
    if not isinstance(result, dict):
        return ""
    trade_id = result.get("offer_id") or result.get("trade_id") or ""
    if not trade_id:
        trade_record = result.get("trade_record") or {}
        if isinstance(trade_record, dict):
            trade_id = trade_record.get("offer_id") or trade_record.get("trade_id") or ""
    return str(trade_id or "")


def get_owned_locked_inputs(wallet_type: str, trade_id: str, args: argparse.Namespace) -> List[dict]:
    if args.settle_secs > 0:
        time.sleep(args.settle_secs)

    for attempt in range(args.poll_count):
        owned = get_coin_list(wallet_type, "owned")
        locked = []
        for coin in owned:
            if str(coin.get("offer_id") or "").lower() == trade_id.lower():
                locked.append(
                    {
                        "coin_id": norm_coin_id(coin.get("coin_id")),
                        "amount_mojos": int(coin.get("amount") or 0),
                    }
                )
        if locked:
            locked.sort(key=lambda item: (item["amount_mojos"], item["coin_id"]))
            return locked
        if attempt < args.poll_count - 1 and args.poll_interval_secs > 0:
            time.sleep(args.poll_interval_secs)
    return []


def cancel_offer(trade_id: str) -> dict:
    payload = {"offer_id": trade_id, "fee": "0", "auto_submit": True}
    try:
        return sage_rpc("cancel_offer", payload, timeout=30)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_case(wallet_type: str, selected_coin: dict, args: argparse.Namespace, case_index: int) -> dict:
    selected_coin_id = norm_coin_id(selected_coin.get("coin_id"))
    selected_amount_mojos = int(selected_coin.get("amount") or 0)
    offer_dict = build_offer_dict(wallet_type, selected_amount_mojos, args)
    payload = make_offer_payload(
        offer_dict=offer_dict,
        selected_coin_id=selected_coin_id,
        expires_at=int(time.time()) + int(args.max_time_secs),
    )

    started_at = utc_now_iso()
    create_result = None
    trade_id = ""
    locked_inputs: List[dict] = []
    cancel_result = None
    create_error = ""

    try:
        create_result = sage_rpc("make_offer", payload, timeout=20)
        trade_id = extract_trade_id(create_result)
        if trade_id:
            locked_inputs = get_owned_locked_inputs(wallet_type, trade_id, args)
            if not args.keep_offers:
                cancel_result = cancel_offer(trade_id)
        else:
            create_error = f"missing_trade_id: {create_result}"
    except Exception as exc:
        create_error = str(exc)

    normalized_selected = norm_coin_id(selected_coin_id)
    selected_present = normalized_selected in [item["coin_id"] for item in locked_inputs]
    extra_inputs = [item for item in locked_inputs if item["coin_id"] != normalized_selected]

    return {
        "wallet_type": wallet_type,
        "case_index": case_index,
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "selected_coin_id": normalized_selected,
        "selected_coin_amount_mojos": selected_amount_mojos,
        "offer_dict": offer_dict,
        "selected_covers_offer": selected_amount_mojos >= abs(int(offer_dict[str(XCH_WALLET_ID if wallet_type == 'xch' else CAT_WALLET_ID)])),
        "make_offer_payload": payload,
        "create_result": create_result,
        "trade_id": trade_id,
        "locked_inputs": locked_inputs,
        "locked_input_count": len(locked_inputs),
        "selected_present": selected_present,
        "selected_exclusive": selected_present and len(locked_inputs) == 1,
        "extra_inputs": extra_inputs,
        "cancel_result": cancel_result,
        "create_error": create_error,
    }


def summarize(results: List[dict]) -> List[dict]:
    rows = []
    by_asset = {}
    for result in results:
        bucket = by_asset.setdefault(
            result["wallet_type"],
            {
                "wallet_type": result["wallet_type"],
                "cases": 0,
                "created": 0,
                "selected_present": 0,
                "selected_exclusive": 0,
                "selected_missing": 0,
                "extra_input_cases": 0,
                "errors": 0,
            },
        )
        bucket["cases"] += 1
        if result.get("trade_id"):
            bucket["created"] += 1
        else:
            bucket["errors"] += 1

        if result.get("selected_present") is True:
            bucket["selected_present"] += 1
        else:
            bucket["selected_missing"] += 1

        if result.get("selected_exclusive") is True:
            bucket["selected_exclusive"] += 1

        if result.get("extra_inputs"):
            bucket["extra_input_cases"] += 1

    for wallet_type in sorted(by_asset):
        rows.append(by_asset[wallet_type])
    return rows


def print_summary(summary_rows: List[dict]) -> None:
    print()
    print("=" * 86)
    print("SUMMARY")
    print("=" * 86)
    header = f"{'Asset':<5} {'Cases':>5} {'Made':>5} {'SelOK':>6} {'SelOnly':>7} {'SelMiss':>7} {'Extra':>6} {'Err':>4}"
    print(header)
    print("-" * len(header))
    for row in summary_rows:
        print(
            f"{row['wallet_type']:<5} {row['cases']:>5} {row['created']:>5} "
            f"{row['selected_present']:>6} {row['selected_exclusive']:>7} "
            f"{row['selected_missing']:>7} {row['extra_input_cases']:>6} "
            f"{row['errors']:>4}"
        )
    print("=" * 86)


def default_report_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return SCRIPT_DIR / f"sage_selected_coin_probe_{stamp}.json"


def main() -> int:
    args = parse_args()
    assets = [asset.strip().lower() for asset in args.assets.split(",") if asset.strip()]
    if not assets:
        print("No assets selected.", file=sys.stderr)
        return 2

    if args.offer_ratio <= 0 or args.offer_ratio >= 1:
        print("--offer-ratio must be > 0 and < 1", file=sys.stderr)
        return 2

    if "cat" in assets and not CAT_ASSET_ID:
        print("CAT_ASSET_ID is required for CAT probe cases.", file=sys.stderr)
        return 2

    if args.verbose_coins:
        for wallet_type in assets:
            print_coin_sample(wallet_type)

    all_results = []
    explicit_coin_map = {
        "xch": args.selected_xch_coin,
        "cat": args.selected_cat_coin,
    }

    log(f"Running standalone Sage probe against {SAGE_URL}")
    for wallet_type in assets:
        for case_index in range(1, args.repeat + 1):
            selected_coin = pick_selectable_coin(wallet_type, explicit_coin_map.get(wallet_type, ""))
            log(
                f"{wallet_type.upper()} case#{case_index}: selected "
                f"{norm_coin_id(selected_coin.get('coin_id'))[:18]}... "
                f"amount={int(selected_coin.get('amount') or 0)}"
            )
            result = run_case(wallet_type, selected_coin, args, case_index)
            all_results.append(result)
            log(
                f"{wallet_type.upper()} case#{case_index}: trade="
                f"{(result.get('trade_id') or 'none')[:12]} "
                f"locks={result.get('locked_input_count', 0)} "
                f"selected_present={result.get('selected_present')}"
            )

    summary_rows = summarize(all_results)
    print_summary(summary_rows)

    report = {
        "generated_at": utc_now_iso(),
        "sage_url": SAGE_URL,
        "wallet_ids": {
            "xch": XCH_WALLET_ID,
            "cat": CAT_WALLET_ID,
        },
        "cat_asset_id": CAT_ASSET_ID,
        "args": vars(args),
        "summary": summary_rows,
        "results": all_results,
    }
    report_path = Path(args.report) if args.report else default_report_path()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
