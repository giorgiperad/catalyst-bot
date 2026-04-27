import os
import sys
import tempfile
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database


class OversizedLockedOffersTests(unittest.TestCase):
    def setUp(self):
        fd, self._db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        database.DB_PATH = self._db_path
        if hasattr(database._local, "conn"):
            database._local.conn = None
        database.init_database()

    def tearDown(self):
        if hasattr(database._local, "conn"):
            conn = getattr(database._local, "conn", None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            database._local.conn = None
        try:
            os.unlink(self._db_path)
        except OSError:
            pass

    def _add_locked_buy(self, trade_id, coin_id, coin_mojos, size_xch,
                        designation="tier_spare"):
        self.assertTrue(database.upsert_coin(
            coin_id=coin_id,
            wallet_type="xch",
            amount_mojos=coin_mojos,
            designation=designation,
            assigned_tier="mid" if designation != "reserve" else "none",
        ))
        self.assertTrue(database.add_offer(
            trade_id=trade_id,
            side="buy",
            price_xch=Decimal("0.001"),
            size_xch=Decimal(str(size_xch)),
            size_cat=Decimal("1000"),
            cat_asset_id="cat",
            tier="mid",
            coin_id=coin_id,
        ))
        self.assertTrue(database.lock_coin(coin_id, trade_id))

    def test_flags_reserve_coin_even_when_amount_would_fit(self):
        self._add_locked_buy(
            "trade-reserve",
            "0x" + "a" * 64,
            1_000_000_000_000,
            "1.0",
            designation="reserve",
        )

        rows = database.get_oversized_locked_offers(max_ratio=1.5)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trade_id"], "trade-reserve")
        self.assertEqual(rows[0]["reason"], "reserve_coin_locked")

    def test_flags_oversized_trade_coin(self):
        self._add_locked_buy(
            "trade-big",
            "0x" + "b" * 64,
            48_000_000_000_000,
            "1.4",
            designation="tier_spare",
        )

        rows = database.get_oversized_locked_offers(max_ratio=1.5)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trade_id"], "trade-big")
        self.assertEqual(rows[0]["reason"], "oversized_coin_locked")

    def test_ignores_correct_sized_tier_coin(self):
        self._add_locked_buy(
            "trade-ok",
            "0x" + "c" * 64,
            1_450_000_000_000,
            "1.4",
            designation="tier_spare",
        )

        self.assertEqual(database.get_oversized_locked_offers(max_ratio=1.5), [])


if __name__ == "__main__":
    unittest.main()
