"""完成横幅分支测试：任一失败走 warning/error，全成功才走 success。

守的缺陷类：完成回调无条件 InfoBar.success，把"部分失败"显示成绿色成功。
桩法：替换模块命名空间里的 InfoBar（接不住则 calls 为空、断言必失败）。
"""
import importlib

import pytest


def _recorder():
    class _Bar:
        def addWidget(self, w):
            self.widget = w

        def show(self):
            self.shown = True

    class _R:
        calls = []

        @classmethod
        def success(cls, *args, **kwargs):
            cls.calls.append(("success", args, kwargs))
            return _Bar()

        @classmethod
        def warning(cls, *args, **kwargs):
            cls.calls.append(("warning", args, kwargs))
            return _Bar()

        @classmethod
        def error(cls, *args, **kwargs):
            cls.calls.append(("error", args, kwargs))
            return _Bar()

    return _R


def _page(module_path, class_name, monkeypatch):
    mod = importlib.import_module(module_path)
    rec = _recorder()
    monkeypatch.setattr(mod, "InfoBar", rec)
    return getattr(mod, class_name)(), rec


def _kinds(rec):
    return [c[0] for c in rec.calls]


def test_markdown_pdf_batch_branches_on_fail(qapp, monkeypatch):
    page, rec = _page(
        "ui.interfaces.text.markdown_pdf_batch_interface",
        "MarkdownPdfBatchInterface",
        monkeypatch,
    )
    page.on_finished(2, 1)
    assert _kinds(rec) == ["warning"], f"有失败应 warning：{rec.calls}"
    assert "失败 1" in rec.calls[0][1][1], rec.calls

    rec.calls.clear()
    page.on_finished(3, 0)
    assert _kinds(rec) == ["success"], f"全成功应 success：{rec.calls}"
    page.deleteLater()


def test_pdf_compress_branches_on_fail(qapp, monkeypatch):
    page, rec = _page(
        "ui.interfaces.pdf.pdf_compress_interface",
        "PDFCompressInterface",
        monkeypatch,
    )
    page.on_finished(1, 3)
    assert _kinds(rec) == ["warning"], f"有失败应 warning：{rec.calls}"
    assert "失败 3" in rec.calls[0][1][1], rec.calls

    rec.calls.clear()
    page.on_finished(4, 0)
    assert _kinds(rec) == ["success"], f"全成功应 success：{rec.calls}"
    page.deleteLater()


def test_pdf_render_branches_on_fail(qapp, monkeypatch):
    page, rec = _page(
        "ui.interfaces.pdf.pdf_render_interface",
        "PDFRenderInterface",
        monkeypatch,
    )
    page.on_finished(2, 5)
    assert _kinds(rec) == ["warning"], f"有失败应 warning：{rec.calls}"
    assert "失败 5" in rec.calls[0][1][1], rec.calls

    rec.calls.clear()
    page.on_finished(6, 0)
    assert _kinds(rec) == ["success"], f"全成功应 success：{rec.calls}"
    assert "成功渲染 6 个文件" in rec.calls[0][1][1], rec.calls
    page.deleteLater()


def test_pdf_image_extract_branches_on_fail(qapp, monkeypatch):
    page, rec = _page(
        "ui.interfaces.pdf.pdf_image_extract_interface",
        "PDFImageExtractInterface",
        monkeypatch,
    )
    page.on_finished(0, 4)
    assert _kinds(rec) == ["warning"], f"有失败应 warning：{rec.calls}"

    rec.calls.clear()
    page.on_finished(4, 0)
    assert _kinds(rec) == ["success"], f"全成功应 success：{rec.calls}"
    page.deleteLater()


def test_image_pdf_uses_converter_result(qapp, monkeypatch):
    """converter 的 (ok, msg) 必须经桥接信号抵达，而不是固定绿横幅。"""
    page, rec = _page(
        "ui.interfaces.image.image_pdf_interface",
        "ImagePdfInterface",
        monkeypatch,
    )
    page.on_finished(False, "没有输入文件")
    assert _kinds(rec) == ["error"], f"失败应 error：{rec.calls}"
    assert "没有输入文件" in rec.calls[0][1][1], rec.calls

    rec.calls.clear()
    page.on_finished(True, "C:/out.pdf")
    assert _kinds(rec) == ["success"], f"成功应 success：{rec.calls}"

    assert page._finished_bridged is not None, "缺桥接信号则 converter 结果永远到不了界面"
    page.deleteLater()


def test_image_pdf_wires_converter_finished_callback(qapp):
    """接线检查：WorkerThread 必须收到 on_finished，否则结果被丢弃。"""
    from ui.threads import WorkerThread

    import inspect

    src = inspect.getsource(
        importlib.import_module("ui.interfaces.image.image_pdf_interface")
        .ImagePdfInterface.start_conversion
    )
    assert "on_finished=self._finished_bridged.emit" in src, (
        "start_conversion 未把 converter 的 on_finished 接进 WorkerThread"
    )
    assert "thread.finished.connect(self.on_finished)" not in src, (
        "thread.finished 载荷是 convert() 返回值（None），不得当结果用"
    )
    assert WorkerThread  # import 探针，确保依赖在


def test_batch_rename_branches_on_partial_failure(qapp, monkeypatch):
    """execute 返回 (成功数, 失败数) 且从不抛异常，部分失败也走 finished。"""
    page, rec = _page(
        "ui.interfaces.utils.batch_rename_interface",
        "BatchRenameInterface",
        monkeypatch,
    )
    page.on_rename_finished((2, 1))
    assert _kinds(rec) == ["warning"], f"部分失败应 warning：{rec.calls}"
    assert "失败 1" in rec.calls[0][1][1], rec.calls

    rec.calls.clear()
    page.on_rename_finished((5, 0))
    assert _kinds(rec) == ["success"], f"全成功应 success：{rec.calls}"
    page.deleteLater()


def test_pdf_pages_progress_state_tracks_failures(qapp, monkeypatch):
    """进度条状态须与横幅同向——set_complete 原为硬编码 True，与横幅脱节。"""
    for path, cls in (
        ("ui.interfaces.pdf.pdf_compress_interface", "PDFCompressInterface"),
        ("ui.interfaces.pdf.pdf_render_interface", "PDFRenderInterface"),
        ("ui.interfaces.pdf.pdf_image_extract_interface", "PDFImageExtractInterface"),
    ):
        page, rec = _page(path, cls, monkeypatch)

        page.on_finished(1, 3)
        assert page.progress.cancel_btn.text() == "失败", (
            f"{cls} 有失败时进度条应显示'失败'，实得 {page.progress.cancel_btn.text()!r}"
        )
        assert page.progress.progress_bar.status_label.text() == "处理失败", cls

        rec.calls.clear()
        page.on_finished(4, 0)
        assert page.progress.cancel_btn.text() == "完成", (
            f"{cls} 全成功时进度条应显示'完成'，实得 {page.progress.cancel_btn.text()!r}"
        )
        page.deleteLater()


def test_watermark_banner_uses_real_success_count(qapp, monkeypatch):
    """error 路径也会计入总数，故全失败必须走 warning。"""
    page, rec = _page(
        "ui.interfaces.image.watermark_remove_interface",
        "WatermarkRemoveInterface",
        monkeypatch,
    )
    page.total_count = 2
    page.finished_count = 0
    page.success_count = 0

    page.on_one_finished(False, "boom1")
    page.on_one_finished(False, "boom2")
    assert _kinds(rec) == ["warning"], f"全失败应 warning：{rec.calls}"
    assert "成功 0" in rec.calls[0][2]["content"], rec.calls

    rec.calls.clear()
    page.total_count = 2
    page.finished_count = 0
    page.success_count = 0
    page.on_one_finished(True, "a.png")
    page.on_one_finished(True, "b.png")
    assert _kinds(rec) == ["success"], f"全成功应 success：{rec.calls}"
    assert "成功处理 2 个图片" in rec.calls[0][2]["content"], rec.calls
    page.deleteLater()


def test_image_vector_counts_failures_and_reports(qapp, monkeypatch):
    """失败必须推进计数并计入横幅——原为 basename(None) 抛异常后计数器停在 0。"""
    page, rec = _page(
        "ui.interfaces.image.image_vector_interface",
        "ImageVectorInterface",
        monkeypatch,
    )
    page.total = 2
    page.finished_count = 0
    page.success_count = 0
    page.last_output = None

    page.on_one_finished(False, "bad input")
    assert page.finished_count == 1, "失败也必须推进计数，否则卡死"

    page.on_one_finished(True, r"C:\out\a.svg")
    assert page.finished_count == 2, "成功推进计数"
    assert page.start_btn.isEnabled(), "完成后按钮必须恢复"
    assert _kinds(rec) == ["warning"], f"有失败应 warning：{rec.calls}"
    assert "成功 1, 失败 1" in rec.calls[0][2]["content"], rec.calls
    assert page.last_output == r"C:\out\a.svg", "成功产出路径要留给'打开所在文件夹'"
    page.deleteLater()


def test_image_vector_wires_converter_result_callback(qapp):
    """接线检查：converter 的 (ok, msg) 必须到界面；thread.finished 载荷是 None。"""
    import inspect

    src = inspect.getsource(
        importlib.import_module(
            "ui.interfaces.image.image_vector_interface"
        ).ImageVectorInterface.start_conversion
    )
    assert "on_finished=self._finished_bridged.emit" in src, (
        "start_conversion 未把 converter 的 on_finished 接进 WorkerThread"
    )
    assert "thread.finished.connect" not in src, (
        "thread.finished 载荷是 convert() 返回值 None → 槽内 basename(None) 抛异常 → 计数卡死"
    )


def test_vectorizer_captures_panic_as_failure(tmp_path):
    """vtracer 的 Rust panic 是 PanicException（非 Exception），必须转成失败回调。"""
    pytest.importorskip("vtracer")
    from core.features.image.image_vectorizer import ImageVectorizer

    events = []
    ImageVectorizer().convert(
        str(tmp_path / "missing.png"),
        str(tmp_path / "out.svg"),
        on_finished=lambda ok, msg: events.append((ok, msg)),
    )

    assert len(events) == 1, "PanicException 必须被捕获并转成回调，不得向上逃逸"
    assert events[0][0] is False, f"应为失败：{events}"
    assert events[0][1], "失败必须带原因"
