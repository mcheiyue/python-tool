import json
import subprocess
import sys
from pathlib import Path

import pytest

from PIL import Image
from pypdf import PdfReader, PdfWriter


def _make_pdf(path, pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_import_does_not_load_qt():
    completed = subprocess.run(
        [sys.executable, "-c", "import sys; import app.cli; print('PyQt6' in sys.modules)"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "False"


def test_cli_merge_returns_json_and_publishes_output(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    output = tmp_path / "merged.pdf"
    _make_pdf(first, 1)
    _make_pdf(second, 2)

    completed = _run_cli(
        "merge", str(first), str(second), "--output", str(output), "--json"
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.isascii(), "JSON stdout must be independent of Windows code page"
    assert json.loads(completed.stdout) == {
        "status": "success",
        "message": "成功合并 2 个文件",
        "outputs": [str(output)],
        "succeeded": 2,
        "failed": 0,
    }
    assert len(PdfReader(str(output)).pages) == 3


def test_cli_split_returns_output_paths(tmp_path):
    source = tmp_path / "source.pdf"
    output_dir = tmp_path / "parts"
    _make_pdf(source, 3)

    completed = _run_cli(
        "split", str(source), "1-2,3", "--output", str(output_dir), "--json"
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["succeeded"] == 2
    assert sorted(result["outputs"]) == sorted(
        str(path) for path in output_dir.glob("*.pdf")
    )


def test_cli_extract_images_reports_created_files(tmp_path):
    source = tmp_path / "photos.pdf"
    output_dir = tmp_path / "images"
    with Image.new("RGB", (24, 24), "red") as image:
        image.save(source, "PDF")

    completed = _run_cli(
        "extract-images", str(source), "--output", str(output_dir), "--json"
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["succeeded"] == 1
    assert result["outputs"]
    assert all(Path(path).is_file() for path in result["outputs"])


def test_cli_image_convert_returns_failure_for_missing_input(tmp_path):
    output = tmp_path / "missing.jpg"

    completed = _run_cli(
        "image-convert",
        str(tmp_path / "missing.png"),
        "--output",
        str(output),
        "--format",
        "JPG",
        "--json",
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "failed"
    assert result["outputs"] == []
    assert not output.exists()


def test_cli_image_convert_publishes_image(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "converted.jpg"
    Image.new("RGB", (8, 8), "red").save(source)

    completed = _run_cli(
        "image-convert",
        str(source),
        "--output",
        str(output),
        "--format",
        "JPG",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == [str(output)]
    assert Image.open(output).format == "JPEG"


def test_cli_image_colors_returns_color_data(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (32, 32), (255, 0, 0)).save(source)

    completed = _run_cli("image-colors", str(source), "--count", "3", "--json")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.isascii()
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == []
    colors = result["data"]["colors"]
    assert colors and colors[0]["hex"] == "#ff0000"


def test_cli_image_colors_reports_failure_for_missing_input(tmp_path):
    completed = _run_cli(
        "image-colors", str(tmp_path / "missing.png"), "--json"
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "failed"
    assert "data" not in result


def test_cli_image_vectorize_publishes_svg(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "out.svg"
    Image.new("RGB", (40, 40), (0, 128, 255)).save(source)

    completed = _run_cli(
        "image-vectorize", str(source), "--output", str(output), "--json"
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == [str(output)]
    assert "<svg" in output.read_text(encoding="utf-8")[:400]


def test_cli_image_to_pdf_merges_and_reports_output(tmp_path):
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    output = tmp_path / "merged.pdf"
    Image.new("RGB", (24, 24), "red").save(first)
    Image.new("RGB", (24, 24), "blue").save(second)

    completed = _run_cli(
        "image-to-pdf", str(first), str(second), "--output", str(output), "--json"
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == [str(output)]
    assert len(PdfReader(str(output)).pages) == 2


def test_cli_image_to_pdf_single_mode_reports_each_output(tmp_path):
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    output_dir = tmp_path / "singles"
    Image.new("RGB", (24, 24), "red").save(first)
    Image.new("RGB", (24, 24), "blue").save(second)

    completed = _run_cli(
        "image-to-pdf",
        str(first),
        str(second),
        "--output",
        str(output_dir),
        "--single",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["succeeded"] == 2
    assert sorted(result["outputs"]) == sorted(
        str(path) for path in output_dir.glob("*.pdf")
    )


def test_cli_text_extract_code_writes_merged_file(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.py").write_text("print('a')", encoding="utf-8")
    (source / "b.py").write_text("print('b')", encoding="utf-8")
    output = tmp_path / "all.txt"

    completed = _run_cli(
        "text-extract-code",
        str(source),
        "--extensions",
        ".py",
        "--output",
        str(output),
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == [str(output)]
    content = output.read_text(encoding="utf-8")
    assert "print('a')" in content and "print('b')" in content


def test_cli_text_extract_code_rejects_output_that_is_an_input(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    target = source / "a.py"
    target.write_text("keep me", encoding="utf-8")

    completed = _run_cli(
        "text-extract-code",
        str(source),
        "--extensions",
        ".py",
        "--output",
        str(target),
        "--json",
    )

    assert completed.returncode == 1
    assert json.loads(completed.stdout)["status"] == "failed"
    assert target.read_text(encoding="utf-8") == "keep me"


def test_cli_text_txt_to_pdf_converts_file(tmp_path):
    source = tmp_path / "note.txt"
    source.write_text("hello world", encoding="utf-8")

    completed = _run_cli("text-txt-to-pdf", str(source), "--json")

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["succeeded"] == 1
    assert result["outputs"] == [str(tmp_path / "note.pdf")]
    assert (tmp_path / "note.pdf").is_file()


def test_cli_files_rename_preview_returns_plan_data(tmp_path):
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    Image.new("RGB", (8, 8), "red").save(first)
    Image.new("RGB", (8, 8), "blue").save(second)

    completed = _run_cli(
        "files-rename-preview",
        str(first),
        str(second),
        "--template",
        "{index3}_{name}.{ext}",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == []
    plan = result["data"]["plan"]
    assert [item["new_name"] for item in plan] == ["001_a.png", "002_b.png"]


def test_cli_files_rename_preview_reports_conflicts_as_failure(tmp_path):
    source = tmp_path / "a.png"
    Image.new("RGB", (8, 8), "red").save(source)

    completed = _run_cli(
        "files-rename-preview",
        str(source),
        "--template",
        "{name}.{ext}",
        "--json",
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "failed"
    assert result["data"]["plan"][0]["conflict"] is True

def _require_ghostscript():
    pytest.importorskip("pytest")
    from core.external_tools.manager import ExternalToolManager

    tool = ExternalToolManager().get_tool("ghostscript")
    path = tool.get_path() if tool and not tool.is_disabled else None
    if not path:
        pytest.skip("Ghostscript 未安装")
    return path


def test_cli_pdf_compress_publishes_smaller_file(tmp_path):
    _require_ghostscript()
    source = tmp_path / "doc.pdf"
    _make_pdf(source, 2)

    completed = _run_cli("pdf-compress", str(source), "--quality", "/screen", "--json")

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["succeeded"] == 1
    output = Path(result["outputs"][0])
    assert output.is_file()
    assert output.name == "doc_compressed.pdf"
    assert len(PdfReader(str(output)).pages) == 2


def test_cli_pdf_compress_reports_missing_ghostscript(monkeypatch, tmp_path):
    import app.cli as cli

    monkeypatch.setattr(cli, "_ghostscript_path", lambda: None)
    source = tmp_path / "doc.pdf"
    _make_pdf(source, 1)

    result = cli._execute(
        cli.build_parser().parse_args(
            ["pdf-compress", str(source), "--json"]
        ),
        lambda: False,
    )

    assert result.status.value == "failed"
    assert "Ghostscript" in result.message
    assert result.outputs == ()


def test_cli_pdf_render_writes_pages(tmp_path):
    source = tmp_path / "doc.pdf"
    output_dir = tmp_path / "pages"
    _make_pdf(source, 2)

    completed = _run_cli(
        "pdf-render", str(source), "--output", str(output_dir), "--dpi", "72", "--json"
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert len(result["outputs"]) == 2
    assert all(Path(path).is_file() for path in result["outputs"])


def test_cli_pdf_render_honours_page_range(tmp_path):
    source = tmp_path / "doc.pdf"
    output_dir = tmp_path / "pages"
    _make_pdf(source, 3)

    completed = _run_cli(
        "pdf-render",
        str(source),
        "--output",
        str(output_dir),
        "--dpi",
        "72",
        "--first-page",
        "2",
        "--last-page",
        "2",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert len(result["outputs"]) == 1
    assert result["outputs"][0].endswith("page_0002.png")


def test_cli_pdf_render_reports_invalid_page_range(tmp_path):
    source = tmp_path / "doc.pdf"
    _make_pdf(source, 2)

    completed = _run_cli(
        "pdf-render",
        str(source),
        "--output",
        str(tmp_path / "pages"),
        "--first-page",
        "2",
        "--last-page",
        "1",
        "--json",
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "failed"
    assert "页码范围无效" in result["message"]


def test_cli_markdown_html_round_trip(tmp_path):
    source = tmp_path / "note.md"
    source.write_text("# Title\n\nSome **bold** text.\n", encoding="utf-8")
    html_dir = tmp_path / "html"
    md_dir = tmp_path / "md"

    first = _run_cli(
        "text-markdown-html",
        str(source),
        "--direction",
        "md-to-html",
        "--output-dir",
        str(html_dir),
        "--json",
    )
    assert first.returncode == 0, first.stderr
    html_path = Path(json.loads(first.stdout)["outputs"][0])
    assert html_path.is_file()
    assert "<h1" in html_path.read_text(encoding="utf-8")

    second = _run_cli(
        "text-markdown-html",
        str(html_path),
        "--direction",
        "html-to-md",
        "--output-dir",
        str(md_dir),
        "--json",
    )
    assert second.returncode == 0, second.stderr
    md_path = Path(json.loads(second.stdout)["outputs"][0])
    assert md_path.is_file()
    assert "Title" in md_path.read_text(encoding="utf-8")


def test_cli_markdown_html_creates_missing_output_dir(tmp_path):
    source = tmp_path / "note.md"
    source.write_text("# T\n", encoding="utf-8")
    output_dir = tmp_path / "nested" / "deep"

    completed = _run_cli(
        "text-markdown-html",
        str(source),
        "--direction",
        "md-to-html",
        "--output-dir",
        str(output_dir),
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    assert output_dir.is_dir()
    assert Path(json.loads(completed.stdout)["outputs"][0]).is_file()


def test_cli_markdown_batch_pdf_reports_missing_pdf_engine(tmp_path):
    source = tmp_path / "note.md"
    source.write_text("# T\n", encoding="utf-8")

    completed = _run_cli(
        "text-markdown-batch-pdf",
        str(source),
        "--pdf-engine",
        "definitely-not-a-real-engine",
        "--json",
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "failed"
    assert "definitely-not-a-real-engine" in result["message"]


def test_cli_markdown_batch_pdf_fails_when_pandoc_absent(monkeypatch, tmp_path):
    import app.cli as cli
    from core.features.text import markdown_pdf_pandoc

    monkeypatch.setattr(
        markdown_pdf_pandoc.PandocMarkdownToPdf,
        "is_available",
        lambda self: False,
    )
    source = tmp_path / "note.md"
    source.write_text("# T\n", encoding="utf-8")

    result = cli._execute(
        cli.build_parser().parse_args(
            ["text-markdown-batch-pdf", str(source), "--json"]
        ),
        lambda: False,
    )

    assert result.status.value == "failed"
    assert "Pandoc" in result.message


def test_cli_libreoffice_convert_reports_missing_tool(monkeypatch, tmp_path):
    import app.cli as cli
    from core.features.office import libreoffice_converter

    monkeypatch.setattr(
        libreoffice_converter.LibreOfficeFormatConverter,
        "is_available",
        lambda self: False,
    )
    source = tmp_path / "doc.docx"
    source.write_bytes(b"not really docx")

    result = cli._execute(
        cli.build_parser().parse_args(
            ["office-libreoffice-convert", str(source), "--to", "pdf", "--json"]
        ),
        lambda: False,
    )

    assert result.status.value == "failed"
    assert "LibreOffice" in result.message


def test_cli_word_markdown_reports_missing_pandoc(monkeypatch, tmp_path):
    import app.cli as cli
    from core.features.office import word_converter

    monkeypatch.setattr(
        word_converter.WordConverter, "is_pandoc_available", lambda self: False
    )
    source = tmp_path / "note.md"
    source.write_text("# T\n", encoding="utf-8")

    result = cli._execute(
        cli.build_parser().parse_args(
            ["office-word-markdown", str(source), "--direction", "md-to-docx", "--json"]
        ),
        lambda: False,
    )

    assert result.status.value == "failed"
    assert "Pandoc" in result.message


def _make_pdf_with_images(path, pages=2):
    with Image.new("RGB", (32, 32), "red") as image:
        image.save(path, "PDF")


def test_pdf_renderer_uses_ghostscript_when_pymupdf_missing(monkeypatch, tmp_path):
    from core.features.pdf import pdf_page_renderer

    _require_ghostscript()
    monkeypatch.setattr(pdf_page_renderer, "PYMUPDF_AVAILABLE", False)
    monkeypatch.setattr(pdf_page_renderer, "fitz", None)

    source = tmp_path / "doc.pdf"
    _make_pdf(source, 3)
    output_dir = tmp_path / "out"
    renderer = pdf_page_renderer.PDFPageRenderer()
    result = {}

    renderer.render_all(
        [str(source)],
        str(output_dir),
        dpi=72,
        use_ghostscript=True,
        on_finished=lambda ok, fail: result.update(ok=ok, fail=fail),
    )

    assert result == {"ok": 1, "fail": 0}
    assert len(list((output_dir / "doc_pages").glob("*.png"))) == 3


def test_ghostscript_page_count_handles_windows_path(monkeypatch, tmp_path):
    from core.features.pdf import pdf_page_renderer

    _require_ghostscript()
    source = tmp_path / "doc.pdf"
    _make_pdf(source, 4)

    renderer = pdf_page_renderer.PDFPageRenderer()
    assert renderer._count_pages_with_ghostscript(str(source)) == 4


def test_cli_pdf_render_auto_falls_back_when_pymupdf_missing(monkeypatch, tmp_path):
    from core.features.pdf import pdf_page_renderer

    _require_ghostscript()
    monkeypatch.setattr(pdf_page_renderer, "PYMUPDF_AVAILABLE", False)
    monkeypatch.setattr(pdf_page_renderer, "fitz", None)
    source = tmp_path / "doc.pdf"
    _make_pdf(source, 2)

    import app.cli as cli

    result = cli._execute(
        cli.build_parser().parse_args(
            [
                "pdf-render",
                str(source),
                "-o",
                str(tmp_path / "out"),
                "--dpi",
                "72",
                "--json",
            ]
        ),
        lambda: False,
    )

    assert result.status.value == "success"
    assert len(result.outputs) == 2


def test_cli_pdf_render_auto_reports_when_no_engine(monkeypatch, tmp_path):
    from core.features.pdf import pdf_page_renderer

    monkeypatch.setattr(pdf_page_renderer, "PYMUPDF_AVAILABLE", False)
    monkeypatch.setattr(pdf_page_renderer, "fitz", None)
    monkeypatch.setattr(
        pdf_page_renderer.PDFPageRenderer, "is_gs_available", lambda self: False
    )
    source = tmp_path / "doc.pdf"
    _make_pdf(source, 1)

    import app.cli as cli

    result = cli._execute(
        cli.build_parser().parse_args(
            ["pdf-render", str(source), "-o", str(tmp_path / "out"), "--dpi", "72"]
        ),
        lambda: False,
    )

    assert result.status.value == "failed"
    assert "渲染引擎" in result.message


def _require_office():
    import comtypes.client

    try:
        app = comtypes.client.CreateObject("Word.Application", dynamic=True)
    except Exception:
        pytest.skip("未安装 Microsoft Office")
    try:
        app.Quit()
    except Exception:
        pass


def _make_docx(path):
    import docx

    document = docx.Document()
    document.add_paragraph("cli office smoke")
    document.save(path)


def _make_xlsx(path):
    import openpyxl

    workbook = openpyxl.Workbook()
    workbook.active["A1"] = "cli"
    workbook.save(path)


def _make_pptx(path, slides=2):
    from pptx import Presentation

    presentation = Presentation()
    for _ in range(slides):
        presentation.slides.add_slide(presentation.slide_layouts[1])
    presentation.save(path)


def test_cli_office_word_to_pdf(tmp_path):
    _require_office()
    source = tmp_path / "a.docx"
    _make_docx(source)

    completed = _run_cli("office-word-to-pdf", str(source), "--json")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == [str(source.with_suffix(".pdf"))]
    assert result["data"]["backend"] == "Microsoft Word"
    assert source.with_suffix(".pdf").is_file()


def test_cli_office_excel_to_pdf(tmp_path):
    _require_office()
    source = tmp_path / "b.xlsx"
    _make_xlsx(source)

    completed = _run_cli("office-excel-to-pdf", str(source), "--json")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["data"]["backend"] == "Microsoft Excel"
    assert source.with_suffix(".pdf").is_file()


def test_cli_office_ppt_to_pdf(tmp_path):
    _require_office()
    source = tmp_path / "deck.pptx"
    _make_pptx(source)

    completed = _run_cli("office-ppt-to-pdf", str(source), "--json")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["data"]["backend"] == "Microsoft PowerPoint"
    assert source.with_suffix(".pdf").is_file()


def test_cli_office_ppt_to_images(tmp_path):
    _require_office()
    source = tmp_path / "deck.pptx"
    output_dir = tmp_path / "imgs"
    _make_pptx(source, slides=2)

    completed = _run_cli(
        "office-ppt-to-images", str(source), "--output-dir", str(output_dir), "--json"
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert len(result["outputs"]) == 2
    assert all(Path(path).is_file() for path in result["outputs"])


def test_cli_office_doc_to_docx(tmp_path):
    _require_office()
    import comtypes.client

    source = tmp_path / "a.docx"
    _make_docx(source)
    legacy = tmp_path / "legacy.doc"

    comtypes.CoInitialize()
    word = comtypes.client.CreateObject("Word.Application", dynamic=True)
    try:
        word.Visible = False
        document = word.Documents.Open(str(source), False, True, False)
        document.SaveAs2(str(legacy), 0)
        document.Close(0)
    finally:
        word.Quit()
        comtypes.CoUninitialize()

    output_dir = tmp_path / "out"
    completed = _run_cli(
        "office-doc-to-docx", str(legacy), "--output-dir", str(output_dir), "--json"
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["outputs"] == [str(output_dir / "legacy.docx")]
    assert (output_dir / "legacy.docx").is_file()


def test_cli_office_to_pdf_reports_failure_when_no_backend(monkeypatch, tmp_path):
    import app.cli as cli
    from core.engines.office import word as word_module

    def boom(self):
        raise OSError("no office")

    monkeypatch.setattr(word_module.WordEngine, "_create_app", boom)
    source = tmp_path / "a.docx"
    source.write_bytes(b"not a real docx")

    result = cli._execute(
        cli.build_parser().parse_args(
            [
                "office-word-to-pdf",
                str(source),
                "--no-libreoffice-fallback",
                "--json",
            ]
        ),
        lambda: False,
    )

    assert result.status.value == "failed"
    assert result.succeeded == 0


def test_cli_office_to_pdf_falls_back_to_libreoffice(monkeypatch, tmp_path):
    import app.cli as cli
    from core.engines.office import libreoffice as lo_module
    from core.engines.office import word as word_module

    def boom(self):
        raise OSError("no office")

    monkeypatch.setattr(word_module.WordEngine, "_create_app", boom)
    monkeypatch.setattr(
        lo_module.LibreOfficeEngine, "convert", lambda self, paths: (1, 0)
    )
    source = tmp_path / "a.docx"
    source.write_bytes(b"not a real docx")

    result = cli._execute(
        cli.build_parser().parse_args(["office-word-to-pdf", str(source), "--json"]),
        lambda: False,
    )

    assert result.data["backend"] == "LibreOffice"
    assert result.succeeded == 1


def test_cli_office_keeps_success_when_cancel_arrives_after_last_file(
    monkeypatch, tmp_path
):
    import app.cli as cli
    from core.engines.office import libreoffice as lo_module
    from core.engines.office import word as word_module

    def boom(self):
        raise OSError("no office")

    monkeypatch.setattr(word_module.WordEngine, "_create_app", boom)
    monkeypatch.setattr(
        lo_module.LibreOfficeEngine, "convert", lambda self, paths: (1, 0)
    )
    source = tmp_path / "a.docx"
    source.write_bytes(b"not a real docx")

    result = cli._execute(
        cli.build_parser().parse_args(["office-word-to-pdf", str(source), "--json"]),
        lambda: True,
    )

    assert result.status.value == "success"
    assert result.succeeded == 1


def test_cli_office_reports_cancelled_when_interrupted(monkeypatch, tmp_path):
    import app.cli as cli
    from core.engines.office import libreoffice as lo_module
    from core.engines.office import word as word_module

    def boom(self):
        raise OSError("no office")

    monkeypatch.setattr(word_module.WordEngine, "_create_app", boom)
    # 两个输入只完成一个：留下未处理的文件，才是真正的中途中断
    monkeypatch.setattr(
        lo_module.LibreOfficeEngine, "convert", lambda self, paths: (1, 0)
    )
    sources = [tmp_path / name for name in ("a.docx", "b.docx")]
    for source in sources:
        source.write_bytes(b"not a real docx")

    result = cli._execute(
        cli.build_parser().parse_args(
            ["office-word-to-pdf", *(str(p) for p in sources), "--json"]
        ),
        lambda: True,
    )

    assert result.status.value == "cancelled"


import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _make_png(path, size=(1200, 1200)):
    from PIL import Image

    Image.new("RGB", size, (40, 70, 100)).save(path)


def _run_watermark(tmp_path, *extra):
    from app.cli import _execute, build_parser

    source = tmp_path / "shot.png"
    _make_png(source)
    args = build_parser().parse_args(
        ["image-remove-watermark", str(source), *extra, "--json"]
    )
    return _execute(args, lambda: False), source


def test_cli_remove_watermark_writes_beside_source(tmp_path):
    result, source = _run_watermark(tmp_path)

    expected = source.with_name("shot_clean.png")
    assert result.status.value == "success"
    assert result.outputs == (str(expected),)
    assert expected.is_file()


def test_cli_remove_watermark_honours_output_dir(tmp_path):
    target_dir = tmp_path / "out"
    result, _ = _run_watermark(tmp_path, "-o", str(target_dir))

    expected = target_dir / "shot_clean.png"
    assert result.status.value == "success"
    assert result.outputs == (str(expected),)
    assert expected.is_file()


def test_cli_remove_watermark_reports_missing_input(tmp_path):
    from app.cli import _execute, build_parser

    missing = tmp_path / "nope.png"
    args = build_parser().parse_args(
        ["image-remove-watermark", str(missing), "--json"]
    )

    result = _execute(args, lambda: False)

    assert result.status.value == "failed"
    assert result.failed == 1


def test_cli_remove_watermark_processes_every_file(tmp_path):
    from app.cli import _execute, build_parser
    from PIL import Image

    sources = []
    for name in ("a.png", "b.png"):
        path = tmp_path / name
        Image.new("RGB", (600, 600), (20, 40, 60)).save(path)
        sources.append(str(path))

    args = build_parser().parse_args(
        ["image-remove-watermark", *sources, "--json"]
    )
    result = _execute(args, lambda: False)

    assert result.status.value == "success"
    assert result.succeeded == 2
    assert len(result.outputs) == 2


def test_cli_markdown_to_pdf_builtin_writes_single_page(tmp_path):
    from app.cli import _execute, build_parser
    from pypdf import PdfReader

    source = tmp_path / "note.md"
    source.write_text("# Title\n\nHello world.\n", encoding="utf-8")
    args = build_parser().parse_args(
        ["text-markdown-to-pdf", str(source), "--engine", "builtin", "--json"]
    )

    result = _execute(args, lambda: False)

    expected = tmp_path / "note.pdf"
    assert result.status.value == "success"
    assert result.outputs == (str(expected),)
    assert result.data["engine"] == "builtin"
    reader = PdfReader(str(expected))
    assert len(reader.pages) == 1
    assert "Hello world" in reader.pages[0].extract_text()


def test_cli_markdown_to_pdf_reports_pandoc_requirement(tmp_path):
    from app.cli import _execute, build_parser

    source = tmp_path / "note.md"
    source.write_text("text\n", encoding="utf-8")
    args = build_parser().parse_args(
        ["text-markdown-to-pdf", str(source), "--engine", "pandoc", "--json"]
    )

    result = _execute(args, lambda: False)

    if result.status.value == "failed":
        assert "Pandoc" in result.message
    else:
        assert result.data["engine"] == "pandoc"


def test_cli_markdown_to_pdf_honours_output_dir(tmp_path):
    from app.cli import _execute, build_parser

    source = tmp_path / "note.md"
    source.write_text("body\n", encoding="utf-8")
    target_dir = tmp_path / "pdf"
    args = build_parser().parse_args(
        [
            "text-markdown-to-pdf",
            str(source),
            "-o",
            str(target_dir),
            "--engine",
            "builtin",
            "--json",
        ]
    )

    result = _execute(args, lambda: False)

    expected = target_dir / "note.pdf"
    assert result.status.value == "success"
    assert result.outputs == (str(expected),)
    assert expected.is_file()


def test_cli_markdown_to_pdf_json_is_ascii(tmp_path):
    import subprocess
    import sys

    source = tmp_path / "note.md"
    source.write_text("body\n", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "text-markdown-to-pdf",
            str(source),
            "--engine",
            "builtin",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        cwd=ROOT,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().isascii()
    assert json.loads(completed.stdout)["status"] == "success"
