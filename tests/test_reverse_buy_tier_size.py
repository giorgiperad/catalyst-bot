"""Regression tests for F79 reverse-buy tier-size flip.

Bug history
-----------
`get_buy_tier_size_xch(tier)` is documented as POSITION-semantic — caller
asks "what size is the inner-position buy slot?" Under
`BUY_LADDER_REVERSED=True` the inner POSITION uses extreme-SIZE coins
(small near mid). Pre-F79, the function only applied the position→size
flip on the legacy fallback path (when `BUY_*_SIZE_XCH` was unset). When
Smart Defaults populated `BUY_*_SIZE_XCH` the flip was bypassed and the
function returned size-indexed values: `get_buy_tier_size_xch("inner")`
returned `BUY_INNER_SIZE_XCH` (the LARGE size used for size-inner coins)
even though the caller asked for the inner POSITION size, which under
reverse-buy should be SMALL.

Result: the buy ladder came out non-reversed (large near mid) despite
`BUY_LADDER_REVERSED=True`, exactly mirroring the sell side instead of
mirroring it.
"""
import os
import sys
import unittest
from decimal import Decimal


class _StubCfg:
    """Minimal cfg object with just the fields config helpers need."""

    def __init__(self, *, reversed_buy: bool,
                 buy_inner=None, buy_mid=None, buy_outer=None, buy_extreme=None,
                 sell_inner=None, sell_mid=None, sell_outer=None, sell_extreme=None,
                 inner=None, mid=None, outer=None, extreme=None):
        self.BUY_LADDER_REVERSED = reversed_buy
        self.BUY_INNER_SIZE_XCH = Decimal(buy_inner) if buy_inner is not None else Decimal("0")
        self.BUY_MID_SIZE_XCH = Decimal(buy_mid) if buy_mid is not None else Decimal("0")
        self.BUY_OUTER_SIZE_XCH = Decimal(buy_outer) if buy_outer is not None else Decimal("0")
        self.BUY_EXTREME_SIZE_XCH = Decimal(buy_extreme) if buy_extreme is not None else Decimal("0")
        self.SELL_INNER_SIZE_XCH = Decimal(sell_inner) if sell_inner is not None else Decimal("0")
        self.SELL_MID_SIZE_XCH = Decimal(sell_mid) if sell_mid is not None else Decimal("0")
        self.SELL_OUTER_SIZE_XCH = Decimal(sell_outer) if sell_outer is not None else Decimal("0")
        self.SELL_EXTREME_SIZE_XCH = Decimal(sell_extreme) if sell_extreme is not None else Decimal("0")
        self.INNER_SIZE_XCH = Decimal(inner) if inner is not None else Decimal("0")
        self.MID_SIZE_XCH = Decimal(mid) if mid is not None else Decimal("0")
        self.OUTER_SIZE_XCH = Decimal(outer) if outer is not None else Decimal("0")
        self.EXTREME_SIZE_XCH = Decimal(extreme) if extreme is not None else Decimal("0")


class GetBuyTierSizeReverseBuyTests(unittest.TestCase):
    """Position-semantic contract: the function returns the size for the
    POSITION the caller asked about, applying the reverse-buy flip."""

    @classmethod
    def setUpClass(cls):
        # Ensure config module is importable
        os.chdir(r"C:\chia_liquidity_bot_v2_v4_tauri")
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    def setUp(self):
        # Save and restore the live cfg so other tests aren't affected
        import config
        self._real_cfg = config.cfg

    def tearDown(self):
        import config
        config.cfg = self._real_cfg

    def _patch_cfg(self, stub):
        import config
        config.cfg = stub

    # ── Non-reverse: position == size (identity) ──────────────────────

    def test_non_reversed_returns_position_indexed_value(self):
        from config import get_buy_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=False,
            buy_inner="2.0876", buy_mid="1.1598",
            buy_outer="0.6379", buy_extreme="0.29",
        ))
        self.assertEqual(get_buy_tier_size_xch("inner"),   Decimal("2.0876"))
        self.assertEqual(get_buy_tier_size_xch("mid"),     Decimal("1.1598"))
        self.assertEqual(get_buy_tier_size_xch("outer"),   Decimal("0.6379"))
        self.assertEqual(get_buy_tier_size_xch("extreme"), Decimal("0.29"))

    # ── Reverse-buy: position inner uses extreme size, etc. ───────────

    def test_reversed_inner_position_returns_extreme_size(self):
        """Position inner (best bid) uses the extreme-SIZE coin (small).

        This is the regression case — pre-F79 returned BUY_INNER_SIZE_XCH
        (2.0876, the large size) even with reverse-buy enabled, producing
        a buy ladder that wasn't actually reversed.
        """
        from config import get_buy_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=True,
            buy_inner="2.0876", buy_mid="1.1598",
            buy_outer="0.6379", buy_extreme="0.29",
        ))
        self.assertEqual(
            get_buy_tier_size_xch("inner"), Decimal("0.29"),
            "Under reverse-buy, position INNER (best bid) must return the "
            "extreme-size value (small), not the inner-size value.",
        )

    def test_reversed_extreme_position_returns_inner_size(self):
        from config import get_buy_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=True,
            buy_inner="2.0876", buy_extreme="0.29",
            buy_mid="1.1598", buy_outer="0.6379",
        ))
        self.assertEqual(
            get_buy_tier_size_xch("extreme"), Decimal("2.0876"),
            "Under reverse-buy, position EXTREME (worst bid) must return "
            "the inner-size value (large).",
        )

    def test_reversed_mid_outer_swap(self):
        from config import get_buy_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=True,
            buy_inner="2.0876", buy_mid="1.1598",
            buy_outer="0.6379", buy_extreme="0.29",
        ))
        self.assertEqual(get_buy_tier_size_xch("mid"),   Decimal("0.6379"))  # outer size
        self.assertEqual(get_buy_tier_size_xch("outer"), Decimal("1.1598"))  # mid size

    # ── Legacy fallback path still works ──────────────────────────────

    def test_legacy_fallback_under_reverse(self):
        """When BUY_*_SIZE_XCH is unset, fall back to legacy INNER_SIZE_XCH
        with the reverse-buy flip applied."""
        from config import get_buy_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=True,
            inner="2.0", mid="1.0", outer="0.5", extreme="0.25",
        ))
        # Position inner under reverse → extreme size in legacy field
        self.assertEqual(get_buy_tier_size_xch("inner"),   Decimal("0.25"))
        self.assertEqual(get_buy_tier_size_xch("extreme"), Decimal("2.0"))

    def test_legacy_fallback_non_reverse(self):
        from config import get_buy_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=False,
            inner="2.0", mid="1.0", outer="0.5", extreme="0.25",
        ))
        self.assertEqual(get_buy_tier_size_xch("inner"),   Decimal("2.0"))
        self.assertEqual(get_buy_tier_size_xch("extreme"), Decimal("0.25"))

    # ── Sell side never flips ─────────────────────────────────────────

    def test_sell_side_ignores_reverse_buy(self):
        from config import get_sell_tier_size_xch
        self._patch_cfg(_StubCfg(
            reversed_buy=True,  # should NOT affect sell
            sell_inner="2.0876", sell_extreme="0.29",
        ))
        self.assertEqual(get_sell_tier_size_xch("inner"),   Decimal("2.0876"))
        self.assertEqual(get_sell_tier_size_xch("extreme"), Decimal("0.29"))


if __name__ == "__main__":
    unittest.main()
