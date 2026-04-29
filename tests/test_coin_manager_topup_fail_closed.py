import unittest
from unittest.mock import patch
import sys
import types

# Track which stub modules we installed so we can clean them up after the
# test class runs.  Other test files (test_amm_monitor.py) import the real
# requests module, so leaving a stub in sys.modules would break them.
_INSTALLED_STUBS: list = []

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    dotenv_stub.set_key = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_stub
    _INSTALLED_STUBS.append("dotenv")

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _DummyResponse:
        status_code = 200

        def json(self):
            return {"status": "success"}

        def raise_for_status(self):
            return None

    class _StubSession:
        """Minimal Session stub — supports headers.update() so amm_monitor.__init__ works."""
        def __init__(self):
            self.headers = {}

        def get(self, *args, **kwargs):
            return _DummyResponse()

        def mount(self, *args, **kwargs):
            pass

    requests_stub.get = lambda *args, **kwargs: _DummyResponse()
    requests_stub.Session = _StubSession
    requests_stub.exceptions = types.SimpleNamespace(
        Timeout=Exception,
        ConnectionError=Exception,
    )
    requests_adapters_stub = types.ModuleType("requests.adapters")
    requests_adapters_stub.HTTPAdapter = object
    requests_stub.adapters = requests_adapters_stub
    sys.modules["requests"] = requests_stub
    sys.modules["requests.adapters"] = requests_adapters_stub
    _INSTALLED_STUBS.extend(["requests", "requests.adapters"])

if "urllib3" not in sys.modules:
    urllib3_stub = types.ModuleType("urllib3")
    urllib3_stub.Retry = object
    urllib3_stub.exceptions = types.SimpleNamespace(InsecureRequestWarning=Warning)
    urllib3_stub.disable_warnings = lambda *args, **kwargs: None
    sys.modules["urllib3"] = urllib3_stub
    _INSTALLED_STUBS.append("urllib3")

import coin_manager


def _record(coin_id: str, amount: int) -> dict:
    return {
        "coin_id": coin_id,
        "coin": {
            "amount": amount,
        },
    }


_CACHED_MODS = ("amm_monitor", "coin_manager", "wallet_sage",
                "wallet_chia", "wallet", "price_engine", "tx_fees",
                "win_subprocess", "config", "database")


class CoinManagerTopupFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Save originals of modules we will replace/evict so tearDownClass
        # can restore them and later test files see the real modules, not
        # stubs we installed at module-load time.
        cls._saved_modules = {
            name: sys.modules.get(name)
            for name in list(_INSTALLED_STUBS) + list(_CACHED_MODS)
        }

    @classmethod
    def tearDownClass(cls):
        # Remove stub modules installed at module-load time so they don't
        # pollute sys.modules for test files that run later.
        for name in _INSTALLED_STUBS:
            sys.modules.pop(name, None)
        # Evict modules that may have been cached against stub requests/
        # urllib3 at import time so later test files re-import fresh.
        for name in _CACHED_MODS:
            sys.modules.pop(name, None)
        # Restore any originals we saved so later files that imported
        # these modules before we loaded keep the same instance.
        for name, saved in cls._saved_modules.items():
            if saved is not None:
                sys.modules[name] = saved

    def _make_manager(self):
        with patch.object(coin_manager.CoinManager, "_resolve_fingerprint", return_value="123456789"):
            return coin_manager.CoinManager()

    def test_extract_sage_transaction_ids_handles_nested_fields(self):
        tx_ids = coin_manager.CoinManager._extract_sage_transaction_ids({
            "transaction_id": "abc123",
            "transaction": {
                "transaction_ids": ["def456", "0xabc123"],
            },
        })
        self.assertEqual(tx_ids, ["0xabc123", "0xdef456"])

    def test_owned_coin_map_falls_back_to_selectable_lower_bound(self):
        manager = self._make_manager()

        with patch.object(coin_manager, "get_owned_coins", side_effect=RuntimeError("owned unavailable")), \
             patch.object(coin_manager, "_get_free_coins_rpc", return_value={
                 "records": [
                     _record("0xcoin1", 100),
                     _record("0xcoin2", 200),
                 ]
             }), \
             patch.object(coin_manager, "log_event"):
            owned_map = manager._get_owned_coin_amount_map(1, "topup_test")

        self.assertEqual(owned_map, {
            "0xcoin1": 100,
            "0xcoin2": 200,
        })

    def test_two_step_split_aborts_when_address_lookup_fails(self):
        manager = self._make_manager()

        with patch.object(coin_manager, "get_next_address", return_value=None), \
             patch.object(coin_manager, "log_event"):
            with self.assertRaises(coin_manager._TopupWalletDegraded):
                manager._two_step_split(
                    name="XCH-mid",
                    wallet_id=1,
                    source_coin_id="0xsource",
                    pool_amount_mojos=400,
                    num_to_create=4,
                    trading_size_mojos=100,
                    is_cat=False,
                )

    def test_two_step_split_continues_when_spacescan_confirms_split_spend(self):
        manager = self._make_manager()

        # sage_topup_split is imported locally inside _sage_one_step_split via
        # `from wallet_sage import sage_topup_split`.  Patch it at the source
        # module so the local `from … import` picks up the mock at call time.
        # Scenario: sage_topup_split returns None (e.g. RPC hiccup), but
        # spacescan confirms the split landed on-chain, so the method recovers
        # and waits until the output coins become selectable.
        with patch("wallet_sage.sage_topup_split", return_value=None), \
             patch.object(coin_manager, "get_next_address", return_value={"success": True, "address": "xch1testaddress"}), \
             patch.object(coin_manager, "get_wallet_type", return_value="sage"), \
             patch.object(manager, "_spacescan_self_send_confirmed", return_value=True), \
             patch.object(manager, "_get_owned_coin_amount_map", side_effect=[
                 {"0xsource": 600},             # pre-snapshot
                 {"0xsource": 600},             # iteration 1 — no new coins yet
                 {"0xchange": 200, "0xa": 100, "0xb": 100, "0xc": 100, "0xd": 100},  # iteration 2 — coins ready
             ]), \
             patch.object(manager, "_get_strict_selectable_coin_id_set", side_effect=[
                 set(),                                      # iteration 1
                 {"0xa", "0xb", "0xc", "0xd"},              # iteration 2
             ]), \
             patch.object(manager, "_get_transaction_confirmation_state", side_effect=[
                 {"known": False, "confirmed": False, "confirmed_count": 0, "total": 1, "height": 0},
                 {"known": False, "confirmed": False, "confirmed_count": 0, "total": 1, "height": 0},
             ]), \
             patch.object(coin_manager, "log_event"), \
             patch.object(coin_manager.time, "sleep", return_value=None):
            result = manager._two_step_split(
                name="XCH-mid",
                wallet_id=1,
                source_coin_id="0xsource",
                pool_amount_mojos=400,
                num_to_create=4,
                trading_size_mojos=100,
                is_cat=False,
            )

        self.assertTrue(result)

    def test_two_step_split_accepts_tx_confirmed_owned_outputs_before_selectable(self):
        manager = self._make_manager()

        # Scenario: sage_topup_split returns a tx result; Sage confirms the tx
        # but the outputs are owned (in owned_map) before they become selectable.
        # The method should accept tx-confirmed + owned outputs as sufficient.
        with patch("wallet_sage.sage_topup_split", return_value={"transaction_id": "def456"}), \
             patch.object(coin_manager, "get_next_address", return_value={"success": True, "address": "xch1testaddress"}), \
             patch.object(coin_manager, "get_wallet_type", return_value="sage"), \
             patch.object(manager, "_get_owned_coin_amount_map", side_effect=[
                 {"0xsource": 600},             # pre-snapshot
                 {"0xsource": 600},             # iteration 1 — tx pending, no new coins
                 {"0xchange": 200, "0xa": 100, "0xb": 100, "0xc": 100, "0xd": 100},  # iteration 2 — coins owned (tx confirmed)
             ]), \
             patch.object(manager, "_get_strict_selectable_coin_id_set", side_effect=[
                 set(),    # iteration 1 — nothing selectable yet
                 set(),    # iteration 2 — coins owned but not yet selectable (key assertion)
             ]), \
             patch.object(manager, "_get_transaction_confirmation_state", side_effect=[
                 {"known": False, "confirmed": False, "confirmed_count": 0, "total": 1, "height": 0},
                 {"known": True, "confirmed": True, "confirmed_count": 1, "total": 1, "height": 123},
             ]), \
             patch.object(coin_manager, "log_event"), \
             patch.object(coin_manager.time, "sleep", return_value=None):
            result = manager._two_step_split(
                name="XCH-mid",
                wallet_id=1,
                source_coin_id="0xsource",
                pool_amount_mojos=400,
                num_to_create=4,
                trading_size_mojos=100,
                is_cat=False,
            )

        self.assertTrue(result)

    def test_sage_topup_split_passes_fee_coin_to_create_transaction(self):
        import wallet_sage

        with patch.object(wallet_sage, "_require_signing_capability", return_value=True), \
             patch.object(wallet_sage, "_get_cat_asset_id", return_value="0xasset"), \
             patch.object(wallet_sage, "create_transaction_rpc", return_value={"success": True}) as create_tx:
            result = wallet_sage.sage_topup_split(
                source_coin_id="0xsource",
                num_coins=1,
                trading_size_mojos=100,
                own_address="xch1testaddress",
                fee_mojos=13,
                is_cat=True,
                fee_coin_id="0xfee",
            )

        self.assertEqual(result, {"success": True})
        create_tx.assert_called_once()
        self.assertEqual(
            create_tx.call_args.kwargs["selected_coin_ids"],
            ["0xsource", "0xfee"],
        )

    def test_cat_one_step_topup_reserves_fee_pool_coin(self):
        manager = self._make_manager()
        manager.fee_pool.refresh([_record("0xfee", 1000)])

        with patch("wallet_sage.sage_topup_split", return_value={"transaction_id": "fee123"}) as split_mock, \
             patch.object(coin_manager, "get_next_address", return_value={"success": True, "address": "xch1testaddress"}), \
             patch.object(manager, "_fee_pool_enabled", return_value=True), \
             patch.object(manager, "_tx_fee_mojos", return_value=13), \
             patch.object(manager, "_get_owned_coin_amount_map", side_effect=[
                 {"0xsource": 600},
                 {"0xsource": 600, "0xa": 100},
             ]), \
             patch.object(manager, "_get_strict_selectable_coin_id_set", return_value={"0xa"}), \
             patch.object(manager, "_get_transaction_confirmation_state", return_value={
                 "known": False,
                 "confirmed": False,
                 "confirmed_count": 0,
                 "total": 1,
                 "height": 0,
             }), \
             patch.object(coin_manager, "log_event"), \
             patch.object(coin_manager.time, "sleep", return_value=None):
            result = manager._sage_one_step_split(
                name="CAT-inner",
                wallet_id=2,
                source_coin_id="0xsource",
                num_to_create=1,
                trading_size_mojos=100,
                is_cat=True,
            )

        self.assertTrue(result)
        self.assertEqual(split_mock.call_args.kwargs["fee_coin_id"], "0xfee")
        self.assertEqual(manager.fee_pool.available_count, 0)

    def test_sage_one_step_split_stamps_sniper_outputs(self):
        manager = self._make_manager()

        with patch("wallet_sage.sage_topup_split", return_value={"transaction_id": "sniper123"}), \
             patch("database.upsert_coin") as upsert_coin, \
             patch("database.set_coin_designation") as set_designation, \
             patch.object(coin_manager, "get_next_address", return_value={"success": True, "address": "xch1testaddress"}), \
             patch.object(manager, "_get_owned_coin_amount_map", side_effect=[
                 {"0xsource": 600},
                 {"0xsource": 600, "0xa": 100, "0xb": 100},
             ]), \
             patch.object(manager, "_get_strict_selectable_coin_id_set", return_value={"0xa", "0xb"}), \
             patch.object(manager, "_get_transaction_confirmation_state", return_value={
                 "known": False,
                 "confirmed": False,
                 "confirmed_count": 0,
                 "total": 1,
                 "height": 0,
             }), \
             patch.object(coin_manager, "log_event"), \
             patch.object(coin_manager.time, "sleep", return_value=None):
            result = manager._sage_one_step_split(
                name="XCH-sniper",
                wallet_id=1,
                source_coin_id="0xsource",
                num_to_create=2,
                trading_size_mojos=100,
                is_cat=False,
            )

        self.assertTrue(result)
        self.assertEqual(upsert_coin.call_count, 2)
        for call in upsert_coin.call_args_list:
            self.assertEqual(call.kwargs["wallet_type"], "xch")
            self.assertEqual(call.kwargs["designation"], "tier_spare")
            self.assertEqual(call.kwargs["assigned_tier"], "sniper")
        self.assertEqual(
            {call.args for call in set_designation.call_args_list},
            {("0xa", "tier_spare", "sniper"), ("0xb", "tier_spare", "sniper")},
        )


if __name__ == "__main__":
    unittest.main()
