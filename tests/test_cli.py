import json
import subprocess
import sys
from pathlib import Path

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
