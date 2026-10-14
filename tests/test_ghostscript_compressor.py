import sys
from pathlib import Path

from core.engines.pdf.ghostscript import GhostscriptCompressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_compress_without_gs_path_fails_early():
    compressor = GhostscriptCompressor()
    logs, events = [], []
    compressor.log.connect(logs.append)
    compressor.finished.connect(lambda ok, fail: events.append((ok, fail)))

    compressor.compress(["a.pdf", "b.pdf"], "/screen")

    assert events == [(0, 2)]
    assert any("未找到" in m for m in logs)


def test_compress_nonexistent_kwarg_path_fails_early():
    compressor = GhostscriptCompressor()
    logs, events = [], []
    compressor.log.connect(logs.append)
    compressor.finished.connect(lambda ok, fail: events.append((ok, fail)))

    compressor.compress(
        ["a.pdf"], "/screen",
        gs_path=str(PROJECT_ROOT / "no_such_gs.exe"),
    )

    assert events == [(0, 1)]
    assert any("未找到" in m for m in logs)


def test_compress_honors_existing_kwarg_path():
    compressor = GhostscriptCompressor()
    logs, events = [], []
    compressor.log.connect(logs.append)
    compressor.finished.connect(lambda ok, fail: events.append((ok, fail)))

    compressor.compress(["a.pdf"], "/screen", gs_path=sys.executable)

    assert events == [(0, 1)]
    assert not any("未找到" in m for m in logs)


def test_ghostscript_engine_has_no_app_dependency():
    for name in ("ghostscript.py", "base.py"):
        src = (PROJECT_ROOT / "core" / "engines" / "pdf" / name).read_text(encoding="utf-8")
        assert "app.container" not in src, f"{name} 仍在依赖 app.container"
