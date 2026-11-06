import os
from pathlib import Path

import pytest

from core.features.text.code_extractor import CodeExtractor


@pytest.mark.parametrize("linked_output", [False, True])
def test_extract_rejects_output_that_is_an_input(tmp_path, linked_output):
    root = tmp_path / "src"
    root.mkdir()
    source = root / "main.py"
    source.write_text("print('keep source')\n", encoding="utf-8")
    output = tmp_path / "alias.txt" if linked_output else source
    if linked_output:
        os.link(source, output)
    events = []

    CodeExtractor().extract(
        str(root), [".py"], str(output),
        on_finished=lambda ok, message: events.append(ok),
    )

    assert events == [False]
    assert source.read_text(encoding="utf-8") == "print('keep source')\n"
    assert output.read_text(encoding="utf-8") == "print('keep source')\n"


def test_extract_read_failure_preserves_previous_output(tmp_path, monkeypatch):
    root = tmp_path / "src"
    root.mkdir()
    source = root / "main.py"
    source.write_text("print(1)", encoding="utf-8")
    output = tmp_path / "merged.txt"
    output.write_text("previous export", encoding="utf-8")
    original_open = open

    def deny_source(file, mode="r", *args, **kwargs):
        if Path(file) == source and mode == "r":
            raise PermissionError("source is unreadable")
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", deny_source)
    events = []

    CodeExtractor().extract(
        str(root), [".py"], str(output),
        on_finished=lambda ok, message: events.append(ok),
    )

    assert events == [False]
    assert output.read_text(encoding="utf-8") == "previous export"
