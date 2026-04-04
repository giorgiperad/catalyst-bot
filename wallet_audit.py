"""
Wallet Audit Script — Compare wallet state vs database state.

Run this while the bot is STOPPED to get a clean snapshot.

Usage:
    python wallet_audit.py

Queries Sage wallet RPC for all coins (XCH + CAT), then compares
against the bot.db coins table. Reports mismatches.
"""

import os
import sys
import sqlite3
import json
import time

# Import wallet_sage directly for RPC access
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env for config
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from wallet_sage import rpc

CAT_ASSET_ID = os.getenv("CAT_ASSET_ID", "")

def get_all_coins(asset_id=None, filter_mode="owned"):
    """Get all coins from Sage wallet."""
    result = rpc("get_coins", {
        "asset_id": asset_id,
        "offset": 0,
        "limit": 500,
        "sort_mode": "amount",
        "filter_mode": filter_mode,
        "ascending": False,
    }, timeout=15)

    if not result or not isinstance(result, dict):
        return []

    coins = (result.get("coins") or result.get("records")
             or result.get("data") or [])
    return coins

def get_open_offers():
    """Get all open offers from Sage wallet."""
    result = rpc("get_offers", {}, timeout=15)
    if not result or not isinstance(result, dict):
        return []
    return result.get("offers") or result.get("data") or []


def main():
    print("=" * 80)
    print("WALLET AUDIT — Sage Wallet vs bot.db")
    print("=" * 80)

    # ---- WALLET: XCH coins ----
    print("\n--- Querying Sage wallet for XCH coins ---")
    xch_owned = get_all_coins(asset_id=None, filter_mode="owned")
    xch_selectable = get_all_coins(asset_id=None, filter_mode="selectable")

    selectable_ids = set()
    for c in xch_selectable:
        cid = (c.get("coin_id") or c.get("id") or c.get("coinId")
               or c.get("name") or "")
        selectable_ids.add(cid.lower().replace("0x", ""))

    print(f"\nWALLET XCH: {len(xch_owned)} owned, {len(xch_selectable)} selectable")
    print(f"\n{'Coin ID':<50s}  {'Amount':>12s}  {'Selectable':>10s}")
    print("-" * 80)

    wallet_xch = {}  # coin_id -> {amount, selectable}
    total_xch = 0
    spendable_xch = 0
    for c in xch_owned:
        cid = (c.get("coin_id") or c.get("id") or c.get("coinId")
               or c.get("name") or "")
        amount = int(c.get("amount", 0))
        is_sel = cid.lower().replace("0x", "") in selectable_ids
        cid_clean = cid.lower()
        if not cid_clean.startswith("0x"):
            cid_clean = "0x" + cid_clean
        wallet_xch[cid_clean] = {"amount": amount, "selectable": is_sel}
        total_xch += amount
        if is_sel:
            spendable_xch += amount
        locked_str = "FREE" if is_sel else "LOCKED"
        print(f"  {cid_clean[:48]}  {amount/1e12:>10.4f}  {locked_str:>10s}")

    print(f"\nXCH Total: {total_xch/1e12:.4f} XCH in {len(wallet_xch)} coins")
    print(f"XCH Spendable: {spendable_xch/1e12:.4f} XCH in {len(xch_selectable)} coins")
    print(f"XCH Locked: {(total_xch-spendable_xch)/1e12:.4f} XCH in {len(xch_owned)-len(xch_selectable)} coins")

    # ---- WALLET: CAT coins ----
    print("\n\n--- Querying Sage wallet for CAT coins ---")
    if not CAT_ASSET_ID:
        print("⚠️  No CAT_ASSET_ID configured in .env — skipping CAT query")
        cat_owned = []
        cat_selectable = []
    else:
        cat_owned = get_all_coins(asset_id=CAT_ASSET_ID, filter_mode="owned")
        cat_selectable = get_all_coins(asset_id=CAT_ASSET_ID, filter_mode="selectable")

    cat_selectable_ids = set()
    for c in cat_selectable:
        cid = (c.get("coin_id") or c.get("id") or c.get("coinId")
               or c.get("name") or "")
        cat_selectable_ids.add(cid.lower().replace("0x", ""))

    print(f"\nWALLET CAT: {len(cat_owned)} owned, {len(cat_selectable)} selectable")
    print(f"\n{'Coin ID':<50s}  {'Amount':>12s}  {'Selectable':>10s}")
    print("-" * 80)

    wallet_cat = {}
    total_cat = 0
    spendable_cat = 0
    for c in cat_owned:
        cid = (c.get("coin_id") or c.get("id") or c.get("coinId")
               or c.get("name") or "")
        amount = int(c.get("amount", 0))
        is_sel = cid.lower().replace("0x", "") in cat_selectable_ids
        cid_clean = cid.lower()
        if not cid_clean.startswith("0x"):
            cid_clean = "0x" + cid_clean
        wallet_cat[cid_clean] = {"amount": amount, "selectable": is_sel}
        total_cat += amount
        if is_sel:
            spendable_cat += amount
        locked_str = "FREE" if is_sel else "LOCKED"
        print(f"  {cid_clean[:48]}  {amount/1e3:>10.3f}  {locked_str:>10s}")

    print(f"\nCAT Total: {total_cat/1e3:.3f} CAT in {len(wallet_cat)} coins")
    print(f"CAT Spendable: {spendable_cat/1e3:.3f} CAT in {len(cat_selectable)} coins")
    print(f"CAT Locked: {(total_cat-spendable_cat)/1e3:.3f} CAT in {len(cat_owned)-len(cat_selectable)} coins")

    # ---- WALLET: Open offers ----
    print("\n\n--- Querying Sage wallet for open offers ---")
    offers = get_open_offers()
    print(f"\nWALLET OFFERS: {len(offers)} open")
    for o in offers[:5]:
        if isinstance(o, dict):
            tid = o.get("trade_id") or o.get("id") or o.get("offer_id") or "?"
            status = o.get("status") or "?"
            print(f"  trade_id={str(tid)[:20]}...  status={status}")
    if len(offers) > 5:
        print(f"  ... and {len(offers)-5} more")

    # ---- DATABASE comparison ----
    print("\n\n" + "=" * 80)
    print("DATABASE COMPARISON")
    print("=" * 80)

    db = sqlite3.connect("bot.db")
    db.row_factory = sqlite3.Row

    # DB XCH coins (free + locked = live)
    db_xch = {}
    for row in db.execute("SELECT coin_id, amount_mojos, status, trade_id, assigned_tier FROM coins WHERE wallet_type='xch' AND status IN ('free', 'locked')").fetchall():
        db_xch[row['coin_id'].lower()] = {
            "amount": row['amount_mojos'],
            "status": row['status'],
            "trade_id": row['trade_id'] or "",
            "tier": row['assigned_tier'] or "none",
        }

    # DB CAT coins (free + locked = live)
    db_cat = {}
    for row in db.execute("SELECT coin_id, amount_mojos, status, trade_id, assigned_tier FROM coins WHERE wallet_type='cat' AND status IN ('free', 'locked')").fetchall():
        db_cat[row['coin_id'].lower()] = {
            "amount": row['amount_mojos'],
            "status": row['status'],
            "trade_id": row['trade_id'] or "",
            "tier": row['assigned_tier'] or "none",
        }

    # ---- XCH mismatches ----
    print(f"\n--- XCH COMPARISON ---")
    print(f"Wallet: {len(wallet_xch)} coins, DB: {len(db_xch)} live coins")

    # In wallet but not in DB
    in_wallet_not_db = []
    for cid, info in wallet_xch.items():
        if cid not in db_xch:
            in_wallet_not_db.append((cid, info))

    if in_wallet_not_db:
        print(f"\n⚠️  IN WALLET but NOT in DB ({len(in_wallet_not_db)} coins):")
        for cid, info in in_wallet_not_db:
            sel = "FREE" if info['selectable'] else "LOCKED"
            print(f"    {cid[:40]}...  {info['amount']/1e12:>8.4f} XCH  wallet={sel}")

    # In DB but not in wallet
    in_db_not_wallet = []
    for cid, info in db_xch.items():
        if cid not in wallet_xch:
            in_db_not_wallet.append((cid, info))

    if in_db_not_wallet:
        print(f"\n⚠️  IN DB but NOT in WALLET ({len(in_db_not_wallet)} coins):")
        for cid, info in in_db_not_wallet:
            print(f"    {cid[:40]}...  {info['amount']/1e12:>8.4f} XCH  db={info['status']}  tier={info['tier']}")

    # Status mismatches
    status_mismatch = []
    for cid in wallet_xch:
        if cid in db_xch:
            w_sel = wallet_xch[cid]['selectable']
            db_status = db_xch[cid]['status']
            # Wallet selectable = should be 'free' in DB
            # Wallet not-selectable = should be 'locked' in DB
            if w_sel and db_status == 'locked':
                status_mismatch.append((cid, "wallet=FREE but db=locked", wallet_xch[cid], db_xch[cid]))
            elif not w_sel and db_status == 'free':
                status_mismatch.append((cid, "wallet=LOCKED but db=free", wallet_xch[cid], db_xch[cid]))

    if status_mismatch:
        print(f"\n⚠️  STATUS MISMATCHES ({len(status_mismatch)} coins):")
        for cid, desc, w, d in status_mismatch:
            print(f"    {cid[:40]}...  {w['amount']/1e12:>8.4f} XCH  {desc}  (db trade={d['trade_id'][:16]})")

    # ---- CAT mismatches ----
    print(f"\n--- CAT COMPARISON ---")
    print(f"Wallet: {len(wallet_cat)} coins, DB: {len(db_cat)} live coins")

    in_wallet_not_db_cat = [(cid, info) for cid, info in wallet_cat.items() if cid not in db_cat]
    in_db_not_wallet_cat = [(cid, info) for cid, info in db_cat.items() if cid not in wallet_cat]

    if in_wallet_not_db_cat:
        print(f"\n⚠️  IN WALLET but NOT in DB ({len(in_wallet_not_db_cat)} coins):")
        for cid, info in in_wallet_not_db_cat:
            sel = "FREE" if info['selectable'] else "LOCKED"
            print(f"    {cid[:40]}...  {info['amount']/1e3:>10.3f} CAT  wallet={sel}")

    if in_db_not_wallet_cat:
        print(f"\n⚠️  IN DB but NOT in WALLET ({len(in_db_not_wallet_cat)} coins):")
        for cid, info in in_db_not_wallet_cat:
            print(f"    {cid[:40]}...  {info['amount']/1e3:>10.3f} CAT  db={info['status']}  tier={info['tier']}")

    cat_status_mismatch = []
    for cid in wallet_cat:
        if cid in db_cat:
            w_sel = wallet_cat[cid]['selectable']
            db_status = db_cat[cid]['status']
            if w_sel and db_status == 'locked':
                cat_status_mismatch.append((cid, "wallet=FREE but db=locked", wallet_cat[cid], db_cat[cid]))
            elif not w_sel and db_status == 'free':
                cat_status_mismatch.append((cid, "wallet=LOCKED but db=free", wallet_cat[cid], db_cat[cid]))

    if cat_status_mismatch:
        print(f"\n⚠️  CAT STATUS MISMATCHES ({len(cat_status_mismatch)} coins):")
        for cid, desc, w, d in cat_status_mismatch:
            print(f"    {cid[:40]}...  {w['amount']/1e3:>10.3f} CAT  {desc}")

    # ---- Summary ----
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    total_issues = (len(in_wallet_not_db) + len(in_db_not_wallet) +
                    len(status_mismatch) + len(in_wallet_not_db_cat) +
                    len(in_db_not_wallet_cat) + len(cat_status_mismatch))

    if total_issues == 0:
        print("✅ Wallet and database are in sync!")
    else:
        print(f"⚠️  Found {total_issues} discrepancies:")
        if in_wallet_not_db:
            print(f"  - {len(in_wallet_not_db)} XCH coins in wallet but missing from DB")
        if in_db_not_wallet:
            print(f"  - {len(in_db_not_wallet)} XCH coins in DB but missing from wallet (stale/gone)")
        if status_mismatch:
            print(f"  - {len(status_mismatch)} XCH coins with wrong free/locked status in DB")
        if in_wallet_not_db_cat:
            print(f"  - {len(in_wallet_not_db_cat)} CAT coins in wallet but missing from DB")
        if in_db_not_wallet_cat:
            print(f"  - {len(in_db_not_wallet_cat)} CAT coins in DB but missing from wallet")
        if cat_status_mismatch:
            print(f"  - {len(cat_status_mismatch)} CAT coins with wrong free/locked status in DB")

    db.close()


if __name__ == "__main__":
    main()
