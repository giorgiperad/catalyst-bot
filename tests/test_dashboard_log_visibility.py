from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "bot_gui.html"


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_tibet_price_shift_events_are_visible_in_system_logs():
    html = GUI.read_text(encoding="utf-8", errors="replace")
    icon_map = _section(html, "const SYSTEM_LOG_EVENT_ICONS = {", "};")

    required_events = [
        "mempool_swap_detected",
        "mempool_imminent_wake",
        "mempool_price_confirmed",
        "mempool_price_move",
        "defensive_cancel_start",
        "mempool_defensive_cancel_done",
        "mempool_defensive_cancel_deferred_pending_cancel_settle",
        "amm_drift_detected",
        "amm_drift_requote_triggered",
        "tibet_swap_detected",
    ]

    for event_type in required_events:
        assert f"{event_type}:" in icon_map


def test_tibet_price_shift_events_have_activity_copy():
    html = GUI.read_text(encoding="utf-8", errors="replace")
    activity_translator = _section(html, "function laTranslate(", "function laHandleEvent(")

    required_events = [
        "mempool_swap_detected",
        "mempool_imminent_wake",
        "mempool_price_confirmed",
        "mempool_price_move",
        "mempool_defensive_cancel_done",
        "mempool_defensive_cancel_deferred_pending_cancel_settle",
        "amm_drift_requote_triggered",
    ]

    for event_type in required_events:
        assert event_type in activity_translator

    assert "Tibet swap spotted early" in activity_translator
    assert "Tibet price shift confirmed" in activity_translator
