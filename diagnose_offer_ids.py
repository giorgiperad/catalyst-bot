#!/usr/bin/env python3
"""
Diagnose Offer ID Mapping — Do coin offer_ids match offer trade_ids?
====================================================================
Queries Sage for:
  1. All owned coins (with their offer_id field)
  2. All open offers (with their offer_id/trade_id)

Then checks:
  - Does every coin's offer_id appear in the set of offer IDs?
  - What format are the IDs in (0x prefix, length, etc)?
  - Which offer locks which coins (grouped by offer)?

Run with bot STOPPED so wallet state is stable.
"""

import os, sys, json, ssl, urllib.request

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

# ── Main ────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  OFFER ID DIAGNOSTIC — Do coin offer_ids match offer IDs?")
    print("=" * 80)

    # ── 1. Get all open offers from Sage ──────────────────────────────
    print("\n[1] FETCHING OFFERS FROM SAGE")
    print("-" * 50)
    res = sage_rpc("get_offers", {
        "include_completed": False,
        "start": 0, "end": 500,
    })

    if not res:
        print("  !! Failed to get offers")
        return

    raw_offers = res.get("offers") or res.get("trades") or res.get("trade_records") or []
    print(f"  Raw response keys: {list(res.keys())}")
    print(f"  Total offers: {len(raw_offers)}")

    if raw_offers and isinstance(raw_offers[0], dict):
        first = raw_offers[0]
        print(f"  First offer keys: {sorted(first.keys())}")
        # Show ALL ID-like fields
        for key in sorted(first.keys()):
            val = first[key]
            if isinstance(val, str) and len(val) > 30:
                print(f"    {key}: {val[:60]}...")
            elif key in ("offer_id", "trade_id", "offer_hash", "id", "status"):
                print(f"    {key}: {repr(val)}")

    # Build offer ID set
    offer_ids = {}  # {normalized_id: offer_dict}
    for o in raw_offers:
        if not isinstance(o, dict): continue
        # Collect ALL potential ID fields
        oid = o.get("offer_id", "")
        tid = o.get("trade_id", "")
        ohash = o.get("offer_hash", "")

        # Use whatever ID is available
        primary_id = oid or tid or ohash
        if primary_id:
            offer_ids[primary_id.lower()] = o

    print(f"\n  Unique offer IDs: {len(offer_ids)}")
    # Show format of first few
    for i, (k, v) in enumerate(list(offer_ids.items())[:3]):
        has_0x = k.startswith("0x")
        print(f"    [{i}] len={len(k)} 0x={has_0x} val={k[:40]}...")

    # ── 2. Get all coins ──────────────────────────────────────────────
    print("\n[2] FETCHING COINS FROM SAGE")
    print("-" * 50)

    all_coins = {}  # {coin_id: {amount, offer_id, wallet_type}}
    for label, asset_id in [("XCH", "xch"), ("CAT", CAT_ASSET_ID)]:
        if asset_id == "xch":
            params = {"offset": 0, "limit": 500, "filter_mode": "owned"}
        else:
            params = {"asset_id": asset_id, "offset": 0, "limit": 500, "filter_mode": "owned"}
        result = sage_rpc("get_coins", params)
        if not result:
            print(f"  !! Failed to get {label} coins")
            continue

        coins_list = result.get("coins") or result.get("records") or result.get("data") or []
        print(f"  {label}: {len(coins_list)} owned coins")

        # Show first coin's keys to understand format
        if coins_list and isinstance(coins_list[0], dict):
            print(f"  {label} coin keys: {sorted(coins_list[0].keys())}")

        for c in coins_list:
            cid = c.get("coin_id", "")
            if not cid: continue
            cid_norm = norm(cid)
            offer_id = c.get("offer_id") or c.get("offer_hash") or None
            all_coins[cid_norm] = {
                "amount": int(c.get("amount", "0")),
                "offer_id_raw": offer_id,
                "offer_id_lower": offer_id.lower() if offer_id else None,
                "wallet_type": label.lower(),
            }

    # ── 3. Analyze locked coins and their offer_ids ───────────────────
    print("\n[3] LOCKED COINS — OFFER_ID ANALYSIS")
    print("-" * 50)

    locked_coins = {cid: info for cid, info in all_coins.items() if info["offer_id_raw"]}
    free_coins = {cid: info for cid, info in all_coins.items() if not info["offer_id_raw"]}

    print(f"  Total coins: {len(all_coins)}")
    print(f"  Locked (has offer_id): {len(locked_coins)}")
    print(f"  Free (no offer_id): {len(free_coins)}")

    xch_locked = {cid: i for cid, i in locked_coins.items() if i["wallet_type"] == "xch"}
    cat_locked = {cid: i for cid, i in locked_coins.items() if i["wallet_type"] == "cat"}
    print(f"  XCH locked: {len(xch_locked)}")
    print(f"  CAT locked: {len(cat_locked)}")

    # ── 4. Match coin offer_ids to offer IDs ──────────────────────────
    print("\n[4] MATCHING COIN OFFER_IDS TO OFFERS")
    print("-" * 50)

    matched = 0
    unmatched = 0
    unmatched_list = []

    # Collect unique offer_ids from coins
    coin_offer_ids = set()
    for info in locked_coins.values():
        oid = info["offer_id_lower"]
        if oid:
            coin_offer_ids.add(oid)

    print(f"  Unique offer_ids on coins: {len(coin_offer_ids)}")
    print(f"  Unique offer IDs from get_offers: {len(offer_ids)}")

    # Show format comparison
    if coin_offer_ids:
        sample = list(coin_offer_ids)[0]
        print(f"\n  Sample coin offer_id: len={len(sample)} 0x={sample.startswith('0x')} val={sample[:40]}...")
    if offer_ids:
        sample = list(offer_ids.keys())[0]
        print(f"  Sample offer ID:      len={len(sample)} 0x={sample.startswith('0x')} val={sample[:40]}...")

    # Try direct match
    for oid in coin_offer_ids:
        if oid in offer_ids:
            matched += 1
        else:
            # Try with/without 0x prefix
            alt = oid[2:] if oid.startswith("0x") else "0x" + oid
            if alt in offer_ids:
                matched += 1
                print(f"  !! 0x prefix mismatch: coin has '{oid[:20]}' but offer uses '{alt[:20]}'")
            else:
                unmatched += 1
                unmatched_list.append(oid)

    print(f"\n  Matched: {matched}")
    print(f"  Unmatched: {unmatched}")
    if unmatched_list:
        print(f"\n  Unmatched coin offer_ids (not found in any offer):")
        for oid in unmatched_list[:10]:
            print(f"    {oid[:60]}...")
        if len(unmatched_list) > 10:
            print(f"    ... and {len(unmatched_list) - 10} more")

    # ── 5. Group coins by offer ───────────────────────────────────────
    print("\n[5] COINS GROUPED BY OFFER")
    print("-" * 50)
    print(f"  (Showing which coin types each offer locks)")

    by_offer = {}  # {offer_id: [coin_info, ...]}
    for cid, info in locked_coins.items():
        oid = info["offer_id_lower"]
        if oid not in by_offer:
            by_offer[oid] = []
        by_offer[oid].append({"coin_id": cid, **info})

    one_side = 0
    both_sides = 0
    for oid, coins in sorted(by_offer.items()):
        types = set(c["wallet_type"] for c in coins)
        if len(types) == 1:
            one_side += 1
        else:
            both_sides += 1

    print(f"  Offers locking ONE side only: {one_side}")
    print(f"  Offers locking BOTH sides: {both_sides}")

    if both_sides > 0:
        print(f"\n  !! Offers locking BOTH sides (first 5):")
        shown = 0
        for oid, coins in sorted(by_offer.items()):
            types = set(c["wallet_type"] for c in coins)
            if len(types) > 1:
                print(f"    offer_id: {oid[:40]}...")
                for c in coins:
                    div = 1e12 if c["wallet_type"] == "xch" else 1e3
                    print(f"      {c['wallet_type'].upper()} coin {c['coin_id'][:20]}... = {c['amount']/div:.4f}")
                shown += 1
                if shown >= 5:
                    break

    # ── 6. Summary ────────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("  SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Open offers: {len(offer_ids)}")
    print(f"  Locked coins: {len(locked_coins)} (XCH: {len(xch_locked)}, CAT: {len(cat_locked)})")
    print(f"  Unique offer_ids on coins: {len(coin_offer_ids)}")
    print(f"  Offer_id → offer match rate: {matched}/{len(coin_offer_ids)}")
    print(f"  Offers locking one side: {one_side}, both sides: {both_sides}")

    if len(xch_locked) == len([o for o in offer_ids.values()
                               if isinstance(o, dict) and
                               (o.get("summary", {}).get("offered", {}).get("xch", 0) or 0) > 0]):
        print(f"  XCH locked count matches buy offer count — CORRECT")
    else:
        # Count buy offers (those offering XCH)
        buy_count = 0
        sell_count = 0
        for o in raw_offers:
            summary = o.get("summary") or {}
            offered = summary.get("offered") or {}
            if offered.get("xch"):
                buy_count += 1
            else:
                sell_count += 1
        print(f"  Buy offers (offering XCH): {buy_count}")
        print(f"  Sell offers (offering CAT): {sell_count}")
        print(f"  XCH locked coins: {len(xch_locked)} (expected: {buy_count} if one-side locking)")
        print(f"  CAT locked coins: {len(cat_locked)} (expected: {sell_count} if one-side locking)")

    print(f"\n{'=' * 80}")
    print("  Done.")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
