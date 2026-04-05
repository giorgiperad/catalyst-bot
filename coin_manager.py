"""
V2 Coin Manager — Intelligent Coin Health Monitoring & Preparation

Monitors spendable coin counts, classifies coins by role, triggers
smart coin splitting/consolidation, and manages the coin_prep_worker.

=== Coin Classification ===
Every spendable coin is classified into one of four roles:

  RESERVE  — Large coins (≥ 2× trading size). Left by coin prep for
             future topups. Can be split into trading coins on demand.
  TRADING  — Right-sized coins (0.5× to 1.5× trading size). Used for
             creating offers. This is the target state.
  SMALL    — Under-sized coins (< 0.5× trading size). Typically from
             partial fills. Need consolidating into usable coins.
  LOCKED   — Coins currently in active offers. Can't be touched.

=== Smart Topup Strategy ===
When free trading coins are low, the topup runs this decision tree:

  1. If RESERVE coins exist → split the largest into trading coins
  2. If enough SMALL coins exist to consolidate → consolidate to self,
     wait for confirmation, then split the consolidated coin
  3. If nothing available → back off 2 hours (fills may bring new coins)

=== Detection Triggers ===
  - needs_coin_prep(): TOTAL coins < 10% of target → full prep needed
  - needs_topup(): FREE coins < 30% of max offers → smart topup
  - check_runtime_health(): every 5 loops, independent check

Key principles:
- Always use RPC, never CLI parsing
- Poll-based confirmation (no fixed timeouts)
- Only one wallet operation at a time (serialisation)
- Backoff resets on fills (new coins available)
- Cooldown resets to 0 after successful topup
"""

import time
import threading
import traceback
import subprocess
import json
import os
import hashlib
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from config import cfg
from database import log_event
from tx_fees import (
    fee_pool_enabled,
    get_effective_transaction_fee_mojos,
    get_fee_coin_size_mojos,
    get_fee_coin_size_xch,
    get_fee_pool_count,
    get_fee_tier_name,
)
from wallet import (
    get_exact_spendable_coins_rpc,
    get_all_coins_for_wallet,
    get_wallet_balance, get_next_address, send_transaction,
    split_coins_rpc,
    get_wallet_type,
    WALLET_ID_XCH,
    get_owned_coins,
    get_owned_coins_detailed,
)
from win_subprocess import hidden_subprocess_kwargs


# Cooldowns
_TOPUP_COOLDOWN = 600            # 10 minutes between topups (normal)
_TOPUP_BACKOFF_BASE = 300        # 5 minutes — first retry when nothing available
_TOPUP_BACKOFF_MAX = 3600        # 60 minutes — ceiling for exponential backoff
# Old fixed 2-hour constant removed. Backoff is now exponential:
# attempt 0 → 5 min, 1 → 10 min, 2 → 20 min, 3 → 40 min, 4+ → 60 min (capped)


class _TopupWalletDegraded(Exception):
    """Raised when wallet RPC becomes too degraded to continue topup safely."""


# -----------------------------------------------------------------------
# Coin record helpers
# -----------------------------------------------------------------------

def _extract_coin_records(rpc_result) -> list:
    """Extract coin records from an RPC get_spendable_coins response.

    Handles both Chia and Sage wallet response formats.
    Detects RPC errors (connection failures, auth errors) and logs them
    rather than silently returning empty lists.
    """
    if not rpc_result or not isinstance(rpc_result, dict):
        return []

    # Check for RPC error responses (Sage returns these as dicts with 'error' key)
    if rpc_result.get("error") or rpc_result.get("success") is False:
        err = rpc_result.get("error", "unknown")
        log_event("warning", "rpc_error_in_coins",
                  f"Wallet RPC returned error instead of coins: {str(err)[:200]}")
        return []

    return rpc_result.get("confirmed_records") or rpc_result.get("records") or []


def _get_free_coins_rpc(wallet_id: int):
    """Get the exact currently free/selectable wallet coins.

    For Sage this bypasses the older owned+selectable merge workaround and
    returns the strict selectable view. For Chia the adapter aliases this to
    the normal spendable RPC, so the call stays backend-safe.
    """
    return get_exact_spendable_coins_rpc(wallet_id)


def _coin_amount(record: dict) -> int:
    """Get mojos amount from a coin record."""
    coin = record.get("coin", {})
    return coin.get("amount", 0)


def _chia_int_to_bytes(v: int) -> bytes:
    """Convert int to bytes using Chia's encoding (variable-length, signed).

    This matches chia.util.ints.int_to_bytes() exactly:
      byte_count = (v.bit_length() + 8) >> 3
      v.to_bytes(byte_count, "big", signed=True)

    Critical: Chia does NOT use fixed 8-byte encoding for coin IDs.
    Using fixed 8 bytes produces WRONG hashes for most amounts.
    """
    if v == 0:
        return b""
    byte_count = (v.bit_length() + 8) >> 3
    return v.to_bytes(byte_count, "big", signed=True)


def _coin_id_from_record(record: dict) -> str:
    """Get coin ID from a coin record.

    Strategy (in order of preference):
      1. Use a pre-computed ID field (Chia uses 'name', Sage uses 'coin_id')
      2. Compute SHA256(parent + puzzle_hash + int_to_bytes(amount))
         using Chia's variable-length int encoding
    """
    coin = record.get("coin", {})

    # ---- Strategy 1: Use wallet-provided ID ----
    # Chia wallet uses 'name', Sage wallet uses 'coin_id' at record level
    name = (coin.get("name", "")
            or record.get("name", "")
            or record.get("coin_id", "")
            or coin.get("coin_id", ""))
    if name:
        # Always normalize: lowercase + 0x prefix.
        # Sage wallet may return mixed-case hex; reconcile_coins_with_wallet
        # uses norm_coin_id() (lowercase). Without normalizing here, the
        # same physical coin gets two DB rows — one from upsert_coin (mixed
        # case, status='free') and one from reconcile (lowercase, status=
        # 'locked'). The free row then "wins" in queries.
        name = name.strip().lower()
        if not name.startswith("0x"):
            name = "0x" + name
        return name

    # ---- Strategy 2: Compute from fields ----
    parent = coin.get("parent_coin_info", "")
    puzzle = coin.get("puzzle_hash", "")
    amount = coin.get("amount", 0)
    if not parent or not puzzle:
        return ""
    try:
        p_bytes = bytes.fromhex(parent.replace("0x", ""))
        z_bytes = bytes.fromhex(puzzle.replace("0x", ""))
        a_bytes = _chia_int_to_bytes(amount)
        return "0x" + hashlib.sha256(p_bytes + z_bytes + a_bytes).hexdigest()
    except Exception:
        return ""


def _classify_coins(records: list, trading_size_mojos: int) -> Dict[str, list]:
    """Classify coin records into reserve / trading / small.

    Thresholds (relative to trading_size_mojos):
      RESERVE:  amount >= 2.0 × trading_size
      TRADING:  0.5 × trading_size <= amount < 2.0 × trading_size
      SMALL:    amount < 0.5 × trading_size
    """
    reserve = []
    trading = []
    small = []

    threshold_reserve = int(trading_size_mojos * 2.0)
    threshold_small = int(trading_size_mojos * 0.5)

    for rec in records:
        amt = _coin_amount(rec)
        if amt >= threshold_reserve:
            reserve.append(rec)
        elif amt >= threshold_small:
            trading.append(rec)
        else:
            small.append(rec)

    # Sort reserve by size descending (biggest first — best to split)
    reserve.sort(key=_coin_amount, reverse=True)
    # Sort small by size descending (for consolidation summary)
    small.sort(key=_coin_amount, reverse=True)

    return {"reserve": reserve, "trading": trading, "small": small}


def _classify_coins_tiered(records: list, tier_sizes_mojos: Dict[str, int]) -> Dict[str, list]:
    """Classify coins into tier-specific buckets when TIER_ENABLED.

    LEGACY fallback — used by non-designation-aware code paths.
    The main path now uses CoinManager._classify_coins_by_designation().

    Each coin is matched to the nearest tier within ±20% tolerance.
    Coins too large for any tier go to 'reserve'.
    Coins too small for any tier go to 'small'.

    Args:
        records: List of coin records from RPC
        tier_sizes_mojos: {"inner": mojos, "mid": mojos, "outer": mojos, "extreme": mojos}

    Returns dict with keys: reserve, inner, mid, outer, extreme, small
    """
    result = {"reserve": [], "inner": [], "mid": [], "outer": [], "extreme": [], "small": []}
    if "sniper" in tier_sizes_mojos:
        result["sniper"] = []
    if "fees" in tier_sizes_mojos:
        result["fees"] = []

    # Sort tier sizes descending for classification
    tiers_sorted = sorted(tier_sizes_mojos.items(), key=lambda x: x[1], reverse=True)
    largest_tier_mojos = tiers_sorted[0][1] if tiers_sorted else 0
    smallest_tier_mojos = tiers_sorted[-1][1] if tiers_sorted else 0

    # Reserve threshold: 2× the largest tier size
    reserve_threshold = int(largest_tier_mojos * 2.0)
    # Small threshold: 0.5× the smallest tier size
    small_threshold = int(smallest_tier_mojos * 0.5)

    for rec in records:
        amt = _coin_amount(rec)

        if amt >= reserve_threshold:
            result["reserve"].append(rec)
            continue

        if amt < small_threshold:
            result["small"].append(rec)
            continue

        # Match to nearest tier within ±20% tolerance
        best_tier = None
        best_diff = float("inf")
        for tier_name, tier_mojos in tiers_sorted:
            low = int(tier_mojos * 0.8)
            high = int(tier_mojos * 1.2)
            if low <= amt <= high:
                diff = abs(amt - tier_mojos)
                if diff < best_diff:
                    best_tier = tier_name
                    best_diff = diff

        if best_tier:
            result[best_tier].append(rec)
        else:
            # Doesn't match any tier — assign to nearest tier anyway
            nearest = None
            nearest_diff = float("inf")
            for tier_name, tier_mojos in tiers_sorted:
                diff = abs(amt - tier_mojos)
                if diff < nearest_diff:
                    nearest = tier_name
                    nearest_diff = diff
            if nearest:
                result[nearest].append(rec)
            else:
                result["small"].append(rec)

    # Sort reserve by size descending
    result["reserve"].sort(key=_coin_amount, reverse=True)
    result["small"].sort(key=_coin_amount, reverse=True)

    return result


def _infer_designation_by_size(amt: int, tier_sizes_mojos: Dict[str, int]) -> Tuple[str, str]:
    """Infer a coin's designation from its amount (for NEW/UNKNOWN coins only).

    Used when a coin has no designation yet. Once designated, this is NOT
    called again — the DB designation is authoritative.

    Returns: (designation, assigned_tier)
    """
    if not tier_sizes_mojos:
        return ('unknown', 'none')

    tiers_sorted = sorted(tier_sizes_mojos.items(), key=lambda x: x[1], reverse=True)
    largest_tier_mojos = tiers_sorted[0][1] if tiers_sorted else 0
    smallest_tier_mojos = tiers_sorted[-1][1] if tiers_sorted else 0

    # Dust threshold: less than 50% of smallest tier
    dust_threshold = int(smallest_tier_mojos * 0.5)
    if amt < dust_threshold:
        return ('dust', 'none')

    # Check if it matches a tier size (±20%)
    for tier_name, tier_mojos in tiers_sorted:
        low = int(tier_mojos * 0.8)
        high = int(tier_mojos * 1.2)
        if low <= amt <= high:
            return ('tier_spare', tier_name)

    # Larger than any tier but doesn't match — could be reserve material
    if amt > int(largest_tier_mojos * 1.2):
        return ('reserve', 'none')

    # Doesn't match any tier exactly — assign to nearest tier as spare
    nearest = None
    nearest_diff = float("inf")
    for tier_name, tier_mojos in tiers_sorted:
        diff = abs(amt - tier_mojos)
        if diff < nearest_diff:
            nearest = tier_name
            nearest_diff = diff
    if nearest:
        return ('tier_spare', nearest)

    return ('unknown', 'none')


def get_tier_distribution(
    max_offers_per_side: int,
    tier_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Calculate how many offers fall in each tier for one side.

    If explicit tier counts are configured, they define the ladder template
    from the inside out. Any remaining slots fall into the extreme tier, and
    smaller ladders simply truncate the outer tiers first.

    Otherwise this falls back to the legacy ratio-based split:
      ratio < 0.1  → inner
      ratio < 0.4  → mid
      ratio < 0.7  → outer
      ratio >= 0.7 → extreme

    Returns {"inner": count, "mid": count, "outer": count, "extreme": count}
    """
    dist = {"inner": 0, "mid": 0, "outer": 0, "extreme": 0}
    if max_offers_per_side <= 0:
        return dist

    configured = tier_counts or {
        "inner": int(getattr(cfg, "INNER_TIER_COUNT", 0) or 0),
        "mid": int(getattr(cfg, "MID_TIER_COUNT", 0) or 0),
        "outer": int(getattr(cfg, "OUTER_TIER_COUNT", 0) or 0),
        "extreme": int(getattr(cfg, "EXTREME_TIER_COUNT", 0) or 0),
    }
    configured = {
        tier: max(0, int(configured.get(tier, 0) or 0))
        for tier in ("inner", "mid", "outer", "extreme")
    }

    if any(configured.values()):
        remaining = max_offers_per_side
        for tier in ("inner", "mid", "outer", "extreme"):
            take = min(configured[tier], remaining)
            dist[tier] = take
            remaining -= take
        if remaining > 0:
            dist["extreme"] += remaining
        return dist

    for slot in range(max_offers_per_side):
        ratio = slot / max_offers_per_side
        if ratio < 0.1:
            dist["inner"] += 1
        elif ratio < 0.4:
            dist["mid"] += 1
        elif ratio < 0.7:
            dist["outer"] += 1
        else:
            dist["extreme"] += 1

    return dist


def get_tier_spare_distribution(
    spare_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Return explicit spare counts per tier, if configured.

    A value of 0 means "no explicit override" for that tier. When every tier is
    zero, callers should fall back to the recommended weighted spare logic.
    """
    configured = (
        spare_counts
        if spare_counts is not None
        else {
            "inner": int(getattr(cfg, "INNER_TIER_SPARE_COUNT", 0) or 0),
            "mid": int(getattr(cfg, "MID_TIER_SPARE_COUNT", 0) or 0),
            "outer": int(getattr(cfg, "OUTER_TIER_SPARE_COUNT", 0) or 0),
            "extreme": int(getattr(cfg, "EXTREME_TIER_SPARE_COUNT", 0) or 0),
        }
    )
    return {
        tier: max(0, int(configured.get(tier, 0) or 0))
        for tier in ("inner", "mid", "outer", "extreme")
    }


def _clamp_coin_prep_multiplier(multiplier_raw) -> float:
    """Clamp the user coin-prep multiplier to the supported range.

    Floor is 1.0 — below this the spare allocation rounds to zero for some
    tiers, leaving no buffer at all.  Smart Defaults also enforces 1.0 as its
    minimum.  Ceiling is 3.0 (prep time beyond this exceeds practical benefit).
    """
    try:
        multiplier = float(multiplier_raw)
    except Exception:
        multiplier = 1.0
    return max(1.0, min(3.0, multiplier))


def _get_tier_size_weights(
    tier_sizes_xch: Optional[Dict[str, Decimal]] = None,
) -> Dict[str, float]:
    """Return relative spare-weighting per tier based on fill frequency.

    Sell side (normal): larger offers sit closer to mid price and fill most
    often, so inner > mid > outer > extreme weighting is correct.

    Buy side with BUY_LADDER_REVERSED: the tier *positions* are flipped —
    inner position uses extreme-sized offers (smallest, closest to mid, fills
    most), extreme position uses inner-sized offers (largest, furthest, rarely
    fills). So buy-side fill frequency is the inverse: extreme > outer > mid >
    inner weighting.

    Since both sides run simultaneously, the combined spare weight is the
    average of sell-side and buy-side weights.  Without reversal, both sides
    are identical so the average equals the normal sell-side weighting.
    """
    sizes = tier_sizes_xch or {
        "inner": getattr(cfg, "INNER_SIZE_XCH", Decimal("0")),
        "mid": getattr(cfg, "MID_SIZE_XCH", Decimal("0")),
        "outer": getattr(cfg, "OUTER_SIZE_XCH", Decimal("0")),
        "extreme": getattr(cfg, "EXTREME_SIZE_XCH", Decimal("0")),
    }
    normalized = {}
    for tier_name in ("inner", "mid", "outer", "extreme"):
        try:
            normalized[tier_name] = max(Decimal("0"), Decimal(str(sizes.get(tier_name, 0) or 0)))
        except Exception:
            normalized[tier_name] = Decimal("0")

    positive_sizes = [value for value in normalized.values() if value > 0]
    if normalized.get("mid", Decimal("0")) > 0:
        reference = normalized["mid"]
    elif positive_sizes:
        reference = max(positive_sizes)
    else:
        reference = Decimal("1")

    # Sell-side weights: proportional to offer size (inner = largest = highest weight)
    sell_weights: Dict[str, float] = {}
    for tier_name, size in normalized.items():
        if size <= 0 or reference <= 0:
            sell_weights[tier_name] = 0.0
        else:
            sell_weights[tier_name] = float(size / reference)

    buy_ladder_reversed = getattr(cfg, "BUY_LADDER_REVERSED", False)
    if not buy_ladder_reversed:
        return sell_weights

    # Buy-side weights with reversal: inner position fills most but uses the
    # extreme-sized coin — so extreme coins churn fastest on buys.
    # Flip inner↔extreme and mid↔outer to reflect reversed fill order.
    reversed_sizes = {
        "inner":   normalized.get("extreme", Decimal("0")),
        "mid":     normalized.get("outer",   Decimal("0")),
        "outer":   normalized.get("mid",     Decimal("0")),
        "extreme": normalized.get("inner",   Decimal("0")),
    }
    buy_weights: Dict[str, float] = {}
    for tier_name, size in reversed_sizes.items():
        if size <= 0 or reference <= 0:
            buy_weights[tier_name] = 0.0
        else:
            buy_weights[tier_name] = float(size / reference)

    # Average both sides — coins serve both sell and buy simultaneously
    weights: Dict[str, float] = {}
    for tier_name in ("inner", "mid", "outer", "extreme"):
        weights[tier_name] = (sell_weights.get(tier_name, 0.0) + buy_weights.get(tier_name, 0.0)) / 2.0
    return weights


def get_weighted_tier_prep_counts(
    max_offers_per_side: int,
    multiplier_raw,
    tier_counts: Optional[Dict[str, int]] = None,
    tier_sizes_xch: Optional[Dict[str, Decimal]] = None,
    spare_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Return prepared coin counts per tier for one asset wallet.

    Base active counts always follow the live ladder distribution. Any spare
    budget from the coin-prep multiplier is then redistributed toward larger
    live tiers, so inner/mid tiers keep more spare coins than outer/extreme.
    """
    dist = get_tier_distribution(max_offers_per_side, tier_counts=tier_counts)
    counts = {tier_name: int(count or 0) for tier_name, count in dist.items()}
    total_slots = sum(counts.values())
    if total_slots <= 0:
        return counts

    explicit_spares = get_tier_spare_distribution(spare_counts=spare_counts)
    if any(explicit_spares.values()):
        return {
            tier_name: counts.get(tier_name, 0) + explicit_spares.get(tier_name, 0)
            for tier_name in ("inner", "mid", "outer", "extreme")
        }

    multiplier = _clamp_coin_prep_multiplier(multiplier_raw)
    # 1.0 means one weighted spare layer across the live ladder.
    spare_budget = max(0, int(round(total_slots * multiplier)))
    if spare_budget <= 0:
        return counts

    tier_order = ("inner", "mid", "outer", "extreme")
    size_weights = _get_tier_size_weights(tier_sizes_xch=tier_sizes_xch)

    weighted_slots = {}
    total_weight = 0.0
    for tier_name in tier_order:
        slot_count = counts.get(tier_name, 0)
        if slot_count <= 0:
            continue
        tier_weight = max(0.0, float(size_weights.get(tier_name, 0.0) or 0.0))
        weight_points = float(slot_count) * (tier_weight if tier_weight > 0 else 1.0)
        weighted_slots[tier_name] = weight_points
        total_weight += weight_points

    if total_weight <= 0:
        return counts

    extras = {tier_name: 0 for tier_name in tier_order}
    remaining = spare_budget
    remainders = []
    for tier_name in tier_order:
        weight_points = weighted_slots.get(tier_name, 0.0)
        if weight_points <= 0:
            continue
        raw_extra = (spare_budget * weight_points) / total_weight
        whole_extra = int(raw_extra)
        extras[tier_name] = whole_extra
        remaining -= whole_extra
        remainders.append(
            {
                "tier": tier_name,
                "fraction": raw_extra - whole_extra,
                "weight": float(size_weights.get(tier_name, 0.0) or 0.0),
                "slots": counts.get(tier_name, 0),
            }
        )

    remainders.sort(
        key=lambda item: (
            -item["fraction"],
            -item["weight"],
            -item["slots"],
            tier_order.index(item["tier"]),
        )
    )
    for item in remainders[:remaining]:
        extras[item["tier"]] += 1

    return {
        tier_name: counts.get(tier_name, 0) + extras.get(tier_name, 0)
        for tier_name in tier_order
    }


def get_recommended_tier_spare_counts(
    max_offers_per_side: int,
    multiplier_raw,
    tier_counts: Optional[Dict[str, int]] = None,
    tier_sizes_xch: Optional[Dict[str, Decimal]] = None,
) -> Dict[str, int]:
    """Return only the spare portion of the prepared tier counts."""
    dist = get_tier_distribution(max_offers_per_side, tier_counts=tier_counts)
    prepared = get_weighted_tier_prep_counts(
        max_offers_per_side,
        multiplier_raw,
        tier_counts=tier_counts,
        tier_sizes_xch=tier_sizes_xch,
        spare_counts={},
    )
    return {
        tier_name: max(0, int(prepared.get(tier_name, 0) or 0) - int(dist.get(tier_name, 0) or 0))
        for tier_name in ("inner", "mid", "outer", "extreme")
    }


def get_tier_coin_requirements(max_offers_per_side: int) -> Dict[str, int]:
    """Calculate prepared coin counts per tier for one asset wallet."""
    return get_weighted_tier_prep_counts(
        max_offers_per_side,
        getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0")),
    )


def _format_amount_xch(mojos: int) -> str:
    """Format mojos as human-readable XCH amount."""
    return f"{Decimal(mojos) / Decimal('1000000000000'):.4f}"


def _format_amount_cat(mojos: int, decimals: int) -> str:
    """Format CAT mojos as human-readable token amount."""
    scale = Decimal(10 ** decimals)
    return f"{Decimal(mojos) / scale:.2f}"


class CoinManager:
    """Manages coin health and preparation for offer creation.

    Maintains a running coin inventory, classifying every spendable coin
    by its role (reserve/trading/small). Uses this to make smart decisions
    about when and how to split or consolidate.
    """

    def __init__(self):
        # Current coin counts (free/spendable only)
        self._xch_coins: int = 0
        self._cat_coins: int = 0

        # Locked coin tracking — coins locked in active offers
        self._xch_locked_coins: int = 0
        self._cat_locked_coins: int = 0
        self._xch_locked_amount: int = 0   # mojos
        self._cat_locked_amount: int = 0   # mojos
        self._xch_total_coins: int = 0     # free + locked
        self._cat_total_coins: int = 0     # free + locked

        # Coin inventory — last snapshot of classified coins
        # When TIER_ENABLED, this also has inner/mid/outer/extreme keys
        self._xch_inventory: Dict[str, list] = {"reserve": [], "trading": [], "small": []}
        self._cat_inventory: Dict[str, list] = {"reserve": [], "trading": [], "small": []}

        # Coin prep state
        self._prep_running: bool = False
        self._topup_running: bool = False
        self._topup_thread: Optional[threading.Thread] = None

        # Backoff state
        self._no_coins_backoff: bool = False
        self._no_coins_backoff_count: int = 0   # consecutive "nothing to work with" hits
        self._last_topup_time: float = 0

        # Warning throttle
        self._last_low_coin_warning: float = 0

        # Coin prep worker process
        self._prep_process: Optional[subprocess.Popen] = None

        # Lock for thread safety
        self._lock = threading.Lock()

        # Worker cancelled IDs
        self._worker_cancelled_ids: set = set()
        self._topup_abort_logged: bool = False
        self._topup_stop_requested: bool = False

        # Fingerprint for CLI commands — auto-detect if not in config
        self._fingerprint = self._resolve_fingerprint()

        # Loop counter for runtime health checks
        self._health_check_counter: int = 0

        # Coin change tracking — stores coin IDs from last snapshot
        self._prev_xch_coin_ids: Optional[set] = None
        self._prev_cat_coin_ids: Optional[set] = None

        # ---- Designation-based tracking (V3 adaptive system) ----
        # Replaces pure amount-based classification with explicit role tracking.
        # Reserve coins are reserve because we SAY they are, not because
        # they happen to be big enough.
        self._reserve_ids_xch: set = set()    # Coin IDs designated as XCH reserve
        self._reserve_ids_cat: set = set()    # Coin IDs designated as CAT reserve
        self._tier_spares: Dict[str, Dict[str, int]] = {
            "xch": {"inner": 0, "mid": 0, "outer": 0, "extreme": 0, "sniper": 0, "fees": 0},
            "cat": {"inner": 0, "mid": 0, "outer": 0, "extreme": 0, "sniper": 0, "fees": 0},
        }
        # Pre-populate from DB so needs_topup/needs_prep have valid data before
        # the first update_coin_counts() cycle completes.
        try:
            from database import get_tier_spare_counts
            for _wt in ("xch", "cat"):
                _spares = get_tier_spare_counts(_wt)
                if _spares:
                    self._tier_spares[_wt] = _spares
        except Exception:
            pass  # DB may not be ready yet — zeros are safe defaults
        self._trading_pace: str = "normal"    # Current pace: slow/normal/busy
        self._last_pace_calc: float = 0       # Timestamp of last pace calculation
        self._reconcile_counter: int = 0      # Counts loops between reconciliations

    def _sniper_pool_enabled(self) -> bool:
        """Whether the dedicated sniper pool should be prepared and maintained."""
        try:
            sniper_size = Decimal(str(getattr(cfg, "SNIPER_SIZE_XCH", "0") or "0"))
        except Exception:
            sniper_size = Decimal("0")
        return (
            bool(getattr(cfg, "TIER_ENABLED", False))
            and bool(getattr(cfg, "SNIPER_ENABLED", False))
            and int(getattr(cfg, "SNIPER_PREP_COUNT", 0) or 0) > 0
            and sniper_size > 0
        )

    def _configured_tier_names(self, include_sniper: bool = True) -> List[str]:
        tiers = ["inner", "mid", "outer", "extreme"]
        if include_sniper and self._sniper_pool_enabled():
            tiers.append("sniper")
        return tiers

    def _configured_tier_sizes_xch(self, include_sniper: bool = True) -> Dict[str, Decimal]:
        sizes = {
            "inner": Decimal(str(getattr(cfg, "INNER_SIZE_XCH", Decimal("0")))),
            "mid": Decimal(str(getattr(cfg, "MID_SIZE_XCH", Decimal("0")))),
            "outer": Decimal(str(getattr(cfg, "OUTER_SIZE_XCH", Decimal("0")))),
            "extreme": Decimal(str(getattr(cfg, "EXTREME_SIZE_XCH", Decimal("0")))),
        }
        if include_sniper and self._sniper_pool_enabled():
            sizes["sniper"] = Decimal(str(getattr(cfg, "SNIPER_SIZE_XCH", Decimal("0"))))
        return sizes

    def _configured_xch_prep_sizes(self) -> Dict[str, Decimal]:
        sizes = dict(self._configured_tier_sizes_xch())
        if self._fee_pool_enabled():
            sizes[get_fee_tier_name()] = Decimal(str(get_fee_coin_size_xch()))
        return sizes

    def _configured_prep_counts(self, wallet_type: str) -> Dict[str, int]:
        """Expected prepared-coin counts per tier for the current config."""
        if not bool(getattr(cfg, "TIER_ENABLED", False)):
            return {}

        max_buy = int(getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25) or 25)
        max_sell = int(getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25) or 25)
        max_per_side = max(max_buy, max_sell)
        tier_dist = get_tier_distribution(max_per_side)

        multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0"))
        tier_counts = get_weighted_tier_prep_counts(max_per_side, multiplier)

        if self._sniper_pool_enabled():
            tier_counts["sniper"] = int(getattr(cfg, "SNIPER_PREP_COUNT", 0) or 0)

        if wallet_type == "xch" and self._fee_pool_enabled():
            tier_counts[get_fee_tier_name()] = int(get_fee_pool_count() or 0)

        return {k: v for k, v in tier_counts.items() if int(v or 0) > 0}

    def _fee_pool_enabled(self) -> bool:
        return bool(getattr(cfg, "ENABLE_COIN_PREP", False)) and fee_pool_enabled()

    def _tx_fee_mojos(self) -> int:
        return get_effective_transaction_fee_mojos()

    def _wallet_rpc_failed(self, rpc_result) -> bool:
        return (
            rpc_result is None
            or not isinstance(rpc_result, dict)
            or bool(rpc_result.get("error"))
            or rpc_result.get("success") is False
        )

    def _looks_like_wallet_rpc_degradation(self, detail) -> bool:
        text = str(detail or "").strip().lower()
        if not text:
            return True
        return any(token in text for token in (
            "timed out",
            "timeout",
            "connection",
            "rpc",
            "http",
            "ssl",
            "empty",
            "none",
        ))

    def _spacescan_coin_state(self, coin_id: str) -> Optional[Dict]:
        if not coin_id:
            return None
        try:
            from spacescan import is_coin_spent
            return is_coin_spent(coin_id)
        except Exception:
            return None

    def _spacescan_self_send_confirmed(self, coin_id: str, expected_address: str,
                                       tag: str) -> bool:
        state = self._spacescan_coin_state(coin_id)
        if not state or not state.get("spent"):
            return False
        receiver = str(state.get("receiver_address") or "").strip()
        try:
            from spacescan import is_known_wallet_address
        except Exception:
            is_known_wallet_address = None
        if expected_address and receiver == expected_address:
            log_event(
                "info",
                f"{tag}_spacescan_self_send",
                f"Spacescan confirms source coin {coin_id[:12]}... spent to "
                f"{receiver[:16]}... even though Sage response was weak",
            )
            return True
        if receiver and is_known_wallet_address and is_known_wallet_address(receiver, {expected_address}):
            log_event(
                "info",
                f"{tag}_spacescan_self_send_known_wallet",
                f"Spacescan confirms source coin {coin_id[:12]}... spent to "
                f"known own address {receiver[:16]}... even though Sage response was weak",
            )
            return True
        return False

    def _spacescan_coin_spent_confirmed(self, coin_id: str, tag: str,
                                        label: str) -> bool:
        state = self._spacescan_coin_state(coin_id)
        if not state or not state.get("spent"):
            return False
        receiver = str(state.get("receiver_address") or "").strip()
        suffix = f" to {receiver[:16]}..." if receiver else ""
        log_event(
            "info",
            f"{tag}_{label}_onchain",
            f"Spacescan confirms coin {coin_id[:12]}... was spent on-chain{suffix}",
        )
        return True

    def _abort_topup_for_wallet_degradation(self, reason: str,
                                            event_type: str = "topup_wallet_degraded"):
        if not self._topup_abort_logged:
            log_event("warning", event_type, reason)
            self._topup_abort_logged = True
        raise _TopupWalletDegraded(reason)

    @staticmethod
    def _extract_sage_transaction_ids(result) -> List[str]:
        """Extract normalized Sage transaction ids from a submit response."""
        if result is None:
            return []

        tx_ids = []
        if isinstance(result, dict):
            raw_ids = result.get("transaction_ids")
            if isinstance(raw_ids, list):
                tx_ids.extend(raw_ids)
            single = result.get("transaction_id") or result.get("tx_id")
            if single:
                tx_ids.append(single)
            nested = result.get("transaction") or result.get("tx")
            if isinstance(nested, dict):
                nested_single = nested.get("transaction_id")
                if nested_single:
                    tx_ids.append(nested_single)
                nested_ids = nested.get("transaction_ids")
                if isinstance(nested_ids, list):
                    tx_ids.extend(nested_ids)

        normalized = []
        seen = set()
        for tx_id in tx_ids:
            clean = str(tx_id or "").strip().lower()
            if not clean:
                continue
            if not clean.startswith("0x"):
                clean = "0x" + clean
            if clean not in seen:
                seen.add(clean)
                normalized.append(clean)
        return normalized

    def _get_transaction_confirmation_state(self, tx_ids: List[str]) -> Dict[str, object]:
        """Summarize Sage transaction confirmation state for runtime top-up."""
        tx_ids = [tid for tid in (tx_ids or []) if tid]
        if not tx_ids or get_wallet_type() != "sage":
            return {"known": False, "confirmed": False, "confirmed_count": 0, "total": 0, "height": 0}

        try:
            from wallet_sage import get_transaction
        except Exception:
            return {"known": False, "confirmed": False, "confirmed_count": 0, "total": len(tx_ids), "height": 0}

        confirmed_count = 0
        best_height = 0
        any_known = False
        for tx_id in tx_ids:
            try:
                tx_info = get_transaction(tx_id)
            except Exception:
                tx_info = None
            if not tx_info or not isinstance(tx_info, dict):
                continue
            any_known = True
            confirmed = bool(tx_info.get("confirmed", False))
            height = int(tx_info.get("confirmed_at_height", 0) or 0)
            if confirmed or height > 0:
                confirmed_count += 1
                best_height = max(best_height, height)

        total = len(tx_ids)
        return {
            "known": any_known,
            "confirmed": (confirmed_count > 0 if total == 1 else confirmed_count == total),
            "confirmed_count": confirmed_count,
            "total": total,
            "height": best_height,
        }

    def _get_owned_coin_amount_map(self, wallet_id: int, name: str) -> Dict[str, int]:
        """Return owned wallet coins as {coin_id: amount_mojos}."""
        try:
            owned_result = get_owned_coins(wallet_id) or {}
            owned_map = {}
            if isinstance(owned_result, dict):
                for cid, amount in owned_result.items():
                    clean = str(cid or "").strip().lower()
                    if not clean:
                        continue
                    if not clean.startswith("0x"):
                        clean = "0x" + clean
                    owned_map[clean] = int(amount or 0)
            return owned_map
        except Exception as e:
            log_event("warning", f"{name}_owned_unavailable",
                      f"Owned coin view unavailable: {str(e)[:160]}")
            # Safe lower-bound fallback: if Sage's owned view flakes out but the
            # strict selectable view is still healthy, treat selectable coins as
            # the minimum owned set instead of silently reporting "0 owned".
            try:
                selectable_result = _get_free_coins_rpc(wallet_id)
                if self._wallet_rpc_failed(selectable_result):
                    return {}
                fallback_map = {}
                for record in _extract_coin_records(selectable_result):
                    cid = _coin_id_from_record(record)
                    if cid:
                        fallback_map[cid] = _coin_amount(record)
                if fallback_map:
                    log_event("info", f"{name}_owned_fallback_selectable",
                              f"Using selectable coin view as owned lower-bound "
                              f"({len(fallback_map)} coins)")
                return fallback_map
            except Exception:
                return {}

    def _get_strict_selectable_coin_id_set(self, wallet_id: int, name: str) -> set:
        """Return strict selectable/free coin ids for a wallet."""
        try:
            if get_wallet_type() == "sage":
                from wallet_sage import get_selectable_coins_only
                result = get_selectable_coins_only(wallet_id)
            else:
                result = _get_free_coins_rpc(wallet_id)
        except Exception as e:
            log_event("warning", f"{name}_selectable_unavailable",
                      f"Selectable coin view unavailable: {str(e)[:160]}")
            return set()

        if self._wallet_rpc_failed(result):
            return set()

        selectable_ids = set()
        for record in _extract_coin_records(result):
            cid = _coin_id_from_record(record)
            if cid:
                selectable_ids.add(cid)
        return selectable_ids

    # -------------------------------------------------------------------
    # Fingerprint resolution
    # -------------------------------------------------------------------

    def _resolve_fingerprint(self) -> str:
        """Get wallet fingerprint — config first, then RPC auto-detect.

        coin_prep_worker had a bug where empty WALLET_FINGERPRINT in .env
        caused CLI splits to fail with 'Invalid value for -f'. This method
        mirrors coin_prep_worker's robust approach.
        """
        # Try config first
        fp = str(getattr(cfg, "WALLET_FINGERPRINT", "") or "").strip()
        if fp and fp.isdigit():
            log_event("info", "coin_mgr_fingerprint",
                      f"Using fingerprint from config: {fp}")
            return fp

        # Auto-detect via RPC
        wallet_type = os.getenv("WALLET_TYPE", "sage").lower().strip()

        if wallet_type == "sage":
            # Sage: use get_current_key() instead of get_logged_in_fingerprint.
            # Retry up to 4 times with short delays — Sage may still be starting
            # up when the bot initializes (e.g. user closed Sage and let the app
            # launch it fresh). Non-fatal: fingerprint is re-resolved later if needed.
            from wallet_sage import get_current_key
            for _attempt in range(4):
                try:
                    key = get_current_key()
                    if key and key.get("fingerprint"):
                        fp_str = str(key["fingerprint"])
                        log_event("info", "coin_mgr_fingerprint",
                                  f"Auto-detected Sage fingerprint: {fp_str}")
                        return fp_str
                except Exception as e:
                    if _attempt < 3:
                        import time as _time
                        _time.sleep(3)
                    else:
                        log_event("warning", "coin_mgr_fingerprint_rpc_fail",
                                  f"Sage fingerprint detection failed after 4 attempts: {e}")
        else:
            # Chia: use get_logged_in_fingerprint RPC
            try:
                from wallet import rpc
                result = rpc("get_logged_in_fingerprint", {})
                rpc_fp = result.get("fingerprint") if result else None
                if rpc_fp:
                    fp_str = str(rpc_fp)
                    log_event("info", "coin_mgr_fingerprint",
                              f"Auto-detected fingerprint via RPC: {fp_str}")
                    return fp_str
            except Exception as e:
                log_event("warning", "coin_mgr_fingerprint_rpc_fail",
                          f"RPC fingerprint detection failed: {e}")

            # CLI fallback (Chia only)
            try:
                import subprocess as sp
                proc = sp.run(
                    ["chia", "keys", "show"],
                    capture_output=True, text=True, timeout=30
                )
                for line in proc.stdout.splitlines():
                    if "fingerprint:" in line.lower():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            maybe_fp = parts[-1].strip()
                            if maybe_fp.isdigit():
                                log_event("info", "coin_mgr_fingerprint",
                                          f"Auto-detected fingerprint via CLI: {maybe_fp}")
                                return maybe_fp
            except Exception as e:
                log_event("warning", "coin_mgr_fingerprint_cli_fail",
                          f"CLI fingerprint detection failed: {e}")

        log_event("error", "coin_mgr_no_fingerprint",
                  "Could not determine wallet fingerprint from config, RPC, or CLI")
        return ""

    # -------------------------------------------------------------------
    # V3: Designation-based coin classification (replaces amount-only)
    # -------------------------------------------------------------------

    def _classify_coins_by_designation(self, records: list, wallet_type: str,
                                        tier_sizes_mojos: Dict[str, int]) -> Dict[str, list]:
        """Classify coins using DB designations first, size-inference as fallback.

        This is the HEART of the V3 adaptive system. Instead of classifying
        coins purely by their amount (which breaks when reserve coins get split
        below the threshold), we check each coin's DESIGNATED ROLE in the DB.

        Workflow:
        1. Coins with existing designations → keep them (reserve stays reserve)
        2. NEW coins (designation='unknown') → infer by size, persist to DB
        3. Returns same dict structure as _classify_coins_tiered() for backward compat

        Args:
            records: Raw coin records from wallet RPC
            wallet_type: 'xch' or 'cat'
            tier_sizes_mojos: {"inner": mojos, "mid": mojos, ...}

        Returns dict with keys: reserve, inner, mid, outer, extreme,
        optional sniper, and small
        """
        result = {
            "reserve": [],
            "inner": [],
            "mid": [],
            "outer": [],
            "extreme": [],
            "sniper": [],
            "fees": [],
            "small": [],
        }

        try:
            from database import get_free_coins, get_locked_coins, set_coin_designation

            # Build a lookup of DB designations for this wallet
            db_coins = get_free_coins(wallet_type)
            db_desig_map = {}  # coin_id → (designation, assigned_tier)
            for dc in db_coins:
                cid = dc.get("coin_id", "")
                desig = dc.get("designation", "unknown") or "unknown"
                atier = dc.get("assigned_tier", "none") or "none"
                db_desig_map[cid] = (desig, atier)

            # Rebalance duplicate-size tiers like XCH sniper/fees. If the DB
            # lost the distinction across a restart, stale designations can put
            # every same-sized free coin into the first matching tier.
            expected_counts = self._configured_prep_counts(wallet_type)
            locked_by_tier = {}
            for locked in get_locked_coins(wallet_type):
                desig = (locked.get("designation") or "unknown").strip()
                atier = (locked.get("assigned_tier") or "none").strip()
                if desig in ("tier_active", "tier_spare") and atier in expected_counts:
                    locked_by_tier[atier] = locked_by_tier.get(atier, 0) + 1

            duplicate_tier_groups = []
            for tier_name, amount in tier_sizes_mojos.items():
                amount_int = int(amount or 0)
                if amount_int <= 0 or tier_name not in expected_counts:
                    continue

                matched_group = None
                for group in duplicate_tier_groups:
                    ref_amount = group["amount"]
                    low = int(ref_amount * 0.8)
                    high = int(ref_amount * 1.2)
                    if low <= amount_int <= high:
                        matched_group = group
                        break

                if matched_group is None:
                    duplicate_tier_groups.append({
                        "amount": amount_int,
                        "tiers": [tier_name],
                    })
                else:
                    matched_group["tiers"].append(tier_name)
                    matched_group["amount"] = min(matched_group["amount"], amount_int)

            for group in duplicate_tier_groups:
                tiers_for_amount = group["tiers"]
                if len(tiers_for_amount) < 2:
                    continue

                matching_coin_ids = []
                for rec in records:
                    cid = _coin_id_from_record(rec)
                    if not cid:
                        continue
                    amt = _coin_amount(rec)
                    for tier_name in tiers_for_amount:
                        tier_amount = int(tier_sizes_mojos.get(tier_name, 0) or 0)
                        if tier_amount <= 0:
                            continue
                        low = int(tier_amount * 0.8)
                        high = int(tier_amount * 1.2)
                        if low <= amt <= high:
                            matching_coin_ids.append(cid)
                            break
                if not matching_coin_ids:
                    continue

                matching_coin_ids = sorted(set(matching_coin_ids))
                free_targets = {
                    tier_name: max(
                        0,
                        int(expected_counts.get(tier_name, 0) or 0)
                        - int(locked_by_tier.get(tier_name, 0) or 0),
                    )
                    for tier_name in tiers_for_amount
                }

                reassigned = {}
                cursor = 0
                for tier_name in tiers_for_amount:
                    take = min(max(0, len(matching_coin_ids) - cursor), free_targets.get(tier_name, 0))
                    if take <= 0:
                        continue
                    for cid in matching_coin_ids[cursor:cursor + take]:
                        reassigned[cid] = tier_name
                    cursor += take

                if cursor < len(matching_coin_ids):
                    leftovers = matching_coin_ids[cursor:]
                    for cid in leftovers:
                        prior_tier = db_desig_map.get(cid, ("unknown", "none"))[1]
                        fallback_tier = prior_tier if prior_tier in tiers_for_amount else tiers_for_amount[-1]
                        reassigned[cid] = fallback_tier

                for cid, tier_name in reassigned.items():
                    set_coin_designation(cid, "tier_spare", tier_name)
                    db_desig_map[cid] = ("tier_spare", tier_name)

            # Track reserve IDs for this wallet
            reserve_ids = set()
            skipped_no_id = 0

            for rec in records:
                cid = _coin_id_from_record(rec)
                if not cid:
                    skipped_no_id += 1
                    continue
                amt = _coin_amount(rec)

                # Check DB designation first
                db_info = db_desig_map.get(cid)
                if db_info and db_info[0] not in ('unknown', None):
                    desig, atier = db_info
                else:
                    # New/unknown coin — infer by size
                    desig, atier = _infer_designation_by_size(amt, tier_sizes_mojos)
                    # Persist the inferred designation so it survives restarts
                    set_coin_designation(cid, desig, atier)

                # Place into the appropriate bucket
                if desig == 'reserve':
                    result["reserve"].append(rec)
                    reserve_ids.add(cid)
                elif desig == 'dust':
                    result["small"].append(rec)
                elif desig in ('tier_spare', 'tier_active'):
                    bucket = atier if atier in result else "small"
                    result[bucket].append(rec)
                else:
                    # 'unknown' or unexpected — infer by size for bucket placement
                    _, inferred_tier = _infer_designation_by_size(amt, tier_sizes_mojos)
                    if inferred_tier in result:
                        result[inferred_tier].append(rec)
                    else:
                        result["small"].append(rec)

            # Warn if coins were skipped (missing coin_id — likely wallet format issue)
            if skipped_no_id > 0:
                log_event("warning", "coins_skipped_no_id",
                          f"{skipped_no_id} {wallet_type} coins skipped — "
                          f"could not determine coin_id (check wallet response format)")

            # Update in-memory reserve tracking
            if wallet_type == 'xch':
                self._reserve_ids_xch = reserve_ids
            else:
                self._reserve_ids_cat = reserve_ids

            # Final startup/restart cleanup for tiers whose configured sizes are
            # close enough that Sage split dust/fees can blur them together
            # (notably XCH sniper vs fees). If DB designations are stale or the
            # exact amounts drift a little, rebalance buckets to expected counts.
            if wallet_type == "xch" and result.get("sniper") and self._fee_pool_enabled():
                fee_target = int(expected_counts.get("fees", 0) or 0)
                sniper_target = int(expected_counts.get("sniper", 0) or 0)
                fee_have = len(result.get("fees", []))
                sniper_have = len(result.get("sniper", []))
                need_fees = max(0, fee_target - fee_have)
                excess_sniper = max(0, sniper_have - sniper_target)
                if need_fees > 0 and excess_sniper > 0:
                    fee_size = int(tier_sizes_mojos.get("fees", 0) or 0)
                    sniper_bucket = result.get("sniper", [])
                    sniper_bucket.sort(key=lambda rec: abs(_coin_amount(rec) - fee_size))
                    move_count = min(need_fees, excess_sniper, len(sniper_bucket))
                    moved = []
                    for _ in range(move_count):
                        rec = sniper_bucket.pop(0)
                        cid = _coin_id_from_record(rec)
                        if cid:
                            set_coin_designation(cid, "tier_spare", "fees")
                            db_desig_map[cid] = ("tier_spare", "fees")
                        moved.append(rec)
                    if moved:
                        result.setdefault("fees", []).extend(moved)

            # Update spare counts from DB
            try:
                from database import get_tier_spare_counts
                self._tier_spares[wallet_type] = get_tier_spare_counts(wallet_type)
            except Exception as e:
                log_event("warning", "tier_spare_counts_failed",
                          f"Could not update tier spare counts for {wallet_type}: {e}")

        except Exception as e:
            # Fallback to legacy classification if DB is unavailable
            log_event("warning", "designation_fallback",
                      f"Designation classification failed ({e}), using legacy")
            result = _classify_coins_tiered(records, tier_sizes_mojos)

        # Sort reserve and small by size descending
        result["reserve"].sort(key=_coin_amount, reverse=True)
        result["small"].sort(key=_coin_amount, reverse=True)

        return result

    def _ensure_reserve_exists(self, wallet_type: str, records: list):
        """Make sure at least one coin is designated as reserve.

        The reserve coin is just whatever's left after tier pools are created.
        It doesn't need a minimum size — it's organic. If no reserve exists,
        we promote the largest undesignated/free coin.

        Called after classification. If the previous reserve was spent/gone,
        finds and promotes the next largest free coin.
        """
        try:
            from database import (get_reserve_coins, designate_reserve,
                                   get_coins_by_designation)

            existing = get_reserve_coins(wallet_type)
            if existing:
                # Reserve exists — nothing to do
                return

            # No reserve — find the largest free undesignated coin
            # Prefer 'unknown' coins, then 'dust' (consolidation material)
            unknowns = get_coins_by_designation(wallet_type, 'unknown')
            if unknowns:
                best = unknowns[0]  # Already sorted by amount DESC
                designate_reserve(best['coin_id'], wallet_type, best['amount_mojos'])
                if wallet_type == 'xch':
                    self._reserve_ids_xch.add(best['coin_id'])
                else:
                    self._reserve_ids_cat.add(best['coin_id'])
                return

            # No unknown coins — check if we have any large dust
            dust = get_coins_by_designation(wallet_type, 'dust')
            if dust:
                best = dust[0]
                designate_reserve(best['coin_id'], wallet_type, best['amount_mojos'])
                if wallet_type == 'xch':
                    self._reserve_ids_xch.add(best['coin_id'])
                else:
                    self._reserve_ids_cat.add(best['coin_id'])
                return

            # No coins to promote — reserve is empty (will be created from
            # freed coins when offers fill/cancel)
            log_event("info", "no_reserve_available",
                      f"No {wallet_type.upper()} reserve coin — will create from freed coins")

        except Exception as e:
            log_event("warning", "ensure_reserve_error",
                      f"Failed to ensure {wallet_type} reserve: {e}")

    # -------------------------------------------------------------------
    # V3: Trading pace and adaptive thresholds
    # -------------------------------------------------------------------

    def get_trading_pace(self) -> str:
        """Returns 'slow', 'normal', or 'busy' based on recent fill rate.

        Caches the result for 5 minutes to avoid hitting the DB every loop.
        """
        now = time.time()
        if now - self._last_pace_calc < 300:  # Cache for 5 min
            return self._trading_pace

        try:
            from database import get_current_pace
            pace = get_current_pace()
            self._trading_pace = pace
            self._last_pace_calc = now
        except Exception as e:
            log_event("debug", "trading_pace_fetch_failed",
                      f"Trading pace DB fetch failed (keeping previous value '{self._trading_pace}'): {e}")

        return self._trading_pace

    def get_startup_advisory(self) -> Dict:
        """Calculate and return collateral allocation advice at startup.

        Tells the user: "You have X XCH. Here's how it'll be allocated
        across tiers and reserve." Helps set expectations before trading.

        Returns dict with:
          - total_available: total confirmed XCH (free + offer-locked)
          - spendable_available: currently free/selectable XCH
          - per_tier_needs: coins needed per tier (active + spares)
          - reserve_size: what's left after tier allocation
          - assessment: 'EXCESS' / 'ADEQUATE' / 'LOW' / 'CRITICAL'
          - message: human-readable advice string
        """
        try:
            from wallet import get_wallet_balance

            # Sage returns confirmed = total held (including offer-locked),
            # spendable = currently free/selectable. On a resumed live book,
            # the advisory must use confirmed balance for "do we have enough
            # capital overall?" and spendable balance only for current headroom.
            xch_bal = get_wallet_balance(cfg.WALLET_ID_XCH)
            wb = xch_bal.get("wallet_balance") or xch_bal if xch_bal else {}
            spendable_mojos = wb.get("spendable_balance", 0) or 0
            confirmed_mojos = wb.get("confirmed_wallet_balance", spendable_mojos) or spendable_mojos
            if isinstance(spendable_mojos, str):
                spendable_mojos = int(spendable_mojos)
            if isinstance(confirmed_mojos, str):
                confirmed_mojos = int(confirmed_mojos)

            spendable_xch = Decimal(str(spendable_mojos)) / Decimal("1000000000000")
            total_xch = Decimal(str(confirmed_mojos)) / Decimal("1000000000000")
            locked_xch = max(Decimal("0"), total_xch - spendable_xch)
            has_locked_collateral = locked_xch > Decimal("0.000001")

            multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0"))
            max_per_side = max(
                getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25),
                getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25))

            if cfg.TIER_ENABLED:
                tier_dist = get_tier_distribution(max_per_side)
                prepared_counts = get_weighted_tier_prep_counts(max_per_side, multiplier)
                per_tier_needs = {}
                total_tier_xch = Decimal("0")
                for t, slots in tier_dist.items():
                    coins_needed = int(prepared_counts.get(t, 0) or 0)
                    tier_size = getattr(cfg, f"{t.upper()}_SIZE_XCH", cfg.MID_SIZE_XCH)
                    tier_xch = tier_size * coins_needed
                    per_tier_needs[t] = {
                        'coins': coins_needed,
                        'xch_each': float(tier_size),
                        'xch_total': float(tier_xch)
                    }
                    total_tier_xch += tier_xch

                reserve_xch = total_xch - total_tier_xch
                largest_tier = max(
                    Decimal(str(getattr(cfg, "INNER_SIZE_XCH", Decimal("1")) or "0")),
                    Decimal(str(getattr(cfg, "MID_SIZE_XCH", Decimal("0.5")) or "0")),
                    Decimal(str(getattr(cfg, "OUTER_SIZE_XCH", Decimal("0")) or "0")),
                    Decimal(str(getattr(cfg, "EXTREME_SIZE_XCH", Decimal("0")) or "0")),
                    Decimal(str(getattr(cfg, "SNIPER_SIZE_XCH", Decimal("0")) or "0")),
                )

                # Two-tier reserve breakdown:
                # (a) configured_reserve — the XCH_RESERVE amount; untouchable,
                #     never split by topup, kept as a hard safety margin
                # (b) topup_pool — whatever remains after configured_reserve;
                #     large unbroken coins the topup worker splits when tier
                #     coins run low.  Topup cannot function if this is too thin.
                configured_reserve = max(Decimal("0"),
                    Decimal(str(getattr(cfg, "XCH_RESERVE", Decimal("0")) or "0")))
                topup_pool = max(Decimal("0"), reserve_xch - configured_reserve)

                total_str = f"{float(total_xch):.1f}"
                spendable_str = f"{float(spendable_xch):.1f}"
                needed_str = f"{float(total_tier_xch):.1f}"
                reserve_str = f"{float(reserve_xch):.1f}"
                configured_str = f"{float(configured_reserve):.1f}"
                topup_pool_str = f"{float(topup_pool):.2f}"

                # Build reserve detail suffix for messages
                if configured_reserve > 0:
                    _reserve_detail = (
                        f"{reserve_str} XCH reserve "
                        f"({configured_str} configured + {topup_pool_str} topup pool)"
                    )
                else:
                    _reserve_detail = (
                        f"{reserve_str} XCH reserve ({topup_pool_str} available for topup splits)"
                    )

                if has_locked_collateral:
                    resume_prefix = (
                        f"{total_str} XCH total, {spendable_str} XCH currently free. "
                        f"Configured tiers need {needed_str} XCH total"
                    )
                else:
                    resume_prefix = (
                        f"{total_str} XCH available. "
                        f"Tiers need {needed_str}"
                    )

                if reserve_xch < 0:
                    assessment = 'CRITICAL'
                    if has_locked_collateral:
                        msg = (
                            f"{resume_prefix}, so the wallet is short by "
                            f"{float(abs(reserve_xch)):.1f} XCH overall. "
                            f"Existing offers may still be live, but the configured book "
                            f"cannot be fully rebuilt at these settings."
                        )
                    else:
                        msg = (f"Need {needed_str} XCH for tiers but only "
                               f"have {total_str} XCH. Reduce tier sizes or "
                               f"number of offers.")
                elif topup_pool < largest_tier * 2:
                    # Warn when the topup pool (not just total reserve) is too thin
                    # to fund a full split of the largest tier.
                    # A topup pool smaller than 2× largest_tier can't reliably
                    # replenish both buy and sell sides in a single split pass.
                    assessment = 'LOW'
                    if has_locked_collateral:
                        msg = (
                            f"{resume_prefix}, leaving {_reserve_detail} (topup pool low). "
                            f"Locked balance is funding live offers; "
                            f"{spendable_str} XCH is the free headroom. "
                            f"Topup pool needs ≥{float(largest_tier * 2):.1f} XCH "
                            f"to reliably replenish the largest tier."
                        )
                    else:
                        msg = (f"{total_str} XCH available. "
                               f"Tiers need {needed_str}, leaving {_reserve_detail} (topup pool low). "
                               f"Topup needs ≥{float(largest_tier * 2):.1f} XCH to split the largest tier.")
                elif reserve_xch > largest_tier * 3:
                    assessment = 'EXCESS'
                    if has_locked_collateral:
                        msg = (
                            f"{resume_prefix}, leaving {_reserve_detail} (plenty). "
                            f"Existing live offers are already using the locked balance; "
                            f"{spendable_str} XCH remains free for topups."
                        )
                    else:
                        msg = (f"{total_str} XCH available. "
                               f"Tiers need {needed_str}, leaving {_reserve_detail} (plenty).")
                else:
                    assessment = 'ADEQUATE'
                    if has_locked_collateral:
                        msg = (
                            f"{resume_prefix}, leaving {_reserve_detail}. "
                            f"Existing live offers are using the locked balance; "
                            f"{spendable_str} XCH remains free for topups."
                        )
                    else:
                        msg = (f"{total_str} XCH available. "
                               f"Tiers need {needed_str}, leaving {_reserve_detail}.")

                return {
                    'total_available': float(total_xch),
                    'spendable_available': float(spendable_xch),
                    'locked_estimate': float(locked_xch),
                    'per_tier_needs': per_tier_needs,
                    'total_tier_xch': float(total_tier_xch),
                    'reserve_size': float(reserve_xch),
                    'configured_reserve': float(configured_reserve),
                    'topup_pool': float(topup_pool),
                    'assessment': assessment,
                    'message': msg
                }
            else:
                # Non-tiered mode — simpler calculation
                target_coins = int(max_per_side * 2 * multiplier)
                coin_size = self.get_target_xch_coin_size()
                needed_xch = coin_size * target_coins
                reserve_xch = total_xch - needed_xch

                if reserve_xch < 0:
                    assessment = 'CRITICAL'
                elif reserve_xch < coin_size * 2:
                    assessment = 'LOW'
                else:
                    assessment = 'ADEQUATE'

                return {
                    'total_available': float(total_xch),
                    'spendable_available': float(spendable_xch),
                    'locked_estimate': float(locked_xch),
                    'target_coins': target_coins,
                    'coin_size': float(coin_size),
                    'needed_xch': float(needed_xch),
                    'reserve_size': float(reserve_xch),
                    'assessment': assessment,
                    'message': (f"{float(total_xch):.1f} XCH available. "
                                f"Need {float(needed_xch):.1f} for {target_coins} coins, "
                                f"leaving {float(reserve_xch):.1f} reserve. "
                                f"Status: {assessment}")
                }

        except Exception as e:
            return {
                'total_available': 0,
                'assessment': 'UNKNOWN',
                'message': f"Could not calculate advisory: {e}"
            }

    def reconcile_with_wallet(self):
        """Authoritative sync: wallet RPC wins any disagreement.

        Called every N loops (configurable), and should be called on startup.

        Uses Sage's filter_mode="owned" (all held coins) and "selectable"
        (free coins only) to determine which coins exist and their status.
        Locked coins = owned - selectable.

        Catches:
          - Coins that vanished (mark gone)
          - Coins that appeared (add as 'unknown' for next classification)
          - Status mismatches (free↔locked sync)
          - Reserve coins that disappeared (promote next largest)
        """
        try:
            from database import (reconcile_coins_with_wallet,
                                   get_reserve_coins)
            from wallet import get_wallet_type

            wallet_type_str = get_wallet_type()
            is_sage = wallet_type_str == "sage"
            wallet_open_offers = None
            wallet_confirmed_locked = set()

            for wt, wallet_id in [("xch", cfg.WALLET_ID_XCH),
                                   ("cat", cfg.CAT_WALLET_ID)]:
                offer_id_map = {}
                selectable_records = None

                if is_sage:
                    # Sage V5 FIX: Use get_owned_coins_detailed() which returns
                    # the offer_id for each coin. This tells us EXACTLY which coins
                    # are locked by offers — no more unreliable set-difference guessing.
                    #
                    # From Sage source (migrations/0002_options.sql):
                    #   owned_coins = wallet_coins WHERE spent IS NULL (includes locked)
                    #   selectable_coins = same + offer_hash IS NULL (free only)
                    # The CoinRecord includes offer_id for locked coins.
                    try:
                        detailed_snapshot = self._get_sage_owned_coin_snapshot(wallet_id)
                    except Exception:
                        detailed_snapshot = None

                    if detailed_snapshot is not None:
                        # Build owned_map and selectable_map from detailed data
                        # This is more accurate than two separate RPC calls because
                        # the data is from a single query — no race condition between
                        # the owned and selectable calls.
                        owned_map = dict(detailed_snapshot["owned_map"])
                        selectable_map = dict(detailed_snapshot["selectable_map"])
                        selectable_records = list(detailed_snapshot["selectable_records"])
                        offer_id_map = dict(detailed_snapshot["offer_id_map"])
                        wallet_confirmed_locked.update(detailed_snapshot["locked_ids"])
                    else:
                        # Fallback: use old owned+selectable approach
                        from wallet import get_owned_coins, get_selectable_coins_map
                        owned_map = get_owned_coins(wallet_id)
                        selectable_map = get_selectable_coins_map(wallet_id)

                    if owned_map is None or selectable_map is None:
                        log_event("warning", "reconcile_skip",
                                  f"Could not fetch {wt} coins from Sage — skipping")
                        continue

                    # Run the full reconciliation
                    stats = reconcile_coins_with_wallet(
                        wallet_selectable=selectable_map,
                        wallet_owned=owned_map,
                        wallet_type=wt
                    )
                    total = (stats["added"] + stats.get("reappeared", 0)
                             + stats["marked_gone"] + stats["freed"] + stats["locked"])
                    if total > 0:
                        print(f"  [CoinMgr] {wt.upper()} reconcile: "
                              f"+{stats['added']} new, "
                              f"{stats.get('reappeared', 0)} reappeared, "
                              f"-{stats['marked_gone']} gone, "
                              f"{stats['locked']} locked, {stats['freed']} freed, "
                              f"{stats['already_ok']} ok", flush=True)

                    # V5 FIX: Use offer_id from wallet to directly link coins.
                    # The offer_id field from Sage tells us exactly which offer
                    # locked each coin — no more unreliable amount-based matching.
                    # This replaces the old link_offers_to_locked_coins() approach.
                    if offer_id_map and stats["locked"] > 0:
                        try:
                            from database import get_connection, _now, log_event as _le
                            from database import norm_coin_id
                            conn = get_connection()
                            now = _now()
                            linked_count = 0
                            # Get all open offers from wallet to map offer_hash → trade_id
                            if wallet_open_offers is None:
                                from wallet import get_all_offers
                                wallet_open_offers = get_all_offers(
                                    include_completed=False,
                                    start=0,
                                    end=500,
                                ) or []
                            all_open = wallet_open_offers
                            # Build {offer_hash: trade_id} mapping
                            hash_to_trade = {}
                            if all_open:
                                for o in all_open:
                                    # Sage offers may have an 'offer_id' or we derive from the offer itself
                                    tid = o.get("trade_id", "")
                                    if tid:
                                        hash_to_trade[tid.lower()] = tid
                            # For each locked coin with an offer_id, try to assign trade_id
                            for cid, oid in offer_id_map.items():
                                # The offer_id from the coin is the offer_hash
                                # We can use it directly as a trade_id identifier
                                # or look it up in our offers mapping
                                trade_id = hash_to_trade.get(oid, oid)
                                if trade_id:
                                    store_id = cid if cid.startswith("0x") else "0x" + cid
                                    cur = conn.execute(
                                        "UPDATE coins SET trade_id=?, last_seen=? "
                                        "WHERE coin_id=? AND status='locked' AND (trade_id IS NULL OR trade_id='')",
                                        (trade_id, now, store_id)
                                    )
                                    if cur.rowcount > 0:
                                        linked_count += 1
                            conn.commit()
                            if linked_count > 0:
                                log_event("debug", "reconcile_direct_link",
                                          f"{wt.upper()} directly linked {linked_count} coins "
                                          f"to offers via offer_id")
                        except Exception as link_e:
                            log_event("debug", "reconcile_direct_link_failed",
                                      f"Direct offer linking failed: {link_e}")

                    # Fallback: amount-based linking ONLY when direct offer_id
                    # linking is not available (i.e. no offer_id_map from Sage)
                    if stats["locked"] > 0 and not offer_id_map:
                        try:
                            from database import link_offers_to_locked_coins
                            if wallet_open_offers is None:
                                from wallet import get_all_offers
                                wallet_open_offers = get_all_offers(
                                    include_completed=False,
                                    start=0,
                                    end=500,
                                ) or []
                            all_open = wallet_open_offers
                            if all_open:
                                link_stats = link_offers_to_locked_coins(
                                    all_open, cfg.CAT_ASSET_ID)
                                linked = link_stats.get("linked", 0)
                                if linked > 0:
                                    log_event("debug", "reconcile_link_offers",
                                              f"{wt.upper()} linked {linked} coins to offers "
                                              f"after reconcile (amount-based fallback)")
                        except Exception as link_e:
                            log_event("debug", "reconcile_link_failed",
                                      f"Post-reconcile offer linking failed: {link_e}")

                else:
                    # Chia wallet: original approach using spendable-only RPC
                    from database import (get_free_coins, get_locked_coins,
                                           mark_coins_gone, mark_coin_spent,
                                           free_coin, upsert_coin, get_open_offers)

                    rpc_result = self._get_coins_fast(wallet_id)
                    rpc_records = _extract_coin_records(rpc_result)
                    rpc_ids = set()
                    for rec in rpc_records:
                        cid = _coin_id_from_record(rec)
                        if cid:
                            rpc_ids.add(cid)

                    db_free = get_free_coins(wt)
                    db_ids = {c["coin_id"] for c in db_free}

                    gone = db_ids - rpc_ids
                    if gone:
                        mark_coins_gone(list(gone))

                    new_coins = rpc_ids - db_ids
                    for rec in rpc_records:
                        cid = _coin_id_from_record(rec)
                        if cid and cid in new_coins:
                            amt = _coin_amount(rec)
                            upsert_coin(cid, wt, amt)

                # Check if reserve disappeared
                if selectable_records is not None:
                    rpc_records = list(selectable_records)
                else:
                    rpc_result = self._get_coins_fast(wallet_id)
                    rpc_records = _extract_coin_records(rpc_result)
                reserves = get_reserve_coins(wt)
                if not reserves:
                    self._ensure_reserve_exists(wt, rpc_records)

            # ---- Chia-only: Reconcile locked coins (Sage handles this above) ----
            if not is_sage:
                try:
                    from database import (get_locked_coins, get_open_offers,
                                           free_coin, mark_coin_spent)
                    open_offers_list = get_open_offers(cat_asset_id=cfg.CAT_ASSET_ID)
                    open_trade_ids = {o["trade_id"] for o in open_offers_list}

                    xch_rpc = self._get_coins_fast(cfg.WALLET_ID_XCH)
                    cat_rpc = self._get_coins_fast(cfg.CAT_WALLET_ID)
                    wallet_spendable = set()
                    for rec in _extract_coin_records(xch_rpc) + _extract_coin_records(cat_rpc):
                        cid = _coin_id_from_record(rec)
                        if cid:
                            wallet_spendable.add(cid)

                    db_locked = get_locked_coins()
                    reconciled = 0
                    for coin in db_locked:
                        cid = coin["coin_id"]
                        linked_trade = coin.get("trade_id", "")
                        if cid in wallet_spendable:
                            free_coin(cid)
                            reconciled += 1
                        elif linked_trade and linked_trade not in open_trade_ids:
                            mark_coin_spent(cid)
                            reconciled += 1
                    if reconciled > 0:
                        log_event("info", "reconcile_locked",
                                  f"Reconciled {reconciled} stale locked coins")
                except Exception as lock_e:
                    log_event("debug", "reconcile_locked_error",
                              f"Locked coin reconciliation failed: {lock_e}")

            # ---- Link offers to their locked coins (assign trade_ids) ----
            try:
                from database import link_offers_to_locked_coins

                # Get all active offers with normalized summaries
                if wallet_open_offers is None:
                    from wallet import get_all_offers
                    wallet_open_offers = get_all_offers(
                        include_completed=False,
                        start=0,
                        end=500,
                    ) or []
                all_offers = wallet_open_offers
                if all_offers and isinstance(all_offers, list):
                    active = [o for o in all_offers
                              if o.get("status") in ("active", "PENDING_ACCEPT")]
                    if active:
                        link_stats = link_offers_to_locked_coins(
                            active, cfg.CAT_ASSET_ID
                        )
                        if link_stats["linked"] > 0:
                            print(f"  [CoinMgr] Linked {link_stats['linked']} offers to coins "
                                  f"({link_stats['already_linked']} already linked, "
                                  f"{link_stats['unmatched_offers']} unmatched offers, "
                                  f"{link_stats['unmatched_coins']} unmatched coins)",
                                  flush=True)
            except Exception as link_e:
                log_event("debug", "offer_link_error",
                          f"Offer-to-coin linking failed: {link_e}")

            # ---- Orphaned locked coin cleanup (V5 FIX) ----
            # Free locked coins whose trade_id no longer matches an open offer.
            #
            # CRITICAL FIX: For Sage wallets, pass the set of coin IDs that
            # the wallet confirms are offer-locked (have offer_id set).
            # The cleanup function will NOT free these coins even if they
            # lack a trade_id in our DB — the wallet is authoritative.
            # This breaks the tug-of-war: reconcile locks → orphan frees → repeat.
            try:
                from database import cleanup_orphaned_locked_coins, get_open_offers
                db_open = get_open_offers(cat_asset_id=cfg.CAT_ASSET_ID)
                wallet_open_ids = {o.get("trade_id", "") for o in db_open
                                   if o.get("trade_id")}

                orphan_stats = cleanup_orphaned_locked_coins(
                    wallet_open_ids,
                    wallet_confirmed_locked=wallet_confirmed_locked
                )
                if orphan_stats["total_freed"] > 0:
                    print(f"  [CoinMgr] Freed {orphan_stats['total_freed']} orphaned locked coins",
                          flush=True)
            except Exception as orphan_e:
                log_event("debug", "orphan_cleanup_error",
                          f"Orphan cleanup during reconcile failed: {orphan_e}")

            log_event("debug", "reconcile_done",
                      "Wallet reconciliation complete")

        except Exception as e:
            log_event("warning", "reconcile_error",
                      f"Wallet reconciliation failed: {e}")

    # -------------------------------------------------------------------
    # V3: Coinset-aware coin query (fast cloud API with wallet fallback)
    # -------------------------------------------------------------------

    def _get_coins_fast(self, wallet_id: int):
        """Get spendable coins — tries Coinset first, falls back to wallet RPC.

        This is the V3 fast path. If a CoinsetClient is available and
        initialized, we use it for ~100ms queries instead of 2-5s wallet RPC.
        Falls back transparently if Coinset is unavailable.

        Returns the same record shape as the wallet coin RPC helpers.
        """
        # Check if we have a coinset client (injected by bot_loop at startup)
        coinset = getattr(self, "_coinset_client", None)
        if coinset and getattr(cfg, "COINSET_ENABLED", True):
            result = coinset.get_spendable_coins(wallet_id)
            if result is not None:
                return result

        # Default: exact currently free/selectable wallet RPC
        return _get_free_coins_rpc(wallet_id)

    @staticmethod
    def _make_simple_coin_record(coin_id: str, amount: int) -> Dict:
        """Build the minimal coin-record shape used by local classification code."""
        cid = str(coin_id or "").strip().lower()
        if cid and not cid.startswith("0x"):
            cid = "0x" + cid
        return {
            "coin_id": cid,
            "coin": {"amount": int(amount or 0)},
        }

    def _get_sage_owned_coin_snapshot(self, wallet_id: int) -> Optional[Dict]:
        """Fetch one Sage owned-coin view and derive owned/selectable state.

        Sage's owned coin records include `offer_id` for offer-locked coins, so a
        single `filter_mode="owned"` query can tell us every owned coin, which
        subset is selectable, and which coins are confirmed locked by offers.
        """
        if get_wallet_type() != "sage":
            return None

        try:
            detailed_map = get_owned_coins_detailed(wallet_id)
        except Exception:
            return None

        if detailed_map is None:
            return None

        owned_map = {}
        selectable_map = {}
        selectable_records = []
        offer_id_map = {}
        locked_ids = set()

        for raw_coin_id, info in (detailed_map or {}).items():
            coin_id = str(raw_coin_id or "").strip().lower()
            if not coin_id:
                continue
            if not coin_id.startswith("0x"):
                coin_id = "0x" + coin_id

            info = info or {}
            amount = int(info.get("amount", 0) or 0)
            owned_map[coin_id] = amount

            offer_id = info.get("offer_id")
            if isinstance(offer_id, str):
                offer_id = offer_id.lower()

            if offer_id:
                offer_id_map[coin_id] = offer_id
                locked_ids.add(coin_id)
            else:
                selectable_map[coin_id] = amount
                selectable_records.append(self._make_simple_coin_record(coin_id, amount))

        return {
            "owned_map": owned_map,
            "selectable_map": selectable_map,
            "selectable_records": selectable_records,
            "owned_ids": set(owned_map.keys()),
            "locked_ids": locked_ids,
            "offer_id_map": offer_id_map,
        }

    # -------------------------------------------------------------------
    # CLI-based coin splitting (reliable — RPC split doesn't broadcast)
    # -------------------------------------------------------------------

    def _split_via_cli(self, wallet_id: int, coin_id: str,
                       num_coins: int, coin_size: Decimal,
                       name: str = "topup") -> bool:
        """Split a coin into smaller coins.

        Uses Sage RPC /split when WALLET_TYPE=sage, or the Chia CLI
        `chia wallet coins split` when WALLET_TYPE=chia.

        Args:
            wallet_id: Wallet ID to split in
            coin_id: The coin ID to split (hex, with or without 0x prefix)
            num_coins: Number of new coins to create
            coin_size: Size of each new coin (in XCH or CAT token amount)
            name: Label for logging

        Returns:
            True if split confirmed (or partially confirmed)
        """
        is_cat = (wallet_id != WALLET_ID_XCH)

        log_event("info", f"split_cli_{name}",
                  f"Split: {num_coins} coins of {coin_size} "
                  f"{'CAT tokens' if is_cat else 'XCH'} (display units) "
                  f"[source: {coin_id[:16]}...]")

        # Get starting coin count for confirmation polling
        start_result = _get_free_coins_rpc(wallet_id)
        start_records = _extract_coin_records(start_result)
        start_count = len(start_records)

        # --- Dispatch to Sage RPC or Chia CLI ---
        wallet_type = get_wallet_type()

        if wallet_type == "sage":
            # Sage native /split endpoint — uses output_count, auto-sizes
            # Sage splits evenly (no amount param needed), so we just specify
            # the number of outputs. The coin is divided equally.
            log_event("info", f"split_sage_{name}",
                      f"Using Sage /split RPC for {num_coins} outputs")
            try:
                # output_count = num_coins + 1 because we want N trading coins
                # plus a remainder. Sage splits the coin into output_count pieces.
                # If we want 6 coins of 3.2 XCH from a 26.98 XCH coin, we can't
                # control individual sizes — Sage divides equally. So we request
                # the total number we need and accept even splits.
                result = split_coins_rpc(
                    wallet_id=wallet_id,
                    target_coin_id=coin_id,
                    num_coins=num_coins + 1,  # +1 for remainder
                    amount_per_coin=0,  # Sage ignores this, splits evenly
                    fee_mojos=self._tx_fee_mojos(),
                    is_cat=is_cat,
                )
                if result is None:
                    log_event("warning", f"split_sage_{name}_fail",
                              f"Sage /split returned None")
                    return False
                # Check for error in response
                if isinstance(result, dict) and result.get("error"):
                    log_event("warning", f"split_sage_{name}_fail",
                              f"Sage /split error: {result['error']}")
                    return False
                log_event("info", f"split_sage_{name}",
                          f"Sage /split submitted successfully")
            except Exception as e:
                log_event("warning", f"split_sage_{name}_error",
                          f"Sage /split error: {e}")
                return False
        else:
            # Chia CLI split (reliable — broadcasts to network every time)
            # NOTE: CLI `-a` takes DISPLAY UNITS (XCH or CAT tokens), NOT mojos.
            bare_coin_id = coin_id.replace("0x", "")

            # Lazy-resolve fingerprint if it was empty at init time
            if not self._fingerprint or not self._fingerprint.strip():
                self._fingerprint = self._resolve_fingerprint()

            cmd = [
                "chia", "wallet", "coins", "split",
                "-f", self._fingerprint,
                "-i", str(wallet_id),
                "-n", str(num_coins),
                "-a", str(coin_size),
                "-t", bare_coin_id,
                "-m", "0"
            ]

            try:
                import subprocess as sp
                process = sp.Popen(
                    cmd,
                    stdin=sp.PIPE,
                    stdout=sp.PIPE,
                    stderr=sp.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input="y\n", timeout=60)
                output = stdout + stderr

                if "submitted to" in output.lower() or "transaction" in output.lower():
                    log_event("info", f"split_cli_{name}",
                              f"CLI split submitted successfully")
                else:
                    log_event("warning", f"split_cli_{name}_fail",
                              f"CLI split failed: {output[:200]}")
                    return False

            except Exception as e:
                log_event("warning", f"split_cli_{name}_error",
                          f"CLI split error: {e}")
                return False

        # --- Wait for confirmation via coin count polling ---
        expected_count = start_count + num_coins
        confirmed = False
        poll_start = time.time()
        max_wait = 180  # 3 minutes (test showed ~61s)

        while (time.time() - poll_start) < max_wait:
            time.sleep(5)
            result = _get_free_coins_rpc(wallet_id)
            records = _extract_coin_records(result)
            current_count = len(records)
            elapsed = int(time.time() - poll_start)

            if current_count >= expected_count:
                log_event("info", f"split_{name}",
                          f"Split confirmed ({current_count} coins, {elapsed}s)")
                confirmed = True
                break

            if elapsed % 30 == 0 and elapsed > 0:
                log_event("info", f"split_{name}_wait",
                          f"Waiting for split... ({current_count}/{expected_count} coins, {elapsed}s)")

        if not confirmed:
            # Check if at least some coins were created
            final_result = _get_free_coins_rpc(wallet_id)
            final_records = _extract_coin_records(final_result)
            final_count = len(final_records)
            new_coins = final_count - start_count
            if new_coins > 0:
                log_event("info", f"split_{name}",
                          f"Partial split: {new_coins}/{num_coins} coins created after {max_wait}s")
                confirmed = True
            else:
                log_event("warning", f"split_{name}_timeout",
                          f"Split not confirmed after {max_wait}s (still {final_count} coins)")

        return confirmed

    # -------------------------------------------------------------------
    # Coin counting & inventory
    # -------------------------------------------------------------------

    def update_coin_counts(self) -> Tuple[int, int]:
        """Count and classify ALL coins for XCH and CAT wallets.

        Updates:
          - Spendable coin counts and inventory (reserve/trading/small/tiers)
          - Locked coin counts and amounts (coins held in active offers)
          - Total coin counts (free + locked)

        The locked coin data comes from comparing get_all_coins_for_wallet()
        (returns everything) with the exact selectable/free coin view.
        """
        if self._prep_running or self._topup_running:
            # During topup/prep: do a lightweight DB-only count update so the
            # bot sees newly-created coins without interfering with the worker.
            try:
                from database import get_all_coins_state
                _db_coins = get_all_coins_state()
                if _db_coins is not None:
                    _xch_free = sum(1 for c in _db_coins if c.get("wallet_type") == "xch" and c.get("status") == "free")
                    _cat_free = sum(1 for c in _db_coins if c.get("wallet_type") == "cat" and c.get("status") == "free")
                    if _xch_free != self._xch_coins or _cat_free != self._cat_coins:
                        self._xch_coins = _xch_free
                        self._cat_coins = _cat_free
            except Exception:
                pass
            return (self._xch_coins, self._cat_coins)

        try:
            # XCH — spendable coins (for inventory classification)
            # V3: uses Coinset fast path if available, falls back to wallet RPC
            wallet_type = get_wallet_type()
            xch_owned_snapshot = (
                self._get_sage_owned_coin_snapshot(cfg.WALLET_ID_XCH)
                if wallet_type == "sage" else None
            )
            if xch_owned_snapshot is not None:
                xch_records = list(xch_owned_snapshot["selectable_records"])
            else:
                xch_result = self._get_coins_fast(cfg.WALLET_ID_XCH)
                xch_records = _extract_coin_records(xch_result)

            # RETRY: If wallet returned 0 coins, try once more after a short wait.
            # Sage wallet sometimes returns empty on the first call after startup.
            if len(xch_records) == 0:
                import time as _time
                log_event("warning", "coin_count_retry",
                          "XCH wallet returned 0 coins — retrying in 3s...")
                _time.sleep(3)
                if wallet_type == "sage":
                    xch_owned_snapshot = self._get_sage_owned_coin_snapshot(cfg.WALLET_ID_XCH)
                    xch_records = list((xch_owned_snapshot or {}).get("selectable_records", []))
                else:
                    xch_result = self._get_coins_fast(cfg.WALLET_ID_XCH)
                    xch_records = _extract_coin_records(xch_result)
                if len(xch_records) > 0:
                    log_event("info", "coin_count_retry_ok",
                              f"Retry succeeded: {len(xch_records)} XCH coins found")

            self._xch_coins = len(xch_records)

            # CAT — spendable coins
            # V3: uses Coinset fast path if available, falls back to wallet RPC
            cat_owned_snapshot = (
                self._get_sage_owned_coin_snapshot(cfg.CAT_WALLET_ID)
                if wallet_type == "sage" else None
            )
            if cat_owned_snapshot is not None:
                cat_records = list(cat_owned_snapshot["selectable_records"])
            else:
                cat_result = self._get_coins_fast(cfg.CAT_WALLET_ID)
                cat_records = _extract_coin_records(cat_result)

            # RETRY: Same retry for CAT wallet
            if len(cat_records) == 0:
                import time as _time
                log_event("warning", "coin_count_retry",
                          "CAT wallet returned 0 coins — retrying in 3s...")
                _time.sleep(3)
                if wallet_type == "sage":
                    cat_owned_snapshot = self._get_sage_owned_coin_snapshot(cfg.CAT_WALLET_ID)
                    cat_records = list((cat_owned_snapshot or {}).get("selectable_records", []))
                else:
                    cat_result = self._get_coins_fast(cfg.CAT_WALLET_ID)
                    cat_records = _extract_coin_records(cat_result)
                if len(cat_records) > 0:
                    log_event("info", "coin_count_retry_ok",
                              f"Retry succeeded: {len(cat_records)} CAT coins found")

            self._cat_coins = len(cat_records)

            # ---- Step 1: Persist coins to database FIRST ----
            # This ensures DB rows exist so set_coin_designation() UPDATE works
            # during classification. Without this, new coins get designated in
            # memory but the DB designation is lost (UPDATE hits 0 rows).

            # For Sage wallet: Also fetch "owned" coins to distinguish between
            # truly gone coins vs Sage-hidden receive-side coins in offers
            xch_owned_ids = set()
            cat_owned_ids = set()
            if wallet_type == "sage":
                if xch_owned_snapshot is not None:
                    xch_owned_ids = set(xch_owned_snapshot["owned_ids"])
                else:
                    xch_owned = get_owned_coins(cfg.WALLET_ID_XCH)
                    if xch_owned:
                        xch_owned_ids = set(xch_owned.keys())

                if cat_owned_snapshot is not None:
                    cat_owned_ids = set(cat_owned_snapshot["owned_ids"])
                else:
                    cat_owned = get_owned_coins(cfg.CAT_WALLET_ID)
                    if cat_owned:
                        cat_owned_ids = set(cat_owned.keys())

            self._persist_coins_to_db(xch_records, "xch", {}, xch_owned_ids)
            self._persist_coins_to_db(cat_records, "cat", {}, cat_owned_ids)

            # ---- Step 2: Classify coins (reads+writes designations in DB) ----
            if cfg.TIER_ENABLED:
                xch_tier_mojos = self._get_tier_sizes_mojos(is_cat=False)
                self._xch_inventory = self._classify_coins_by_designation(
                    xch_records, "xch", xch_tier_mojos)
                self._ensure_reserve_exists("xch", xch_records)

                cat_tier_mojos = self._get_tier_sizes_mojos(is_cat=True)
                self._cat_inventory = self._classify_coins_by_designation(
                    cat_records, "cat", cat_tier_mojos)
                self._ensure_reserve_exists("cat", cat_records)
            else:
                xch_trading_mojos = int(self.get_target_xch_coin_size() * Decimal("1000000000000"))
                self._xch_inventory = _classify_coins(xch_records, xch_trading_mojos)

                cat_scale = Decimal(10) ** Decimal(cfg.CAT_DECIMALS)
                cat_trading_mojos = int(self.get_target_cat_coin_size() * cat_scale)
                self._cat_inventory = _classify_coins(cat_records, cat_trading_mojos)

            # ---- Locked coin tracking ----
            # Get ALL coins (free + locked) and subtract spendable to find locked
            self._update_locked_coins(xch_records, cat_records)

        except Exception as e:
            log_event("warning", "coin_count_failed", f"Failed to count coins: {e}")

        return (self._xch_coins, self._cat_coins)

    def _persist_coins_to_db(self, records: list, wallet_type: str,
                                inventory: Dict[str, list], owned_ids: set = None):
        """Persist all spendable coins to the coins table in the database.

        For each coin in the current snapshot:
          - Upsert it (insert new or update last_seen)
          - Classify its tier from the inventory dict

        After upserting, any DB coins that were 'free' but weren't seen
        in this snapshot get marked as 'gone' (they vanished from the wallet).

        Sage wallet fix: If a coin is missing from selectable but exists in owned_ids
        (from filter_mode="owned"), it's not gone — it's just hidden because it's the
        receive-side of an active offer. Only mark truly missing coins as gone.

        SAFETY: If the wallet RPC returned 0 coins but the DB has coins,
        this is almost certainly a transient RPC failure — NOT all coins
        vanishing. We skip the mark-gone step to preserve designations.

        Args:
            records: Raw coin records from the RPC
            wallet_type: 'xch' or 'cat'
            inventory: Classified inventory dict (from _classify_coins or _classify_coins_tiered)
            owned_ids: Set of coin IDs from filter_mode="owned" (Sage wallet only, None for Chia)
        """
        try:
            from database import upsert_coin, get_free_coins, mark_coins_gone

            # Build a coin_id → tier lookup from the inventory classification
            coin_tier_map = {}
            for tier_name, tier_records in inventory.items():
                for rec in tier_records:
                    cid = _coin_id_from_record(rec)
                    if cid:
                        coin_tier_map[cid] = tier_name

            # Upsert all current coins — track new vs existing for summary
            seen_ids = set()
            new_count = 0
            for rec in records:
                cid = _coin_id_from_record(rec)
                if not cid:
                    continue
                amt = _coin_amount(rec)
                tier = coin_tier_map.get(cid, "unknown")
                upsert_coin(cid, wallet_type, amt, tier)
                seen_ids.add(cid)

            # Mark coins that vanished — were 'free' in DB but not in current snapshot
            # Normalize DB coin IDs to match the format from _coin_id_from_record()
            from database import norm_coin_id
            db_free = get_free_coins(wallet_type)
            missing_ids = [c["coin_id"] for c in db_free
                           if norm_coin_id(c["coin_id"]) not in seen_ids]
            gone_count = 0
            sage_hidden_count = 0
            if missing_ids:
                # SAFETY GUARD: If wallet returned 0 coins but DB has many,
                # this is a wallet RPC failure, not mass disappearance.
                # Don't nuke the entire coin DB — it destroys prep designations.
                if len(seen_ids) == 0 and len(missing_ids) > 5:
                    log_event("warning", "coin_persist_skip_gone",
                              f"Wallet returned 0 {wallet_type} coins but DB has "
                              f"{len(missing_ids)} free — skipping mark-gone "
                              f"(likely RPC failure, not mass disappearance)")
                else:
                    # SAGE FIX: Check if coins are missing from selectable but present
                    # in owned_ids. If so, they're just hidden (receive-side of offer),
                    # not gone. Only mark truly missing coins as gone.
                    truly_gone_ids = []
                    if owned_ids is not None:
                        # Sage wallet case: have owned coin IDs from filter_mode="owned"
                        for coin_id in missing_ids:
                            normalized = norm_coin_id(coin_id).lower()
                            if normalized in owned_ids:
                                # Coin is in owned but not selectable → hidden by Sage
                                sage_hidden_count += 1
                                log_event("debug", "sage_receive_side_hidden",
                                          f"{wallet_type.upper()} coin {normalized[:12]}... "
                                          f"hidden (receive-side of offer)")
                            else:
                                # Truly gone
                                truly_gone_ids.append(coin_id)
                        gone_count = mark_coins_gone(truly_gone_ids) if truly_gone_ids else 0
                    else:
                        # Chia wallet case: no owned_ids available, use original behavior
                        gone_count = mark_coins_gone(missing_ids)

            # Log sync summary with structured data
            # (individual coin events already logged by database.py)
            reappeared_count = 0  # counted by upsert_coin in database.py
            summary_msg = (f"{wallet_type.upper()} sync: {len(seen_ids)} in wallet, "
                          f"{gone_count} gone, {len(db_free)} were free in DB")
            if sage_hidden_count > 0:
                summary_msg += f", {sage_hidden_count} hidden by Sage"
            log_event("debug", "coin_sync_summary",
                      summary_msg,
                      data={"wallet_type": wallet_type,
                            "coins_in_wallet": len(seen_ids),
                            "gone_count": gone_count,
                            "sage_hidden_count": sage_hidden_count,
                            "db_free_before": len(db_free)})

        except Exception as e:
            log_event("warning", "coin_persist_failed",
                      f"Failed to persist {wallet_type} coins to DB: {e}")

    def _update_locked_coins(self, xch_spendable: list, cat_spendable: list):
        """Calculate locked coins using BOTH the coins table AND the offers table.

        Strategy:
          1. Check coins table for locked coins (populated by lock_coin() calls)
          2. ALWAYS also check the offers table for open offers
          3. Use whichever source reports MORE locked coins (handles the case where
             the coins table hasn't been populated yet for pre-existing offers)

        This hybrid approach ensures:
          - New offers (created with the coins table code) use coins-table data
          - Old offers (from before coins table existed) still show as locked
          - On restart, locked counts are correct immediately
        """
        try:
            # ---- Source 1: Coins table ----
            coins_xch_locked = 0
            coins_xch_locked_mojos = 0
            coins_cat_locked = 0
            coins_cat_locked_mojos = 0
            try:
                from database import get_coin_summary
                summary = get_coin_summary()
                coins_xch_locked = summary.get('xch_locked_count', 0)
                coins_xch_locked_mojos = summary.get('xch_locked_mojos', 0)
                coins_cat_locked = summary.get('cat_locked_count', 0)
                coins_cat_locked_mojos = summary.get('cat_locked_mojos', 0)
            except Exception as e:
                log_event("warning", "coin_summary_fetch_failed",
                          f"Coin summary DB fetch failed (locked counts will be zero): {e}")

            # ---- Source 2: Offers table (always check) ----
            from database import get_open_offers
            open_offers = get_open_offers(cat_asset_id=cfg.CAT_ASSET_ID)

            buy_offers = [o for o in open_offers if o.get("side") == "buy"]
            offers_xch_locked = len(buy_offers)
            offers_xch_locked_mojos = 0
            for o in buy_offers:
                try:
                    size_xch = Decimal(str(o.get("size_xch", 0)))
                    offers_xch_locked_mojos += int(size_xch * Decimal("1000000000000"))
                except Exception as e:
                    log_event("debug", "buy_offer_mojo_calc_failed",
                              f"XCH locked mojo calc failed for offer {o.get('trade_id','?')[:12]}: {e}")

            sell_offers = [o for o in open_offers if o.get("side") == "sell"]
            offers_cat_locked = len(sell_offers)
            offers_cat_locked_mojos = 0
            cat_scale = Decimal(10) ** Decimal(cfg.CAT_DECIMALS)
            for o in sell_offers:
                try:
                    size_cat = Decimal(str(o.get("size_cat", 0)))
                    offers_cat_locked_mojos += int(size_cat * cat_scale)
                except Exception as e:
                    log_event("debug", "sell_offer_mojo_calc_failed",
                              f"CAT locked mojo calc failed for offer {o.get('trade_id','?')[:12]}: {e}")

            # ---- Use the OFFERS table as the authoritative source ----
            # The offers table knows exactly which side each offer locks:
            #   buy offers lock XCH coins, sell offers lock CAT coins.
            # The coins table may be inflated because Sage's "non-selectable"
            # includes coins on BOTH sides of an offer, not just the offered side.
            # Fall back to coins table only if offers table is empty (shouldn't happen).
            self._xch_locked_coins = offers_xch_locked if offers_xch_locked > 0 else coins_xch_locked
            self._xch_locked_amount = offers_xch_locked_mojos if offers_xch_locked > 0 else coins_xch_locked_mojos
            self._cat_locked_coins = offers_cat_locked if offers_cat_locked > 0 else coins_cat_locked
            self._cat_locked_amount = offers_cat_locked_mojos if offers_cat_locked > 0 else coins_cat_locked_mojos

            # Total = free (from RPC) + locked
            self._xch_total_coins = len(xch_spendable) + self._xch_locked_coins
            self._cat_total_coins = len(cat_spendable) + self._cat_locked_coins

        except Exception as e:
            log_event("warning", "locked_coin_count_failed",
                      f"Failed to count locked coins: {e}")

    def get_inventory_summary(self) -> Dict:
        """Get a human-readable summary of the coin inventory."""
        xch_inv = self._xch_inventory
        cat_inv = self._cat_inventory

        xch_reserve_total = sum(_coin_amount(r) for r in xch_inv.get("reserve", []))
        cat_reserve_total = sum(_coin_amount(r) for r in cat_inv.get("reserve", []))
        xch_small_total = sum(_coin_amount(r) for r in xch_inv.get("small", []))
        cat_small_total = sum(_coin_amount(r) for r in cat_inv.get("small", []))

        summary = {
            "xch_reserve": len(xch_inv.get("reserve", [])),
            "xch_reserve_total": _format_amount_xch(xch_reserve_total),
            "xch_small": len(xch_inv.get("small", [])),
            "xch_small_total": _format_amount_xch(xch_small_total),
            "cat_reserve": len(cat_inv.get("reserve", [])),
            "cat_reserve_total": _format_amount_cat(cat_reserve_total, cfg.CAT_DECIMALS),
            "cat_small": len(cat_inv.get("small", [])),
            "cat_small_total": _format_amount_cat(cat_small_total, cfg.CAT_DECIMALS),
            "tier_enabled": cfg.TIER_ENABLED,
        }

        if cfg.TIER_ENABLED:
            # Tier-aware: show per-tier counts
            tier_names = self._configured_tier_names()
            for tier in tier_names:
                summary[f"xch_{tier}"] = len(xch_inv.get(tier, []))
                summary[f"cat_{tier}"] = len(cat_inv.get(tier, []))
            summary["xch_fees"] = len(xch_inv.get("fees", []))
            summary["cat_fees"] = len(cat_inv.get("fees", []))
            # Total trading = sum of all tier buckets
            summary["xch_trading"] = sum(summary[f"xch_{t}"] for t in tier_names)
            summary["cat_trading"] = sum(summary[f"cat_{t}"] for t in tier_names)
        else:
            summary["xch_trading"] = len(xch_inv.get("trading", []))
            summary["cat_trading"] = len(cat_inv.get("trading", []))
            summary["xch_fees"] = 0
            summary["cat_fees"] = 0

        # Locked coin data — coins held in active offers
        summary["xch_locked_coins"] = self._xch_locked_coins
        summary["xch_locked_amount"] = _format_amount_xch(self._xch_locked_amount)
        summary["xch_locked_amount_raw"] = self._xch_locked_amount
        summary["cat_locked_coins"] = self._cat_locked_coins
        summary["cat_locked_amount"] = _format_amount_cat(self._cat_locked_amount, cfg.CAT_DECIMALS)
        summary["cat_locked_amount_raw"] = self._cat_locked_amount
        summary["xch_total_coins"] = self._xch_total_coins
        summary["cat_total_coins"] = self._cat_total_coins

        return summary

    def get_free_coin_counts(self, active_buy_count: int = 0,
                              active_sell_count: int = 0) -> Dict[str, int]:
        """Get truly free coins (spendable minus active offers).

        Includes active reservation totals as informational fields so callers
        and the GUI can see how much capacity is currently reserved by
        in-flight offer creation attempts across threads.
        """
        free_xch = max(0, self._xch_coins - active_buy_count)
        free_cat = max(0, self._cat_coins - active_sell_count)

        # Fetch active reservation totals (mojos held by in-flight creates).
        # Fail-open: reservation data is additive, not critical path.
        reserved_xch_mojos = 0
        reserved_cat_mojos = 0
        try:
            from reservation_manager import ReservationManager as _RM
            _totals = _RM().get_reserved_totals()
            reserved_xch_mojos = _totals.get("xch", 0)
            reserved_cat_mojos = _totals.get("cat", 0)
        except Exception:
            pass

        return {
            "xch_spendable": self._xch_coins,
            "cat_spendable": self._cat_coins,
            "xch_free": free_xch,
            "cat_free": free_cat,
            "active_buy": active_buy_count,
            "active_sell": active_sell_count,
            # Active reservation amounts (in mojos) — informational only.
            # These represent capacity held by in-flight offer creation threads.
            "reserved_xch_mojos": reserved_xch_mojos,
            "reserved_cat_mojos": reserved_cat_mojos,
        }

    def coin_readiness_report(self) -> Dict:
        """Produce a detailed coin readiness report showing per-tier availability
        vs requirements. Called at startup so the bot knows exactly what coins
        are available before creating any offers.

        Returns a dict with:
          - per-tier status (available, needed, active_slots, spare, status)
          - overall_ready: True if all tiers have enough coins for active offers
          - overall_status: "READY", "LOW_SPARES", or "CRITICAL"
        """
        report = {"tiers": {}, "overall_ready": True, "overall_status": "READY"}

        if not cfg.TIER_ENABLED:
            # Non-tiered: simple check
            xch_trading = len(self._xch_inventory.get("trading", []))
            cat_trading = len(self._cat_inventory.get("trading", []))
            target_xch = cfg.MAX_ACTIVE_BUY_OFFERS if cfg.ENABLE_BUY else 0
            target_cat = cfg.MAX_ACTIVE_SELL_OFFERS if cfg.ENABLE_SELL else 0
            report["xch_trading"] = xch_trading
            report["cat_trading"] = cat_trading
            report["xch_needed"] = target_xch
            report["cat_needed"] = target_cat
            if xch_trading < target_xch or cat_trading < target_cat:
                report["overall_ready"] = False
                report["overall_status"] = "LOW"
            log_event("info", "coin_readiness",
                      f"COIN READINESS: XCH {xch_trading}/{target_xch} trading, "
                      f"CAT {cat_trading}/{target_cat} trading — "
                      f"Status: {report['overall_status']}")
            return report

        # ---- Tiered readiness ----
        max_per_side = max(
            getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25),
            getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25))
        tier_dist = get_tier_distribution(max_per_side)
        multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0"))
        prepared_counts = get_weighted_tier_prep_counts(max_per_side, multiplier)

        any_critical = False
        any_low = False

        for tier_name in ["inner", "mid", "outer", "extreme"]:
            slots_per_side = tier_dist.get(tier_name, 0)

            # XCH coins are for BUY offers, CAT coins are for SELL offers
            # So each asset only needs slots_per_side, NOT doubled
            xch_needed = slots_per_side if cfg.ENABLE_BUY else 0
            cat_needed = slots_per_side if cfg.ENABLE_SELL else 0
            xch_target = int(prepared_counts.get(tier_name, 0) or 0) if cfg.ENABLE_BUY else 0
            cat_target = int(prepared_counts.get(tier_name, 0) or 0) if cfg.ENABLE_SELL else 0
            xch_spare = xch_target - xch_needed
            cat_spare = cat_target - cat_needed
            active_needed = xch_needed + cat_needed  # Total for summary

            xch_have = len(self._xch_inventory.get(tier_name, []))
            cat_have = len(self._cat_inventory.get(tier_name, []))

            # Status per asset — compare each to its own needed count
            xch_status = "READY" if xch_have >= xch_needed else ("LOW" if xch_have > 0 else "EMPTY")
            cat_status = "READY" if cat_have >= cat_needed else ("LOW" if cat_have > 0 else "EMPTY")
            # Mark as ready if that side is disabled
            if not cfg.ENABLE_BUY:
                xch_status = "READY"
            if not cfg.ENABLE_SELL:
                cat_status = "READY"

            # Spare buffer remaining
            xch_spare_remaining = max(0, xch_have - xch_needed)
            cat_spare_remaining = max(0, cat_have - cat_needed)

            tier_info = {
                "slots_per_side": slots_per_side,
                "active_needed": active_needed,
                "total_prepped": xch_target + cat_target,
                "spare_target": xch_spare + cat_spare,
                "xch_available": xch_have,
                "xch_needed": xch_needed,
                "cat_available": cat_have,
                "cat_needed": cat_needed,
                "xch_spare_remaining": xch_spare_remaining,
                "cat_spare_remaining": cat_spare_remaining,
                "xch_status": xch_status,
                "cat_status": cat_status,
            }
            report["tiers"][tier_name] = tier_info

            if xch_status == "EMPTY" or cat_status == "EMPTY":
                any_critical = True
            elif xch_status == "LOW" or cat_status == "LOW":
                any_low = True

            log_event("info", "coin_readiness",
                      f"  {tier_name.upper():>8}: "
                      f"XCH {xch_have:>3}/{xch_needed} [{xch_status}] | "
                      f"CAT {cat_have:>3}/{cat_needed} [{cat_status}] | "
                      f"Spares: XCH {xch_spare_remaining}, CAT {cat_spare_remaining}")

        if self._sniper_pool_enabled():
            sniper_target = int(getattr(cfg, "SNIPER_PREP_COUNT", 0) or 0)
            sniper_xch_have = len(self._xch_inventory.get("sniper", []))
            sniper_cat_have = len(self._cat_inventory.get("sniper", []))
            sniper_xch_needed = sniper_target if cfg.ENABLE_BUY else 0
            # Snipers are XCH-only (opportunistic buys) — no CAT sniper coins needed
            sniper_cat_needed = 0
            sniper_xch_status = "READY" if sniper_xch_have >= sniper_xch_needed else ("LOW" if sniper_xch_have > 0 else "EMPTY")
            sniper_cat_status = "READY" if sniper_cat_have >= sniper_cat_needed else ("LOW" if sniper_cat_have > 0 else "EMPTY")
            report["tiers"]["sniper"] = {
                "slots_per_side": 0,
                "active_needed": 0,
                "total_prepped": sniper_target * 2,
                "spare_target": sniper_target * 2,
                "xch_available": sniper_xch_have,
                "xch_needed": sniper_xch_needed,
                "cat_available": sniper_cat_have,
                "cat_needed": sniper_cat_needed,
                "xch_spare_remaining": sniper_xch_have,
                "cat_spare_remaining": sniper_cat_have,
                "xch_status": sniper_xch_status if cfg.ENABLE_BUY else "READY",
                "cat_status": sniper_cat_status if cfg.ENABLE_SELL else "READY",
            }
            if (cfg.ENABLE_BUY and sniper_xch_status == "EMPTY") or (cfg.ENABLE_SELL and sniper_cat_status == "EMPTY"):
                any_critical = True
            elif (cfg.ENABLE_BUY and sniper_xch_status == "LOW") or (cfg.ENABLE_SELL and sniper_cat_status == "LOW"):
                any_low = True
            log_event("info", "coin_readiness",
                      f"  {'SNIPER':>8}: "
                      f"XCH {sniper_xch_have:>3}/{sniper_xch_needed} [{sniper_xch_status}] | "
                      f"CAT {sniper_cat_have:>3}/{sniper_cat_needed} [{sniper_cat_status}] | "
                      f"Dedicated pool")

        if self._fee_pool_enabled():
            fee_target = get_fee_pool_count()
            fee_have = len(self._xch_inventory.get("fees", []))
            fee_status = "READY" if fee_have >= fee_target else ("LOW" if fee_have > 0 else "EMPTY")
            report["tiers"]["fees"] = {
                "slots_per_side": 0,
                "active_needed": 0,
                "total_prepped": fee_target,
                "spare_target": fee_target,
                "xch_available": fee_have,
                "xch_needed": fee_target,
                "cat_available": 0,
                "cat_needed": 0,
                "xch_spare_remaining": fee_have,
                "cat_spare_remaining": 0,
                "xch_status": fee_status,
                "cat_status": "READY",
            }
            if fee_status == "EMPTY":
                any_critical = True
            elif fee_status == "LOW":
                any_low = True
            log_event(
                "info",
                "coin_readiness",
                f"  {'FEES':>8}: XCH {fee_have:>3}/{fee_target} [{fee_status}] | "
                f"Fee coins at {str(get_fee_coin_size_xch())} XCH each",
            )

        if any_critical:
            report["overall_ready"] = False
            report["overall_status"] = "CRITICAL"
        elif any_low:
            report["overall_ready"] = False
            report["overall_status"] = "LOW_SPARES"

        # Summary line
        total_xch = sum(t["xch_available"] for t in report["tiers"].values())
        total_cat = sum(t["cat_available"] for t in report["tiers"].values())
        total_needed = sum(t["active_needed"] for t in report["tiers"].values())
        total_target = sum(t["total_prepped"] for t in report["tiers"].values())

        log_event("info", "coin_readiness",
                  f"COIN READINESS: {total_xch} XCH + {total_cat} CAT trading coins | "
                  f"Active slots: {total_needed} | Target (with spares): {total_target} | "
                  f"Multiplier: {multiplier}x | Status: {report['overall_status']}")

        return report

    def log_inventory(self, reason: str = "periodic"):
        """Log the current coin inventory to the console/SSE.

        Args:
            reason: What triggered this log — used to tag the event so we
                    can see the coin state at every stage of the lifecycle.
                    Values: 'startup', 'offer_created', 'offer_cancelled',
                            'offer_filled', 'coin_prep', 'topup', 'periodic'
        """
        inv = self.get_inventory_summary()

        # Locked coin summary line (always shown)
        locked_line = (
            f" || LOCKED: XCH {inv.get('xch_locked_coins', 0)} coins "
            f"({inv.get('xch_locked_amount', '0')}), "
            f"CAT {inv.get('cat_locked_coins', 0)} coins "
            f"({inv.get('cat_locked_amount', '0')})"
        )

        if inv.get("tier_enabled"):
            # V3: Show per-tier spare counts from designation system
            xch_spares = self._tier_spares.get("xch", {})
            cat_spares = self._tier_spares.get("cat", {})
            pace = self.get_trading_pace()

            xch_tier_detail = " | ".join(
                f"{t}: {inv.get(f'xch_{t}', 0)} total, {xch_spares.get(t, 0)} spare"
                for t in self._configured_tier_names())
            cat_tier_detail = " | ".join(
                f"{t}: {inv.get(f'cat_{t}', 0)} total, {cat_spares.get(t, 0)} spare"
                for t in self._configured_tier_names())
            fee_detail = ""
            if self._fee_pool_enabled():
                fee_detail = f" | fees: {inv.get('xch_fees', 0)} total, {xch_spares.get('fees', 0)} spare"

            log_event("info", "coin_inventory",
                      f"[{reason.upper()}] XCH: reserve={inv['xch_reserve']} "
                      f"({inv['xch_reserve_total']} XCH) | {xch_tier_detail}{fee_detail} | "
                      f"dust={inv['xch_small']} | "
                      f"CAT: reserve={inv['cat_reserve']} | {cat_tier_detail} | "
                      f"dust={inv['cat_small']} | pace={pace}"
                      f"{locked_line}")
        else:
            log_event("info", "coin_inventory",
                      f"[{reason.upper()}] FREE — "
                      f"XCH: {inv['xch_reserve']} reserve ({inv['xch_reserve_total']} XCH), "
                      f"{inv['xch_trading']} trading, {inv['xch_small']} small ({inv['xch_small_total']} XCH) | "
                      f"CAT: {inv['cat_reserve']} reserve ({inv['cat_reserve_total']}), "
                      f"{inv['cat_trading']} trading, {inv['cat_small']} small ({inv['cat_small_total']})"
                      f"{locked_line}")

    def snapshot_coins(self, reason: str = "check") -> Dict:
        """Take a fresh coin snapshot, classify, and log with reason tag.

        This is the main entry point for lifecycle tracking — call it
        whenever something happens that changes the coin state:
          - Bot startup → snapshot_coins("startup")
          - After creating offers → snapshot_coins("offer_created")
          - After detecting fills → snapshot_coins("offer_filled")
          - After cancelling offers → snapshot_coins("offer_cancelled")
          - After coin prep/topup → snapshot_coins("coin_prep")

        Detects and logs which specific coins appeared or disappeared since
        the last snapshot, giving full visibility into coin state changes.

        Returns the inventory summary dict.
        """
        # Don't re-scan during active topup/prep (would interfere)
        if not (self._prep_running or self._topup_running):
            self.update_coin_counts()

        # --- Coin change detection ---
        self._detect_coin_changes(reason)

        self.log_inventory(reason=reason)
        return self.get_inventory_summary()

    def _detect_coin_changes(self, reason: str):
        """Compare current coin IDs to previous snapshot and log changes.

        Tracks which coins were created (new IDs) and destroyed (missing IDs)
        since the last call. This gives full visibility into the UTXO lifecycle.
        """
        # Build current coin ID sets
        current_xch_ids = set()
        current_cat_ids = set()

        for category, records in self._xch_inventory.items():
            for rec in records:
                coin_id = _coin_id_from_record(rec)
                if coin_id:
                    current_xch_ids.add(coin_id)

        for category, records in self._cat_inventory.items():
            for rec in records:
                coin_id = _coin_id_from_record(rec)
                if coin_id:
                    current_cat_ids.add(coin_id)

        # Compare to previous snapshot
        if hasattr(self, '_prev_xch_coin_ids') and self._prev_xch_coin_ids is not None:
            new_xch = current_xch_ids - self._prev_xch_coin_ids
            gone_xch = self._prev_xch_coin_ids - current_xch_ids

            if new_xch or gone_xch:
                log_event("info", "coin_state_change",
                          f"[{reason.upper()}] XCH coins: "
                          f"+{len(new_xch)} new, -{len(gone_xch)} removed "
                          f"(was {len(self._prev_xch_coin_ids)}, now {len(current_xch_ids)})")

                # Log individual new coins (up to 5)
                for i, cid in enumerate(list(new_xch)[:5]):
                    log_event("debug", "coin_created",
                              f"  NEW XCH coin: {cid[:20]}...")
                if len(new_xch) > 5:
                    log_event("debug", "coin_created",
                              f"  ... and {len(new_xch) - 5} more new XCH coins")

        if hasattr(self, '_prev_cat_coin_ids') and self._prev_cat_coin_ids is not None:
            new_cat = current_cat_ids - self._prev_cat_coin_ids
            gone_cat = self._prev_cat_coin_ids - current_cat_ids

            if new_cat or gone_cat:
                log_event("info", "coin_state_change",
                          f"[{reason.upper()}] CAT coins: "
                          f"+{len(new_cat)} new, -{len(gone_cat)} removed "
                          f"(was {len(self._prev_cat_coin_ids)}, now {len(current_cat_ids)})")

                for i, cid in enumerate(list(new_cat)[:5]):
                    log_event("debug", "coin_created",
                              f"  NEW CAT coin: {cid[:20]}...")
                if len(new_cat) > 5:
                    log_event("debug", "coin_created",
                              f"  ... and {len(new_cat) - 5} more new CAT coins")

        # Save for next comparison
        self._prev_xch_coin_ids = current_xch_ids
        self._prev_cat_coin_ids = current_cat_ids

    # -------------------------------------------------------------------
    # Coin prep threshold checks
    # -------------------------------------------------------------------

    def needs_coin_prep(self, active_buy_count: int = 0,
                        active_sell_count: int = 0) -> bool:
        """Check if FULL coin prep needed (total coins critically low).

        Target is calculated dynamically — same logic as start_coin_prep() —
        so the 10% threshold is always relative to what was actually prepped,
        not a stale XCH_TARGET_COINS value from .env (which Smart Defaults
        never updates).
        """
        if not cfg.ENABLE_COIN_PREP:
            return False
        if self._prep_running or self._topup_running:
            return False

        est_xch_total = self._xch_coins + active_buy_count
        est_cat_total = self._cat_coins + active_sell_count

        # --- Dynamic target: mirrors start_coin_prep() logic ---
        max_buy = int(getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25))
        max_sell = int(getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25))
        multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", 1.0)
        if cfg.TIER_ENABLED:
            max_per_side = max(max_buy, max_sell)
            tier_counts = get_weighted_tier_prep_counts(max_per_side, multiplier)
            target_xch = max(cfg.XCH_TARGET_COINS, sum(tier_counts.values()))
            target_cat = target_xch  # symmetric: CAT mirrors XCH total
        else:
            computed = int((max_buy + max_sell) * float(multiplier))
            computed = max(computed, max_buy + max_sell)
            # Fall back to cfg value if it's larger (user may have over-ridden)
            target_xch = max(cfg.XCH_TARGET_COINS, computed)
            target_cat = max(cfg.CAT_TARGET_COINS, computed)

        needs_xch = est_xch_total < int(target_xch * 0.1) if target_xch > 0 else False
        needs_cat = est_cat_total < int(target_cat * 0.1) if target_cat > 0 else False

        if needs_xch or needs_cat:
            log_event("warning", "low_coins_total",
                      f"LOW COINS! XCH: {self._xch_coins} spendable + {active_buy_count} in offers = "
                      f"{est_xch_total}/{target_xch}, CAT: {self._cat_coins} spendable + "
                      f"{active_sell_count} in offers = {est_cat_total}/{target_cat}")
        return needs_xch or needs_cat

    def needs_topup(self, active_buy_count: int = 0,
                    active_sell_count: int = 0) -> bool:
        """Check if live coin top-up should run (free coins low).

        V3 ADAPTIVE: Uses trading pace to adjust the trigger threshold.
        Busy market → trigger earlier (50% spares). Slow → later (20%).
        """
        if self._topup_running or self._prep_running:
            return False

        # Cooldown — exponential when no coins are available
        if self._no_coins_backoff:
            cooldown = min(
                _TOPUP_BACKOFF_MAX,
                _TOPUP_BACKOFF_BASE * (2 ** self._no_coins_backoff_count),
            )
        else:
            cooldown = _TOPUP_COOLDOWN
        if time.time() - self._last_topup_time < cooldown:
            return False

        # V3: Adaptive spare threshold based on trading pace
        pace = self.get_trading_pace()
        if pace == 'busy':
            spare_keep_pct = getattr(cfg, "TOPUP_BUSY_PCT", 50) / 100.0
        elif pace == 'slow':
            spare_keep_pct = getattr(cfg, "TOPUP_SLOW_PCT", 20) / 100.0
        else:
            spare_keep_pct = getattr(cfg, "TOPUP_NORMAL_PCT", 30) / 100.0

        multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0"))

        if cfg.TIER_ENABLED:
            # V3: Check per-tier spare counts from DB designations
            needs_any = False
            max_per_side = max(
                getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25),
                getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25))
            tier_dist = get_tier_distribution(max_per_side)
            prepared_counts = get_weighted_tier_prep_counts(max_per_side, multiplier)

            for tier_name, slots in tier_dist.items():
                # slots = offers per side for this tier
                # XCH coins serve buy offers, CAT coins serve sell offers
                # So each wallet type needs `slots` active coins (NOT doubled)
                per_side_prepped = int(prepared_counts.get(tier_name, 0) or 0)
                per_side_spare = per_side_prepped - slots  # spares per wallet type

                # Current spares from DB (only free tier_spare coins)
                xch_spares_now = self._tier_spares.get("xch", {}).get(tier_name, 0)
                cat_spares_now = self._tier_spares.get("cat", {}).get(tier_name, 0)

                # Threshold: trigger when spares drop below pace-adjusted %
                spare_threshold = max(1, int(per_side_spare * spare_keep_pct))

                if (xch_spares_now < spare_threshold and cfg.ENABLE_BUY) or \
                   (cat_spares_now < spare_threshold and cfg.ENABLE_SELL):
                    needs_any = True
                    break

            if not needs_any and self._sniper_pool_enabled():
                sniper_target = int(getattr(cfg, "SNIPER_PREP_COUNT", 0) or 0)
                sniper_threshold = max(1, int(sniper_target * spare_keep_pct))
                sniper_xch_now = self._tier_spares.get("xch", {}).get("sniper", 0)
                sniper_cat_now = self._tier_spares.get("cat", {}).get("sniper", 0)
                if (cfg.ENABLE_BUY and sniper_xch_now < sniper_threshold) or \
                   (cfg.ENABLE_SELL and sniper_cat_now < sniper_threshold):
                    needs_any = True

            if not needs_any and self._fee_pool_enabled():
                fee_target = get_fee_pool_count()
                fee_threshold = max(1, int(fee_target * spare_keep_pct))
                fee_xch_now = self._tier_spares.get("xch", {}).get("fees", 0)
                if fee_xch_now < fee_threshold:
                    needs_any = True

            if needs_any:
                log_event("warning", "low_coins_adaptive",
                          f"Tier spares below {spare_keep_pct*100:.0f}% threshold "
                          f"(pace={pace}). XCH spares: {self._tier_spares.get('xch', {})}, "
                          f"CAT spares: {self._tier_spares.get('cat', {})}")
            return needs_any
        else:
            # Non-tiered: original logic with adaptive threshold
            free_xch = max(0, self._xch_coins - active_buy_count)
            free_cat = max(0, self._cat_coins - active_sell_count)

            xch_spare = int(cfg.MAX_ACTIVE_BUY_OFFERS * multiplier)
            cat_spare = int(cfg.MAX_ACTIVE_SELL_OFFERS * multiplier)
            target_free_xch = max(3, int(xch_spare * spare_keep_pct))
            target_free_cat = max(2, int(cat_spare * spare_keep_pct))

            needs_xch = free_xch < target_free_xch and cfg.ENABLE_BUY
            needs_cat = free_cat < target_free_cat and cfg.ENABLE_SELL

            if needs_xch or needs_cat:
                log_event("warning", "low_coins_free",
                          f"Low FREE coins! XCH: {free_xch} free (threshold {target_free_xch}), "
                          f"CAT: {free_cat} free (threshold {target_free_cat}) "
                          f"[pace={pace}, spare buffer at {spare_keep_pct*100:.0f}%, "
                          f"multiplier={multiplier}x]")
            return needs_xch or needs_cat

    def check_runtime_health(self, active_buy_count: int = 0,
                              active_sell_count: int = 0) -> bool:
        """Runtime coin health check — every 5 loops, independent."""
        if not getattr(cfg, "ENABLE_RUNTIME_COIN_HEALTH", False):
            return False
        if self._topup_running or self._prep_running:
            return False

        self._health_check_counter += 1
        if self._health_check_counter % 5 != 0:
            return False

        free_xch = max(0, self._xch_coins - active_buy_count)
        free_cat = max(0, self._cat_coins - active_sell_count)
        # Same spare-aware threshold as needs_topup()
        multiplier = float(getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0")))
        xch_spare = int(cfg.MAX_ACTIVE_BUY_OFFERS * multiplier)
        cat_spare = int(cfg.MAX_ACTIVE_SELL_OFFERS * multiplier)
        target_free_xch = max(3, int(xch_spare * 0.2))
        target_free_cat = max(2, int(cat_spare * 0.2))

        needs_xch = free_xch < target_free_xch and cfg.ENABLE_BUY
        needs_cat = free_cat < target_free_cat and cfg.ENABLE_SELL

        if needs_xch or needs_cat:
            cooldown = min(_TOPUP_BACKOFF_MAX, _TOPUP_BACKOFF_BASE * (2 ** self._no_coins_backoff_count)) if self._no_coins_backoff else _TOPUP_COOLDOWN
            if time.time() - self._last_topup_time < cooldown:
                if time.time() - self._last_low_coin_warning > 600:
                    remaining = int((cooldown - (time.time() - self._last_topup_time)) / 60)
                    log_event("warning", "coin_health_cooldown",
                              f"Low coins but topup on cooldown ({remaining}m remaining)")
                    self._last_low_coin_warning = time.time()
                return False

            log_event("warning", "coin_health_trigger",
                      f"[COIN HEALTH] XCH: {free_xch} free (need {target_free_xch}), "
                      f"CAT: {free_cat} free (need {target_free_cat})")
            return True

        if self._health_check_counter % 50 == 0:
            log_event("debug", "coin_health_ok",
                      f"Coin health OK: XCH={free_xch} free, CAT={free_cat} free")
        return False

    # -------------------------------------------------------------------
    # Live coin top-up (background thread)
    # -------------------------------------------------------------------

    def start_topup(self, active_buy_count: int = 0,
                    active_sell_count: int = 0) -> bool:
        """Start a live coin top-up in a background thread."""
        with self._lock:
            if self._topup_running:
                return False
            self._topup_running = True
            self._topup_stop_requested = False
        self._last_topup_time = time.time()

        self._topup_thread = threading.Thread(
            target=self._topup_worker,
            args=(active_buy_count, active_sell_count),
            daemon=True,
            name="coin-topup"
        )
        self._topup_thread.start()

        log_event("info", "topup_started",
                  "Live coin top-up started (existing offers stay active)")
        return True

    def stop_topup(self, wait_secs: float = 10.0) -> bool:
        """Request any running top-up worker to stop."""
        thread = None
        with self._lock:
            if not self._topup_running:
                return False
            self._topup_stop_requested = True
            thread = self._topup_thread
        log_event("info", "topup_stop_requested", "Stopping background coin top-up")
        if thread and thread.is_alive() and wait_secs > 0:
            thread.join(timeout=wait_secs)
        return True

    def _topup_should_stop(self) -> bool:
        """Whether a running top-up worker has been asked to stop."""
        return bool(getattr(self, "_topup_stop_requested", False))

    def _topup_worker(self, active_buy: int, active_sell: int):
        """Smart topup worker — classifies coins and decides strategy.

        Decision tree:
          1. Reserve coin exists → split it directly
          2. Many small coins → consolidate then split
          3. Nothing available → back off
        """
        try:
            self._topup_abort_logged = False
            if self._topup_should_stop():
                log_event("info", "topup_stopped", "Coin top-up stopped before work began")
                return

            # ---- Pre-check: is wallet synced? ----
            # After creating many offers rapidly, the wallet can be briefly
            # unsynced. get_spendable_coins_rpc() returns 0 during this window,
            # which would cause a false "no coins" backoff of 2 hours.
            # Wait briefly for sync before proceeding.
            wallet_ready = False
            wallet_backend = str(os.getenv("WALLET_TYPE", "sage") or "sage").strip().lower()
            for sync_attempt in range(6):  # Up to 30 seconds
                try:
                    from wallet import get_wallet_sync_status
                    sync_info = get_wallet_sync_status()
                    sync_state = str(sync_info.get("sync_state") or "").strip().lower() if sync_info else ""
                    if sync_info and sync_info.get("synced", False):
                        wallet_ready = True
                        break
                    elif (
                        wallet_backend == "sage"
                        and sync_info
                        and sync_info.get("reachable")
                        and sync_state in ("", "unknown")
                        and not sync_info.get("syncing", False)
                    ):
                        wallet_ready = True
                        break
                    else:
                        if sync_attempt == 0:
                            log_event("info", "topup_wait_sync",
                                      "Wallet not synced — waiting before topup scan...")
                        time.sleep(5)
                except Exception:
                    # get_wallet_sync_status may not exist — skip the check
                    wallet_ready = True
                    break

            if not wallet_ready:
                log_event("warning", "topup_wallet_unsynced",
                          "Wallet still not synced after 30s — short cooldown, will retry next cycle")
                self._last_topup_time = time.time()
                # DON'T set _no_coins_backoff — this is temporary, not "no coins"
                return

            # ---- Fresh coin inventory ----
            xch_result = _get_free_coins_rpc(cfg.WALLET_ID_XCH)
            cat_result = _get_free_coins_rpc(cfg.CAT_WALLET_ID)

            xch_records = _extract_coin_records(xch_result)
            cat_records = _extract_coin_records(cat_result)

            # ---- Sanity check: if we got 0 coins, wallet may still be catching up ----
            # The wallet can report synced=true but still not show coins for a few seconds
            # after creating 50+ offers. If we see 0 total coins but had active offers,
            # this is almost certainly a transient state — don't back off.
            total_records = len(xch_records) + len(cat_records)
            total_active = active_buy + active_sell
            if total_records == 0 and total_active > 0:
                log_event("info", "topup_zero_transient",
                          f"Wallet returned 0 spendable coins but {total_active} offers are active — "
                          f"wallet likely still catching up. Short cooldown, will retry.")
                self._last_topup_time = time.time()
                return

            # ---- Classify coins (V3: designation-based) ----
            if cfg.TIER_ENABLED:
                xch_tier_mojos = self._get_tier_sizes_mojos(is_cat=False)
                cat_tier_mojos = self._get_tier_sizes_mojos(is_cat=True)
                xch_inv = self._classify_coins_by_designation(xch_records, "xch", xch_tier_mojos)
                cat_inv = self._classify_coins_by_designation(cat_records, "cat", cat_tier_mojos)

                # Log tier breakdown
                tier_names = self._configured_tier_names()
                xch_tier_counts = ", ".join(
                    f"{t}={len(xch_inv.get(t, []))}" for t in tier_names)
                cat_tier_counts = ", ".join(
                    f"{t}={len(cat_inv.get(t, []))}" for t in tier_names)
                log_event("info", "topup_inventory",
                          f"Topup inventory (tiered) — "
                          f"XCH: {len(xch_inv['reserve'])} reserve, {xch_tier_counts}, "
                          f"{len(xch_inv['small'])} small | "
                          f"CAT: {len(cat_inv['reserve'])} reserve, {cat_tier_counts}, "
                          f"{len(cat_inv['small'])} small")
            else:
                xch_trading_mojos = int(self.get_target_xch_coin_size() * Decimal("1000000000000"))
                cat_scale = Decimal(10) ** Decimal(cfg.CAT_DECIMALS)
                cat_trading_mojos = int(self.get_target_cat_coin_size() * cat_scale)
                xch_inv = _classify_coins(xch_records, xch_trading_mojos)
                cat_inv = _classify_coins(cat_records, cat_trading_mojos)

                log_event("info", "topup_inventory",
                          f"Topup inventory — "
                          f"XCH: {len(xch_inv['reserve'])} reserve, {len(xch_inv['trading'])} trading, "
                          f"{len(xch_inv['small'])} small | "
                          f"CAT: {len(cat_inv['reserve'])} reserve, {len(cat_inv['trading'])} trading, "
                          f"{len(cat_inv['small'])} small")

            did_anything = False

            if cfg.TIER_ENABLED:
                # ---- Tier-aware topup: check each tier ----
                max_per_side = max(
                    getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25),
                    getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25))
                tier_dist = get_tier_distribution(max_per_side)
                # tier_dist gives slots per side per tier.
                # XCH coins serve buy offers, CAT coins serve sell offers.
                # So each wallet type needs `slots` coins (per side), NOT doubled.

                # V3 Adaptive threshold: spare buffer % based on trading pace
                multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0"))
                pace = self.get_trading_pace()
                if pace == 'busy':
                    spare_keep_pct = getattr(cfg, "TOPUP_BUSY_PCT", 50) / 100.0
                elif pace == 'slow':
                    spare_keep_pct = getattr(cfg, "TOPUP_SLOW_PCT", 20) / 100.0
                else:
                    spare_keep_pct = getattr(cfg, "TOPUP_NORMAL_PCT", 30) / 100.0

                xch_scale = Decimal("1000000000000")
                cat_scale_dec = Decimal(10) ** Decimal(cfg.CAT_DECIMALS)
                live_tier_sizes_xch = self._configured_tier_sizes_xch()
                prepared_counts = get_weighted_tier_prep_counts(
                    max_per_side,
                    multiplier,
                    tier_sizes_xch=live_tier_sizes_xch,
                )

                for tier_name in ["inner", "mid", "outer", "extreme"]:
                    if self._topup_should_stop():
                        log_event("info", "topup_stopped", "Coin top-up stopped during tier replenishment")
                        return
                    slots_per_side = tier_dist.get(tier_name, 0)
                    if slots_per_side == 0:
                        continue

                    # Runtime top-up replenishes free spare inventory only.
                    per_side_prepped = int(prepared_counts.get(tier_name, 0) or 0)
                    spare_allocation = per_side_prepped - slots_per_side
                    if spare_allocation <= 0:
                        continue
                    topup_threshold = max(1, int(spare_allocation * spare_keep_pct))

                    # XCH: check if this tier needs coins (XCH = buy side)
                    xch_have = len(xch_inv.get(tier_name, []))
                    if xch_have < topup_threshold and cfg.ENABLE_BUY:
                        xch_tier_size = int(live_tier_sizes_xch.get(tier_name, cfg.MID_SIZE_XCH) * xch_scale)
                        target_full = spare_allocation
                        # Buffer: 25% of spare allocation, min 1, max 2.
                        # Scales with tier depth rather than being flat +2 for all
                        # tiers (flat +2 over-splits small-spare tiers like outer/extreme).
                        _buf = max(1, min(2, int(spare_allocation * 0.25)))
                        deficit = max(0, target_full - xch_have) + _buf
                        log_event("info", f"topup_xch_{tier_name}",
                                  f"XCH {tier_name} tier low: {xch_have}/{topup_threshold} threshold "
                                  f"(target {target_full}) — "
                                  f"need {deficit} at {_format_amount_xch(xch_tier_size)} each")
                        result = self._smart_topup_wallet(
                            f"XCH-{tier_name}", cfg.WALLET_ID_XCH,
                            xch_inv, xch_tier_size, deficit,
                            is_cat=False
                        )
                        if result:
                            did_anything = True
                        # Always re-fetch after a split attempt (success or fail).
                        # Prevents next tier from trying the same locked coin.
                        time.sleep(3)
                        fresh = _get_free_coins_rpc(cfg.WALLET_ID_XCH)
                        fresh_records = _extract_coin_records(fresh)
                        xch_inv = self._classify_coins_by_designation(fresh_records, "xch", self._get_tier_sizes_mojos(is_cat=False))

                    # CAT: check if this tier needs coins (CAT = sell side)
                    cat_have = len(cat_inv.get(tier_name, []))
                    if cat_have < topup_threshold and cfg.ENABLE_SELL:
                        cat_tier_mojos_val = self._get_tier_sizes_mojos(is_cat=True).get(tier_name, 0)
                        if cat_tier_mojos_val > 0:
                            target_full = spare_allocation
                            _buf = max(1, min(2, int(spare_allocation * 0.25)))
                            deficit = max(0, target_full - cat_have) + _buf
                            cat_size_display = _format_amount_cat(cat_tier_mojos_val, cfg.CAT_DECIMALS)
                            log_event("info", f"topup_cat_{tier_name}",
                                      f"CAT {tier_name} tier low: {cat_have}/{topup_threshold} threshold "
                                      f"(target {target_full}) — "
                                      f"need {deficit} at {cat_size_display} each")
                            # For CAT, use token amount (not mojos) for split
                            xch_tier_size_dec = live_tier_sizes_xch.get(tier_name, cfg.MID_SIZE_XCH)
                            price = self._get_current_price()
                            if price and price > 0:
                                cat_token_size = int((
                                    xch_tier_size_dec
                                    / price
                                    * self._get_coin_prep_headroom_multiplier()
                                ).quantize(Decimal("1")))
                            else:
                                cat_token_size = int(cfg.CAT_COIN_SIZE)

                            result = self._smart_topup_wallet(
                                f"CAT-{tier_name}", cfg.CAT_WALLET_ID,
                                cat_inv, cat_tier_mojos_val, deficit,
                                is_cat=True, cat_token_amount=cat_token_size
                            )
                            if result:
                                did_anything = True
                            # Always re-fetch after a split attempt (success or fail).
                            # If it failed, the reserve coin may be locked from the
                            # attempt — without refreshing, the next tier would try
                            # the same locked coin and fail again.
                            time.sleep(3)
                            fresh = _get_free_coins_rpc(cfg.CAT_WALLET_ID)
                            fresh_records = _extract_coin_records(fresh)
                            cat_inv = self._classify_coins_by_designation(fresh_records, "cat", self._get_tier_sizes_mojos(is_cat=True))

                if self._sniper_pool_enabled():
                    if self._topup_should_stop():
                        log_event("info", "topup_stopped", "Coin top-up stopped during sniper replenishment")
                        return
                    sniper_target = int(getattr(cfg, "SNIPER_PREP_COUNT", 0) or 0)
                    sniper_threshold = max(1, int(sniper_target * spare_keep_pct))
                    sniper_xch_size_dec = live_tier_sizes_xch.get("sniper", Decimal("0"))
                    sniper_cat_mojos_val = self._get_tier_sizes_mojos(is_cat=True).get("sniper", 0)

                    sniper_xch_have = len(xch_inv.get("sniper", []))
                    if sniper_xch_have < sniper_threshold and cfg.ENABLE_BUY and sniper_xch_size_dec > 0:
                        sniper_xch_size = int(sniper_xch_size_dec * xch_scale)
                        deficit = (sniper_target - sniper_xch_have) + 2
                        log_event("info", "topup_xch_sniper",
                                  f"XCH sniper pool low: {sniper_xch_have}/{sniper_threshold} threshold "
                                  f"(target {sniper_target}) — need {deficit} at {_format_amount_xch(sniper_xch_size)} each")
                        result = self._smart_topup_wallet(
                            "XCH-sniper", cfg.WALLET_ID_XCH,
                            xch_inv, sniper_xch_size, deficit,
                            is_cat=False
                        )
                        if result:
                            did_anything = True
                        time.sleep(3)
                        fresh = _get_free_coins_rpc(cfg.WALLET_ID_XCH)
                        fresh_records = _extract_coin_records(fresh)
                        xch_inv = self._classify_coins_by_designation(fresh_records, "xch", self._get_tier_sizes_mojos(is_cat=False))

                    sniper_cat_have = len(cat_inv.get("sniper", []))
                    if sniper_cat_have < sniper_threshold and cfg.ENABLE_SELL and sniper_cat_mojos_val > 0:
                        deficit = (sniper_target - sniper_cat_have) + 2
                        sniper_cat_display = _format_amount_cat(sniper_cat_mojos_val, cfg.CAT_DECIMALS)
                        log_event("info", "topup_cat_sniper",
                                  f"CAT sniper pool low: {sniper_cat_have}/{sniper_threshold} threshold "
                                  f"(target {sniper_target}) — need {deficit} at {sniper_cat_display} each")
                        price = self._get_current_price()
                        if price and price > 0 and sniper_xch_size_dec > 0:
                            cat_token_size = int((
                                sniper_xch_size_dec
                                / price
                                * self._get_coin_prep_headroom_multiplier()
                            ).quantize(Decimal("1")))
                        else:
                            cat_token_size = int(cfg.CAT_COIN_SIZE)

                        result = self._smart_topup_wallet(
                            "CAT-sniper", cfg.CAT_WALLET_ID,
                            cat_inv, sniper_cat_mojos_val, deficit,
                            is_cat=True, cat_token_amount=cat_token_size
                        )
                        if result:
                            did_anything = True
                        time.sleep(3)
                        fresh = _get_free_coins_rpc(cfg.CAT_WALLET_ID)
                        fresh_records = _extract_coin_records(fresh)
                        cat_inv = self._classify_coins_by_designation(fresh_records, "cat", self._get_tier_sizes_mojos(is_cat=True))

                if self._fee_pool_enabled():
                    if self._topup_should_stop():
                        log_event("info", "topup_stopped", "Coin top-up stopped during fee replenishment")
                        return
                    fee_target = get_fee_pool_count()
                    fee_threshold = max(1, int(fee_target * spare_keep_pct))
                    fee_xch_mojos = get_fee_coin_size_mojos()
                    fee_xch_have = len(xch_inv.get("fees", []))
                    if fee_xch_have < fee_threshold and fee_xch_mojos > 0:
                        deficit = (fee_target - fee_xch_have) + 2
                        log_event(
                            "info",
                            "topup_xch_fees",
                            f"XCH fee pool low: {fee_xch_have}/{fee_threshold} threshold "
                            f"(target {fee_target}) — need {deficit} at {_format_amount_xch(fee_xch_mojos)} each",
                        )
                        result = self._smart_topup_wallet(
                            "XCH-fees", cfg.WALLET_ID_XCH,
                            xch_inv, fee_xch_mojos, deficit,
                            is_cat=False
                        )
                        if result:
                            did_anything = True
                        time.sleep(3)
                        fresh = _get_free_coins_rpc(cfg.WALLET_ID_XCH)
                        fresh_records = _extract_coin_records(fresh)
                        xch_inv = self._classify_coins_by_designation(
                            fresh_records,
                            "xch",
                            self._get_tier_sizes_mojos(is_cat=False),
                        )

            else:
                # ---- Non-tiered: original uniform topup ----
                free_xch_trading = max(0, len(xch_inv["trading"]) - active_buy)
                free_cat_trading = max(0, len(cat_inv["trading"]) - active_sell)

                target_free_xch = max(3, int(cfg.MAX_ACTIVE_BUY_OFFERS * 0.3))
                target_free_cat = max(2, int(cfg.MAX_ACTIVE_SELL_OFFERS * 0.3))

                if free_xch_trading < target_free_xch and cfg.ENABLE_BUY:
                    needed = target_free_xch - free_xch_trading + 5
                    xch_trading_mojos = int(self.get_target_xch_coin_size() * Decimal("1000000000000"))
                    xch_result = self._smart_topup_wallet(
                        "XCH", cfg.WALLET_ID_XCH,
                        xch_inv, xch_trading_mojos, needed,
                        is_cat=False
                    )
                    if xch_result:
                        did_anything = True

                if free_cat_trading < target_free_cat and cfg.ENABLE_SELL:
                    if did_anything:
                        time.sleep(5)
                    needed = target_free_cat - free_cat_trading + 3
                    cat_scale_val = Decimal(10) ** Decimal(cfg.CAT_DECIMALS)
                    cat_trading_mojos = int(self.get_target_cat_coin_size() * cat_scale_val)
                    cat_result = self._smart_topup_wallet(
                        "CAT", cfg.CAT_WALLET_ID,
                        cat_inv, cat_trading_mojos, needed,
                        is_cat=True
                    )
                    if cat_result:
                        did_anything = True

            if not did_anything:
                # Check if coins exist but are all locked in offers (normal state)
                # vs genuinely empty wallet. Only back off if truly nothing to work with.
                from wallet import get_wallet_balance
                try:
                    xch_bal = get_wallet_balance(cfg.WALLET_ID_XCH)
                    xch_total = Decimal(str(xch_bal.get("confirmed_wallet_balance", 0))) / Decimal("1000000000000")
                except Exception:
                    xch_total = Decimal("0")

                if xch_total > cfg.XCH_RESERVE + Decimal("1"):
                    # Wallet has balance — coins just locked in offers. Short cooldown.
                    self._last_topup_time = time.time()
                    log_event("info", "topup_coins_locked",
                              f"All coins locked in offers ({xch_total:.4f} XCH total in wallet) — "
                              f"will retry after fills free coins (normal state)")
                    return
                else:
                    self._no_coins_backoff = True
                    self._no_coins_backoff_count += 1
                    self._last_topup_time = time.time()
                    backoff_secs = min(
                        _TOPUP_BACKOFF_MAX,
                        _TOPUP_BACKOFF_BASE * (2 ** self._no_coins_backoff_count),
                    )
                    log_event("info", "topup_no_action",
                              f"No coins available to split or consolidate — "
                              f"backing off {backoff_secs//60:.0f} min "
                              f"(attempt {self._no_coins_backoff_count}, "
                              f"resets on fills or successful topup)")
                    return

            # Poll for confirmation
            pre_xch = len(xch_records)
            pre_cat = len(cat_records)
            self._poll_for_confirmation(pre_xch, pre_cat)

            # Success — reset cooldown and backoff counter
            self._last_topup_time = 0
            self._no_coins_backoff = False
            self._no_coins_backoff_count = 0

            # V3: Re-check reserve after topup (in case reserve was split)
            if cfg.TIER_ENABLED:
                self._ensure_reserve_exists("xch", xch_records)
                self._ensure_reserve_exists("cat", cat_records)

        except _TopupWalletDegraded:
            self._last_topup_time = time.time()
            self._no_coins_backoff = False
        except Exception as e:
            log_event("error", "topup_error", f"Topup worker error: {e}")
        finally:
            with self._lock:
                self._topup_running = False
                self._topup_stop_requested = False
            self.update_coin_counts()
            self.log_inventory()

    def _smart_topup_wallet(self, name: str, wallet_id: int,
                             inventory: Dict[str, list],
                             trading_size_mojos: int, needed: int,
                             is_cat: bool = False,
                             cat_token_amount: int = None) -> bool:
        """Smart topup for one wallet. Returns True if an action was taken.

        Two-step process (mirrors coin_prep_worker):
          Step 1: Send-to-self to create an intermediate coin of exact size
                  (num_coins × coin_size mojos)
          Step 2: Track the new coin ID via snapshot/diff, then split it

        Fallback strategies:
          Strategy 1: Use a reserve coin as the funding source
          Strategy 2: Consolidate small coins first

        Args:
            cat_token_amount: When tier-aware CAT topup, the token-unit size
                              (not mojos) for this specific tier. If None, uses
                              get_target_cat_coin_size() as before.
        """
        reserve_coins = inventory["reserve"]
        small_coins = inventory["small"]

        # ---- Strategy 1: Use a reserve coin to create trading coins ----
        if reserve_coins:
            # Re-fetch FRESH coins (IDs may be stale after other transactions)
            log_event("info", f"topup_{name.lower()}_refetch",
                      f"Re-fetching fresh {name} coins before split...")

            fresh_result = _get_free_coins_rpc(wallet_id)
            fresh_records = _extract_coin_records(fresh_result)
            # Use a loose threshold: any coin >= 1x trading_size can fund a split.
            # The old 2x threshold was too strict for the inner tier — the reserve
            # coin (e.g. 11.56 XCH) was smaller than 2 × 6.09 XCH = 12.18 XCH,
            # causing the re-fetch to see "no reserve" and silently abort.
            fresh_inv = _classify_coins(fresh_records, trading_size_mojos // 2 or 1)

            if not fresh_inv["reserve"]:
                log_event("warning", f"topup_{name.lower()}_reserve_gone",
                          f"{name} reserve coin vanished between scan and split — "
                          f"coins may have been spent. Will retry next cycle.")
                small_coins = fresh_inv["small"]
            else:
                largest = fresh_inv["reserve"][0]
                largest_amount = _coin_amount(largest)
                source_coin_id = _coin_id_from_record(largest)

                if is_cat:
                    amt_str = _format_amount_cat(largest_amount, cfg.CAT_DECIMALS)
                    size_str = _format_amount_cat(trading_size_mojos, cfg.CAT_DECIMALS)
                else:
                    amt_str = _format_amount_xch(largest_amount)
                    size_str = _format_amount_xch(trading_size_mojos)

                max_possible = largest_amount // trading_size_mojos
                num_to_create = min(needed, max_possible, 15)

                if num_to_create < 1:
                    log_event("warning", f"topup_{name.lower()}_skip",
                              f"{name} reserve coin ({amt_str}) too small for "
                              f"even 1 trading coin ({size_str})")
                else:
                    # Calculate exact intermediate coin size
                    pool_amount_mojos = num_to_create * trading_size_mojos

                    if is_cat:
                        pool_str = _format_amount_cat(pool_amount_mojos, cfg.CAT_DECIMALS)
                    else:
                        pool_str = _format_amount_xch(pool_amount_mojos)

                    log_event("info", f"topup_{name.lower()}_start",
                              f"Creating {name} pool coin ({pool_str}) from reserve "
                              f"({amt_str}) → will split into {num_to_create} × {size_str} "
                              f"[source: {source_coin_id[:12]}...]")

                    success = self._two_step_split(
                        name=name,
                        wallet_id=wallet_id,
                        source_coin_id=source_coin_id,
                        pool_amount_mojos=pool_amount_mojos,
                        num_to_create=num_to_create,
                        trading_size_mojos=trading_size_mojos,
                        is_cat=is_cat,
                    )

                    if success:
                        log_event("success", f"topup_{name.lower()}_split_ok",
                                  f"{name} topup complete: {num_to_create} new trading coins")
                        return True
                    else:
                        log_event("warning", f"topup_{name.lower()}_split_fail",
                                  f"{name} two-step split failed — will retry next cycle")
                        # Fall through to strategy 2

        # ---- Strategy 2: Consolidate small coins ----
        # Trigger with ≥2 small coins (down from 3) so price-shift misfits
        # and post-fill dust don't sit idle indefinitely with just 1–2 coins.
        if len(small_coins) >= 2:
            total_small = sum(_coin_amount(r) for r in small_coins)

            if total_small >= trading_size_mojos * 2:
                if is_cat:
                    total_str = _format_amount_cat(total_small, cfg.CAT_DECIMALS)
                else:
                    total_str = _format_amount_xch(total_small)

                log_event("info", f"topup_{name.lower()}_consolidate",
                          f"Consolidating {len(small_coins)} small {name} coins "
                          f"({total_str} total) into one coin for splitting")

                success = self._consolidate_coins(name, wallet_id, total_small, is_cat)
                if success:
                    log_event("success", f"topup_{name.lower()}_consolidate_ok",
                              f"{name} consolidation submitted — will split after confirmation")
                    return True
                else:
                    log_event("warning", f"topup_{name.lower()}_consolidate_fail",
                              f"{name} consolidation failed")
            else:
                if is_cat:
                    total_str = _format_amount_cat(total_small, cfg.CAT_DECIMALS)
                    need_str = _format_amount_cat(trading_size_mojos * 2, cfg.CAT_DECIMALS)
                else:
                    total_str = _format_amount_xch(total_small)
                    need_str = _format_amount_xch(trading_size_mojos * 2)
                log_event("info", f"topup_{name.lower()}_small_insufficient",
                          f"{len(small_coins)} small {name} coins total {total_str} "
                          f"(need at least {need_str} to consolidate)")

        log_event("info", f"topup_{name.lower()}_none",
                  f"No {name} reserve or consolidatable coins available")
        return False

    def _two_step_split(self, name: str, wallet_id: int,
                         source_coin_id: str, pool_amount_mojos: int,
                         num_to_create: int, trading_size_mojos: int,
                         is_cat: bool) -> bool:
        """Two-step coin split (mirrors coin_prep_worker approach).

        Step 1: Send exact amount to self → creates a pool coin of precise size
        Step 2: Snapshot before/after to track the new coin ID, then split it

        This is more reliable than direct split because:
        - We control the exact size of the intermediate coin
        - Sage's /split divides evenly, so equal-sized pieces = correct trading coins
        - Coin ID tracking via snapshot ensures we split the right coin
        """
        tag = f"topup_{name.lower()}"
        if self._topup_should_stop():
            log_event("info", f"{tag}_stopped", f"{name} top-up stopped before split")
            return False
        amount_str = (
            _format_amount_cat(pool_amount_mojos, cfg.CAT_DECIMALS)
            if is_cat else _format_amount_xch(pool_amount_mojos)
        )

        # ---- Step 1: Send-to-self to create pool coin ----
        try:
            addr_result = get_next_address(wallet_id=wallet_id, new_address=False)
            if not addr_result or not addr_result.get("success"):
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: Sage could not provide a wallet address "
                    f"for pool coin creation."
                )
            address = addr_result.get("address", "")
            if not address:
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: Sage returned an empty wallet address "
                    f"for pool coin creation."
                )
        except _TopupWalletDegraded:
            raise
        except Exception as e:
            self._abort_topup_for_wallet_degradation(
                f"{name} topup paused: wallet address lookup failed ({e})."
            )

        def _amount_matches_target(amount: int, target: int) -> bool:
            if amount == target:
                return True
            tolerance = max(1, int(target * 0.01))
            return abs(amount - target) < tolerance

        # Snapshot coins BEFORE the send. Use owned view as the primary truth so
        # a newly-created pool coin does not get confused with older hidden coins.
        before_snapshot = self._snapshot_coin_ids(wallet_id, f"{name}-before-pool")
        before_owned_map = self._get_owned_coin_amount_map(wallet_id, f"{name}-before-pool-owned") or {}

        log_event("info", f"{tag}_send_to_self",
                  f"Sending {amount_str} to self to create pool coin...")

        result = {}
        try:
            # Verify source coin is still spendable right before sending.
            # Another operation (gap closer, offer creation) might have consumed it.
            verify_result = _get_free_coins_rpc(wallet_id)
            if self._wallet_rpc_failed(verify_result):
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: spendable-coin verification failed "
                    f"before pool send."
                )
            verify_records = _extract_coin_records(verify_result)
            verify_ids = {_coin_id_from_record(r) for r in verify_records}
            if source_coin_id not in verify_ids:
                log_event("warning", f"{tag}_source_gone",
                          f"Source coin {source_coin_id[:16]}... no longer spendable — "
                          f"may have been consumed by another operation. Aborting split.")
                return False

            # Use source_coin_ids on Sage to ensure we spend from the reserve coin.
            # Chia's send_transaction doesn't support this param — it picks coins
            # automatically, but we've already re-fetched fresh IDs so it should
            # pick the largest available coin (our reserve).
            wallet_type = get_wallet_type()
            send_kwargs = {
                "wallet_id": wallet_id,
                "amount_mojos": pool_amount_mojos,
                "address": address,
                "fee_mojos": self._tx_fee_mojos(),
            }
            if wallet_type == "sage":
                send_kwargs["source_coin_ids"] = [source_coin_id]
            result = send_transaction(**send_kwargs)
            if not result:
                if self._spacescan_self_send_confirmed(source_coin_id, address, tag):
                    log_event("info", f"{tag}_send_onchain_pending",
                              "Spacescan confirms the pool self-send landed on-chain — "
                              "continuing while Sage catches up")
                    result = {}
                else:
                    self._abort_topup_for_wallet_degradation(
                        f"{name} topup paused: send-to-self returned no result from Sage."
                    )
            if isinstance(result, dict) and result.get("error"):
                send_error = result.get("error")
                if self._spacescan_self_send_confirmed(source_coin_id, address, tag):
                    log_event("info", f"{tag}_send_onchain_pending",
                              "Spacescan confirms the pool self-send landed on-chain — "
                              "continuing while Sage catches up")
                elif self._looks_like_wallet_rpc_degradation(send_error):
                    self._abort_topup_for_wallet_degradation(
                        f"{name} topup paused: send-to-self RPC degraded ({send_error})."
                    )
                else:
                    log_event("warning", f"{tag}_send_fail",
                              f"send_transaction error: {send_error}")
                    return False

            # Extract transaction info from response for tracking
            tx_ids = self._extract_sage_transaction_ids(result)
            if isinstance(result, dict):
                # Sage may return coin_spends with output coin info
                coin_spends = result.get("coin_spends", [])
                if coin_spends:
                    log_event("info", f"{tag}_send_tx_info",
                              f"Transaction has {len(coin_spends)} coin spends")

            send_info = f"Pool coin creation submitted"
            if tx_ids:
                send_info += f" (tx: {tx_ids[0][:16]}...)"
            send_info += f" [source: {source_coin_id[:12]}..., amount: {pool_amount_mojos}]"
            log_event("info", f"{tag}_send_ok", send_info)
        except _TopupWalletDegraded:
            raise
        except Exception as e:
            if self._spacescan_self_send_confirmed(source_coin_id, address, tag):
                log_event("info", f"{tag}_send_onchain_pending",
                          "Spacescan confirms the pool self-send landed on-chain — "
                          "continuing while Sage catches up")
            elif self._looks_like_wallet_rpc_degradation(e):
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: send-to-self RPC error ({e})."
                )
            else:
                log_event("warning", f"{tag}_send_error", f"send_transaction failed: {e}")
                return False

        # ---- Wait for the pool coin to appear ----
        # Strategy: Poll spendable coins and look for a coin matching our
        # exact pool amount that wasn't in the before-snapshot.
        # Also track coin IDs we've already seen to avoid confusion from
        # concurrent operations (gap closer, etc.) changing the coin set.
        pool_coin_id = None
        pool_confirmed = False
        pool_owned_logged = False
        pool_tx_logged = False
        poll_start = time.time()
        max_wait = 180
        poll_interval_s = 5
        known_coin_ids = {
            str(cid or "").strip().lower()
            for cid in (before_owned_map.keys() or before_snapshot.keys())
            if cid
        }

        # Log the send response for debugging
        if isinstance(result, dict):
            resp_keys = list(result.keys())
            log_event("debug", f"{tag}_send_response",
                      f"send_xch response keys: {resp_keys}")

        while (time.time() - poll_start) < max_wait:
            if self._topup_should_stop():
                log_event("info", f"{tag}_stopped", f"{name} top-up stopped while waiting for pool coin")
                return False
            time.sleep(poll_interval_s)
            # Fresh scan of ALL current spendable coins
            current = _get_free_coins_rpc(wallet_id)
            if self._wallet_rpc_failed(current):
                if self._spacescan_self_send_confirmed(source_coin_id, address, tag):
                    self._abort_topup_for_wallet_degradation(
                        f"{name} topup paused: pool self-send is on-chain but Sage "
                        f"did not refresh its spendable coin view."
                    )
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: spendable-coin polling failed while "
                    f"waiting for the pool coin."
                )
            records = _extract_coin_records(current)
            owned_map = self._get_owned_coin_amount_map(wallet_id, f"{tag}-pool-owned") or {}
            selectable_ids = self._get_strict_selectable_coin_id_set(wallet_id, f"{tag}-pool-selectable") or set()
            tx_state = self._get_transaction_confirmation_state(tx_ids)

            if tx_state["confirmed"] and not pool_tx_logged:
                suffix = f" at height {tx_state['height']}" if tx_state["height"] else ""
                log_event("info", f"{tag}_pool_tx_confirmed",
                          f"Pool coin transaction confirmed{suffix}")
                pool_tx_logged = True

            candidate_ids = sorted(
                cid for cid, amt in owned_map.items()
                if cid not in known_coin_ids and _amount_matches_target(amt, pool_amount_mojos)
            )
            if candidate_ids:
                pool_coin_id = candidate_ids[0]
                if not pool_owned_logged:
                    log_event("info", f"{tag}_pool_owned",
                              f"Pool coin is present in owned wallet view [ID: {pool_coin_id[:12]}...]")
                    pool_owned_logged = True
                if pool_coin_id in selectable_ids:
                    pool_confirmed = True
            else:
                for r in records:
                    cid = _coin_id_from_record(r)
                    amt = _coin_amount(r)
                    if not cid or cid in known_coin_ids:
                        continue
                    if _amount_matches_target(amt, pool_amount_mojos):
                        pool_coin_id = cid
                        pool_confirmed = True
                        break
                    known_coin_ids.add(cid)

            if pool_confirmed and pool_coin_id:
                if is_cat:
                    coin_str = _format_amount_cat(pool_amount_mojos, cfg.CAT_DECIMALS)
                else:
                    coin_str = _format_amount_xch(pool_amount_mojos)

                log_event("info", f"{tag}_pool_found",
                          f"Pool coin confirmed: {coin_str} "
                          f"[ID: {pool_coin_id[:12]}...] "
                          f"({int(time.time() - poll_start)}s)")
                break

            elapsed = int(time.time() - poll_start)
            if elapsed % 30 == 0 and elapsed > 0:
                total_coins = len(records)
                new_count = len([1 for r in records
                                  if _coin_id_from_record(r) not in before_snapshot])
                pool_state = "no exact owned output yet"
                if pool_coin_id:
                    owned_ready = pool_coin_id in owned_map
                    selectable_ready = pool_coin_id in selectable_ids
                    pool_state = (
                        f"owned={'yes' if owned_ready else 'no'}, "
                        f"selectable={'yes' if selectable_ready else 'no'}, "
                        f"tx={'confirmed' if tx_state['confirmed'] else 'pending'}"
                    )
                log_event("info", f"{tag}_pool_wait",
                          f"Waiting for pool coin ({_format_amount_xch(pool_amount_mojos) if not is_cat else _format_amount_cat(pool_amount_mojos, cfg.CAT_DECIMALS)})... "
                          f"({elapsed}s, {total_coins} spendable coins, "
                          f"{new_count} new since send, {pool_state})")

            # At 120s mark, try get_pending_transactions to check if tx is still alive
            if 118 < elapsed < 125:
                try:
                    if get_wallet_type() == "sage":
                        from wallet_sage import get_pending_transactions
                        pending = get_pending_transactions() or []
                        pending_count = len(pending) if isinstance(pending, list) else 0
                        log_event("info", f"{tag}_pending_check",
                                  f"Pending transactions: {pending_count} "
                                  f"(if 0, tx may have been dropped)")
                except Exception as e:
                    log_event("debug", f"{tag}_pending_check_failed",
                              f"Pending tx check failed (non-critical): {e}")

        if not pool_confirmed or not pool_coin_id:
            if pool_coin_id:
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: pool coin exists in Sage's owned view but "
                    f"did not become selectable after {max_wait}s."
                )
            if self._spacescan_self_send_confirmed(source_coin_id, address, tag):
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: pool self-send is on-chain but Sage did "
                    f"not surface the new pool coin after {max_wait}s."
                )
            log_event("warning", f"{tag}_pool_timeout",
                      f"Pool coin not confirmed after {max_wait}s")
            return False

        # ---- Step 2: Split the tracked pool coin ----
        log_event("info", f"{tag}_splitting",
                  f"Splitting pool coin into {num_to_create} trading coins "
                  f"[pool ID: {pool_coin_id[:12]}...]")

        wallet_type = get_wallet_type()

        if wallet_type == "sage":
            # Sage native /split — output_count = num_to_create (even split)
            try:
                split_result = split_coins_rpc(
                    wallet_id=wallet_id,
                    target_coin_id=pool_coin_id,
                    num_coins=num_to_create,
                    amount_per_coin=trading_size_mojos,
                    fee_mojos=self._tx_fee_mojos(),
                    is_cat=is_cat,
                )
                if split_result is None:
                    if self._spacescan_coin_spent_confirmed(pool_coin_id, tag, "split"):
                        log_event("info", f"{tag}_split_onchain_pending",
                                  "Spacescan shows the pool coin spent on-chain despite "
                                  "a weak Sage split response — continuing confirmation poll")
                    else:
                        self._abort_topup_for_wallet_degradation(
                            f"{name} topup paused: Sage /split returned no result."
                        )
                if isinstance(split_result, dict) and split_result.get("error"):
                    split_error = split_result.get("error")
                    if self._spacescan_coin_spent_confirmed(pool_coin_id, tag, "split"):
                        log_event("info", f"{tag}_split_onchain_pending",
                                  "Spacescan shows the pool coin spent on-chain despite "
                                  "a weak Sage split response — continuing confirmation poll")
                    elif self._looks_like_wallet_rpc_degradation(split_error):
                        self._abort_topup_for_wallet_degradation(
                            f"{name} topup paused: Sage /split degraded ({split_error})."
                        )
                    else:
                        log_event("warning", f"{tag}_split_rpc_fail",
                                  f"Sage /split error: {split_error}")
                        return False
                split_tx_ids = self._extract_sage_transaction_ids(split_result)
                split_msg = "Sage /split submitted successfully"
                if split_tx_ids:
                    split_msg += f" (tx: {split_tx_ids[0][:16]}...)"
                log_event("info", f"{tag}_split_submitted", split_msg)
            except _TopupWalletDegraded:
                raise
            except Exception as e:
                if self._spacescan_coin_spent_confirmed(pool_coin_id, tag, "split"):
                    log_event("info", f"{tag}_split_onchain_pending",
                              "Spacescan shows the pool coin spent on-chain despite "
                              "a Sage split exception — continuing confirmation poll")
                elif self._looks_like_wallet_rpc_degradation(e):
                    self._abort_topup_for_wallet_degradation(
                        f"{name} topup paused: Sage /split RPC error ({e})."
                    )
                else:
                    log_event("warning", f"{tag}_split_rpc_error",
                              f"Sage /split error: {e}")
                    return False
        else:
            split_tx_ids = []
            # Chia CLI split — needs display units
            if is_cat:
                cli_coin_size = Decimal(str(cat_token_amount or int(self.get_target_cat_coin_size())))
            else:
                cli_coin_size = Decimal(trading_size_mojos) / Decimal("1000000000000")

            # Use the low-level CLI path from _split_via_cli but just the CLI part
            bare_coin_id = pool_coin_id.replace("0x", "")
            if not self._fingerprint or not self._fingerprint.strip():
                self._fingerprint = self._resolve_fingerprint()

            cmd = [
                "chia", "wallet", "coins", "split",
                "-f", self._fingerprint,
                "-i", str(wallet_id),
                "-n", str(num_to_create),
                "-a", str(cli_coin_size),
                "-t", bare_coin_id,
                "-m", "0"
            ]

            try:
                import subprocess as sp
                process = sp.Popen(
                    cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, text=True
                )
                stdout, stderr = process.communicate(input="y\n", timeout=60)
                output = stdout + stderr

                if "submitted to" in output.lower() or "transaction" in output.lower():
                    log_event("info", f"{tag}_split_submitted",
                              "CLI split submitted successfully")
                else:
                    log_event("warning", f"{tag}_split_cli_fail",
                              f"CLI split failed: {output[:200]}")
                    return False
            except Exception as e:
                log_event("warning", f"{tag}_split_cli_error", f"CLI split error: {e}")
                return False

        # ---- Wait for split confirmation via tx + owned + selectable state ----
        split_start = time.time()
        split_max_wait = 120
        split_poll_interval_s = 4
        split_tx_logged = False
        split_owned_logged = False
        pre_split_owned_ids = set(
            (self._get_owned_coin_amount_map(wallet_id, f"{tag}-pre-split-owned") or {}).keys()
        )

        while (time.time() - split_start) < split_max_wait:
            if self._topup_should_stop():
                log_event("info", f"{tag}_stopped", f"{name} top-up stopped while waiting for split confirmation")
                return False
            time.sleep(split_poll_interval_s)
            result = _get_free_coins_rpc(wallet_id)
            if self._wallet_rpc_failed(result):
                if self._spacescan_coin_spent_confirmed(pool_coin_id, tag, "split"):
                    self._abort_topup_for_wallet_degradation(
                        f"{name} topup paused: split is on-chain but Sage did not "
                        f"refresh its spendable coin view."
                    )
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: spendable-coin polling failed while "
                    f"waiting for split confirmation."
                )
            owned_map = self._get_owned_coin_amount_map(wallet_id, f"{tag}-split-owned") or {}
            selectable_ids = self._get_strict_selectable_coin_id_set(wallet_id, f"{tag}-split-selectable") or set()
            tx_state = self._get_transaction_confirmation_state(split_tx_ids)
            elapsed = int(time.time() - split_start)

            pool_visible = pool_coin_id in owned_map
            pool_selectable = pool_coin_id in selectable_ids
            pool_consumed = (not pool_visible) or (pool_coin_id and not pool_selectable)
            new_output_ids = sorted(
                cid for cid, amount in owned_map.items()
                if cid not in pre_split_owned_ids and _amount_matches_target(amount, trading_size_mojos)
            )
            owned_output_count = len(new_output_ids)
            selectable_output_count = sum(1 for cid in new_output_ids if cid in selectable_ids)
            outputs_selectable = (
                owned_output_count >= num_to_create and
                selectable_output_count >= num_to_create
            )

            if tx_state["confirmed"] and not split_tx_logged:
                suffix = f" at height {tx_state['height']}" if tx_state["height"] else ""
                log_event("info", f"{tag}_split_tx_confirmed",
                          f"Split transaction confirmed{suffix}")
                split_tx_logged = True

            if pool_consumed and owned_output_count >= num_to_create and not split_owned_logged:
                if outputs_selectable:
                    log_event("info", f"{tag}_split_outputs_ready",
                              f"Split outputs are owned and selectable ({owned_output_count}/{num_to_create})")
                else:
                    log_event("info", f"{tag}_split_outputs_owned",
                              f"Split outputs are owned ({owned_output_count}/{num_to_create}) — "
                              f"waiting for selectable view to catch up")
                split_owned_logged = True

            if pool_consumed and owned_output_count >= num_to_create and (outputs_selectable or tx_state["confirmed"]):
                if outputs_selectable:
                    detail = f"{selectable_output_count}/{num_to_create} selectable"
                else:
                    detail = f"{owned_output_count}/{num_to_create} owned, selectable lagging"
                log_event("info", f"{tag}_split_confirmed",
                          f"Split confirmed after {elapsed}s ({detail})")
                return True

            if elapsed % 20 == 0 and elapsed > 0:
                tx_label = "confirmed" if tx_state["confirmed"] else "pending"
                log_event("info", f"{tag}_split_wait",
                          f"Waiting for split... (tx={tx_label}, "
                          f"{owned_output_count}/{num_to_create} owned, "
                          f"{selectable_output_count}/{num_to_create} selectable, {elapsed}s)")

        # Final post-timeout diagnostic
        final_result = _get_free_coins_rpc(wallet_id)
        if self._wallet_rpc_failed(final_result):
            if self._spacescan_coin_spent_confirmed(pool_coin_id, tag, "split"):
                self._abort_topup_for_wallet_degradation(
                    f"{name} topup paused: split is on-chain but Sage did not "
                    f"finish refreshing after timeout."
                )
            self._abort_topup_for_wallet_degradation(
                f"{name} topup paused: spendable-coin refresh failed after split timeout."
            )

        owned_map = self._get_owned_coin_amount_map(wallet_id, f"{tag}-split-timeout-owned") or {}
        selectable_ids = self._get_strict_selectable_coin_id_set(wallet_id, f"{tag}-split-timeout-selectable") or set()
        tx_state = self._get_transaction_confirmation_state(split_tx_ids)
        new_output_ids = sorted(
            cid for cid, amount in owned_map.items()
            if cid not in pre_split_owned_ids and _amount_matches_target(amount, trading_size_mojos)
        )
        owned_output_count = len(new_output_ids)
        selectable_output_count = sum(1 for cid in new_output_ids if cid in selectable_ids)
        if tx_state["confirmed"] and owned_output_count >= num_to_create:
            log_event("info", f"{tag}_split_confirmed",
                      f"Split confirmed after {split_max_wait}s "
                      f"({owned_output_count}/{num_to_create} owned, selectable lagging)")
            return True

        log_event("warning", f"{tag}_split_timeout",
                  f"Split not confirmed after {split_max_wait}s "
                  f"(tx={'confirmed' if tx_state['confirmed'] else 'pending'}, "
                  f"{owned_output_count}/{num_to_create} owned, "
                  f"{selectable_output_count}/{num_to_create} selectable)")
        return False

    def _snapshot_coin_ids(self, wallet_id: int, label: str) -> dict:
        """Snapshot current spendable coins as {coin_id: amount_mojos}.

        Used for before/after diffing to track newly created coins.
        Same approach as coin_prep_worker.
        """
        result = _get_free_coins_rpc(wallet_id)
        records = _extract_coin_records(result)
        snapshot = {}
        for r in records:
            cid = _coin_id_from_record(r)
            amt = _coin_amount(r)
            if cid:
                snapshot[cid] = amt
        return snapshot

    def _diff_coin_snapshots(self, before: dict, after: dict) -> list:
        """Find NEW coins that appeared between snapshots.

        Returns list of {"coin_id": ..., "amount": ...} for new coins only.
        """
        new_ids = set(after.keys()) - set(before.keys())
        return [{"coin_id": cid, "amount": after[cid]} for cid in new_ids]

    def _consolidate_coins(self, name: str, wallet_id: int,
                            total_amount: int, is_cat: bool) -> bool:
        """Consolidate all coins in a wallet by sending total balance to self.

        This creates one large coin from many small ones.
        """
        try:
            # Get address
            addr_result = get_next_address(wallet_id=wallet_id, new_address=False)
            if not addr_result or not addr_result.get("success"):
                log_event("warning", f"consolidate_{name.lower()}_addr_fail",
                          "Could not get wallet address for consolidation")
                return False

            address = addr_result.get("address", "")
            if not address:
                return False

            fee = self._tx_fee_mojos()
            if is_cat:
                # CAT: fee is paid in XCH from XCH balance — send full CAT amount
                send_amount = total_amount
            else:
                # XCH: fee comes from the same XCH balance — subtract to avoid overspend
                send_amount = max(0, total_amount - fee)
                if send_amount <= 0:
                    log_event("warning", f"consolidate_{name.lower()}_skip",
                              f"Consolidation skipped: total_amount {total_amount} mojos "
                              f"insufficient to cover fee {fee} mojos")
                    return False
            result = send_transaction(
                wallet_id=wallet_id,
                amount_mojos=send_amount,
                address=address,
                fee_mojos=fee
            )

            if result and result.get("success"):
                return True
            else:
                error = (result or {}).get("error", "Unknown")
                log_event("warning", f"consolidate_{name.lower()}_fail",
                          f"Consolidation send failed: {error}")
                return False

        except Exception as e:
            log_event("error", f"consolidate_{name.lower()}_error",
                      f"Consolidation error: {e}")
            return False

    def _poll_for_confirmation(self, pre_xch: int, pre_cat: int,
                                max_polls: int = 36, poll_interval: int = 5):
        """Poll until coin counts change (confirms splits/consolidation).

        Max 3 minutes (36 polls × 5 seconds). Shorter than the old 10-minute
        timeout because if a split hasn't confirmed by then, the transaction
        likely failed or the wallet is stuck — better to retry next cycle
        than block the topup thread for 10 minutes.
        """
        for i in range(max_polls):
            if self._topup_should_stop():
                log_event("info", "topup_stopped", "Coin top-up stopped while waiting for inventory confirmation")
                return
            time.sleep(poll_interval)
            elapsed = (i + 1) * poll_interval

            try:
                xch_result = _get_free_coins_rpc(cfg.WALLET_ID_XCH)
                cat_result = _get_free_coins_rpc(cfg.CAT_WALLET_ID)

                new_xch = len(_extract_coin_records(xch_result))
                new_cat = len(_extract_coin_records(cat_result))

                if new_xch != pre_xch or new_cat != pre_cat:
                    self._xch_coins = new_xch
                    self._cat_coins = new_cat
                    log_event("info", "topup_inventory_changed",
                              f"Coin inventory changed in {elapsed}s. "
                              f"XCH: {pre_xch}→{new_xch}, CAT: {pre_cat}→{new_cat}")
                    return

                if elapsed % 15 == 0:
                    log_event("info", "topup_waiting",
                              f"Waiting for confirmation... XCH: {new_xch}, "
                              f"CAT: {new_cat} ({elapsed}s / {max_polls * poll_interval}s max)")

            except Exception as e:
                log_event("warning", "topup_wait_poll_failed",
                          f"Topup confirmation poll failed: {e}")

        log_event("warning", "topup_timeout",
                  f"No coin count change after {max_polls * poll_interval}s — "
                  f"will retry next cycle")

    # -------------------------------------------------------------------
    # Full coin prep (subprocess)
    # -------------------------------------------------------------------

    def start_coin_prep(self) -> bool:
        """Launch the full coin_prep_worker as a subprocess."""
        # Kill any existing worker before starting a new one.
        # Two workers on the same wallet causes coin conflicts.
        if self._prep_process and self._prep_process.poll() is None:
            old_pid = self._prep_process.pid
            log_event("warning", "coin_prep_kill",
                      f"Killing previous coin prep worker (PID: {old_pid}) before new run")
            try:
                self._prep_process.terminate()
                try:
                    self._prep_process.wait(timeout=3)
                except Exception:
                    self._prep_process.kill()
                    self._prep_process.wait(timeout=2)
            except Exception as e:
                log_event("warning", "coin_prep_kill_failed",
                          f"Could not terminate previous coin prep worker (PID {self._prep_process.pid}): {e}")
            self._prep_process = None
            with self._lock:
                self._prep_running = False

        # Atomic check-and-set: both the guard and the flag update must be
        # inside the same lock acquisition to prevent two callers from both
        # passing the check and spawning duplicate workers.
        with self._lock:
            if self._prep_running or self._topup_running:
                return False
            self._prep_running = True

        try:
            worker_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "coin_prep_worker.py"
            )

            if not os.path.exists(worker_path):
                log_event("error", "coin_prep_missing",
                          f"coin_prep_worker.py not found at {worker_path}")
                with self._lock:
                    self._prep_running = False
                return False
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            # Build CLI args to pass correct config to the worker.
            # This ensures the worker uses the ACTUAL bot settings
            # (from GUI) instead of stale .env values.
            cmd = ["python", worker_path]
            max_buy = getattr(cfg, "MAX_ACTIVE_BUY_OFFERS", 25)
            max_sell = getattr(cfg, "MAX_ACTIVE_SELL_OFFERS", 25)

            # Coin prep multiplier: prep up to N× coins for spare capacity
            multiplier = getattr(cfg, "COIN_PREP_MULTIPLIER", Decimal("1.0"))
            prep_headroom_pct = getattr(cfg, "COIN_PREP_HEADROOM_PCT", Decimal("10"))

            if cfg.TIER_ENABLED:
                # Tier-aware coin prep: pass tier sizes and counts
                max_per_side = max(max_buy, max_sell)
                tier_counts = get_weighted_tier_prep_counts(max_per_side, multiplier)
                if self._sniper_pool_enabled():
                    tier_counts["sniper"] = int(getattr(cfg, "SNIPER_PREP_COUNT", 0) or 0)
                cat_total_coins = sum(tier_counts.values())
                if self._fee_pool_enabled():
                    tier_counts[get_fee_tier_name()] = get_fee_pool_count()
                total_coins = sum(tier_counts.values())

                tier_sizes_str = ",".join(
                    f"{tier}={size}"
                    for tier, size in self._configured_xch_prep_sizes().items()
                )
                tier_counts_str = ",".join(f"{k}={v}" for k, v in tier_counts.items())

                cmd.extend(["--xch-target", str(total_coins)])
                cmd.extend(["--tier-sizes", tier_sizes_str])
                cmd.extend(["--tier-counts", tier_counts_str])
                cmd.extend(["--cat-target", str(cat_total_coins)])
                cmd.extend(["--prep-headroom-pct", str(prep_headroom_pct)])

                tier_detail = " + ".join(
                    f"{c} {t} × {self._configured_xch_prep_sizes().get(t, Decimal('0'))}"
                    for t, c in tier_counts.items() if c > 0
                )
                log_event("info", "coin_prep_config",
                          f"Tier coin prep ({multiplier}×): {total_coins} coins = {tier_detail} "
                          f"(+{prep_headroom_pct}% headroom)")
            else:
                # Uniform coin prep with multiplier
                target_xch_size = self.get_target_xch_coin_size()
                total_coins = int((max_buy + max_sell) * multiplier)
                # Ensure at least max_buy + max_sell (1× minimum)
                total_coins = max(total_coins, max_buy + max_sell)
                cmd.extend(["--xch-target", str(total_coins)])
                cmd.extend(["--xch-size", str(target_xch_size)])
                cmd.extend(["--cat-target", str(total_coins)])
                cmd.extend(["--prep-headroom-pct", str(prep_headroom_pct)])
                log_event("info", "coin_prep_config",
                          f"Coin prep config ({multiplier}×): {total_coins} XCH coins × "
                          f"{target_xch_size} each, {total_coins} CAT coins "
                          f"(+{prep_headroom_pct}% headroom)")

            self._prep_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
                **hidden_subprocess_kwargs(),
            )

            log_event("info", "coin_prep_started",
                      f"Coin prep worker started (PID: {self._prep_process.pid})")
            return True

        except Exception as e:
            with self._lock:
                self._prep_running = False
            log_event("error", "coin_prep_start_failed",
                      f"Failed to start coin prep worker: {e}")
            return False

    def check_coin_prep_status(self) -> Dict:
        """Check if coin prep subprocess is still running."""
        if not self._prep_process:
            return {"running": False}

        poll = self._prep_process.poll()

        if poll is not None:
            with self._lock:
                self._prep_running = False

            try:
                stdout_data = self._prep_process.stdout.read() if self._prep_process.stdout else ""
                stderr_data = self._prep_process.stderr.read() if self._prep_process.stderr else ""
                if stdout_data:
                    log_event("info", "coin_prep_stdout",
                              f"Worker output (last 500 chars): ...{stdout_data[-500:]}")
                if stderr_data:
                    log_event("error", "coin_prep_stderr",
                              f"Worker errors: {stderr_data[-500:]}")
                if poll != 0:
                    log_event("error", "coin_prep_failed",
                              f"Worker exited with code {poll}. stderr: {stderr_data[-300:]}")
            except Exception as e:
                log_event("warning", "coin_prep_output_read_failed",
                          f"Could not read coin prep worker output: {e}")

            cancelled_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "worker_cancelled_ids.json"
            )
            if os.path.exists(cancelled_file):
                try:
                    with open(cancelled_file, "r") as f:
                        cancelled = json.load(f)
                    self._worker_cancelled_ids.update(cancelled)
                    os.remove(cancelled_file)
                    log_event("info", "coin_prep_cancelled_ids",
                              f"Loaded {len(cancelled)} cancelled IDs from worker")
                except Exception as e:
                    log_event("warning", "coin_prep_cancelled_ids_load_failed",
                              f"Could not load worker cancelled IDs file: {e}")

            self.update_coin_counts()

            return {
                "running": False,
                "exit_code": poll,
                "cancelled_ids": list(self._worker_cancelled_ids),
            }

        return {"running": True, "pid": self._prep_process.pid}

    def get_worker_cancelled_ids(self) -> set:
        """Get and clear worker-cancelled IDs."""
        ids = self._worker_cancelled_ids.copy()
        self._worker_cancelled_ids.clear()
        return ids

    # -------------------------------------------------------------------
    # State queries
    # -------------------------------------------------------------------

    def _get_tier_sizes_mojos(self, is_cat: bool = False) -> Dict[str, int]:
        """Get tier sizes in mojos for tier-aware coin classification.

        Returns {"inner": mojos, "mid": mojos, "outer": mojos, "extreme": mojos}
        For CAT, derives from XCH tier sizes / price with configurable prep headroom.
        """
        prep_mult = self._get_coin_prep_headroom_multiplier()
        tier_sizes_xch = self._configured_tier_sizes_xch()
        if is_cat:
            price = self._get_current_price()
            cat_scale = Decimal(10) ** Decimal(cfg.CAT_DECIMALS)
            result = {}
            for tier, xch_size in tier_sizes_xch.items():
                if price and price > 0:
                    cat_amount = (xch_size / price * prep_mult).quantize(Decimal("1"))
                else:
                    cat_amount = cfg.CAT_COIN_SIZE
                result[tier] = int(cat_amount * cat_scale)
            return result
        else:
            xch_scale = Decimal("1000000000000")
            result = {
                tier: int((size_xch * prep_mult) * xch_scale)
                for tier, size_xch in tier_sizes_xch.items()
            }
            if self._fee_pool_enabled():
                result[get_fee_tier_name()] = get_fee_coin_size_mojos()
            return result

    def get_target_xch_coin_size(self) -> Decimal:
        """Get prepared XCH coin size for classification and splitting.

        This is the prepared coin size, not the live offer size. Prepared
        coins are larger than live offers by the configurable headroom.
        """
        prep_mult = self._get_coin_prep_headroom_multiplier()
        if cfg.TIER_ENABLED:
            return cfg.MID_SIZE_XCH * prep_mult
        trade_size = getattr(cfg, "DEFAULT_TRADE_XCH", None)
        if trade_size and trade_size > 0:
            return trade_size * prep_mult
        return cfg.XCH_COIN_SIZE * prep_mult

    def get_target_cat_coin_size(self) -> Decimal:
        """Get prepared CAT coin size for classification and splitting.

        Derives from XCH trade size and current mid price:
          CAT per offer = trade_size_xch / price
          With configurable prep headroom.

        Falls back to CAT_COIN_SIZE config if price unavailable.
        """
        try:
            xch_trade_size = self.get_target_xch_coin_size()
            # Try to get price from the price engine (cached last price)
            price = self._get_current_price()
            if price and price > 0:
                cat_per_offer = xch_trade_size / price
                cat_coin_size = cat_per_offer.quantize(Decimal("1"))
                return cat_coin_size
        except Exception as e:
            log_event("debug", "cat_coin_size_calc_failed",
                      f"CAT coin size calculation failed (falling back to config): {e}")
        # Fallback to config value
        return cfg.CAT_COIN_SIZE

    def _get_coin_prep_headroom_multiplier(self) -> Decimal:
        """Return the multiplier applied to prepared coin sizes."""
        try:
            headroom_pct = Decimal(str(getattr(cfg, "COIN_PREP_HEADROOM_PCT", Decimal("10"))))
        except Exception:
            headroom_pct = Decimal("10")
        if headroom_pct < 0:
            headroom_pct = Decimal("0")
        return Decimal("1") + (headroom_pct / Decimal("100"))

    def _get_current_price(self) -> Optional[Decimal]:
        """Get current mid price for CAT size derivation.

        Tries the price engine's cached price first (fast, no API call).
        Falls back to a direct Dexie API fetch if no cached price.
        """
        # Method 1: Use price engine's cached price (set by bot_loop)
        if hasattr(self, '_price_engine') and self._price_engine:
            try:
                last = self._price_engine.get_last_price()
                if last and last > 0:
                    return last
            except Exception as e:
                log_event("debug", "price_engine_cache_fetch_failed",
                          f"Price engine cache fetch failed (will try Dexie): {e}")

        # Method 2: Direct Dexie API call (for topup worker, which runs
        # in a thread and may not have access to price engine)
        try:
            import requests
            cat_asset_id = cfg.CAT_ASSET_ID
            if cat_asset_id:
                _dexie_base = str(getattr(cfg, "DEXIE_API_BASE", "https://api.dexie.space") or "https://api.dexie.space").rstrip("/")
                resp = requests.get(
                    f"{_dexie_base}/v2/prices/tickers?ticker_id={cat_asset_id}_xch",
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tickers = data.get("tickers", [])
                    if tickers and tickers[0].get("last_price"):
                        price = Decimal(str(tickers[0]["last_price"]))
                        if price > 0:
                            return price
        except Exception as e:
            log_event("debug", "dexie_price_fetch_failed",
                      f"Direct Dexie price fetch failed (coin sizing will use config default): {e}")
        return None

    def is_busy(self) -> bool:
        """Check if any coin operation is in progress.

        Reads both flags under the lock to avoid torn reads where one flag
        is stale while the other is current.
        """
        with self._lock:
            return self._prep_running or self._topup_running

    def reset_backoff(self):
        """Reset no-coins backoff (called after fills bring new coins)."""
        if self._no_coins_backoff:
            self._no_coins_backoff = False
            log_event("debug", "topup_backoff_reset",
                      "Topup backoff reset — fills brought new coins")

    def get_status(self) -> Dict:
        """Get current coin manager status for GUI/API."""
        return {
            "xch_coins": self._xch_coins,
            "cat_coins": self._cat_coins,
            "xch_locked_coins": self._xch_locked_coins,
            "cat_locked_coins": self._cat_locked_coins,
            "xch_total_coins": self._xch_total_coins,
            "cat_total_coins": self._cat_total_coins,
            "prep_running": self._prep_running,
            "topup_running": self._topup_running,
            "no_coins_backoff": self._no_coins_backoff,
            "inventory": self.get_inventory_summary(),
        }
