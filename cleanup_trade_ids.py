#!/usr/bin/env python3
"""
Cleanup bad trade_id assignments from coins table.
Run BEFORE restarting the bot so direct offer_id linking can start fresh.

What it does:
  1. Shows current state (how many coins have trade_ids)
  2. Clears ALL trade_ids from locked coins
  3. The bot's direct offer_id linking will reassign them correctly on next cycle
"""

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")

def main():
    if not os.path.exists(DB_PATH):
        print("!! bot.db not found")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Show current state
    print("=== BEFORE CLEANUP ===")
    rows = conn.execute(
        "SELECT wallet_type, status, "
        "COUNT(*) as total, "
        "SUM(CASE WHEN trade_id IS NOT NULL AND trade_id != '' THEN 1 ELSE 0 END) as has_tid "
        "FROM coins GROUP BY wallet_type, status ORDER BY wallet_type, status"
    ).fetchall()
    for r in rows:
        print(f"  {r['wallet_type'].upper()} {r['status']:8s}: {r['total']:4d} total, {r['has_tid']:4d} have trade_id")

    # Count bad linkages (XCH linked to sell offers, CAT linked to buy offers)
    bad = conn.execute("""
        SELECT c.wallet_type, c.coin_id, c.trade_id, o.side
        FROM coins c
        LEFT JOIN offers o ON c.trade_id = o.trade_id
        WHERE c.status = 'locked' AND c.trade_id IS NOT NULL AND c.trade_id != ''
        AND o.side IS NOT NULL
        AND ((c.wallet_type = 'xch' AND o.side = 'sell')
          OR (c.wallet_type = 'cat' AND o.side = 'buy'))
    """).fetchall()
    print(f"\n  Bad linkages (wrong side): {len(bad)}")

    # Clear all trade_ids from locked coins
    result = conn.execute(
        "UPDATE coins SET trade_id = NULL "
        "WHERE status = 'locked' AND trade_id IS NOT NULL AND trade_id != ''"
    )
    cleared = result.rowcount
    conn.commit()
    print(f"\n  Cleared {cleared} trade_ids from locked coins")

    # Show after state
    print("\n=== AFTER CLEANUP ===")
    rows = conn.execute(
        "SELECT wallet_type, status, "
        "COUNT(*) as total, "
        "SUM(CASE WHEN trade_id IS NOT NULL AND trade_id != '' THEN 1 ELSE 0 END) as has_tid "
        "FROM coins GROUP BY wallet_type, status ORDER BY wallet_type, status"
    ).fetchall()
    for r in rows:
        print(f"  {r['wallet_type'].upper()} {r['status']:8s}: {r['total']:4d} total, {r['has_tid']:4d} have trade_id")

    conn.close()
    print("\nDone. Start the bot — direct offer_id linking will reassign trade_ids correctly.")

if __name__ == "__main__":
    main()
