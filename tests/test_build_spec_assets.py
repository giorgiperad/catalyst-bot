import re
from pathlib import Path


def test_pyinstaller_spec_bundles_gui_asset_references():
    root = Path(__file__).resolve().parents[1]
    gui = (root / "bot_gui.html").read_text(encoding="utf-8")
    spec = (root / "catalyst.spec").read_text(encoding="utf-8")

    referenced_assets = set(re.findall(r'["\']/assets/([^"\']+)["\']', gui))
    assert referenced_assets, "bot_gui.html should reference bundled assets"

    missing = sorted(
        asset
        for asset in referenced_assets
        if (root / "assets" / asset).is_file() and asset not in spec
    )
    assert missing == []
