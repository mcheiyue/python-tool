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
