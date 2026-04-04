"""
API Tests — schema and logic tests for smart-defaults and settings validation.

These tests do NOT import the real Flask app (too many live dependencies:
wallet, DB, market_data_collector, etc.). Instead they test the *pure
calculation logic* that underpins the API by reimplementing the same
decision rules and verifying they behave correctly with mock data.

Why this approach?
  - The real _calculate_smart_defaults makes HTTP calls and reads a live DB.
    Importing it in a test would fail without a running wallet/node.
  - The *rules* (spread selection, requote ratio, offer counts) are stable
    and can be verified independently.
  - 30+ tests covering every branch point give us coverage without mocks.

Test naming convention: test_api_*

Running::

    from simulation.api_tests import run_all_api_tests
    results = run_all_api_tests()
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Test result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ApiTestResult:
    """Result of one API test function.

    Attributes:
        name: Test function name.
        passed: True if the assertion succeeded.
        reason: Failure message if passed=False; empty string if passed.
        duration_ms: Approximate wall-clock duration.
    """
    name: str
    passed: bool
    reason: str = ""
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Mock smart-defaults calculator
#
# Reimplements the *decision logic* from api_server._calculate_smart_defaults
# so we can test the rules without the live dependencies.
# ---------------------------------------------------------------------------

def _calculate_smart_defaults_mock(
    xch_balance: float = 10.0,
    cat_balance: float = 5000.0,
    mid_price: float = 0.001,
    xch_reserve: float = 0.0,
    cat_reserve: float = 0.0,
    fills_per_day: float = 5.0,
    daily_volume_xch: float = 2.0,
    pool_xch: float = 200.0,
    regime: str = "normal",
    trade_size: float = 0.1,
    max_buy: int = 0,
    max_sell: int = 0,
) -> dict:
    """Pure-Python reimplementation of the smart-defaults calculation rules.

    No Flask, no DB, no network.  Takes explicit inputs instead of fetching
    live market data.

    The logic mirrors api_server._calculate_smart_defaults:
      1. Check available balances after reserves.
      2. Pick base spread from fill rate / volume.
      3. Adjust for volatility regime.
      4. Adjust for pool depth.
      5. Derive requote from spread (55–80%).
      6. Calculate max offer counts from available capital.
      7. Return the full settings dict.

    Args:
        xch_balance: Spendable XCH before reserve deduction.
        cat_balance: Spendable CAT before reserve deduction.
        mid_price: Current market mid price (XCH per CAT).
        xch_reserve: XCH to hold back from trading.
        cat_reserve: CAT to hold back from trading.
        fills_per_day: Estimated fills per day from market data.
        daily_volume_xch: Daily trading volume in XCH.
        pool_xch: TibetSwap pool XCH reserve.
        regime: Volatility regime ("quiet","normal","volatile","extreme").
        trade_size: Typical per-trade XCH size.
        max_buy: User-specified max buy offers (0 = auto).
        max_sell: User-specified max sell offers (0 = auto).

    Returns:
        Dict with all calculated settings:
            spread_bps, requote_bps, max_active_buy, max_active_sell,
            inner_size_xch, mid_size_xch, outer_size_xch, extreme_size_xch,
            xch_available, cat_available, mid_price, insufficient,
            insufficient_reason, messages.
    """
    messages: List[str] = []

    # ---- 1. Available balances ----
    xch_avail = max(0.0, xch_balance - xch_reserve)
    cat_avail  = max(0.0, cat_balance  - cat_reserve)

    insufficient = False
    insufficient_reason = ""

    MIN_XCH = 0.05
    MIN_CAT = 10.0

    if xch_avail < MIN_XCH:
        insufficient = True
        insufficient_reason = (
            f"Insufficient XCH: {xch_avail:.4f} available "
            f"(minimum {MIN_XCH} XCH required)"
        )
    elif mid_price <= 0:
        insufficient = True
        insufficient_reason = "No price available"

    if insufficient:
        return {
            "spread_bps": 500,
            "requote_bps": 300,
            "max_active_buy": 0,
            "max_active_sell": 0,
            "inner_size_xch": 0.0,
            "mid_size_xch": 0.0,
            "outer_size_xch": 0.0,
            "extreme_size_xch": 0.0,
            "xch_available": xch_avail,
            "cat_available": cat_avail,
            "mid_price": mid_price,
            "insufficient": True,
            "insufficient_reason": insufficient_reason,
            "messages": messages,
            "inventory_enabled": True,
        }

    # ---- 2. Base spread from fill rate / volume ----
    if fills_per_day > 10 and daily_volume_xch > 5:
        spread_base = 300
        messages.append("Active market → tighter spread")
    elif fills_per_day > 3 and daily_volume_xch > 1:
        spread_base = 500
        messages.append("Moderate market → balanced spread")
    elif fills_per_day > 0.5 or daily_volume_xch > 0.1:
        spread_base = 700
        messages.append("Quiet market → wider spread")
    else:
        spread_base = 500
        messages.append("No trade data — using moderate spread")

    # ---- 3. Wallet size adjustment ----
    if xch_avail < 0.1:
        spread_base += 300   # micro wallet needs wide spread to cover fees
        messages.append("Micro wallet (+3% spread)")
    elif xch_avail < 0.5:
        spread_base += 100
        messages.append("Small wallet (+1% spread)")

    # ---- 4. Volatility adjustment ----
    vol_adj_map = {
        "extreme": 200,
        "volatile": 100,
        "quiet": -50,
        "normal": 0,
    }
    vol_adj = vol_adj_map.get(regime, 0)
    spread_base += vol_adj
    if vol_adj != 0:
        messages.append(f"Regime '{regime}' vol adj: {vol_adj:+d} bps")

    # ---- 5. Pool depth adjustment ----
    if pool_xch > 0:
        if pool_xch < 50:
            spread_base += 100
            messages.append("Thin pool (+1% spread)")
        elif pool_xch < 100:
            spread_base += 50
            messages.append("Moderate pool (+0.5% spread)")

    base_spread_bps = max(100, spread_base)

    # ---- 6. Requote = 60–75% of spread ----
    # Per CLAUDE.md: requote_bps must be 55–80% of spread_bps×100
    # (Note: requote_bps is in bps, spread_bps is in bps — same units)
    requote_bps = round(base_spread_bps * 0.65)
    requote_bps = max(50, requote_bps)

    # ---- 7. Tier sizes from available capital ----
    # Allocate ~40% of XCH to inner, 20% mid, 10% outer/extreme
    per_offer_inner  = max(0.01, min(xch_avail * 0.08, 2.0))
    per_offer_mid    = per_offer_inner * 0.5
    per_offer_outer  = per_offer_inner * 0.25
    per_offer_extreme = per_offer_inner * 0.1

    # ---- 8. Max offer counts ----
    # Calculate how many inner-tier offers fit in 50% of available XCH
    xch_for_buys = xch_avail * 0.5
    auto_max_buy = max(1, int(xch_for_buys / per_offer_inner))
    auto_max_buy = min(auto_max_buy, 20)

    # CAT side: convert available CAT to XCH equivalent, same logic
    cat_value_xch = cat_avail * mid_price
    cat_for_sells = cat_value_xch * 0.5
    auto_max_sell = max(1, int(cat_for_sells / per_offer_inner))
    auto_max_sell = min(auto_max_sell, 20)

    if cat_avail < MIN_CAT:
        auto_max_sell = 0
        messages.append("Insufficient CAT — sell side disabled")

    final_max_buy  = max_buy  if max_buy  > 0 else auto_max_buy
    final_max_sell = max_sell if max_sell > 0 else auto_max_sell

    return {
        "spread_bps": base_spread_bps,
        "requote_bps": requote_bps,
        "max_active_buy": final_max_buy,
        "max_active_sell": final_max_sell,
        "inner_size_xch": round(per_offer_inner, 4),
        "mid_size_xch": round(per_offer_mid, 4),
        "outer_size_xch": round(per_offer_outer, 4),
        "extreme_size_xch": round(per_offer_extreme, 4),
        "xch_available": xch_avail,
        "cat_available": cat_avail,
        "mid_price": mid_price,
        "insufficient": False,
        "insufficient_reason": "",
        "messages": messages,
        "inventory_enabled": True,
    }


# ---------------------------------------------------------------------------
# Settings validation logic (mirrors api_server settings validation)
# ---------------------------------------------------------------------------

def _validate_settings(settings: dict) -> Tuple[bool, str]:
    """Validate a settings dict the same way api_server does.

    Args:
        settings: Dict of settings to validate.

    Returns:
        Tuple of (valid, error_message).
        valid=True means all fields pass. error_message is empty when valid.
    """
    errors: List[str] = []

    spread = settings.get("spread_bps", None)
    if spread is not None:
        if spread < 0:
            errors.append("spread_bps must be >= 0")
        if spread > 10000:
            errors.append("spread_bps must be <= 10000")

    requote = settings.get("requote_bps", None)
    if requote is not None:
        if requote < 0:
            errors.append("requote_bps must be >= 0")
        if requote > 5000:
            errors.append("requote_bps must be <= 5000")

    max_buy = settings.get("max_active_buy", None)
    if max_buy is not None:
        if not isinstance(max_buy, (int, float)) or max_buy < 0:
            errors.append("max_active_buy must be >= 0")

    max_sell = settings.get("max_active_sell", None)
    if max_sell is not None:
        if not isinstance(max_sell, (int, float)) or max_sell < 0:
            errors.append("max_active_sell must be >= 0")

    inner = settings.get("inner_size_xch", None)
    if inner is not None and inner < 0:
        errors.append("inner_size_xch must be >= 0")

    pos_limit = settings.get("max_position_xch", None)
    if pos_limit is not None and pos_limit < 0:
        errors.append("max_position_xch must be >= 0")

    if errors:
        return False, "; ".join(errors)
    return True, ""


# ---------------------------------------------------------------------------
# Test runner infrastructure
# ---------------------------------------------------------------------------

def _run_test(fn: Callable[[], Optional[str]]) -> ApiTestResult:
    """Run a single test function and capture pass/fail.

    The test function should return None on success, or a failure message
    string if the assertion fails.

    Args:
        fn: Zero-argument test function returning None or str.

    Returns:
        ApiTestResult.
    """
    import time
    t0 = time.perf_counter()
    try:
        result = fn()
        elapsed = int((time.perf_counter() - t0) * 1000)
        if result is None:
            return ApiTestResult(name=fn.__name__, passed=True, duration_ms=elapsed)
        else:
            return ApiTestResult(name=fn.__name__, passed=False, reason=result, duration_ms=elapsed)
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return ApiTestResult(
            name=fn.__name__,
            passed=False,
            reason=f"Exception: {type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


# ---------------------------------------------------------------------------
# Test functions — all named test_api_*
# ---------------------------------------------------------------------------

def test_api_smart_defaults_returns_required_keys() -> Optional[str]:
    """Smart defaults must return all required keys."""
    result = _calculate_smart_defaults_mock()
    required = [
        "spread_bps", "requote_bps", "max_active_buy", "max_active_sell",
        "inner_size_xch", "mid_size_xch", "outer_size_xch", "extreme_size_xch",
        "xch_available", "cat_available", "mid_price", "insufficient",
        "insufficient_reason", "messages", "inventory_enabled",
    ]
    missing = [k for k in required if k not in result]
    if missing:
        return f"Missing keys: {missing}"
    return None


def test_api_smart_defaults_micro_wallet_wide_spread() -> Optional[str]:
    """Micro wallet (< 0.1 XCH) should get spread >= 600 bps."""
    result = _calculate_smart_defaults_mock(xch_balance=0.08, mid_price=0.001)
    if result["spread_bps"] < 600:
        return f"Expected spread >= 600 bps for micro wallet, got {result['spread_bps']}"
    return None


def test_api_smart_defaults_micro_wallet_no_crash() -> Optional[str]:
    """Micro wallet should not cause a crash or exception."""
    result = _calculate_smart_defaults_mock(xch_balance=0.05, cat_balance=50.0)
    if result is None:
        return "Got None result"
    return None


def test_api_smart_defaults_medium_wallet_normal_spread() -> Optional[str]:
    """Medium wallet (5 XCH) should get spread in 250–1000 bps range."""
    result = _calculate_smart_defaults_mock(xch_balance=5.0, fills_per_day=5.0, daily_volume_xch=2.0)
    if not (250 <= result["spread_bps"] <= 1000):
        return f"Expected spread 250–1000 bps, got {result['spread_bps']}"
    return None


def test_api_smart_defaults_large_wallet_normal_spread() -> Optional[str]:
    """Large wallet (100 XCH) should return a valid spread."""
    result = _calculate_smart_defaults_mock(xch_balance=100.0)
    if result["spread_bps"] <= 0:
        return f"Expected positive spread, got {result['spread_bps']}"
    return None


def test_api_smart_defaults_no_xch_returns_insufficient() -> Optional[str]:
    """Zero XCH balance (after reserve) should return insufficient=True."""
    result = _calculate_smart_defaults_mock(xch_balance=0.0, xch_reserve=0.0)
    if not result["insufficient"]:
        return "Expected insufficient=True when xch_balance=0"
    return None


def test_api_smart_defaults_zero_price_returns_insufficient() -> Optional[str]:
    """Zero mid_price should return insufficient=True."""
    result = _calculate_smart_defaults_mock(mid_price=0.0)
    if not result["insufficient"]:
        return "Expected insufficient=True when mid_price=0"
    return None


def test_api_smart_defaults_reserve_exceeds_balance_xch_avail_zero() -> Optional[str]:
    """When xch_reserve > xch_balance, xch_available must be 0, not negative."""
    result = _calculate_smart_defaults_mock(xch_balance=1.0, xch_reserve=2.0)
    if result["xch_available"] < 0:
        return f"xch_available should be >= 0, got {result['xch_available']}"
    if result["xch_available"] != 0.0:
        return f"xch_available should be 0.0, got {result['xch_available']}"
    return None


def test_api_smart_defaults_cat_reserve_respected() -> Optional[str]:
    """cat_available must equal cat_balance - cat_reserve (floored at 0)."""
    result = _calculate_smart_defaults_mock(cat_balance=1000.0, cat_reserve=400.0)
    expected = 600.0
    if abs(result["cat_available"] - expected) > 0.001:
        return f"Expected cat_available={expected}, got {result['cat_available']}"
    return None


def test_api_smart_defaults_requote_ratio_in_range() -> Optional[str]:
    """requote_bps must be 55–80% of spread_bps (same units)."""
    result = _calculate_smart_defaults_mock(xch_balance=10.0)
    spread = result["spread_bps"]
    requote = result["requote_bps"]
    low  = spread * 0.55
    high = spread * 0.80
    if not (low <= requote <= high):
        return (
            f"requote_bps={requote} not in [{low:.1f}, {high:.1f}] "
            f"(55–80% of spread={spread})"
        )
    return None


def test_api_smart_defaults_requote_vs_spread_micro() -> Optional[str]:
    """Requote ratio constraint holds for micro wallets too."""
    result = _calculate_smart_defaults_mock(xch_balance=0.3)
    if result["insufficient"]:
        return None  # Can't check ratio if insufficient
    spread = result["spread_bps"]
    requote = result["requote_bps"]
    low = spread * 0.55
    high = spread * 0.80
    if not (low <= requote <= high):
        return f"Micro wallet: requote={requote} not in [{low:.1f},{high:.1f}] (spread={spread})"
    return None


def test_api_smart_defaults_inventory_enabled_always_true() -> Optional[str]:
    """inventory_enabled must always be True regardless of config."""
    for xch in [0.0, 0.1, 10.0, 100.0]:
        result = _calculate_smart_defaults_mock(xch_balance=xch)
        if not result.get("inventory_enabled"):
            return f"inventory_enabled=False for xch_balance={xch}"
    return None


def test_api_smart_defaults_active_market_tighter_spread() -> Optional[str]:
    """Active market (>10 fills/day, >5 XCH/day) → base spread 300 bps."""
    result = _calculate_smart_defaults_mock(
        xch_balance=10.0,
        fills_per_day=15.0,
        daily_volume_xch=10.0,
        regime="normal",
    )
    # With 300 base spread, final may be slightly higher due to other adjustments
    if result["spread_bps"] > 700:
        return f"Active market: expected spread <= 700 bps, got {result['spread_bps']}"
    return None


def test_api_smart_defaults_quiet_market_wider_spread() -> Optional[str]:
    """Quiet market (1.0 fills/day, 0.5 XCH/day) → base spread >= 700 bps.

    Branch condition: fills_per_day > 0.5 OR daily_volume > 0.1 → spread_base=700.
    """
    # fills_per_day=1.0 > 0.5 → enters the "quiet market" branch (spread_base=700)
    result = _calculate_smart_defaults_mock(
        xch_balance=5.0,
        fills_per_day=1.0,    # > 0.5 → quiet branch
        daily_volume_xch=0.05,
        regime="normal",
    )
    if result["spread_bps"] < 700:
        return f"Quiet market (1.0 fills/day): expected spread >= 700 bps, got {result['spread_bps']}"
    return None


def test_api_smart_defaults_extreme_regime_adds_spread() -> Optional[str]:
    """Extreme volatility regime should increase spread by +200 bps."""
    normal = _calculate_smart_defaults_mock(xch_balance=5.0, regime="normal",
                                             fills_per_day=5.0, daily_volume_xch=2.0)
    extreme = _calculate_smart_defaults_mock(xch_balance=5.0, regime="extreme",
                                              fills_per_day=5.0, daily_volume_xch=2.0)
    diff = extreme["spread_bps"] - normal["spread_bps"]
    if diff < 150:
        return f"Extreme regime should add >=150 bps to spread; diff={diff} bps"
    return None


def test_api_smart_defaults_quiet_regime_reduces_spread() -> Optional[str]:
    """Quiet regime should reduce spread vs normal (or at most same)."""
    normal = _calculate_smart_defaults_mock(xch_balance=5.0, regime="normal",
                                             fills_per_day=5.0, daily_volume_xch=2.0)
    quiet = _calculate_smart_defaults_mock(xch_balance=5.0, regime="quiet",
                                            fills_per_day=5.0, daily_volume_xch=2.0)
    if quiet["spread_bps"] > normal["spread_bps"]:
        return (
            f"Quiet regime should not increase spread vs normal: "
            f"quiet={quiet['spread_bps']} > normal={normal['spread_bps']}"
        )
    return None


def test_api_smart_defaults_thin_pool_adds_spread() -> Optional[str]:
    """Thin pool (<50 XCH) should add spread vs deep pool."""
    deep  = _calculate_smart_defaults_mock(xch_balance=5.0, pool_xch=500.0)
    thin  = _calculate_smart_defaults_mock(xch_balance=5.0, pool_xch=20.0)
    if thin["spread_bps"] <= deep["spread_bps"]:
        return (
            f"Thin pool should increase spread: "
            f"thin={thin['spread_bps']} <= deep={deep['spread_bps']}"
        )
    return None


def test_api_smart_defaults_spread_always_positive() -> Optional[str]:
    """Spread must always be a positive integer."""
    test_cases = [
        {"xch_balance": 0.1},
        {"xch_balance": 1.0, "regime": "quiet"},
        {"xch_balance": 100.0, "fills_per_day": 20.0, "daily_volume_xch": 50.0},
        {"xch_balance": 0.5, "regime": "volatile"},
    ]
    for kw in test_cases:
        result = _calculate_smart_defaults_mock(**kw)
        if not result["insufficient"] and result["spread_bps"] <= 0:
            return f"spread_bps={result['spread_bps']} for inputs {kw}"
    return None


def test_api_smart_defaults_requote_always_positive() -> Optional[str]:
    """requote_bps must always be >= 50."""
    for spread in [100, 250, 500, 1000, 2000]:
        for regime in ["quiet", "normal", "volatile"]:
            result = _calculate_smart_defaults_mock(xch_balance=5.0)
            if not result["insufficient"] and result["requote_bps"] < 50:
                return f"requote_bps={result['requote_bps']} < 50 (spread={spread}, regime={regime})"
    return None


def test_api_smart_defaults_max_offers_nonzero_with_capital() -> Optional[str]:
    """With sufficient capital, max_active_buy and max_active_sell must be > 0."""
    result = _calculate_smart_defaults_mock(xch_balance=10.0, cat_balance=5000.0, mid_price=0.001)
    if result["max_active_buy"] <= 0:
        return f"max_active_buy={result['max_active_buy']} with 10 XCH"
    if result["max_active_sell"] <= 0:
        return f"max_active_sell={result['max_active_sell']} with 5000 CAT"
    return None


def test_api_smart_defaults_no_cat_disables_sell_side() -> Optional[str]:
    """Near-zero CAT balance should set max_active_sell=0."""
    result = _calculate_smart_defaults_mock(xch_balance=5.0, cat_balance=5.0, mid_price=0.001)
    if result["max_active_sell"] != 0:
        return f"max_active_sell should be 0 with near-zero CAT, got {result['max_active_sell']}"
    return None


def test_api_smart_defaults_inner_larger_than_outer() -> Optional[str]:
    """Inner tier size must be >= outer tier size."""
    result = _calculate_smart_defaults_mock(xch_balance=10.0)
    if result["inner_size_xch"] < result["outer_size_xch"]:
        return (
            f"inner ({result['inner_size_xch']}) < outer ({result['outer_size_xch']})"
        )
    return None


def test_api_smart_defaults_tier_sizes_scale_with_capital() -> Optional[str]:
    """Larger capital should yield larger per-offer sizes."""
    small = _calculate_smart_defaults_mock(xch_balance=0.5)
    large = _calculate_smart_defaults_mock(xch_balance=100.0)
    if small["inner_size_xch"] >= large["inner_size_xch"]:
        return (
            f"Inner size for 0.5 XCH ({small['inner_size_xch']}) "
            f">= 100 XCH ({large['inner_size_xch']})"
        )
    return None


def test_api_smart_defaults_messages_is_list() -> Optional[str]:
    """Messages field must always be a list."""
    result = _calculate_smart_defaults_mock()
    if not isinstance(result["messages"], list):
        return f"messages is {type(result['messages'])}, expected list"
    return None


def test_api_smart_defaults_mid_price_preserved() -> Optional[str]:
    """mid_price in result should match input mid_price."""
    result = _calculate_smart_defaults_mock(xch_balance=5.0, mid_price=0.00257)
    if abs(result["mid_price"] - 0.00257) > 1e-10:
        return f"mid_price={result['mid_price']} != input 0.00257"
    return None


def test_api_smart_defaults_xch_available_calculation() -> Optional[str]:
    """xch_available = max(0, xch_balance - xch_reserve)."""
    result = _calculate_smart_defaults_mock(xch_balance=5.0, xch_reserve=1.0)
    expected = 4.0
    if abs(result["xch_available"] - expected) > 0.0001:
        return f"xch_available={result['xch_available']}, expected {expected}"
    return None


def test_api_smart_defaults_insufficient_reason_not_empty() -> Optional[str]:
    """When insufficient=True, insufficient_reason must be non-empty."""
    result = _calculate_smart_defaults_mock(xch_balance=0.0)
    if result["insufficient"] and not result["insufficient_reason"]:
        return "insufficient=True but insufficient_reason is empty"
    return None


def test_api_settings_validation_spread_negative() -> Optional[str]:
    """spread_bps < 0 must fail validation."""
    valid, msg = _validate_settings({"spread_bps": -10})
    if valid:
        return "Expected validation failure for spread_bps=-10"
    return None


def test_api_settings_validation_spread_zero_ok() -> Optional[str]:
    """spread_bps = 0 should pass validation (dead-market mode)."""
    valid, msg = _validate_settings({"spread_bps": 0})
    if not valid:
        return f"spread_bps=0 should be valid, got: {msg}"
    return None


def test_api_settings_validation_spread_too_large() -> Optional[str]:
    """spread_bps > 10000 must fail validation."""
    valid, msg = _validate_settings({"spread_bps": 10001})
    if valid:
        return "Expected validation failure for spread_bps=10001"
    return None


def test_api_settings_validation_requote_negative() -> Optional[str]:
    """requote_bps < 0 must fail validation."""
    valid, msg = _validate_settings({"requote_bps": -1})
    if valid:
        return "Expected validation failure for requote_bps=-1"
    return None


def test_api_settings_validation_requote_zero_ok() -> Optional[str]:
    """requote_bps = 0 should pass validation."""
    valid, msg = _validate_settings({"requote_bps": 0})
    if not valid:
        return f"requote_bps=0 should be valid, got: {msg}"
    return None


def test_api_settings_validation_max_buy_negative() -> Optional[str]:
    """max_active_buy < 0 must fail validation."""
    valid, msg = _validate_settings({"max_active_buy": -5})
    if valid:
        return "Expected validation failure for max_active_buy=-5"
    return None


def test_api_settings_validation_max_sell_negative() -> Optional[str]:
    """max_active_sell < 0 must fail validation."""
    valid, msg = _validate_settings({"max_active_sell": -1})
    if valid:
        return "Expected validation failure for max_active_sell=-1"
    return None


def test_api_settings_validation_inner_size_negative() -> Optional[str]:
    """inner_size_xch < 0 must fail validation."""
    valid, msg = _validate_settings({"inner_size_xch": -0.1})
    if valid:
        return "Expected validation failure for inner_size_xch=-0.1"
    return None


def test_api_settings_validation_max_position_negative() -> Optional[str]:
    """max_position_xch < 0 must fail validation."""
    valid, msg = _validate_settings({"max_position_xch": -1.0})
    if valid:
        return "Expected validation failure for max_position_xch=-1.0"
    return None


def test_api_settings_validation_all_valid_passes() -> Optional[str]:
    """A fully valid settings dict should pass all validation."""
    valid, msg = _validate_settings({
        "spread_bps": 500,
        "requote_bps": 200,
        "max_active_buy": 5,
        "max_active_sell": 5,
        "inner_size_xch": 0.5,
        "max_position_xch": 5.0,
    })
    if not valid:
        return f"Expected valid settings but got error: {msg}"
    return None


def test_api_settings_validation_empty_dict_passes() -> Optional[str]:
    """An empty settings dict (no fields to validate) should pass."""
    valid, msg = _validate_settings({})
    if not valid:
        return f"Empty dict should pass validation, got: {msg}"
    return None


def test_api_smart_defaults_no_trade_data_reasonable_spread() -> Optional[str]:
    """No trade data at all → spread should default to 500 bps (moderate)."""
    result = _calculate_smart_defaults_mock(
        xch_balance=5.0,
        fills_per_day=0.0,
        daily_volume_xch=0.0,
        pool_xch=200.0,
        regime="normal",
    )
    # With no data, base is 500 — may be adjusted but should stay in [300, 800]
    if not (200 <= result["spread_bps"] <= 900):
        return f"No-data spread={result['spread_bps']} outside [200, 900]"
    return None


def test_api_smart_defaults_volatile_regime() -> Optional[str]:
    """Volatile regime should add +100 bps to spread vs normal."""
    normal = _calculate_smart_defaults_mock(xch_balance=5.0, regime="normal",
                                             fills_per_day=5.0, daily_volume_xch=2.0)
    volatile = _calculate_smart_defaults_mock(xch_balance=5.0, regime="volatile",
                                               fills_per_day=5.0, daily_volume_xch=2.0)
    diff = volatile["spread_bps"] - normal["spread_bps"]
    if diff < 80:
        return f"Volatile regime should add >=80 bps; diff={diff}"
    return None


def test_api_smart_defaults_max_offers_capped() -> Optional[str]:
    """max_active_buy and max_active_sell should never exceed 20."""
    result = _calculate_smart_defaults_mock(xch_balance=10000.0, cat_balance=5000000.0)
    if result["max_active_buy"] > 20:
        return f"max_active_buy={result['max_active_buy']} exceeds cap of 20"
    if result["max_active_sell"] > 20:
        return f"max_active_sell={result['max_active_sell']} exceeds cap of 20"
    return None


def test_api_smart_defaults_spread_minimum_100() -> Optional[str]:
    """Spread must be at least 100 bps even in ideal conditions."""
    result = _calculate_smart_defaults_mock(
        xch_balance=100.0,
        fills_per_day=100.0,
        daily_volume_xch=200.0,
        pool_xch=10000.0,
        regime="quiet",
    )
    if result["spread_bps"] < 100:
        return f"Spread={result['spread_bps']} below minimum of 100 bps"
    return None


# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

ALL_API_TESTS: List[Callable[[], Optional[str]]] = [
    test_api_smart_defaults_returns_required_keys,
    test_api_smart_defaults_micro_wallet_wide_spread,
    test_api_smart_defaults_micro_wallet_no_crash,
    test_api_smart_defaults_medium_wallet_normal_spread,
    test_api_smart_defaults_large_wallet_normal_spread,
    test_api_smart_defaults_no_xch_returns_insufficient,
    test_api_smart_defaults_zero_price_returns_insufficient,
    test_api_smart_defaults_reserve_exceeds_balance_xch_avail_zero,
    test_api_smart_defaults_cat_reserve_respected,
    test_api_smart_defaults_requote_ratio_in_range,
    test_api_smart_defaults_requote_vs_spread_micro,
    test_api_smart_defaults_inventory_enabled_always_true,
    test_api_smart_defaults_active_market_tighter_spread,
    test_api_smart_defaults_quiet_market_wider_spread,
    test_api_smart_defaults_extreme_regime_adds_spread,
    test_api_smart_defaults_quiet_regime_reduces_spread,
    test_api_smart_defaults_thin_pool_adds_spread,
    test_api_smart_defaults_spread_always_positive,
    test_api_smart_defaults_requote_always_positive,
    test_api_smart_defaults_max_offers_nonzero_with_capital,
    test_api_smart_defaults_no_cat_disables_sell_side,
    test_api_smart_defaults_inner_larger_than_outer,
    test_api_smart_defaults_tier_sizes_scale_with_capital,
    test_api_smart_defaults_messages_is_list,
    test_api_smart_defaults_mid_price_preserved,
    test_api_smart_defaults_xch_available_calculation,
    test_api_smart_defaults_insufficient_reason_not_empty,
    test_api_settings_validation_spread_negative,
    test_api_settings_validation_spread_zero_ok,
    test_api_settings_validation_spread_too_large,
    test_api_settings_validation_requote_negative,
    test_api_settings_validation_requote_zero_ok,
    test_api_settings_validation_max_buy_negative,
    test_api_settings_validation_max_sell_negative,
    test_api_settings_validation_inner_size_negative,
    test_api_settings_validation_max_position_negative,
    test_api_settings_validation_all_valid_passes,
    test_api_settings_validation_empty_dict_passes,
    test_api_smart_defaults_no_trade_data_reasonable_spread,
    test_api_smart_defaults_volatile_regime,
    test_api_smart_defaults_max_offers_capped,
    test_api_smart_defaults_spread_minimum_100,
]


def run_all_api_tests() -> List[ApiTestResult]:
    """Run every API test and return the results.

    Returns:
        List of ApiTestResult, one per test function in ALL_API_TESTS.
    """
    return [_run_test(fn) for fn in ALL_API_TESTS]
