from importlib import import_module
from threading import Event

import pytest
from PyQt6.QtCore import Qt
from pypdf import PdfReader, PdfWriter

from core import task_registry


@pytest.mark.parametrize("operation", ["merge", "split", "extract"])
def test_pdf_page_cancel_restores_controls_and_allows_successful_retry(qtbot, monkeypatch, tmp_path, operation):
    registry = task_registry.TaskRegistry()
    monkeypatch.setattr(task_registry, "registry", registry)
    source = tmp_path / "input.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    writer.write(source)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    entered, release = Event(), Event()

    def delayed_reader(*args, **kwargs):
        reader = PdfReader(*args, **kwargs)
        entered.set()
        release.wait(10)
        return reader

    if operation == "merge":
        from ui.interfaces.pdf.pdf_merge_interface import PDFMergeInterface

        page = PDFMergeInterface()
        page.on_files_dropped([str(source)])
        output = output_dir / "merged.pdf"
        page.out_edit.setText(str(output))
        start = page.start_merge
        module = "pdf_merger"
    elif operation == "split":
        from ui.interfaces.pdf.pdf_split_interface import PDFSplitInterface

        page = PDFSplitInterface()
        page.file_edit.setText(str(source))
        page.range_edit.setText("1-3")
        page.out_edit.setText(str(output_dir))
        output = output_dir / "input_part1_1-3.pdf"
        start = page.start_split
        module = "pdf_splitter"
    else:
        from ui.interfaces.pdf.pdf_image_extract_interface import PDFImageExtractInterface

        page = PDFImageExtractInterface()
        page.on_files_dropped([str(source)])
        page.out_edit.setText(str(output_dir))
        output = None
        start = page.start_extract
        module = "pdf_image_extractor"
    if output is not None:
        output.write_bytes(b"previous output")
    monkeypatch.setattr(import_module(f"core.features.pdf.{module}"), "PdfReader", delayed_reader)
    qtbot.addWidget(page)
    page.show()
    try:
        qtbot.mouseClick(page.start_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(entered.is_set)
        first_worker = page.thread
        terminal = []
        first_worker.cancelled.connect(lambda: terminal.append("cancelled"))
        assert not page.start_btn.isEnabled()
        assert not page.out_edit.isEnabled()
        start()
        assert page.thread is first_worker
        qtbot.mouseClick(page.progress.cancel_btn, Qt.MouseButton.LeftButton)
        assert not page.start_btn.isEnabled()
        release.set()
        qtbot.waitUntil(lambda: page.start_btn.isEnabled())
        assert terminal == ["cancelled"]
        assert page.progress.cancel_btn.text() == "已取消"
        assert page.out_edit.isEnabled()
        if output is not None:
            assert output.read_bytes() == b"previous output"
        else:
            assert not [path for path in output_dir.rglob("*") if path.is_file()]

        qtbot.mouseClick(page.start_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: page.start_btn.isEnabled())
        assert page.progress.cancel_btn.text() == "完成"
        if output is not None:
            assert len(PdfReader(output).pages) == 3
    finally:
        release.set()
        if page.thread is not None:
            assert page.thread.wait(2000)
        qtbot.waitUntil(lambda: not registry.has_active())
        registry.deleteLater()
