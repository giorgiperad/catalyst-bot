import unittest
from unittest.mock import patch
import sys
import types

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    dotenv_stub.set_key = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_stub

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _DummyResponse:
        status_code = 200

        def json(self):
            return {"status": "success"}

        def raise_for_status(self):
            return None

    requests_stub.get = lambda *args, **kwargs: _DummyResponse()
    requests_stub.Session = object
    requests_stub.exceptions = types.SimpleNamespace(
        Timeout=Exception,
        ConnectionError=Exception,
    )
    requests_adapters_stub = types.ModuleType("requests.adapters")
    requests_adapters_stub.HTTPAdapter = object
    requests_stub.adapters = requests_adapters_stub
    sys.modules["requests"] = requests_stub
    sys.modules["requests.adapters"] = requests_adapters_stub

if "urllib3" not in sys.modules:
    urllib3_stub = types.ModuleType("urllib3")
    urllib3_stub.Retry = object
    urllib3_stub.exceptions = types.SimpleNamespace(InsecureRequestWarning=Warning)
    urllib3_stub.disable_warnings = lambda *args, **kwargs: None
    sys.modules["urllib3"] = urllib3_stub

import coin_manager


def _record(coin_id: str, amount: int) -> dict:
    return {
        "coin_id": coin_id,
        "coin": {
            "amount": amount,
        },
    }


class CoinManagerTopupFailClosedTests(unittest.TestCase):
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
        rpc_sequence = [
            {"records": [_record("0xsource", 600)]},
            {"records": [
                _record("0xsource", 600),
                _record("0xpool", 400),
            ]},
            {"records": [
                _record("0xchange", 200),
                _record("0xa", 100),
                _record("0xb", 100),
                _record("0xc", 100),
                _record("0xd", 100),
            ]},
        ]

        with patch.object(coin_manager, "get_next_address", return_value={"success": True, "address": "xch1testaddress"}), \
             patch.object(manager, "_snapshot_coin_ids", return_value={"0xsource": 600}), \
             patch.object(coin_manager, "_get_free_coins_rpc", side_effect=rpc_sequence), \
             patch.object(coin_manager, "get_wallet_type", return_value="sage"), \
             patch.object(coin_manager, "send_transaction", return_value={"tx_id": "abc123"}), \
             patch.object(coin_manager, "split_coins_rpc", return_value=None), \
             patch.object(manager, "_get_owned_coin_amount_map", side_effect=[
                 {"0xsource": 600},
                 {"0xsource": 600, "0xpool": 400},
                 {"0xsource": 600, "0xpool": 400},
                 {"0xchange": 200, "0xa": 100, "0xb": 100, "0xc": 100, "0xd": 100},
             ]), \
             patch.object(manager, "_get_strict_selectable_coin_id_set", side_effect=[
                 {"0xpool"},
                 {"0xa", "0xb", "0xc", "0xd"},
             ]), \
             patch.object(manager, "_get_transaction_confirmation_state", side_effect=[
                 {"known": False, "confirmed": False, "confirmed_count": 0, "total": 1, "height": 0},
                 {"known": False, "confirmed": False, "confirmed_count": 0, "total": 1, "height": 0},
             ]), \
             patch.object(manager, "_spacescan_coin_spent_confirmed", return_value=True), \
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
        rpc_sequence = [
            {"records": [_record("0xsource", 600)]},
            {"records": [
                _record("0xsource", 600),
                _record("0xpool", 400),
            ]},
            {"records": [
                _record("0xchange", 200),
                _record("0xa", 100),
                _record("0xb", 100),
                _record("0xc", 100),
                _record("0xd", 100),
            ]},
        ]

        with patch.object(coin_manager, "get_next_address", return_value={"success": True, "address": "xch1testaddress"}), \
             patch.object(manager, "_snapshot_coin_ids", return_value={"0xsource": 600}), \
             patch.object(coin_manager, "_get_free_coins_rpc", side_effect=rpc_sequence), \
             patch.object(coin_manager, "get_wallet_type", return_value="sage"), \
             patch.object(coin_manager, "send_transaction", return_value={"transaction_id": "abc123"}), \
             patch.object(coin_manager, "split_coins_rpc", return_value={"transaction_id": "def456"}), \
             patch.object(manager, "_get_owned_coin_amount_map", side_effect=[
                 {"0xsource": 600},
                 {"0xsource": 600, "0xpool": 400},
                 {"0xsource": 600, "0xpool": 400},
                 {"0xchange": 200, "0xa": 100, "0xb": 100, "0xc": 100, "0xd": 100},
             ]), \
             patch.object(manager, "_get_strict_selectable_coin_id_set", side_effect=[
                 {"0xpool"},
                 set(),
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
