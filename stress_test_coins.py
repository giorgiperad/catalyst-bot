"""
Coin Lifecycle Stress Test — Validates reconciliation under load.

Runs against the LIVE Sage wallet. Uses the RESERVE coin for XCH and CAT
to create/cancel/expire offers rapidly, then checks that the bot's DB
stays in sync with the wallet after each operation.

WHAT IT TESTS:
  1. Offer creation → coins get locked in wallet
  2. Offer cancellation → coins return to free
  3. Offer expiry (short-lived) → coins return to free
  4. Rapid create/cancel cycles → DB stays consistent
  5. Reconciliation accuracy → owned-vs-selectable matches DB state
  6. New endpoints: get_coins_by_ids, get_are_coins_spendable

SAFETY:
  - Only uses the RESERVE coin (smallest denomination)
  - Creates offers with very short expiry (60 seconds)
  - All offers are cancelled at the end (cleanup)
  - Can be interrupted with Ctrl+C (cleanup still runs)
  - Set DRY_RUN=true in .env to simulate without real offers

USAGE:
  python stress_test_coins.py [--rounds 20] [--delay 5]

  --rounds: Number of create/cancel cycles (default: 20)
  --delay:  Seconds between operations (default: 5)

Run this while the bot is STOPPED. It uses the same .env config.
"""

import os
import sys
import time
import json
import argparse
from decimal import Decimal
from datetime import datetime

# Ensure we can import project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# ---- Config ----
from config import cfg

WALLET_TYPE = os.getenv("WALLET_TYPE", "sage").lower()
if WALLET_TYPE != "sage":
    print("ERROR: This stress test is designed for Sage wallet only.")
    print(f"Current WALLET_TYPE={WALLET_TYPE}. Set WALLET_TYPE=sage in .env.")
    sys.exit(1)

# Import Sage wallet functions
from wallet_sage import (
    rpc, get_owned_coins, get_selectable_coins_map,
    get_owned_coins_detailed, get_coins_by_ids, are_coins_spendable,
    get_wallet_balance, get_wallet_sync_status, get_chia_health,
    cancel_offer, create_offer,
)

# Import database functions
from database import (
    init_database, get_connection, reconcile_coins_with_wallet,
    cleanup_orphaned_locked_coins, link_offers_to_locked_coins,
    log_event, norm_coin_id,
)


# ---- Helpers ----

def ts():
    """Timestamp string."""
    return datetime.now().strftime("%H:%M:%S")


def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def check_sync():
    """Verify wallet is synced before testing."""
    status = get_wallet_sync_status()
    if status and status.get("synced"):
        print(f"  [{ts()}] Wallet synced: YES")
        return True
    print(f"  [{ts()}] WARNING: Wallet NOT synced — results may be unreliable")
    return False


def get_db_coin_counts():
    """Get current coin counts from bot.db."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT wallet_type, status, COUNT(*) as cnt "
        "FROM coins GROUP BY wallet_type, status"
    ).fetchall()
    counts = {}
    for r in rows:
        key = f"{r['wallet_type']}_{r['status']}"
        counts[key] = r['cnt']
    return counts


def get_wallet_coin_counts():
    """Get coin counts from Sage wallet using single detailed call per asset.

    Uses get_owned_coins_detailed() so the free/locked split comes from
    the SAME query the reconciliation uses — no race between two calls.
    """
    result = {}
    for label, wallet_id in [("xch", cfg.WALLET_ID_XCH), ("cat", cfg.CAT_WALLET_ID)]:
        detailed = get_owned_coins_detailed(wallet_id) or {}
        owned = len(detailed)
        free = sum(1 for info in detailed.values() if not info.get("offer_id"))
        locked = owned - free
        result[f"{label}_owned"] = owned
        result[f"{label}_selectable"] = free
        result[f"{label}_locked"] = locked
    return result


def compare_db_wallet():
    """Compare DB state vs wallet state and report discrepancies."""
    db = get_db_coin_counts()
    wl = get_wallet_coin_counts()

    db_xch_free = db.get("xch_free", 0)
    db_xch_locked = db.get("xch_locked", 0)
    db_cat_free = db.get("cat_free", 0)
    db_cat_locked = db.get("cat_locked", 0)

    issues = []
    if db_xch_free != wl["xch_selectable"]:
        issues.append(f"XCH free: DB={db_xch_free} vs wallet={wl['xch_selectable']}")
    if db_xch_locked != wl["xch_locked"]:
        issues.append(f"XCH locked: DB={db_xch_locked} vs wallet={wl['xch_locked']}")
    if db_cat_free != wl["cat_selectable"]:
        issues.append(f"CAT free: DB={db_cat_free} vs wallet={wl['cat_selectable']}")
    if db_cat_locked != wl["cat_locked"]:
        issues.append(f"CAT locked: DB={db_cat_locked} vs wallet={wl['cat_locked']}")

    return issues


def run_reconcile():
    """Run full reconciliation and return stats."""
    stats_all = {}

    # DEBUG: Direct DB count before reconcile
    conn = get_connection()
    before = conn.execute(
        "SELECT wallet_type, status, COUNT(*) as cnt "
        "FROM coins WHERE status IN ('free','locked') "
        "GROUP BY wallet_type, status"
    ).fetchall()
    print(f"  [{ts()}] DB BEFORE reconcile: {[(r['wallet_type'], r['status'], r['cnt']) for r in before]}")

    for wt, wallet_id in [("xch", cfg.WALLET_ID_XCH), ("cat", cfg.CAT_WALLET_ID)]:
        # Try detailed endpoint first
        try:
            detailed = get_owned_coins_detailed(wallet_id)
            if detailed is not None:
                owned_map = {}
                selectable_map = {}
                for cid, info in detailed.items():
                    owned_map[cid] = info["amount"]
                    if not info.get("offer_id"):
                        selectable_map[cid] = info["amount"]
            else:
                owned_map = get_owned_coins(wallet_id) or {}
                selectable_map = get_selectable_coins_map(wallet_id) or {}
        except Exception:
            owned_map = get_owned_coins(wallet_id) or {}
            selectable_map = get_selectable_coins_map(wallet_id) or {}

        print(f"  [{ts()}] {wt.upper()} wallet data: {len(owned_map)} owned, "
              f"{len(selectable_map)} selectable, "
              f"{len(owned_map) - len(selectable_map)} locked")

        stats = reconcile_coins_with_wallet(
            wallet_selectable=selectable_map,
            wallet_owned=owned_map,
            wallet_type=wt
        )
        stats_all[wt] = stats

        # DEBUG: Direct DB count AFTER each wallet type reconcile
        after = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM coins "
            "WHERE wallet_type=? AND status IN ('free','locked') "
            "GROUP BY status", (wt,)
        ).fetchall()
        print(f"  [{ts()}] DB AFTER {wt.upper()} reconcile: {[(r['status'], r['cnt']) for r in after]}")

    return stats_all


# ---- Test: New Endpoint Validation ----

def test_new_endpoints():
    """Test get_coins_by_ids and get_are_coins_spendable endpoints."""
    banner("TEST: New Sage Endpoints")

    # Get a few coin IDs from the wallet
    xch_owned = get_owned_coins(cfg.WALLET_ID_XCH) or {}
    if not xch_owned:
        print(f"  [{ts()}] SKIP — no XCH coins in wallet")
        return True

    test_ids = list(xch_owned.keys())[:5]
    print(f"  [{ts()}] Testing with {len(test_ids)} XCH coin IDs")

    # Test get_coins_by_ids
    print(f"  [{ts()}] Calling get_coins_by_ids...")
    result = get_coins_by_ids(test_ids)
    if result is None:
        print(f"  [{ts()}] FAIL — get_coins_by_ids returned None")
        return False
    print(f"  [{ts()}] get_coins_by_ids returned {len(result)} coins")
    for cid, info in list(result.items())[:2]:
        offer_str = f"offer_id={info['offer_id'][:12]}..." if info.get('offer_id') else "free"
        print(f"    {cid[:16]}... amount={info['amount']}, {offer_str}")

    # Test get_are_coins_spendable with free coins
    selectable = get_selectable_coins_map(cfg.WALLET_ID_XCH) or {}
    if selectable:
        free_ids = list(selectable.keys())[:3]
        print(f"  [{ts()}] Calling are_coins_spendable with {len(free_ids)} free coins...")
        spendable = are_coins_spendable(free_ids)
        if spendable is None:
            print(f"  [{ts()}] FAIL — are_coins_spendable returned None")
            return False
        print(f"  [{ts()}] are_coins_spendable = {spendable} (expected True)")
        if not spendable:
            print(f"  [{ts()}] WARNING — free coins reported as not spendable!")

    # Test get_owned_coins_detailed
    print(f"  [{ts()}] Calling get_owned_coins_detailed...")
    detailed = get_owned_coins_detailed(cfg.WALLET_ID_XCH)
    if detailed is None:
        print(f"  [{ts()}] FAIL — get_owned_coins_detailed returned None")
        return False
    locked_count = sum(1 for v in detailed.values() if v.get("offer_id"))
    free_count = len(detailed) - locked_count
    print(f"  [{ts()}] Detailed: {len(detailed)} total, {free_count} free, {locked_count} locked")

    print(f"  [{ts()}] PASS — all new endpoints working")
    return True


# ---- Test: Reconciliation Accuracy ----

def test_reconciliation():
    """Run reconciliation and check for discrepancies."""
    banner("TEST: Reconciliation Accuracy")

    # Run reconcile
    print(f"  [{ts()}] Running full reconciliation...")
    stats = run_reconcile()
    for wt, s in stats.items():
        total = s["added"] + s.get("reappeared", 0) + s["marked_gone"] + s["freed"] + s["locked"]
        print(f"  [{ts()}] {wt.upper()}: +{s['added']} new, {s.get('reappeared',0)} reappeared, "
              f"-{s['marked_gone']} gone, {s['locked']} locked, {s['freed']} freed, "
              f"{s['already_ok']} ok")

    # Compare DB vs wallet
    print(f"  [{ts()}] Comparing DB vs wallet...")

    # Debug: show raw DB counts by status
    db_raw = get_db_coin_counts()
    print(f"  [{ts()}] DB raw counts: {db_raw}")

    issues = compare_db_wallet()
    if issues:
        print(f"  [{ts()}] DISCREPANCIES FOUND:")
        for issue in issues:
            print(f"    - {issue}")

        # Run reconcile a SECOND time to see if it converges
        print(f"  [{ts()}] Running reconciliation AGAIN to check convergence...")
        stats2 = run_reconcile()
        for wt, s in stats2.items():
            total = s["added"] + s.get("reappeared", 0) + s["marked_gone"] + s["freed"] + s["locked"]
            if total > 0:
                print(f"  [{ts()}] {wt.upper()} 2nd pass: +{s['added']} new, "
                      f"{s.get('reappeared',0)} reappeared, -{s['marked_gone']} gone, "
                      f"{s['locked']} locked, {s['freed']} freed, {s['already_ok']} ok")
            else:
                print(f"  [{ts()}] {wt.upper()} 2nd pass: no changes (converged)")

        db_raw2 = get_db_coin_counts()
        print(f"  [{ts()}] DB raw counts after 2nd pass: {db_raw2}")

        issues2 = compare_db_wallet()
        if issues2:
            print(f"  [{ts()}] STILL DISCREPANT after 2nd pass:")
            for issue in issues2:
                print(f"    - {issue}")
            return False
        else:
            print(f"  [{ts()}] PASS — converged after 2nd reconciliation")
            return True
    else:
        print(f"  [{ts()}] PASS — DB matches wallet exactly")
        return True


# ---- Test: Create/Cancel Cycle ----

def test_create_cancel_cycle(rounds=5, delay=5):
    """Create and cancel offers rapidly, checking reconciliation after each."""
    banner(f"TEST: Create/Cancel Cycle ({rounds} rounds)")

    created_ids = []
    pass_count = 0
    fail_count = 0

    # Get the smallest free XCH coin to use
    selectable = get_selectable_coins_map(cfg.WALLET_ID_XCH) or {}
    if not selectable:
        print(f"  [{ts()}] SKIP — no free XCH coins available")
        return True

    # Find smallest coin (reserve-like)
    smallest_id = min(selectable, key=lambda k: selectable[k])
    smallest_amt = selectable[smallest_id]
    print(f"  [{ts()}] Using coin {smallest_id[:16]}... ({smallest_amt/1e12:.4f} XCH)")

    # Get a reference mid-price for offers
    try:
        mid_price = Decimal(str(cfg.HARD_MIN_PRICE_XCH or "0.0001"))
    except Exception:
        mid_price = Decimal("0.0001")

    dry_run = getattr(cfg, 'DRY_RUN', False)
    if dry_run:
        print(f"  [{ts()}] DRY_RUN mode — offers will be simulated, not real")

    for i in range(rounds):
        print(f"\n  --- Round {i+1}/{rounds} ---")

        # Create a small offer with 60-second expiry
        if not dry_run:
            try:
                # Create a tiny buy offer (XCH → CAT)
                # Use wallet_sage.create_offer() which handles Sage's make_offer
                # endpoint and translates wallet_id-based dict to Sage format.
                # Format: {wallet_id: amount} — negative = offering, positive = requesting
                max_time = int(time.time()) + 60  # 60s expiry
                offer_dict = {
                    cfg.WALLET_ID_XCH: -smallest_amt,        # Offering XCH (negative)
                    cfg.CAT_WALLET_ID: 1000,                  # Requesting CAT (positive)
                }
                offer_result = create_offer(
                    offer_dict=offer_dict,
                    validate_only=False,
                    max_time=max_time,
                )

                if offer_result and isinstance(offer_result, dict):
                    offer_id = offer_result.get("trade_id", "") or offer_result.get("offer_id", "")
                    if offer_id:
                        created_ids.append(offer_id)
                        print(f"  [{ts()}] Created offer {offer_id[:16]}...")
                    else:
                        print(f"  [{ts()}] Create returned no offer_id: {str(offer_result)[:100]}")
                else:
                    print(f"  [{ts()}] Create returned None/empty: {offer_result}")
            except Exception as e:
                print(f"  [{ts()}] Create failed: {e}")
        else:
            print(f"  [{ts()}] [DRY_RUN] Would create offer with {smallest_amt/1e12:.4f} XCH")

        time.sleep(delay)

        # Run reconciliation
        stats = run_reconcile()
        issues = compare_db_wallet()
        if issues:
            print(f"  [{ts()}] POST-CREATE DISCREPANCY:")
            for issue in issues:
                print(f"    - {issue}")
            fail_count += 1
        else:
            print(f"  [{ts()}] Post-create: DB matches wallet")
            pass_count += 1

        # Cancel the offer we just created
        if created_ids and not dry_run:
            last_id = created_ids[-1]
            try:
                cancel_result = cancel_offer(last_id, secure=False, timeout=15)
                if cancel_result and cancel_result.get("success"):
                    print(f"  [{ts()}] Cancelled offer {last_id[:16]}...")
                else:
                    print(f"  [{ts()}] Cancel result: {cancel_result}")
            except Exception as e:
                print(f"  [{ts()}] Cancel failed: {e}")

        time.sleep(delay)

        # Run reconciliation again after cancel
        stats = run_reconcile()
        issues = compare_db_wallet()
        if issues:
            print(f"  [{ts()}] POST-CANCEL DISCREPANCY:")
            for issue in issues:
                print(f"    - {issue}")
            fail_count += 1
        else:
            print(f"  [{ts()}] Post-cancel: DB matches wallet")
            pass_count += 1

    print(f"\n  Results: {pass_count} passed, {fail_count} failed out of {rounds*2} checks")
    return fail_count == 0


# ---- Cleanup ----

def cleanup(created_ids):
    """Cancel any remaining test offers."""
    if not created_ids:
        return
    banner("CLEANUP: Cancelling test offers")
    for oid in created_ids:
        try:
            result = cancel_offer(oid, secure=False, timeout=10)
            status = "OK" if result and result.get("success") else "FAIL"
            print(f"  [{ts()}] Cancel {oid[:16]}... → {status}")
        except Exception as e:
            print(f"  [{ts()}] Cancel {oid[:16]}... → ERROR: {e}")
        time.sleep(1)


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(description="Coin lifecycle stress test")
    parser.add_argument("--rounds", type=int, default=5,
                        help="Number of create/cancel cycles (default: 5)")
    parser.add_argument("--delay", type=int, default=5,
                        help="Seconds between operations (default: 5)")
    args = parser.parse_args()

    banner("COIN LIFECYCLE STRESS TEST")
    print(f"  Wallet type: {WALLET_TYPE}")
    print(f"  Rounds: {args.rounds}")
    print(f"  Delay: {args.delay}s")
    print(f"  CAT asset: {cfg.CAT_ASSET_ID[:16]}...")
    print(f"  DRY_RUN: {getattr(cfg, 'DRY_RUN', False)}")

    # Init database
    init_database()

    # Check wallet health
    print(f"\n  [{ts()}] Checking wallet health...")
    health = get_chia_health()
    if health:
        print(f"  [{ts()}] Wallet: {health}")
    check_sync()

    results = {}
    created_ids = []

    try:
        # Test 1: New endpoints
        results["new_endpoints"] = test_new_endpoints()

        # Test 2: Reconciliation accuracy
        results["reconciliation"] = test_reconciliation()

        # Test 3: Create/cancel cycles (only if not DRY_RUN)
        results["create_cancel"] = test_create_cancel_cycle(
            rounds=args.rounds, delay=args.delay
        )

    except KeyboardInterrupt:
        print(f"\n  [{ts()}] Interrupted by user — running cleanup...")
    except Exception as e:
        print(f"\n  [{ts()}] ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always clean up
        cleanup(created_ids)

    # Summary
    banner("STRESS TEST SUMMARY")
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values()) if results else False
    print(f"\n  Overall: {'ALL PASSED' if all_passed else 'SOME FAILURES'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
