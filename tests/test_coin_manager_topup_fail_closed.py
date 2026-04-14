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


class CoinManagerTopupFailClosedTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # Remove stub modules installed at module-load time so they don't
        # pollute sys.modules for test files that run later (e.g. test_amm_monitor).
        for name in _INSTALLED_STUBS:
            sys.modules.pop(name, None)
        # Also evict any modules that may have been cached with the stub
        # requests/urllib3 so they get a fresh import in later test files.
        for name in list(sys.modules):
            if name in ("amm_monitor", "coin_manager", "wallet_sage",
                        "wallet_chia", "wallet", "price_engine", "tx_fees",
                        "win_subprocess", "config", "database"):
                sys.modules.pop(name, None)

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


if __name__ == "__main__":
    unittest.main()
