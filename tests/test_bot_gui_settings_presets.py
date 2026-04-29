from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_settings_preset_action_names_are_attribute_escaped():
    html = (ROOT / "bot_gui.html").read_text(encoding="utf-8")
    preset_render = html.split("function presetsRender()", 1)[1].split(
        "async function _saveCurrentAsPresetPostSave()", 1
    )[0]

    assert "function escapeAttr" in html
    assert "const nameAttr = escapeAttr(name);" in preset_render
    assert "data-preset-name=\"' + nameAttr + '\">" in preset_render
    assert "data-preset-name=\"' + nameEsc + '\">" not in preset_render
