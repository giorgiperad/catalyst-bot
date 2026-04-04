#!/usr/bin/env python3
"""
Coin Verification Script — DB vs Sage Wallet Comparison
========================================================
Queries the bot's SQLite database AND the live Sage wallet,
then compares coin IDs to find any discrepancies.

Reports:
  1. DB coin status summary
  2. Wallet coin counts (owned, selectable, locked)
  3. Coins in DB but NOT in wallet (stale DB records)
  4. Coins in wallet but NOT in DB (missing from DB)
  5. Status mismatches (DB says free but wallet says locked, etc.)
  6. Offer linkage check (locked coins → open offers)

Run with bot STOPPED so wallet state is stable.
"""

import sys
import os
import sqlite3
import json
import ssl
import urllib.request
from decimal import Decimal
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────
# Load from .env the same way the bot does
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

def load_env():
    """Load .env file into a dict."""
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env()

SAGE_URL = env.get("SAGE_RPC_URL", "https://localhost:9257")
SAGE_CERT = env.get("SAGE_CERT_PATH", "")
SAGE_KEY = env.get("SAGE_KEY_PATH", "")
CAT_ASSET_ID = env.get("CAT_ASSET_ID", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")

XCH_WALLET_ID = int(env.get("CHIA_WALLET_ID_XCH", "1"))
CAT_WALLET_ID_NUM = int(env.get("CAT_WALLET_ID", "2"))

# ── Sage RPC Helper ─────────────────────────────────────────────────

def sage_rpc(method, params=None):
    """Call Sage wallet RPC."""
    url = f"{SAGE_URL}/{method}"
    data = json.dumps(params or {}).encode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if SAGE_CERT and SAGE_KEY:
        ctx.load_cert_chain(SAGE_CERT, SAGE_KEY)

    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  !! RPC error calling {method}: {e}")
        return None


def get_wallet_coins(asset_id, filter_mode):
    """Get coins from Sage with a specific filter mode."""
    if asset_id == "xch":
        params = {"offset": 0, "limit": 500, "filter_mode": filter_mode}
    else:
        params = {"asset_id": asset_id, "offset": 0, "limit": 500, "filter_mode": filter_mode}

    result = sage_rpc("get_coins", params)
    if not result:
        return {}

    coins_list = result.get("coins") or result.get("records") or result.get("data") or []
    coin_map = {}
    for c in coins_list:
        cid = c.get("coin_id", "")
        if not cid:
            continue
        # Normalise to 0x lowercase
        if not cid.startswith("0x"):
            cid = "0x" + cid.lower()
        else:
            cid = cid.lower()

        offer_id = c.get("offer_id") or c.get("offer_hash") or None
        if offer_id and isinstance(offer_id, str):
            offer_id = offer_id.lower()

        coin_map[cid] = {
            "amount": int(c.get("amount", "0")),
            "offer_id": offer_id,
            "created_height": c.get("created_height"),
        }
    return coin_map


def norm(coin_id):
    """Normalise coin ID to 0x lowercase."""
    if not coin_id:
        return ""
    cid = coin_id.strip().lower()
    if not cid.startswith("0x"):
        cid = "0x" + cid
    return cid


# ── Main ────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  COIN VERIFICATION — DB vs Sage Wallet")
    print("=" * 70)

    # ── 1. DB Summary ───────────────────────────────────────────────
    print("\n[1] DATABASE COIN SUMMARY")
    print("-" * 50)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT wallet_type, status, COUNT(*) as cnt, SUM(amount_mojos) as total
        FROM coins GROUP BY wallet_type, status ORDER BY wallet_type, status
    """).fetchall()

    db_summary = {}
    for r in rows:
        wt = r["wallet_type"]
        st = r["status"]
        if wt not in db_summary:
            db_summary[wt] = {}
        db_summary[wt][st] = {"count": r["cnt"], "total_mojos": r["total"]}
        amt_display = r["total"] / 1e12 if wt == "xch" else r["total"] / 1e3
        unit = "XCH" if wt == "xch" else "CAT"
        print(f"  {wt:4s} | {st:8s} | {r['cnt']:4d} coins | {amt_display:>14.4f} {unit}")

    # ── 2. Get ALL DB coins (active only: free + locked) ────────────
    print("\n[2] LOADING DB COINS (active: free + locked)")
    print("-" * 50)

    db_coins = {}
    for wt in ["xch", "cat"]:
        db_coins[wt] = {}
        rows = conn.execute("""
            SELECT coin_id, status, amount_mojos, trade_id, tier, designation
            FROM coins WHERE wallet_type = ? AND status IN ('free', 'locked')
        """, (wt,)).fetchall()
        for r in rows:
            cid = norm(r["coin_id"])
            db_coins[wt][cid] = {
                "status": r["status"],
                "amount": r["amount_mojos"],
                "trade_id": r["trade_id"],
                "tier": r["tier"],
                "designation": r["designation"],
            }
        print(f"  {wt:4s}: {len(db_coins[wt])} active coins in DB "
              f"({sum(1 for c in db_coins[wt].values() if c['status']=='free')} free, "
              f"{sum(1 for c in db_coins[wt].values() if c['status']=='locked')} locked)")

    # ── 3. Get open offers from DB ──────────────────────────────────
    print("\n[3] OPEN OFFERS IN DB")
    print("-" * 50)

    open_offers = conn.execute("""
        SELECT trade_id, side, status FROM offers WHERE status = 'open'
    """).fetchall()
    buy_offers = [r for r in open_offers if r["side"] == "buy"]
    sell_offers = [r for r in open_offers if r["side"] == "sell"]
    print(f"  Open buys:  {len(buy_offers)}")
    print(f"  Open sells: {len(sell_offers)}")
    open_trade_ids = set(r["trade_id"] for r in open_offers)

    # ── 4. Query Sage Wallet ────────────────────────────────────────
    print("\n[4] QUERYING SAGE WALLET")
    print("-" * 50)

    wallet_coins = {}
    for label, asset_id in [("xch", "xch"), ("cat", CAT_ASSET_ID)]:
        print(f"  Fetching {label} owned coins...")
        owned = get_wallet_coins(asset_id, "owned")
        print(f"    Owned: {len(owned)} coins")

        print(f"  Fetching {label} selectable coins...")
        selectable = get_wallet_coins(asset_id, "selectable")
        print(f"    Selectable: {len(selectable)} coins")

        # Derive locked = owned - selectable
        locked_ids = set(owned.keys()) - set(selectable.keys())
        print(f"    Locked (derived): {len(locked_ids)} coins")

        wallet_coins[label] = {
            "owned": owned,
            "selectable": selectable,
            "locked_ids": locked_ids,
        }

    # ── 5. COMPARISON ───────────────────────────────────────────────
    for wt in ["xch", "cat"]:
        print(f"\n{'=' * 70}")
        print(f"  COMPARISON: {wt.upper()} COINS")
        print(f"{'=' * 70}")

        db = db_coins[wt]
        wallet_owned = wallet_coins[wt]["owned"]
        wallet_selectable = wallet_coins[wt]["selectable"]
        wallet_locked = wallet_coins[wt]["locked_ids"]

        db_ids = set(db.keys())
        wallet_ids = set(wallet_owned.keys())

        # 5a. Coins in DB but NOT in wallet
        db_only = db_ids - wallet_ids
        print(f"\n  [5a] In DB but NOT in wallet: {len(db_only)}")
        if db_only:
            for cid in sorted(db_only)[:10]:
                info = db[cid]
                amt = info["amount"] / 1e12 if wt == "xch" else info["amount"] / 1e3
                print(f"    {cid[:18]}... | DB status={info['status']} | "
                      f"amt={amt:.4f} | trade_id={info['trade_id'] or 'none'}")
            if len(db_only) > 10:
                print(f"    ... and {len(db_only) - 10} more")

        # 5b. Coins in wallet but NOT in DB
        wallet_only = wallet_ids - db_ids
        print(f"\n  [5b] In wallet but NOT in DB: {len(wallet_only)}")
        if wallet_only:
            for cid in sorted(wallet_only)[:10]:
                info = wallet_owned[cid]
                amt = info["amount"] / 1e12 if wt == "xch" else info["amount"] / 1e3
                locked = "LOCKED" if cid in wallet_locked else "free"
                offer = info.get("offer_id") or "none"
                print(f"    {cid[:18]}... | wallet={locked} | "
                      f"amt={amt:.4f} | offer_id={offer[:18] if offer != 'none' else 'none'}...")
            if len(wallet_only) > 10:
                print(f"    ... and {len(wallet_only) - 10} more")

        # 5c. Status mismatches (coins in BOTH but status disagrees)
        common = db_ids & wallet_ids
        mismatches = []
        for cid in common:
            db_status = db[cid]["status"]
            wallet_is_locked = cid in wallet_locked
            wallet_status = "locked" if wallet_is_locked else "free"
            if db_status != wallet_status:
                mismatches.append((cid, db_status, wallet_status))

        print(f"\n  [5c] Status mismatches (DB vs wallet): {len(mismatches)}")
        if mismatches:
            for cid, db_st, w_st in mismatches[:15]:
                info = db[cid]
                amt = info["amount"] / 1e12 if wt == "xch" else info["amount"] / 1e3
                print(f"    {cid[:18]}... | DB={db_st:6s} wallet={w_st:6s} | "
                      f"amt={amt:.4f} | trade_id={info['trade_id'] or 'none'}")
            if len(mismatches) > 15:
                print(f"    ... and {len(mismatches) - 15} more")

        # 5d. Amount mismatches
        amt_mismatches = []
        for cid in common:
            db_amt = db[cid]["amount"]
            w_amt = wallet_owned[cid]["amount"]
            if db_amt != w_amt:
                amt_mismatches.append((cid, db_amt, w_amt))
        print(f"\n  [5d] Amount mismatches: {len(amt_mismatches)}")
        if amt_mismatches:
            for cid, db_a, w_a in amt_mismatches[:5]:
                print(f"    {cid[:18]}... | DB={db_a} wallet={w_a}")

        # 5e. Locked coins → open offer linkage
        print(f"\n  [5e] Offer linkage check:")
        db_locked = {cid: info for cid, info in db.items() if info["status"] == "locked"}
        linked = sum(1 for c in db_locked.values() if c["trade_id"] and c["trade_id"] in open_trade_ids)
        unlinked = sum(1 for c in db_locked.values() if not c["trade_id"] or c["trade_id"] not in open_trade_ids)
        print(f"    DB locked coins: {len(db_locked)}")
        print(f"    Linked to open offer: {linked}")
        print(f"    NOT linked to open offer: {unlinked}")
        if unlinked > 0:
            for cid, info in sorted(db_locked.items()):
                if not info["trade_id"] or info["trade_id"] not in open_trade_ids:
                    amt = info["amount"] / 1e12 if wt == "xch" else info["amount"] / 1e3
                    tid = info["trade_id"] or "NONE"
                    print(f"      {cid[:18]}... | trade_id={tid[:18]}... | amt={amt:.4f}")
                    if unlinked > 10:
                        break  # Just show a sample

        # 5f. Summary verdict
        print(f"\n  [VERDICT] {wt.upper()}:")
        ok = True
        if db_only:
            print(f"    !! {len(db_only)} coins in DB marked active but NOT in wallet (should be 'gone')")
            ok = False
        if wallet_only:
            print(f"    !! {len(wallet_only)} coins in wallet but missing from DB")
            ok = False
        if mismatches:
            print(f"    !! {len(mismatches)} status mismatches (DB disagrees with wallet)")
            ok = False
        if amt_mismatches:
            print(f"    !! {len(amt_mismatches)} amount mismatches")
            ok = False
        if ok and not db_only and not wallet_only:
            print(f"    PASS — DB and wallet are in perfect sync")

    # ── 6. Overall Summary ──────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  OVERALL SUMMARY")
    print(f"{'=' * 70}")

    for wt in ["xch", "cat"]:
        db = db_coins[wt]
        w = wallet_coins[wt]
        db_free = sum(1 for c in db.values() if c["status"] == "free")
        db_locked = sum(1 for c in db.values() if c["status"] == "locked")
        w_owned = len(w["owned"])
        w_sel = len(w["selectable"])
        w_lock = len(w["locked_ids"])

        unit = "XCH" if wt == "xch" else "CAT"
        print(f"\n  {unit}:")
        print(f"    DB active:    {len(db):4d} (free={db_free}, locked={db_locked})")
        print(f"    Wallet owned: {w_owned:4d} (selectable={w_sel}, locked={w_lock})")
        match = "MATCH" if (db_free == w_sel and db_locked == w_lock) else "MISMATCH"
        print(f"    → {match}")

    conn.close()
    print(f"\n{'=' * 70}")
    print("  Done.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
