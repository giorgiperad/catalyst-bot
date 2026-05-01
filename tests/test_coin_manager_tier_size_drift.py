"""Tier-size drift checks should match live offer coin-fit bounds."""

import coin_manager
import database
from config import cfg


def _coin(amount_mojos):
    return {"amount_mojos": int(amount_mojos)}


def _patch_drift_inputs(monkeypatch, amounts_by_key):
    monkeypatch.setattr(cfg, "TIER_ENABLED", True, raising=False)
    monkeypatch.setattr(cfg, "COIN_MAX_SIZE_RATIO", 1.5, raising=False)

    def fake_tier_sizes(is_cat=False):
        return {"inner": 1000, "mid": 500, "outer": 250, "extreme": 125}

    def fake_coins(wallet_type, designation, tier):
        assert designation == "tier_spare"
        return [_coin(v) for v in amounts_by_key.get((wallet_type, tier), [])]

    monkeypatch.setattr(coin_manager, "get_tier_sizes_mojos_from_cfg", fake_tier_sizes)
    monkeypatch.setattr(database, "get_coins_by_designation", fake_coins)


def test_standalone_drift_accepts_usable_oversize_coins(monkeypatch):
    _patch_drift_inputs(monkeypatch, {("cat", "outer"): [305, 305]})

    findings = coin_manager.check_tier_size_drift_standalone()

    assert findings == []


def test_standalone_drift_flags_under_floor_coins(monkeypatch):
    _patch_drift_inputs(monkeypatch, {("xch", "inner"): [970, 970]})

    findings = coin_manager.check_tier_size_drift_standalone()

    assert len(findings) == 1
    assert findings[0]["side"] == "xch"
    assert findings[0]["tier"] == "inner"
    assert findings[0]["ratio"] == 0.97


def test_standalone_drift_flags_above_configured_max_ratio(monkeypatch):
    _patch_drift_inputs(monkeypatch, {("cat", "mid"): [755, 755]})

    findings = coin_manager.check_tier_size_drift_standalone()

    assert len(findings) == 1
    assert findings[0]["side"] == "cat"
    assert findings[0]["tier"] == "mid"
    assert findings[0]["ratio"] == 1.51


def test_instance_drift_uses_same_bounds(monkeypatch):
    _patch_drift_inputs(monkeypatch, {("cat", "outer"): [305, 305]})
    manager = coin_manager.CoinManager.__new__(coin_manager.CoinManager)

    findings = manager.check_tier_size_drift()

    assert findings == []
