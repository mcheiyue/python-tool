"""Markdown 转换链特征测试（蓝图 §4：纯文本输入，pandoc 缺席走纯 Python 分支）。

锁定 R6 改写后的 MarkdownConverter 回调契约与纯 Python 分支行为。
Pandoc 分支不在本测试范围（需真装 pandoc + LaTeX），由界面手工冒烟覆盖。
"""
import pytest

from core.features.text.markdown_converter import MarkdownConverter


class _FakePandocTool:
    """pandoc 缺席替身，强制走纯 Python 分支"""

    def check_installed(self):
        return False

    def get_path(self):
        return None


@pytest.fixture
def converter(monkeypatch):
    c = MarkdownConverter()
    c.pandoc_tool = _FakePandocTool()
    return c


def _run(callable_, **kwargs):
    events = {"logs": [], "finished": []}
    callable_(
        on_log=events["logs"].append,
        on_finished=lambda ok, fail: events["finished"].append((ok, fail)),
        **kwargs,
    )
    return events


def test_md_to_html_basic(converter, tmp_path):
    src = tmp_path / "doc.md"
    src.write_text("# 标题\n\n正文 **粗体**\n\n```python\nprint(1)\n```\n", encoding="utf-8")

    events = _run(converter.convert_markdown_to_html, files=[str(src)], output_dir=str(tmp_path))

    out = tmp_path / "doc.html"
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "<h1" in html and "标题" in html
    assert "<strong>粗体</strong>" in html
    assert "<code" in html
    assert events["finished"] == [(1, 0)]


def test_html_to_md_basic(converter, tmp_path):
    src = tmp_path / "page.html"
    src.write_text("<h1>Title</h1><p>Hello <a href='http://x'>link</a></p>", encoding="utf-8")

    events = _run(converter.convert_html_to_markdown, files=[str(src)], output_dir=str(tmp_path))

    out = tmp_path / "page.md"
    assert out.exists()
    md = out.read_text(encoding="utf-8")
    assert "Title" in md and "link" in md
    assert events["finished"] == [(1, 0)]


def test_missing_input_counts_as_failure(converter, tmp_path):
    events = _run(
        converter.convert_markdown_to_html,
        files=[str(tmp_path / "nope.md")],
        output_dir=str(tmp_path),
    )

    assert events["finished"] == [(0, 1)]
    assert not (tmp_path / "nope.html").exists()


def test_stop_halts_batch(converter, tmp_path):
    files = []
    for i in range(3):
        p = tmp_path / f"f{i}.md"
        p.write_text(f"# doc {i}", encoding="utf-8")
        files.append(str(p))

    # 循环头检查 _is_running：progress 在检查之后触发，
    # 故在 curr==0 停止时仅处理完第 0 个文件，其余跳过
    events = {"finished": []}

    def on_progress(curr, total, msg):
        if curr == 0:
            converter.stop()

    converter.convert_markdown_to_html(
        files, str(tmp_path),
        on_progress=on_progress,
        on_finished=lambda ok, fail: events["finished"].append((ok, fail)),
    )

    assert events["finished"] == [(1, 0)]
    assert not (tmp_path / "f1.html").exists()


def test_log_and_progress_callbacks(converter, tmp_path):
    src = tmp_path / "x.md"
    src.write_text("# hi", encoding="utf-8")

    logs, progress = [], []
    converter.convert_markdown_to_html(
        [str(src)], str(tmp_path),
        on_log=logs.append,
        on_progress=lambda c, t, m: progress.append((c, t)),
    )

    assert any("成功" in m for m in logs)
    assert (0, 1) in progress and (1, 1) in progress
