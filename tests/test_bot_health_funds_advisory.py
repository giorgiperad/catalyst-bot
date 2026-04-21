"""Tests for the low-funds advisory check in bot_health.

Emits a persistent alert via the AlertStore when the wallet doesn't have
enough spendable XCH or CAT above the hard reserve to support even one
inner-tier refill split. Auto-clears when the balance climbs back above
the operating floor.
"""

import sys
import types
import unittest
from decimal import Decimal
from unittest.mock import patch, MagicMock


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


import bot_health


class _FakeEventBus:
    """Capture AlertStore calls in-memory."""

    def __init__(self):
        self.alerts = {}
        self.cleared = []
        self._alert_store = self

    def alert(self, alert_id, severity, title, message,
              action=None, action_label=None, action_value=None):
        self.alerts[alert_id] = {
            "id": alert_id,
            "severity": severity,
            "title": title,
            "message": message,
        }

    def set_alert(self, alert_id, severity, title, message, *args, **kwargs):
        self.alert(alert_id, severity, title, message)

    def clear(self, alert_id):
        self.cleared.append(alert_id)
        self.alerts.pop(alert_id, None)


class FundsAdvisoryTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # Leave bot_health / config / database loaded: tearing them down
        # and letting another test class re-import them triggers subtle
        # timing issues with module-level state (e.g. the bot_health
        # `_last_report` throttle cache). Stubs are safe to pop.
        for name in _INSTALLED_STUBS:
            sys.modules.pop(name, None)
        # Clear our fake api_server specifically so drift tests don't
        # inherit it.
        sys.modules.pop("api_server", None)

    def _install_fake_bus(self):
        """Install a fake event bus accessible via `from api_server import events`."""
        bus = _FakeEventBus()
        fake_api = types.ModuleType("api_server")
        fake_api.events = bus
        sys.modules["api_server"] = fake_api
        return bus

    def _uninstall_fake_bus(self):
        sys.modules.pop("api_server", None)

    # ------------------------------------------------------------------
    # Healthy wallet → no alert
    # ------------------------------------------------------------------

    def test_healthy_wallet_no_alert(self):
        """Spendable >> operating floor → pass, no alert raised."""
        bus = self._install_fake_bus()
        try:
            cfg = bot_health.cfg
            # Spendable 100 XCH, reserve 10 XCH, floor ~ 2×0.6 = 1.2 XCH
            balance = {"wallet_balance": {"spendable_balance": 100 * 10**12}}
            with patch.object(cfg, "XCH_RESERVE", Decimal("10")), \
                 patch.object(cfg, "CAT_RESERVE", Decimal("0")), \
                 patch.object(cfg, "SELL_INNER_SIZE_XCH", Decimal("0.6023")), \
                 patch.object(cfg, "WALLET_ID_XCH", 1), \
                 patch.object(cfg, "CAT_WALLET_ID", 2), \
                 patch.object(cfg, "WALLET_ADDRESS", "xch1test..."), \
                 patch("wallet.get_wallet_type", return_value="sage"), \
                 patch("wallet_sage.get_wallet_balance", return_value=balance):
                check = bot_health.check_funds_advisory(auto_repair=True)

            self.assertEqual(check.status, "pass")
            self.assertEqual(check.anomaly_count, 0)
            self.assertNotIn("funds_advisory_xch", bus.alerts)
        finally:
            self._uninstall_fake_bus()

    # ------------------------------------------------------------------
    # Low XCH → alert raised with address + suggested amount
    # ------------------------------------------------------------------

    def test_low_xch_raises_alert_with_address(self):
        """Spendable below floor → alert with send-to address and amount."""
        bus = self._install_fake_bus()
        try:
            cfg = bot_health.cfg
            # Spendable 10.05 XCH, reserve 10 XCH → available 0.05 XCH.
            # Floor = 2×0.6023 + 0.01 = 1.2146 XCH. 0.05 < 1.21 → alert.
            balance = {"wallet_balance": {"spendable_balance": 10_050_000_000_000}}
            with patch.object(cfg, "XCH_RESERVE", Decimal("10")), \
                 patch.object(cfg, "CAT_RESERVE", Decimal("0")), \
                 patch.object(cfg, "SELL_INNER_SIZE_XCH", Decimal("0.6023")), \
                 patch.object(cfg, "WALLET_ID_XCH", 1), \
                 patch.object(cfg, "CAT_WALLET_ID", 2), \
                 patch.object(cfg, "WALLET_ADDRESS", "xch1demo123..."), \
                 patch("wallet.get_wallet_type", return_value="sage"), \
                 patch("wallet_sage.get_wallet_balance", return_value=balance):
                check = bot_health.check_funds_advisory(auto_repair=True)

            self.assertEqual(check.status, "warn")
            self.assertGreaterEqual(check.anomaly_count, 1)
            self.assertIn("funds_advisory_xch", bus.alerts)
            alert = bus.alerts["funds_advisory_xch"]
            self.assertEqual(alert["severity"], "warning")
            self.assertIn("XCH", alert["title"])
            self.assertIn("xch1demo123...", alert["message"])
            # Suggested amount ≥ 5 × 0.6023 ≈ 3.01 XCH
            self.assertIn("Send at least", alert["message"])
        finally:
            self._uninstall_fake_bus()

    # ------------------------------------------------------------------
    # Recovery → alert auto-clears when funds replenished
    # ------------------------------------------------------------------

    def test_alert_auto_clears_when_funds_restored(self):
        """After the user tops up, the next check clears the alert."""
        bus = self._install_fake_bus()
        try:
            cfg = bot_health.cfg
            # First call: low.
            low_balance = {"wallet_balance": {"spendable_balance": 10_050_000_000_000}}
            with patch.object(cfg, "XCH_RESERVE", Decimal("10")), \
                 patch.object(cfg, "CAT_RESERVE", Decimal("0")), \
                 patch.object(cfg, "SELL_INNER_SIZE_XCH", Decimal("0.6023")), \
                 patch.object(cfg, "WALLET_ID_XCH", 1), \
                 patch.object(cfg, "CAT_WALLET_ID", 2), \
                 patch.object(cfg, "WALLET_ADDRESS", "xch1..."), \
                 patch("wallet.get_wallet_type", return_value="sage"), \
                 patch("wallet_sage.get_wallet_balance", return_value=low_balance):
                bot_health.check_funds_advisory(auto_repair=True)

            self.assertIn("funds_advisory_xch", bus.alerts)

            # Second call: funds restored.
            healthy_balance = {"wallet_balance": {"spendable_balance": 50 * 10**12}}
            with patch.object(cfg, "XCH_RESERVE", Decimal("10")), \
                 patch.object(cfg, "CAT_RESERVE", Decimal("0")), \
                 patch.object(cfg, "SELL_INNER_SIZE_XCH", Decimal("0.6023")), \
                 patch.object(cfg, "WALLET_ID_XCH", 1), \
                 patch.object(cfg, "CAT_WALLET_ID", 2), \
                 patch.object(cfg, "WALLET_ADDRESS", "xch1..."), \
                 patch("wallet.get_wallet_type", return_value="sage"), \
                 patch("wallet_sage.get_wallet_balance", return_value=healthy_balance):
                check = bot_health.check_funds_advisory(auto_repair=True)

            self.assertEqual(check.status, "pass")
            self.assertNotIn("funds_advisory_xch", bus.alerts)
            self.assertIn("funds_advisory_xch", bus.cleared)
        finally:
            self._uninstall_fake_bus()

    # ------------------------------------------------------------------
    # Read-only mode
    # ------------------------------------------------------------------

    def test_read_only_mode_reports_but_no_alert(self):
        """auto_repair=False reports findings but does NOT emit an alert."""
        bus = self._install_fake_bus()
        try:
            cfg = bot_health.cfg
            low_balance = {"wallet_balance": {"spendable_balance": 10_050_000_000_000}}
            with patch.object(cfg, "XCH_RESERVE", Decimal("10")), \
                 patch.object(cfg, "CAT_RESERVE", Decimal("0")), \
                 patch.object(cfg, "SELL_INNER_SIZE_XCH", Decimal("0.6023")), \
                 patch.object(cfg, "WALLET_ID_XCH", 1), \
                 patch.object(cfg, "CAT_WALLET_ID", 2), \
                 patch.object(cfg, "WALLET_ADDRESS", "xch1..."), \
                 patch("wallet.get_wallet_type", return_value="sage"), \
                 patch("wallet_sage.get_wallet_balance", return_value=low_balance):
                check = bot_health.check_funds_advisory(auto_repair=False)

            # Condition still detected and reported...
            self.assertEqual(check.status, "warn")
            self.assertGreaterEqual(check.anomaly_count, 1)
            # ...but no user-visible alert was pushed.
            self.assertNotIn("funds_advisory_xch", bus.alerts)
        finally:
            self._uninstall_fake_bus()


if __name__ == "__main__":
    unittest.main()
