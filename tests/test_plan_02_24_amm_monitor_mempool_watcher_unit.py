"""Slice 02-24 — amm_monitor.py + mempool_watcher.py unit tests.

mempool_watcher: _encode_amount (pure), compute_coin_id (pure).
amm_monitor: AMMMonitor.get_drift_bps, get_arb_pressure_label,
             check_amm_buffer — tested by injecting state directly
             into the instance (no network I/O or background thread started).
"""

import sys
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

try:
    from mempool_watcher import _encode_amount, compute_coin_id
    _SKIP_MW = None
except ModuleNotFoundError as exc:
    _SKIP_MW = str(exc)

try:
    from amm_monitor import AMMMonitor
    import config as _config_module
    _SKIP_AMM = None
except ModuleNotFoundError as exc:
    _SKIP_AMM = str(exc)

# 32-byte hex strings for coin-ID tests
_PARENT = "a" * 64
_PUZZLE = "b" * 64


# ---------------------------------------------------------------------------
# _encode_amount
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP_MW is not None, f"mempool_watcher unavailable: {_SKIP_MW}")
class TestEncodeAmount(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(_encode_amount(0), b"\x00")

    def test_one(self):
        self.assertEqual(_encode_amount(1), b"\x01")

    def test_127_no_high_bit(self):
        # 0x7f: high bit NOT set — no leading zero needed
        self.assertEqual(_encode_amount(127), b"\x7f")

    def test_128_high_bit_set(self):
        # 0x80: high bit IS set — prepend 0x00 to keep unsigned
        self.assertEqual(_encode_amount(128), b"\x00\x80")

    def test_255_high_bit_set(self):
        self.assertEqual(_encode_amount(255), b"\x00\xff")

    def test_256_two_bytes(self):
        # 0x01 0x00 — high bit of 0x01 not set
        self.assertEqual(_encode_amount(256), b"\x01\x00")

    def test_large_value(self):
        # 1_000_000_000_000 = 0x000000E8D4A51000
        # bytes: e8 d4 a5 10 00 — 0xe8 has high bit set → prepend 0x00
        result = _encode_amount(1_000_000_000_000)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)
        # Verify round-trip via int.from_bytes interpretation
        val = int.from_bytes(result, "big")
        self.assertEqual(val, 1_000_000_000_000)

    def test_returns_bytes(self):
        self.assertIsInstance(_encode_amount(42), bytes)


# ---------------------------------------------------------------------------
# compute_coin_id
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP_MW is not None, f"mempool_watcher unavailable: {_SKIP_MW}")
class TestComputeCoinId(unittest.TestCase):
    def test_returns_64_char_hex(self):
        result = compute_coin_id(_PARENT, _PUZZLE, 1000)
        self.assertEqual(len(result), 64)
        int(result, 16)  # must be valid hex

    def test_deterministic(self):
        r1 = compute_coin_id(_PARENT, _PUZZLE, 1000)
        r2 = compute_coin_id(_PARENT, _PUZZLE, 1000)
        self.assertEqual(r1, r2)

    def test_different_amount_gives_different_id(self):
        r1 = compute_coin_id(_PARENT, _PUZZLE, 1000)
        r2 = compute_coin_id(_PARENT, _PUZZLE, 2000)
        self.assertNotEqual(r1, r2)

    def test_invalid_hex_parent_returns_empty(self):
        self.assertEqual(compute_coin_id("not_hex", _PUZZLE, 100), "")

    def test_invalid_hex_puzzle_returns_empty(self):
        self.assertEqual(compute_coin_id(_PARENT, "ZZZ", 100), "")

    def test_0x_prefix_stripped(self):
        # lstrip("0x") normalises 0x-prefixed inputs
        r1 = compute_coin_id(_PARENT, _PUZZLE, 100)
        r2 = compute_coin_id("0x" + _PARENT, "0x" + _PUZZLE, 100)
        self.assertEqual(r1, r2)


# ---------------------------------------------------------------------------
# AMMMonitor helpers
# ---------------------------------------------------------------------------

def _make_monitor() -> "AMMMonitor":
    """Return an AMMMonitor instance with no background thread started."""
    return AMMMonitor(price_engine=None)


def _inject_state(mon: "AMMMonitor", amm_price=None, available=True):
    """Inject fake AMM state directly into the monitor."""
    mon._state = {
        "amm_price": amm_price,
        "available": available,
    }


def _fake_cfg(enable_buffer=False, buffer_bps="30"):
    return SimpleNamespace(
        ENABLE_AMM_BUFFER=enable_buffer,
        AMM_BUFFER_BPS=buffer_bps,
    )


# ---------------------------------------------------------------------------
# AMMMonitor.get_drift_bps
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP_AMM is not None, f"amm_monitor unavailable: {_SKIP_AMM}")
class TestGetDriftBps(unittest.TestCase):
    def setUp(self):
        self.mon = _make_monitor()

    def test_no_state_returns_none(self):
        self.assertIsNone(self.mon.get_drift_bps())

    def test_no_amm_price_returns_none(self):
        _inject_state(self.mon, amm_price=None)
        self.assertIsNone(self.mon.get_drift_bps())

    def test_no_quoted_prices_returns_none(self):
        _inject_state(self.mon, amm_price=Decimal("0.001"))
        self.assertIsNone(self.mon.get_drift_bps())

    def test_same_price_gives_zero_drift(self):
        price = Decimal("0.001")
        _inject_state(self.mon, amm_price=price)
        self.mon._last_quoted_buy = price
        self.mon._last_quoted_sell = price
        drift = self.mon.get_drift_bps()
        self.assertIsNotNone(drift)
        self.assertEqual(drift, Decimal("0"))

    def test_1pct_drift_is_100bps(self):
        amm = Decimal("0.001010")   # 1% above quoted
        quoted = Decimal("0.001000")
        _inject_state(self.mon, amm_price=amm)
        self.mon._last_quoted_buy = quoted
        self.mon._last_quoted_sell = quoted
        drift = self.mon.get_drift_bps()
        self.assertIsNotNone(drift)
        self.assertAlmostEqual(float(drift), 100.0, places=0)

    def test_uses_buy_only_when_no_sell(self):
        price = Decimal("0.001")
        _inject_state(self.mon, amm_price=price)
        self.mon._last_quoted_buy = price
        self.mon._last_quoted_sell = None
        drift = self.mon.get_drift_bps()
        self.assertIsNotNone(drift)
        self.assertEqual(drift, Decimal("0"))

    def test_drift_is_always_non_negative(self):
        _inject_state(self.mon, amm_price=Decimal("0.0009"))  # amm below quoted
        self.mon._last_quoted_buy = Decimal("0.001")
        self.mon._last_quoted_sell = Decimal("0.001")
        drift = self.mon.get_drift_bps()
        self.assertIsNotNone(drift)
        self.assertGreaterEqual(drift, Decimal("0"))


# ---------------------------------------------------------------------------
# AMMMonitor.get_arb_pressure_label
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP_AMM is not None, f"amm_monitor unavailable: {_SKIP_AMM}")
class TestGetArbPressureLabel(unittest.TestCase):
    def setUp(self):
        self.mon = _make_monitor()

    def _label_for(self, score: float) -> str:
        with patch.object(self.mon, "get_arb_pressure", return_value=score):
            return self.mon.get_arb_pressure_label()

    def test_low_below_0_3(self):
        self.assertEqual(self._label_for(0.0), "low")
        self.assertEqual(self._label_for(0.29), "low")

    def test_moderate_0_3_to_0_6(self):
        self.assertEqual(self._label_for(0.3), "moderate")
        self.assertEqual(self._label_for(0.59), "moderate")

    def test_high_0_6_to_0_9(self):
        self.assertEqual(self._label_for(0.6), "high")
        self.assertEqual(self._label_for(0.89), "high")

    def test_critical_at_0_9(self):
        self.assertEqual(self._label_for(0.9), "critical")
        self.assertEqual(self._label_for(1.0), "critical")


# ---------------------------------------------------------------------------
# AMMMonitor.check_amm_buffer
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP_AMM is not None, f"amm_monitor unavailable: {_SKIP_AMM}")
class TestCheckAmmBuffer(unittest.TestCase):
    def setUp(self):
        self.mon = _make_monitor()
        self._orig_cfg = _config_module.cfg
        # Ensure our module stays in sys.modules even if a prior tearDown removed it
        sys.modules["config"] = _config_module

    def tearDown(self):
        _config_module.cfg = self._orig_cfg
        sys.modules["config"] = _config_module

    def _set_cfg(self, enable=True, bps="30"):
        _config_module.cfg = _fake_cfg(enable_buffer=enable, buffer_bps=bps)
        sys.modules["config"] = _config_module

    def test_buffer_disabled_always_returns_true(self):
        self._set_cfg(enable=False)
        _inject_state(self.mon, amm_price=Decimal("0.001"))
        self.assertTrue(self.mon.check_amm_buffer(Decimal("0.001"), "buy"))

    def test_no_state_returns_true_fail_open(self):
        self._set_cfg(enable=True)
        # _state is None → fail open
        self.assertTrue(self.mon.check_amm_buffer(Decimal("0.001"), "buy"))

    def test_state_not_available_returns_true_fail_open(self):
        self._set_cfg(enable=True)
        _inject_state(self.mon, amm_price=Decimal("0.001"), available=False)
        self.assertTrue(self.mon.check_amm_buffer(Decimal("0.001"), "buy"))

    def test_buy_safe_below_threshold(self):
        # AMM = 0.001, buffer=30bps → threshold = 0.001 * (1 - 0.003) = 0.000997
        # offer=0.0009 < threshold → safe → True
        self._set_cfg(enable=True, bps="30")
        _inject_state(self.mon, amm_price=Decimal("0.001"))
        self.assertTrue(self.mon.check_amm_buffer(Decimal("0.0009"), "buy"))

    def test_buy_unsafe_above_threshold(self):
        # offer=0.001 >= threshold (0.000997) → inside buffer → False
        self._set_cfg(enable=True, bps="30")
        _inject_state(self.mon, amm_price=Decimal("0.001"))
        self.assertFalse(self.mon.check_amm_buffer(Decimal("0.001"), "buy"))

    def test_sell_safe_above_threshold(self):
        # AMM = 0.001, buffer=30bps → threshold = 0.001 * (1 + 0.003) = 0.001003
        # offer=0.002 > threshold → safe → True
        self._set_cfg(enable=True, bps="30")
        _inject_state(self.mon, amm_price=Decimal("0.001"))
        self.assertTrue(self.mon.check_amm_buffer(Decimal("0.002"), "sell"))

    def test_sell_unsafe_below_threshold(self):
        # offer=0.001 <= threshold (0.001003) → inside buffer → False
        self._set_cfg(enable=True, bps="30")
        _inject_state(self.mon, amm_price=Decimal("0.001"))
        self.assertFalse(self.mon.check_amm_buffer(Decimal("0.001"), "sell"))


if __name__ == "__main__":
    unittest.main()
