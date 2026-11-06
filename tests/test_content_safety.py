"""内容安全类回归：Markdown 代码块原文、图片批量转 PDF 的部分失败、取消停止、WebP 输出。"""
import fitz
import pytest
from PIL import Image
from pypdf import PdfReader

from core.features.pdf.image_to_pdf_converter import ImageToPdfConverter
from core.features.pdf.pdf_page_renderer import PDFPageRenderer
from core.utils.md_normalizer import normalize_markdown


class TestMarkdownCodeFencePreserved:
    def test_heading_without_space_is_normalized(self):
        assert normalize_markdown("#标题") == "# 标题"

    def test_fenced_code_block_is_untouched(self):
        source = "~~~python\n#!/usr/bin/env python\n#comment\n~~~\n#标题"
        assert normalize_markdown(source) == "~~~python\n#!/usr/bin/env python\n#comment\n~~~\n# 标题"

    def test_backtick_fence_closes_after_opening(self):
        source = "```\n#not a heading\n```\n##标题"
        assert normalize_markdown(source) == "```\n#not a heading\n```\n## 标题"


def _png(path, color):
    Image.new("RGB", (40, 30), color).save(path)
    return path


class TestImageToPdfPartialFailure:
    def test_one_broken_image_is_reported_not_hidden(self, tmp_path):
        good = _png(tmp_path / "good.png", (255, 0, 0))
        broken = tmp_path / "broken.png"
        broken.write_bytes(b"not an image")

        events = []
        ImageToPdfConverter().convert(
            [good, broken], str(tmp_path / "out"), False,
            on_finished=lambda ok, msg: events.append((ok, msg)),
        )

        assert events[0][0] is False, f"部分失败不能折叠为全成功：{events}"
        assert "成功 1" in events[0][1] and "失败 1" in events[0][1]


class TestWorkerCancelStopsOwner:
    def test_cancel_calls_owner_stop(self):
        from ui.threads import WorkerThread

        class Owner:
            def __init__(self):
                self.stopped = False

            def work(self):
                return None

            def stop(self):
                self.stopped = True

        owner = Owner()
        thread = WorkerThread(owner.work)
        thread.cancel()
        assert owner.stopped is True
        assert thread._is_cancelled is True

    def test_is_busy_false_without_thread(self):
        from ui.threads import is_busy

        class Page:
            thread = None

        assert is_busy(Page()) is False


class TestRendererWebp:
    def test_pymupdf_default_path_writes_webp(self, tmp_path):
        pdf_path = tmp_path / "one.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        events = []
        PDFPageRenderer().render_all(
            [str(pdf_path)], str(tmp_path / "out"), dpi=72,
            output_format="webp", page_range=None, use_ghostscript=False,
            on_finished=lambda ok, fail: events.append((ok, fail)),
        )

        assert events == [(1, 0)], f"WebP 渲染失败：{events}"
        produced = list((tmp_path / "out" / "one_pages").glob("*.webp"))
        assert len(produced) == 1
        with Image.open(produced[0]) as image:
            assert image.format == "WEBP"
