"""BaseOfficeConverter 模板方法的编排特征测试。

用 FakeOfficeEngine（mock COM）锁定 convert() 的信号序列与
成功/失败/停止/启动失败四条路径的行为契约。
"""

from unittest.mock import MagicMock

import comtypes
import pytest

from core.engines.office.base import BaseOfficeConverter


class FakeOfficeEngine(BaseOfficeConverter):
    """mock 掉全部 COM 依赖的编排探针。"""

    def __init__(self, fail_open_paths=()):
        super().__init__()
        self.fail_open_paths = set(fail_open_paths)
        self.opened = []
        self.saved = []
        self.closed = 0
        self.quit_called = False

    @property
    def app_name(self) -> str:
        return "Fake Office"

    def _create_app(self):
        return MagicMock()

    def _open_document(self, app, file_path: str):
        if file_path in self.fail_open_paths:
            raise RuntimeError("open failed")
        self.opened.append(file_path)
        return MagicMock()

    def _save_as_pdf(self, doc, output_path: str):
        self.saved.append(output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("pdf")

    def _close_document(self, doc):
        self.closed += 1

    def _quit_app(self, app):
        self.quit_called = True


@pytest.fixture
def no_com(monkeypatch):
    monkeypatch.setattr(comtypes, "CoInitialize", lambda: None)
    monkeypatch.setattr(comtypes, "CoUninitialize", lambda: None)


def _collect(engine):
    events = []
    engine.progress.connect(lambda c, t, m: events.append(("progress", c, t, m)))
    engine.log.connect(lambda m: events.append(("log", m)))
    engine.finished.connect(lambda s, f: events.append(("finished", s, f)))
    return events


def _make_files(tmp_path, names):
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_text("x", encoding="utf-8")
        paths.append(str(p))
    return paths


class TestOfficeEngineOrchestration:
    def test_success_signal_sequence(self, no_com, tmp_path):
        files = _make_files(tmp_path, ["a.docx", "b.docx", "c.docx"])
        engine = FakeOfficeEngine()
        events = _collect(engine)

        engine.convert(files)

        assert events == [
            ("log", "正在启动 Fake Office..."),
            ("progress", 1, 3, "a.docx"), ("log", "正在转换: a.docx"), ("log", "✅ 成功: a.docx"),
            ("progress", 2, 3, "b.docx"), ("log", "正在转换: b.docx"), ("log", "✅ 成功: b.docx"),
            ("progress", 3, 3, "c.docx"), ("log", "正在转换: c.docx"), ("log", "✅ 成功: c.docx"),
            ("finished", 3, 0),
        ]
        assert len(engine.saved) == 3
        assert engine.closed == 3
        assert engine.quit_called is True

    def test_partial_failure_continues(self, no_com, tmp_path):
        files = _make_files(tmp_path, ["a.docx", "bad.docx", "c.docx"])
        engine = FakeOfficeEngine(fail_open_paths={files[1]})
        events = _collect(engine)

        engine.convert(files)

        assert ("finished", 2, 1) in events
        fail_logs = [m for k, m in [(e[0], e[1]) for e in events if e[0] == "log"] if "失败" in m]
        assert len(fail_logs) == 1
        assert "bad.docx" in fail_logs[0]
        assert len(engine.saved) == 2
        assert engine.closed == 2

    def test_stop_between_items(self, no_com, tmp_path):
        files = _make_files(tmp_path, ["a.docx", "b.docx", "c.docx"])
        engine = FakeOfficeEngine()
        events = _collect(engine)
        engine.log.connect(lambda m: engine.stop() if "✅" in m else None)

        engine.convert(files)

        assert ("finished", 1, 0) in events
        assert ("log", "任务停止") in events
        assert len(engine.opened) == 1
        assert len(engine.saved) == 1

    def test_app_creation_failure_emits_zero_counts(self, no_com, tmp_path):
        files = _make_files(tmp_path, ["a.docx"])

        class ExplodingEngine(FakeOfficeEngine):
            def _create_app(self):
                raise RuntimeError("COM unavailable")

        engine = ExplodingEngine()
        events = _collect(engine)

        engine.convert(files)

        assert ("log", "🔥 严重错误: COM unavailable") in events
        assert events[-1] == ("finished", 0, 0)
