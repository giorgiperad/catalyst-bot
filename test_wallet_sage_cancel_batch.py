import itertools
import sys
import types
import unittest
from unittest.mock import patch

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    requests_stub.exceptions = types.SimpleNamespace(RequestException=Exception)
    requests_adapters_stub = types.ModuleType("requests.adapters")
    requests_adapters_stub.HTTPAdapter = object
    requests_stub.adapters = requests_adapters_stub
    sys.modules["requests"] = requests_stub
    sys.modules["requests.adapters"] = requests_adapters_stub

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    dotenv_stub.set_key = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_stub

if "urllib3" not in sys.modules:
    urllib3_stub = types.ModuleType("urllib3")
    urllib3_stub.Retry = object
    urllib3_stub.disable_warnings = lambda *args, **kwargs: None
    urllib3_stub.exceptions = types.SimpleNamespace(InsecureRequestWarning=Warning)
    sys.modules["urllib3"] = urllib3_stub

import wallet_sage


class WalletSageCancelBatchTests(unittest.TestCase):
    def test_get_still_locked_trade_ids_ignores_0x_prefix(self):
        owned = {
            "0xcoin1": {"offer_id": "0xABC123"},
            "0xcoin2": {"offer_id": "def456"},
            "0xcoin3": {"offer_id": None},
        }

        locked = wallet_sage._get_still_locked_trade_ids(
            {"abc123", "0xdef456", "zzz999"}, owned
        )

        self.assertEqual(locked, {"abc123", "0xdef456"})

    def test_cancel_batch_confirms_by_unlock_when_offer_not_active_or_locked(self):
        ticks = itertools.count(start=0, step=1)

        with patch.object(wallet_sage, "cancel_offer", return_value={"success": True}), \
             patch.object(wallet_sage, "get_spendable_coin_count", return_value=100), \
             patch.object(wallet_sage, "get_pending_transactions", return_value=[]), \
             patch.object(wallet_sage, "get_all_offers", return_value=[]), \
             patch.object(wallet_sage, "get_owned_coins_detailed", return_value={}), \
             patch("builtins.print"), \
             patch.object(wallet_sage.time, "sleep", return_value=None), \
             patch.object(wallet_sage.time, "time", side_effect=lambda: next(ticks)):
            results = wallet_sage.cancel_offers_batch(["0xabc123"], secure=False)

        self.assertTrue(results["0xabc123"]["success"])
        self.assertEqual(results["0xabc123"]["method"], "confirmed_by_unlock")


if __name__ == "__main__":
    unittest.main()
