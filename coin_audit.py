#!/usr/bin/env python3
"""
Coin Audit — Full dump of wallet coin IDs vs DB coin records.
Shows every coin, its amount, lock status in wallet, and what the DB thinks.
"""

import os, sys, json, ssl, sqlite3, urllib.request

# ── Load .env ───────────────────────────────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
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

# ── Sage RPC ────────────────────────────────────────────────────────
def sage_rpc(method, params=None):
    url = f"{SAGE_URL}/{method}"
    data = json.dumps(params or {}).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if SAGE_CERT and SAGE_KEY:
        ctx.load_cert_chain(SAGE_CERT, SAGE_KEY)
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  !! RPC error {method}: {e}")
        return None

def norm(cid):
    if not cid: return ""
    cid = cid.strip().lower()
    if not cid.startswith("0x"): cid = "0x" + cid
    return cid

def get_coins(asset_id, filter_mode):
    if asset_id == "xch":
        params = {"offset": 0, "limit": 500, "filter_mode": filter_mode}
    else:
        params = {"asset_id": asset_id, "offset": 0, "limit": 500, "filter_mode": filter_mode}
    result = sage_rpc("get_coins", params)
    if not result: return {}
    coins_list = result.get("coins") or result.get("records") or result.get("data") or []
    coin_map = {}
    for c in coins_list:
        cid = c.get("coin_id", "")
        if not cid: continue
        cid = norm(cid)
        offer_id = c.get("offer_id") or c.get("offer_hash") or None
        if offer_id and isinstance(offer_id, str):
            offer_id = offer_id.lower()
            if not offer_id.startswith("0x"): offer_id = "0x" + offer_id
        coin_map[cid] = {
            "amount": int(c.get("amount", "0")),
            "offer_id": offer_id,
        }
    return coin_map

# ── Main ────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  COIN AUDIT — Every coin ID, wallet vs DB")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    for label, asset_id in [("XCH", "xch"), ("CAT", CAT_ASSET_ID)]:
        wt = label.lower() if label == "XCH" else "cat"
        div = 1e12 if wt == "xch" else 1e3

        print(f"\n{'=' * 80}")
        print(f"  {label} COINS")
        print(f"{'=' * 80}")

        # Get wallet data
        owned = get_coins(asset_id, "owned")
        selectable = get_coins(asset_id, "selectable")
        selectable_ids = set(selectable.keys())

        # Get DB data (all statuses)
        db_rows = conn.execute("""
            SELECT coin_id, status, amount_mojos, trade_id
            FROM coins WHERE wallet_type = ?
        """, (wt,)).fetchall()
        db_map = {}
        for r in db_rows:
            cid = norm(r["coin_id"])
            db_map[cid] = {
                "status": r["status"],
                "amount": r["amount_mojos"],
                "trade_id": r["trade_id"],
            }

        # Get offer details for trade_id lookups
        offer_map = {}
        for r in conn.execute("SELECT trade_id, side, status FROM offers").fetchall():
            offer_map[r["trade_id"]] = {"side": r["side"], "status": r["status"]}

        # ── SECTION A: All wallet coins ─────────────────────────────
        print(f"\n  --- WALLET COINS ({len(owned)} owned) ---")
        print(f"  {'COIN_ID':<20} {'AMOUNT':>12} {'WALLET':>8} {'OFFER_ID':>20}  |  {'DB_STATUS':>10} {'DB_TRADE_ID':>20} {'OFFER_SIDE':>6} {'OFFER_ST':>10}")
        print(f"  {'-'*20} {'-'*12} {'-'*8} {'-'*20}  |  {'-'*10} {'-'*20} {'-'*6} {'-'*10}")

        wallet_issues = []
        for cid in sorted(owned.keys()):
            w = owned[cid]
            amt = w["amount"] / div
            w_status = "free" if cid in selectable_ids else "LOCKED"
            w_offer = (w.get("offer_id") or "")[:20] if w.get("offer_id") else "-"

            # DB lookup
            db = db_map.get(cid)
            if db:
                db_status = db["status"]
                db_tid = (db["trade_id"] or "")[:20] if db.get("trade_id") else "-"
                offer_info = offer_map.get(db["trade_id"], {})
                o_side = offer_info.get("side", "-")
                o_status = offer_info.get("status", "-")
            else:
                db_status = "MISSING"
                db_tid = "-"
                o_side = "-"
                o_status = "-"

            # Flag issues
            issue = ""
            if db_status == "MISSING":
                issue = " !! NOT IN DB"
            elif w_status == "free" and db_status == "locked":
                issue = " !! DB=locked but wallet=free"
            elif w_status == "LOCKED" and db_status == "free":
                issue = " !! DB=free but wallet=LOCKED"
            elif w_status == "LOCKED" and db_status == "locked":
                # Check if the offer side makes sense for this coin type
                if o_side == "buy" and wt == "cat":
                    issue = " !! BUY offer locking CAT coin??"
                elif o_side == "sell" and wt == "xch":
                    issue = " !! SELL offer locking XCH coin??"

            print(f"  {cid[:20]} {amt:>12.4f} {w_status:>8} {w_offer:>20}  |  {db_status:>10} {db_tid:>20} {o_side:>6} {o_status:>10}{issue}")

            if issue:
                wallet_issues.append({
                    "coin_id": cid, "amount": amt, "wallet_status": w_status,
                    "wallet_offer_id": w.get("offer_id"),
                    "db_status": db_status, "db_trade_id": db.get("trade_id") if db else None,
                    "offer_side": o_side, "offer_status": o_status, "issue": issue
                })

        # ── SECTION B: DB coins NOT in wallet ───────────────────────
        db_active_not_in_wallet = []
        for cid, db in db_map.items():
            if db["status"] in ("free", "locked") and cid not in owned:
                db_active_not_in_wallet.append((cid, db))

        if db_active_not_in_wallet:
            print(f"\n  --- DB ACTIVE COINS NOT IN WALLET ({len(db_active_not_in_wallet)}) ---")
            for cid, db in db_active_not_in_wallet:
                amt = db["amount"] / div
                print(f"  {cid[:20]} {amt:>12.4f}  DB={db['status']}  trade_id={db.get('trade_id','none')}")

        # ── SECTION C: Issue summary ────────────────────────────────
        print(f"\n  --- {label} ISSUES FOUND: {len(wallet_issues)} ---")
        if wallet_issues:
            for i in wallet_issues:
                print(f"  {i['issue'].strip()}")
                print(f"    coin: {i['coin_id']}")
                print(f"    amount: {i['amount']:.4f} {label}")
                print(f"    wallet: {i['wallet_status']}, offer_id: {i['wallet_offer_id'] or 'none'}")
                print(f"    db: {i['db_status']}, trade_id: {i['db_trade_id'] or 'none'}")
                print(f"    offer: side={i['offer_side']}, status={i['offer_status']}")
                print()
        else:
            print(f"  None — all {label} coins check out.")

    # ── FINAL COUNTS ────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("  FINAL COUNTS")
    print(f"{'=' * 80}")
    for label, asset_id in [("XCH", "xch"), ("CAT", CAT_ASSET_ID)]:
        wt = label.lower() if label == "XCH" else "cat"
        owned = get_coins(asset_id, "owned")
        selectable = get_coins(asset_id, "selectable")
        w_free = len(selectable)
        w_locked = len(owned) - len(selectable)

        db_free = conn.execute("SELECT COUNT(*) FROM coins WHERE wallet_type=? AND status='free'", (wt,)).fetchone()[0]
        db_locked = conn.execute("SELECT COUNT(*) FROM coins WHERE wallet_type=? AND status='locked'", (wt,)).fetchone()[0]
        db_gone = conn.execute("SELECT COUNT(*) FROM coins WHERE wallet_type=? AND status='gone'", (wt,)).fetchone()[0]
        db_spent = conn.execute("SELECT COUNT(*) FROM coins WHERE wallet_type=? AND status='spent'", (wt,)).fetchone()[0]

        open_side = "buy" if wt == "xch" else "sell"
        expected_locked = conn.execute("SELECT COUNT(*) FROM offers WHERE status='open' AND side=?", (open_side,)).fetchone()[0]

        print(f"\n  {label}:")
        print(f"    Wallet:  {len(owned)} owned = {w_free} free + {w_locked} locked")
        print(f"    DB:      {db_free} free + {db_locked} locked + {db_gone} gone + {db_spent} spent")
        print(f"    Expected locked (open {open_side} offers): {expected_locked}")
        if w_locked != expected_locked:
            print(f"    !! DISCREPANCY: wallet has {w_locked} locked but only {expected_locked} open {open_side} offers")
            print(f"       Extra locked: {w_locked - expected_locked} coins")

    conn.close()
    print(f"\n{'=' * 80}")
    print("  Done.")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
