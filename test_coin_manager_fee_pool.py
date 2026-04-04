import importlib
import os
import sys
import types
import unittest
from decimal import Decimal


class CoinManagerFeePoolTests(unittest.TestCase):
    def setUp(self):
        self._saved_wallet_type = os.environ.get("WALLET_TYPE")
        os.environ["WALLET_TYPE"] = "chia"

        fake_config = types.ModuleType("config")
        fake_config.cfg = types.SimpleNamespace(
            COINSET_ENABLED=False,
            WALLET_ID_XCH=1,
            CAT_WALLET_ID=2,
            TIER_ENABLED=True,
            ENABLE_COIN_PREP=True,
            CAT_DECIMALS=3,
            INNER_SIZE_XCH=Decimal("1.0"),
            MID_SIZE_XCH=Decimal("0.5"),
            OUTER_SIZE_XCH=Decimal("0.25"),
            EXTREME_SIZE_XCH=Decimal("0.1"),
            SNIPER_ENABLED=False,
            SNIPER_SIZE_XCH=Decimal("0"),
            SNIPER_PREP_COUNT=0,
            COIN_PREP_HEADROOM_PCT=Decimal("10"),
            CAT_COIN_SIZE=Decimal("4000"),
            TRANSACTION_FEE_MODE="manual",
            TRANSACTION_FEE_XCH=Decimal("0.00000050"),
            TRANSACTION_FEE_TARGET_SECS=300,
            TRANSACTION_FEE_ESTIMATE_COST=20_000_000,
            FEE_PREP_COUNT=20,
            FEE_COIN_SIZE_XCH=Decimal("0.0001"),
        )
        sys.modules["config"] = fake_config

        fake_database = types.ModuleType("database")
        fake_database.log_event = lambda *args, **kwargs: None
        sys.modules["database"] = fake_database

        fake_wallet = types.ModuleType("wallet")
        fake_wallet.get_exact_spendable_coins_rpc = lambda wallet_id: {"success": True, "records": []}
        fake_wallet.get_all_coins_for_wallet = lambda *args, **kwargs: []
        fake_wallet.get_wallet_balance = lambda *args, **kwargs: {"wallet_balance": {"spendable_balance": 0}}
        fake_wallet.get_next_address = lambda *args, **kwargs: {"success": True, "address": "xch1test"}
        fake_wallet.send_transaction = lambda *args, **kwargs: {"success": True}
        fake_wallet.split_coins_rpc = lambda *args, **kwargs: {"success": True}
        fake_wallet.get_wallet_type = lambda: "chia"
        fake_wallet.WALLET_ID_XCH = 1
        fake_wallet.get_owned_coins = lambda *args, **kwargs: {}
        fake_wallet.get_owned_coins_detailed = lambda *a, **kw: None
        fake_wallet.rpc = lambda *args, **kwargs: {"fingerprint": "123"}
        sys.modules["wallet"] = fake_wallet

        sys.modules.pop("tx_fees", None)
        sys.modules.pop("coin_manager", None)
        self.coin_manager = importlib.import_module("coin_manager")
        self.manager = self.coin_manager.CoinManager()

    def tearDown(self):
        for name in ["coin_manager", "tx_fees", "wallet", "database", "config"]:
            sys.modules.pop(name, None)

        if self._saved_wallet_type is None:
            os.environ.pop("WALLET_TYPE", None)
        else:
            os.environ["WALLET_TYPE"] = self._saved_wallet_type

    def test_fee_tier_is_xch_only(self):
        xch_sizes = self.manager._get_tier_sizes_mojos(is_cat=False)
        cat_sizes = self.manager._get_tier_sizes_mojos(is_cat=True)

        self.assertIn("fees", xch_sizes)
        self.assertEqual(xch_sizes["fees"], 100_000_000)
        self.assertNotIn("fees", cat_sizes)


if __name__ == "__main__":
    unittest.main()
