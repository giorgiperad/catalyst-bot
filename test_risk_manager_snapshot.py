from decimal import Decimal
from unittest import TestCase, main
from unittest.mock import patch

import risk_manager


class RiskManagerSnapshotTests(TestCase):
    def test_record_snapshot_passes_mid_price_and_leaves_missing_balances_null(self):
        calls = []

        def fake_record_inventory_snapshot(**kwargs):
            calls.append(kwargs)
            return True

        with patch.object(
            risk_manager,
            "record_inventory_snapshot",
            side_effect=fake_record_inventory_snapshot,
        ):
            manager = risk_manager.RiskManager()
            manager._net_position_cat = Decimal("11629.243")
            manager.record_snapshot(mid_price=Decimal("0.00012078"))

        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0]["xch_balance"])
        self.assertIsNone(calls[0]["cat_balance"])
        self.assertEqual(calls[0]["mid_price"], Decimal("0.00012078"))


if __name__ == "__main__":
    main()
