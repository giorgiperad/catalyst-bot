"""Regression test for F80: get_tier_sizes_mojos_from_cfg must return
SIZE-indexed sizes for the buy side under reverse-buy so the F70 SSOT
misfit-rejection path (which compares classify_coin's output against a
SIZE-indexed preferred_tier from coin_size_tier_for_slot_position) works.

Bug history
-----------
F79 made get_buy_tier_size_xch POSITION-semantic. That broke
get_tier_sizes_mojos_from_cfg, which had been calling it directly,
producing a POSITION-indexed tier_sizes dict. F70's classifier then
labeled a 0.29 XCH coin as "inner" (POSITION tier, since 0.29 is the
inner-POSITION size under reverse-buy), but the selector wanted "extreme"
(the SIZE tier returned by coin_size_tier_for_slot_position). All buy-side
coins got rejected as misfits, slots suspended, requote produced 0 offers.

F80 fix: read BUY_*_SIZE_XCH fields directly under reverse-buy so the
dict stays SIZE-indexed (matches the DB designation scheme and the
SIZE-indexed preferred_tier).
"""
import os
import sys
import types
import unittest
from decimal import Decimal
from unittest.mock import patch


class _StubCfg:
    def __init__(self, *, reversed_buy: bool):
        self.TIER_ENABLED = True
        self.BUY_LADDER_REVERSED = reversed_buy
        # Position-indexed env values — Smart Defaults wrote these the way
        # we'd see them in production with BUY_LADDER_REVERSED toggled on.
        # Convention: BUY_INNER_SIZE_XCH stores the SIZE for the inner SIZE
        # bucket (largest XCH coin = 2.0876).
        self.BUY_INNER_SIZE_XCH = Decimal("2.0876")
        self.BUY_MID_SIZE_XCH = Decimal("1.1598")
        self.BUY_OUTER_SIZE_XCH = Decimal("0.6379")
        self.BUY_EXTREME_SIZE_XCH = Decimal("0.29")
        self.SELL_INNER_SIZE_XCH = Decimal("2.0111")
        self.SELL_MID_SIZE_XCH = Decimal("1.1173")
        self.SELL_OUTER_SIZE_XCH = Decimal("0.6145")
        self.SELL_EXTREME_SIZE_XCH = Decimal("0.2793")
        self.INNER_SIZE_XCH = Decimal("0")
        self.MID_SIZE_XCH = Decimal("0")
        self.OUTER_SIZE_XCH = Decimal("0")
        self.EXTREME_SIZE_XCH = Decimal("0")
        self.CAT_DECIMALS = 3
        self.COIN_PREP_HEADROOM_PCT = Decimal("10")
        self.COIN_PREP_HEADROOM_MULT = Decimal("1.0")
        self.WALLET_FINGERPRINT = ""


# Stubs needed for coin_manager import
def _ensure_stubs():
    if "dotenv" not in sys.modules:
        d = types.ModuleType("dotenv")
        d.load_dotenv = lambda *a, **kw: None
        d.set_key = lambda *a, **kw: None
        sys.modules["dotenv"] = d
    if "requests" not in sys.modules:
        r = types.ModuleType("requests")
        class _Resp:
            status_code = 200
            def json(self): return {}
            def raise_for_status(self): pass
        class _Session:
            headers = {}
            def get(self, *a, **kw): return _Resp()
            def mount(self, *a, **kw): pass
        r.get = lambda *a, **kw: _Resp()
        r.Session = _Session
        r.exceptions = types.SimpleNamespace(Timeout=Exception, ConnectionError=Exception)
        a = types.ModuleType("requests.adapters")
        a.HTTPAdapter = object
        r.adapters = a
        sys.modules["requests"] = r
        sys.modules["requests.adapters"] = a
    if "urllib3" not in sys.modules:
        u = types.ModuleType("urllib3")
        u.Retry = object
        u.exceptions = types.SimpleNamespace(InsecureRequestWarning=Warning)
        u.disable_warnings = lambda *a, **kw: None
        sys.modules["urllib3"] = u

_ensure_stubs()


class TierSizesReverseBuyTests(unittest.TestCase):
    """Verify the dict returned for the BUY side stays SIZE-indexed
    regardless of reverse-buy mode, so F70 classifier comparisons hold."""

    @classmethod
    def setUpClass(cls):
        os.chdir(r"C:\chia_liquidity_bot_v2_v4_tauri")
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    def setUp(self):
        import config, coin_manager
        self._real_cfg = config.cfg
        self._real_cm_cfg = getattr(coin_manager, 'cfg', None)

    def tearDown(self):
        import config, coin_manager
        config.cfg = self._real_cfg
        if self._real_cm_cfg is not None:
            coin_manager.cfg = self._real_cm_cfg

    def _patch_cfg(self, stub):
        import config, coin_manager
        config.cfg = stub
        coin_manager.cfg = stub

    def test_non_reverse_returns_size_indexed(self):
        """Baseline: non-reverse should still return SIZE-indexed sizes
        (which equals position-indexed for non-reverse — they're the same)."""
        from coin_manager import get_tier_sizes_mojos_from_cfg
        self._patch_cfg(_StubCfg(reversed_buy=False))
        sizes = get_tier_sizes_mojos_from_cfg(is_cat=False)
        # Inner key holds the largest size (BUY_INNER_SIZE_XCH = 2.0876)
        self.assertEqual(sizes["inner"], int(Decimal("2.0876") * 10**12))
        self.assertEqual(sizes["mid"], int(Decimal("1.1598") * 10**12))
        self.assertEqual(sizes["outer"], int(Decimal("0.6379") * 10**12))
        self.assertEqual(sizes["extreme"], int(Decimal("0.29") * 10**12))

    def test_reverse_buy_returns_size_indexed_not_position_indexed(self):
        """The CRITICAL F80 regression case. Pre-F80 (post-F79):
        get_buy_tier_size_xch flipped position→size, so the dict ended
        up POSITION-indexed (inner=0.29, extreme=2.09). F70 then labeled
        a 0.29 coin as "inner" but selector wanted "extreme" → reject all,
        buy requote returned 0 offers, slots suspended.

        Post-F80: env fields are read directly so the dict is SIZE-indexed
        (inner=2.09 = the inner-SIZE bucket value, extreme=0.29 = the
        smallest-SIZE bucket). Classifier labels match selector preference.
        """
        from coin_manager import get_tier_sizes_mojos_from_cfg
        self._patch_cfg(_StubCfg(reversed_buy=True))
        sizes = get_tier_sizes_mojos_from_cfg(is_cat=False)
        # MUST be SIZE-indexed: inner key = largest XCH coin = 2.0876
        self.assertEqual(
            sizes["inner"], int(Decimal("2.0876") * 10**12),
            "Inner key must hold the LARGEST size (size-indexed), not the "
            "small position-inner size. Otherwise F70 misfit rejection "
            "labels coins by POSITION and rejects all buy-side coins.",
        )
        self.assertEqual(
            sizes["extreme"], int(Decimal("0.29") * 10**12),
            "Extreme key must hold the SMALLEST size (size-indexed)."
        )
        self.assertEqual(sizes["mid"], int(Decimal("1.1598") * 10**12))
        self.assertEqual(sizes["outer"], int(Decimal("0.6379") * 10**12))

    def test_reverse_buy_cat_path_unchanged(self):
        """Sell side should be unaffected by reverse-buy."""
        from coin_manager import get_tier_sizes_mojos_from_cfg
        self._patch_cfg(_StubCfg(reversed_buy=True))
        # CAT path needs a price — patch api_server.bot to None so we hit
        # the fallback (XCH sizes used directly)
        with patch.dict(sys.modules, {'api_server': types.ModuleType('api_server')}):
            sys.modules['api_server'].bot = None
            sizes = get_tier_sizes_mojos_from_cfg(is_cat=True)
        # Sell side is never flipped — these should be SELL_*_SIZE_XCH
        # values (non-flipped). They get scaled to CAT mojos via price
        # conversion, but the relative shape stays size-indexed.
        # Just check the dict has the right keys with reasonable values.
        self.assertEqual(set(sizes.keys()), {"inner", "mid", "outer", "extreme"})
        # Inner should be the largest
        self.assertGreater(sizes["inner"], sizes["mid"])
        self.assertGreater(sizes["mid"], sizes["outer"])
        self.assertGreater(sizes["outer"], sizes["extreme"])


if __name__ == "__main__":
    unittest.main()
