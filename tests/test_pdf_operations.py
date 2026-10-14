import os
from pypdf import PdfReader, PdfWriter

from core.features.pdf.pdf_merger import PDFMerger
from core.features.pdf.pdf_splitter import PDFSplitter
from core.features.pdf.pdf_image_extractor import PDFImageExtractor


def _make_pdf(path, pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)


class TestPDFMergerCharacterization:
    def test_merge_two_files(self, tmp_path):
        f1 = tmp_path / "a.pdf"
        _make_pdf(str(f1), 3)
        f2 = tmp_path / "b.pdf"
        _make_pdf(str(f2), 2)
        out = tmp_path / "merged.pdf"

        events = []
        merger = PDFMerger()
        merger.finished.connect(lambda ok, msg: events.append((ok, msg)))
        merger.merge([str(f1), str(f2)], str(out))

        assert events == [(True, "成功合并 2 个文件")]
        assert len(PdfReader(str(out)).pages) == 5

    def test_merge_empty_list(self, tmp_path):
        events = []
        merger = PDFMerger()
        merger.finished.connect(lambda ok, msg: events.append((ok, msg)))
        merger.merge([], str(tmp_path / "out.pdf"))

        assert events == [(False, "文件列表为空")]
        assert not (tmp_path / "out.pdf").exists()

    def test_merge_aborts_on_unreadable(self, tmp_path):
        good = tmp_path / "ok.pdf"
        _make_pdf(str(good), 1)
        bad = tmp_path / "bad.pdf"
        bad.write_text("not a pdf")
        out = tmp_path / "out.pdf"

        events = []
        merger = PDFMerger()
        merger.finished.connect(lambda ok, msg: events.append((ok, msg)))
        merger.merge([str(good), str(bad)], str(out))

        assert len(events) == 1
        ok, msg = events[0]
        assert ok is False
        assert "读取文件" in msg and "失败" in msg
        assert not out.exists()


class TestPDFSplitterCharacterization:
    def test_split_ranges(self, tmp_path):
        src = tmp_path / "doc.pdf"
        _make_pdf(str(src), 5)

        events = []
        splitter = PDFSplitter()
        splitter.finished.connect(lambda ok, msg: events.append((ok, msg)))
        splitter.split(str(src), "1-2, 4", str(tmp_path))

        assert events == [(True, "拆分完成")]
        parts = list(tmp_path.glob("doc_part*"))
        assert sorted(p.name for p in parts) == ["doc_part1_1-2.pdf", "doc_part2_4-4.pdf"]
        counts = {p.name: len(PdfReader(str(p)).pages) for p in parts}
        assert counts["doc_part1_1-2.pdf"] == 2
        assert counts["doc_part2_4-4.pdf"] == 1

    def test_split_invalid_range_text(self, tmp_path):
        src = tmp_path / "doc.pdf"
        _make_pdf(str(src), 3)

        events = []
        splitter = PDFSplitter()
        splitter.finished.connect(lambda ok, msg: events.append((ok, msg)))
        splitter.split(str(src), "abc", str(tmp_path))

        assert events == [(False, "无效的页码范围")]

    def test_parse_ranges_variants(self):
        splitter = PDFSplitter()
        assert splitter._parse_ranges("1-5, 8, 10-end", 12) == [(1, 5), (8, 8), (10, 12)]
        assert splitter._parse_ranges("1-2，4", 5) == [(1, 2), (4, 4)]
        assert splitter._parse_ranges("3", 5) == [(3, 3)]
        assert splitter._parse_ranges("5-3", 5) == [(3, 5)]
        assert splitter._parse_ranges("0-2", 5) == [(1, 2)]
        assert splitter._parse_ranges("abc", 5) is None


class TestPDFImageExtractorCharacterization:
    def test_extract_empty_list(self, tmp_path):
        events = []
        extractor = PDFImageExtractor()
        extractor.finished.connect(lambda a, b: events.append((a, b)))
        extractor.extract([], str(tmp_path))

        assert events == [(0, 0)]

    def test_extract_skips_non_pdf(self, tmp_path):
        txt = tmp_path / "note.txt"
        txt.write_text("hello")

        events = []
        extractor = PDFImageExtractor()
        extractor.finished.connect(lambda a, b: events.append((a, b)))
        extractor.extract([str(txt)], str(tmp_path))

        assert events == [(0, 1)]

    def test_extract_blank_pdf_success_and_cleanup(self, tmp_path):
        src = tmp_path / "plain.pdf"
        _make_pdf(str(src), 2)

        events = []
        extractor = PDFImageExtractor()
        extractor.finished.connect(lambda a, b: events.append((a, b)))
        extractor.extract([str(src)], str(tmp_path))

        assert events == [(1, 0)]
        assert not (tmp_path / "plain_images").exists()
