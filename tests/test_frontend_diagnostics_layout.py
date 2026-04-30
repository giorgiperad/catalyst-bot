from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "bot_gui.html"
RISK_MANAGER = ROOT / "src" / "catalyst" / "risk_manager.py"


def test_diagnostics_are_distributed_across_existing_workflow_tabs():
    html = GUI.read_text(encoding="utf-8", errors="replace")

    required_ids = [
        "offersDiagnosticsGrid",
        "diagBuyRequotePressure",
        "diagSellRequotePressure",
        "diagPendingCancels",
        "diagRequoteBatch",
        "intelSourceCoverage",
        "intelArbGapTrend",
        "pnlFlowDiagnostics",
        "pnlPendingVerification",
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in html


def test_market_price_history_has_range_controls_without_adding_new_main_tab():
    html = GUI.read_text(encoding="utf-8", errors="replace")

    assert 'data-price-range="24"' in html
    assert 'data-price-range="0.333333"' in html
    assert 'id="v4View-analysis"' not in html


def test_market_diagnostics_uses_live_amm_and_summary_sources():
    html = GUI.read_text(encoding="utf-8", errors="replace")

    assert "_lastAmmPriceData" in html
    assert "_lastMarketSummary" in html
    assert "summaryTibetXch" in html


def test_close_gap_recommendation_has_confidence_gate():
    html = GUI.read_text(encoding="utf-8", errors="replace")

    assert "_SA_CLOSE_GAP_PROMOTE_BPS = 200" in html
    assert "_SA_CLOSE_GAP_CONFIRM_UPDATES = 3" in html
    assert "saCloseGapSignalReady(" in html
    assert "closeGapCandidate" in html
    assert "if (closeGapReady)" in html


def test_min_spread_clamp_copy_is_diagnostic_not_directive():
    html = GUI.read_text(encoding="utf-8", errors="replace")
    text = RISK_MANAGER.read_text(encoding="utf-8", errors="replace")

    assert "raise MIN_SPREAD_BPS" not in text
    assert "configured minimum clamp" in text
    assert "normalizeMarketConditionText" in html
    assert "raise MIN_SPREAD_BPS" not in html


def test_running_settings_restart_warning_is_setup_only():
    html = GUI.read_text(encoding="utf-8", errors="replace")

    assert "function updateSettingsRestartBannerVisibility()" in html
    assert "const setupActive = !!(setupView && setupView.classList.contains('is-active'));" in html
    assert "isRunning && setupActive" in html
    assert "try { updateSettingsRestartBannerVisibility(); } catch (_) {}" in html
    assert "banner.classList.toggle('is-visible', isRunning);" not in html
