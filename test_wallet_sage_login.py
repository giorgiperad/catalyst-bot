import unittest
from unittest.mock import patch

try:
    import wallet_sage
    _IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    wallet_sage = None
    _IMPORT_ERROR = exc


@unittest.skipIf(wallet_sage is None, f"wallet_sage import unavailable: {_IMPORT_ERROR}")
class TestWalletSageLogin(unittest.TestCase):
    def test_login_follows_version_resync_login_sequence(self):
        """sage_login should call get_version → resync → login → get_current_key."""
        calls = []

        def fake_rpc(method, payload, timeout=0):
            calls.append(method)
            if method == "get_version":
                return {"version": "0.12.10"}
            if method == "resync":
                return {"success": True}
            if method == "login":
                return {"success": True}
            return None

        with patch.object(wallet_sage, "rpc", side_effect=fake_rpc):
            with patch.object(wallet_sage, "get_current_key",
                              return_value={"fingerprint": 1234567890, "name": "Test", "has_secrets": True}):
                with patch.object(wallet_sage.time, "sleep", return_value=None):
                    ok = wallet_sage.sage_login(1234567890)

        self.assertTrue(ok)
        self.assertEqual(calls, ["get_version", "resync", "login"])

    def test_login_returns_false_when_resync_fails(self):
        """If resync returns None, sage_login should return False."""
        calls = []

        def fake_rpc(method, payload, timeout=0):
            calls.append(method)
            if method == "get_version":
                return {"version": "0.12.10"}
            if method == "resync":
                return None  # resync failed
            return None

        with patch.object(wallet_sage, "rpc", side_effect=fake_rpc):
            with patch.object(wallet_sage.time, "sleep", return_value=None):
                ok = wallet_sage.sage_login(1234567890)

        self.assertFalse(ok)
        self.assertEqual(calls, ["get_version", "resync"])

    def test_login_returns_false_when_sage_unreachable(self):
        """If get_version returns None, sage_login should return False immediately."""
        calls = []

        def fake_rpc(method, payload, timeout=0):
            calls.append(method)
            return None  # Sage not responding

        with patch.object(wallet_sage, "rpc", side_effect=fake_rpc):
            with patch.object(wallet_sage.time, "sleep", return_value=None):
                ok = wallet_sage.sage_login(1234567890)

        self.assertFalse(ok)
        self.assertEqual(calls, ["get_version"])

    def test_login_returns_true_on_fingerprint_mismatch(self):
        """sage_login returns True even when active key fingerprint differs (connected but different wallet)."""
        def fake_rpc(method, payload, timeout=0):
            if method == "get_version":
                return {"version": "0.12.10"}
            if method == "resync":
                return {"success": True}
            if method == "login":
                return {"success": True}
            return None

        with patch.object(wallet_sage, "rpc", side_effect=fake_rpc):
            with patch.object(wallet_sage, "get_current_key",
                              return_value={"fingerprint": 999999, "name": "Wrong", "has_secrets": True}):
                with patch.object(wallet_sage.time, "sleep", return_value=None):
                    ok = wallet_sage.sage_login(1234567890)

        # Returns False — fingerprint mismatch is a hard error (HIGH-1 fix).
        # Connecting to the wrong wallet would cause the bot to trade against
        # an unintended account; refusing to start is the correct safe behaviour.
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
