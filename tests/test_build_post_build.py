from pathlib import Path

import build


def test_post_build_accepts_pyinstaller_internal_html_asset(tmp_path, monkeypatch, capsys):
    output_dir = tmp_path / "dist" / "Catalyst"
    internal_dir = output_dir / "_internal"
    internal_dir.mkdir(parents=True)

    exe_path = output_dir / "Catalyst.exe"
    exe_path.write_bytes(b"exe")
    (internal_dir / "bot_gui.html").write_text("<html></html>", encoding="utf-8")

    env_example = tmp_path / ".env.example"
    env_example.write_text("CAT_ASSET_ID=\n", encoding="utf-8")

    monkeypatch.setattr(build, "OUTPUT_DIR", str(output_dir))
    monkeypatch.setattr(build, "ENV_EXAMPLE", str(env_example))
    monkeypatch.setattr(build.sys, "platform", "win32")

    build._post_build()

    output = capsys.readouterr().out
    assert "WARNING: bot_gui.html not found" not in output
    assert "HTML assets verified in bundle." in output
    assert (output_dir / ".env.example").read_text(encoding="utf-8") == "CAT_ASSET_ID=\n"
