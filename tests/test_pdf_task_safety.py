from threading import Event

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from core.features.pdf.pdf_image_extractor import PDFImageExtractor
from core.features.pdf.pdf_merger import PDFMerger
from core.features.pdf.pdf_splitter import PDFSplitter
from core.utils.atomic_output import atomic_output


@pytest.fixture
def pdf_job(tmp_path, request):
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    writer.write(source)
    if request.param == "merge":
        output = tmp_path / "merged.pdf"

        def execute(**kwargs):
            return PDFMerger().merge([str(source)], str(output), **kwargs)
    else:
        output = tmp_path / "source_part1_1-3.pdf"

        def execute(**kwargs):
            return PDFSplitter().split(str(source), "1-3", str(tmp_path), **kwargs)
    output.write_bytes(b"previous output")
    return output, execute


@pytest.mark.parametrize("pdf_job", ["merge", "split"], indirect=True)
def test_failed_pdf_write_preserves_previous_output(pdf_job, monkeypatch):
    output, execute = pdf_job
    previous_entries = set(output.parent.iterdir())
    outcomes = []

    def broken_write(self, stream):
        stream.write(b"partial PDF")
        raise OSError("disk write failed")

    monkeypatch.setattr(PdfWriter, "write", broken_write)
    execute(on_finished=lambda ok, message: outcomes.append(ok))

    assert outcomes == [False]
    assert output.read_bytes() == b"previous output"
    assert set(output.parent.iterdir()) == previous_entries


@pytest.mark.parametrize("pdf_job", ["merge", "split"], indirect=True)
def test_cancel_during_pages_stops_before_writing(pdf_job, monkeypatch):
    output, execute = pdf_job
    cancelled = Event()
    added = []
    add_page = PdfWriter.add_page

    def cancel_after_page(self, page, *args, **kwargs):
        result = add_page(self, page, *args, **kwargs)
        added.append(page)
        cancelled.set()
        return result

    monkeypatch.setattr(PdfWriter, "add_page", cancel_after_page)

    result = execute(should_cancel=cancelled.is_set)

    assert len(added) == 1
    assert output.read_bytes() == b"previous output"
    assert result.status.value == "cancelled"


@pytest.mark.parametrize("pdf_job", ["merge", "split"], indirect=True)
def test_cancel_during_write_does_not_publish_partial_result(pdf_job, monkeypatch):
    output, execute = pdf_job
    previous_entries = set(output.parent.iterdir())
    cancelled = Event()
    write = PdfWriter.write

    def cancel_after_write(self, stream):
        result = write(self, stream)
        cancelled.set()
        return result

    monkeypatch.setattr(PdfWriter, "write", cancel_after_write)

    result = execute(should_cancel=cancelled.is_set)

    assert output.read_bytes() == b"previous output"
    assert set(output.parent.iterdir()) == previous_entries
    assert result.status.value == "cancelled"


@pytest.mark.parametrize("pdf_job", ["merge", "split"], indirect=True)
def test_successful_pdf_replaces_previous_output(pdf_job):
    output, execute = pdf_job
    outcomes = []

    execute(on_finished=lambda ok, message: outcomes.append(ok))

    assert outcomes == [True]
    assert len(PdfReader(output).pages) == 3


def test_merge_rejects_output_aliasing_input(tmp_path):
    source = tmp_path / "input.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(source)
    original = source.read_bytes()
    outcomes = []

    PDFMerger().merge(
        [str(source)], str(source),
        on_finished=lambda ok, message: outcomes.append(ok),
    )

    assert outcomes == [False]
    assert source.read_bytes() == original


def test_atomic_output_supports_windows_maximum_filename(tmp_path):
    target = tmp_path / ("a" * 244 + ".pdf")

    with atomic_output(target) as stream:
        stream.write(b"complete")

    assert target.read_bytes() == b"complete"


def test_extract_cancel_keeps_completed_image_and_skips_following_pages(tmp_path):
    source = tmp_path / "photos.pdf"
    with Image.new("RGB", (24, 24), "red") as first:
        with Image.new("RGB", (24, 24), "blue") as second:
            first.save(source, save_all=True, append_images=[second])
    cancelled = Event()
    output = tmp_path / "photos_images"
    outcomes = []

    def cancel_after_image(message):
        if output.exists() and any(output.iterdir()):
            cancelled.set()

    result = PDFImageExtractor().extract(
        [str(source)], str(tmp_path), should_cancel=cancelled.is_set,
        on_log=cancel_after_image,
        on_finished=lambda ok, fail: outcomes.append((ok, fail)),
    )

    images = list(output.iterdir())
    assert len(images) == 1
    with Image.open(images[0]) as image:
        assert image.size == (24, 24)
    assert outcomes == []
    assert result.status.value == "cancelled"
