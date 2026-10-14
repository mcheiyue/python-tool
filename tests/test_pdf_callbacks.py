from PIL import Image

from core.features.pdf.pdf_page_renderer import PDFPageRenderer
from core.features.pdf.image_to_pdf_converter import ImageToPdfConverter


def test_render_all_emits_callbacks(sample_pdf, tmp_path):
    renderer = PDFPageRenderer()
    logs, events = [], []

    renderer.render_all(
        [str(sample_pdf)], str(tmp_path), dpi=72,
        on_log=logs.append,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)]
    assert logs
    assert len(list(tmp_path.glob("*_pages/page_*.png"))) == 1


def test_image_to_pdf_merge_emits_callbacks(tmp_path):
    img = tmp_path / "in.png"
    Image.new("RGB", (10, 10), "red").save(img)
    out = tmp_path / "out.pdf"

    logs, events = [], []
    converter = ImageToPdfConverter()
    converter.convert(
        [str(img)], str(out), True,
        on_log=logs.append,
        on_finished=lambda ok, msg: events.append((ok, msg)),
    )

    assert events == [(True, str(out))]
    assert out.exists()
    assert logs


def test_image_to_pdf_empty_input_reports_failure():
    events = []
    converter = ImageToPdfConverter()
    converter.convert([], "unused.pdf", True, on_finished=lambda ok, msg: events.append((ok, msg)))

    assert events == [(False, "没有输入文件")]
