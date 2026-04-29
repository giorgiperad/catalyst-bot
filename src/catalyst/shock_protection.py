"""TibetSwap price-shock protection policy.

The trading loop handles wallet orchestration; this module only decides when a
confirmed Tibet reserve move is large enough to clear stale offers, which tiers
are exposed, and which side is vulnerable.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Tuple


@dataclass(frozen=True)
class TibetShockAction:
    cancel: bool
    trigger_pct: Decimal
    trigger_source: str
    tiers: Tuple[str, ...]
    sides: Tuple[str, ...]


def _decimal_attr(cfg, name: str, default: str) -> Decimal:
    try:
        raw = getattr(cfg, name, default)
        if raw is None or raw == "":
            raw = default
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def tibet_shock_trigger_pct(cfg) -> Decimal:
    """Return the percent move that triggers defensive cancel.

    ``TIBET_SHOCK_CANCEL_TRIGGER_PCT`` is an explicit operator override.
    A value of 0 keeps the older auto mode: half of the inner edge, with a
    0.50% floor so very tight books still react to meaningful AMM moves.
    """
    manual = _decimal_attr(cfg, "TIBET_SHOCK_CANCEL_TRIGGER_PCT", "0")
    if manual > 0:
        return manual

    min_edge_bps = _decimal_attr(cfg, "MIN_EDGE_BPS", "100")
    return max(Decimal("0.50"), min_edge_bps / Decimal("200"))


def _trigger_source(cfg) -> str:
    manual = _decimal_attr(cfg, "TIBET_SHOCK_CANCEL_TRIGGER_PCT", "0")
    return "configured" if manual > 0 else "auto_min_edge"


def tibet_shock_tiers(magnitude_pct: Decimal, cfg) -> Tuple[str, ...]:
    mid_pct = _decimal_attr(cfg, "TIBET_SHOCK_CANCEL_MID_PCT", "5")
    outer_pct = _decimal_attr(cfg, "TIBET_SHOCK_CANCEL_OUTER_PCT", "10")
    if mid_pct <= 0:
        mid_pct = Decimal("5")
    if outer_pct <= 0:
        outer_pct = Decimal("10")
    if outer_pct < mid_pct:
        outer_pct = mid_pct

    if magnitude_pct >= outer_pct:
        return ("inner", "mid", "outer")
    if magnitude_pct >= mid_pct:
        return ("inner", "mid")
    return ("inner",)


def tibet_shock_sides(direction: str) -> Tuple[str, ...]:
    norm = str(direction or "").strip().lower()
    if norm == "up":
        return ("sell",)
    if norm == "down":
        return ("buy",)
    return ("buy", "sell")


def evaluate_tibet_shock(magnitude_pct, direction: str, cfg) -> TibetShockAction:
    try:
        pct = abs(Decimal(str(magnitude_pct or "0")))
    except (InvalidOperation, ValueError, TypeError):
        pct = Decimal("0")

    trigger = tibet_shock_trigger_pct(cfg)
    return TibetShockAction(
        cancel=pct >= trigger,
        trigger_pct=trigger,
        trigger_source=_trigger_source(cfg),
        tiers=tibet_shock_tiers(pct, cfg),
        sides=tibet_shock_sides(direction),
    )
