"""Text 家族功能级 E2E（真实输入 → 跑一遍 → 断言产出物）。

清单：.omo/feature-e2e-plan.md 批 2。本批全部四个模块此前零测试覆盖。

铁律：这批模块全部把异常吞进回调，必须断言载荷。
本机实测：pandoc 3.12.1 可用、xelatex 缺失、fpdf2 已装。
"""
import shutil

import pytest

from core.features.text.code_extractor import CodeExtractor
from core.features.text.markdown_converter import MarkdownConverter
from core.features.text.markdown_pdf_pandoc import PandocMarkdownToPdf
from core.features.text.txt_converter import TxtConverter


def _has_pandoc() -> bool:
    tool = __import__(
        "core.external_tools.manager", fromlist=["ExternalToolManager"]
    ).ExternalToolManager().get_tool("pandoc")
    return bool(tool) and tool.check_installed()


# ---------- 6. CodeExtractor：目录树递归合并到单文件 ----------


def test_code_extractor_merges_only_requested_extensions(tmp_path):
    root = tmp_path / "src"
    (root / "sub").mkdir(parents=True)
    (root / "a.py").write_text("print(1)\n", encoding="utf-8")
    (root / "sub" / "b.c").write_text("int main(){}\n", encoding="utf-8")
    (root / "c.txt").write_text("IGNORED\n", encoding="utf-8")
    out = tmp_path / "merged.txt"

    events = []
    CodeExtractor().extract(
        str(root),
        [".py", ".c"],
        str(out),
        on_finished=lambda ok, msg: events.append((ok, msg)),
    )

    assert len(events) == 1, "on_finished 必须恰好一次"
    assert events[0][0] is True, f"载荷异常：{events}"

    text = out.read_text(encoding="utf-8", errors="replace")
    assert "print(1)" in text and "int main" in text, "两个 .py/.c 内容都应合入"
    assert "IGNORED" not in text, ".txt 不在 extensions 内，不应被合入"
    assert "=" * 50 in text and "File: " in text, "缺少分隔符契约"


def test_code_extractor_zero_match_reports_failure(tmp_path):
    root = tmp_path / "only_txt"
    root.mkdir()
    (root / "x.txt").write_text("n\n", encoding="utf-8")
    out = tmp_path / "out.txt"

    events = []
    CodeExtractor().extract(
        str(root), [".py"], str(out), on_finished=lambda ok, msg: events.append((ok, msg))
    )

    assert len(events) == 1
    assert events[0][0] is False, f"0 匹配必须报失败，实得：{events[0]}"
    assert "未找到匹配的文件" in events[0][1], f"失败需说明原因，实得：{events[0][1]}"


def test_code_extractor_zero_match_preserves_existing_output(tmp_path):
    root = tmp_path / "only_txt"
    root.mkdir()
    (root / "x.txt").write_text("n\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    out.write_text("PRECIOUS USER CONTENT\n", encoding="utf-8")

    events = []
    CodeExtractor().extract(
        str(root), [".py"], str(out), on_finished=lambda ok, msg: events.append((ok, msg))
    )

    assert events[0][0] is False
    assert out.read_text(encoding="utf-8") == "PRECIOUS USER CONTENT\n", (
        "0 匹配不得截断用户已有的输出文件"
    )


def test_code_extract_rejects_empty_extensions(qapp, monkeypatch, tmp_path):
    import importlib

    mod = importlib.import_module("ui.interfaces.text.code_extract_interface")
    calls = []

    class _Rec:
        @staticmethod
        def error(title, msg, **kwargs):
            calls.append(msg)

        @staticmethod
        def success(title, msg, **kwargs):
            calls.append(msg)

    monkeypatch.setattr(mod, "InfoBar", _Rec)

    page = mod.CodeExtractInterface()
    root = tmp_path / "src"
    root.mkdir()
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    page.dir_edit.setText(str(root))
    page.ext_edit.setText("  ,  ")
    page.out_edit.setText(str(tmp_path / "out.txt"))

    page.start_extract()

    assert any("扩展名" in m for m in calls), f"空扩展名必须前置报错，实得：{calls}"
    assert page.thread is None, "空扩展名不得启动线程"
    page.deleteLater()


# ---------- 7. TxtConverter：txt → PDF（fpdf2，纯 Python） ----------


def test_txt_to_pdf_produces_pdf(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()  # 产品不自动建输出目录，fpdf 会抛异常并计入 fail
    src = tmp_path / "sample.txt"
    src.write_text("中文测试 English line\n第二行\n", encoding="utf-8")

    events = []
    TxtConverter().convert(
        [str(src)],
        output_dir=str(out_dir),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"载荷异常：{events}"
    pdf = out_dir / "sample.pdf"
    assert pdf.exists(), "未产出 PDF"
    assert pdf.read_bytes()[:4] == b"%PDF", "魔数应为 %PDF"


def test_txt_to_pdf_reports_missing_output_dir(tmp_path):
    """负向：输出目录不存在必须计入失败，而不是静默产出到别处。"""
    src = tmp_path / "s.txt"
    src.write_text("x\n", encoding="utf-8")
    missing = tmp_path / "nope"

    events = []
    TxtConverter().convert(
        [str(src)],
        output_dir=str(missing),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], f"输出目录缺失应报 (0,1)：{events}"


# ---------- 8. PandocMarkdownToPdf：xelatex 缺失分支 ----------


def test_pandoc_pdf_reports_missing_pdf_engine(tmp_path):
    if shutil.which("xelatex"):
        pytest.skip("本机有 xelatex，本负向用例不适用")

    src = tmp_path / "doc.md"
    src.write_text("# 标题\n\n内容\n", encoding="utf-8")
    logs, events = [], []
    PandocMarkdownToPdf().convert_batch(
        [str(src)],
        output_dir=str(tmp_path),
        on_log=logs.append,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], f"缺 xelatex 应报 (0,1)：{events}"
    assert any("PDF 引擎" in m for m in logs), f"缺少引擎缺失日志：{logs}"
    assert not (tmp_path / "doc.pdf").exists(), "引擎缺失时不应产出文件"


def test_pandoc_pdf_reports_missing_pandoc(tmp_path, monkeypatch):
    """负向双保险：pandoc 缺席路径与 xelatex 缺席路径必须是不同日志。"""
    converter = PandocMarkdownToPdf()
    monkeypatch.setattr(converter, "is_available", lambda: False)

    src = tmp_path / "d.md"
    src.write_text("x\n", encoding="utf-8")
    logs, events = [], []
    converter.convert_batch(
        [str(src)],
        output_dir=str(tmp_path),
        on_log=logs.append,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], f"缺 pandoc 应报 (0,1)：{events}"
    assert any("Pandoc 未安装" in m for m in logs), f"日志：{logs}"


def test_pandoc_pdf_converts_markdown_when_engine_installed(tmp_path):
    if not shutil.which("xelatex") or not _has_pandoc():
        pytest.skip("xelatex/pandoc 缺失，正向用例不适用")

    src = tmp_path / "doc.md"
    src.write_text("# Title\n\nhello **world**\n", encoding="utf-8")
    events = []
    PandocMarkdownToPdf().convert_batch(
        [str(src)],
        output_dir=str(tmp_path),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"载荷异常：{events}"
    out = tmp_path / "doc.pdf"
    assert out.exists(), "未产出 pdf"
    assert out.read_bytes()[:4] == b"%PDF", "不是合法 PDF"


# ---------- 9. MarkdownConverter：pandoc 分支（此前只测了纯 Python 分支） ----------


def _convert_md(conv, src, out_dir, use_pandoc):
    events = []
    conv.convert_markdown_to_html(
        [str(src)],
        output_dir=str(out_dir),
        use_pandoc=use_pandoc,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )
    assert events == [(1, 0)], f"载荷异常（use_pandoc={use_pandoc}）：{events}"
    return (out_dir / "doc.html").read_text(encoding="utf-8", errors="replace")


def test_markdown_pandoc_branch_differs_from_basic(tmp_path):
    """两分支都产完整 HTML 且载荷都是 (1,0)——必须靠内容判别分支真的换了。

    实测判别标记（本机 pandoc 3.12.1）：
      basic  → 含自定义 CSS `-apple-system`，无 pandoc 标记
      pandoc → 含 `<meta name="generator" content="pandoc ...">`，无 -apple-system
    """
    if not _has_pandoc():
        pytest.skip("pandoc 缺失")

    src = tmp_path / "doc.md"
    src.write_text("# 标题\n\n正文 **粗体**\n\n```python\nprint(1)\n```\n", encoding="utf-8")

    basic_dir = tmp_path / "basic"
    pandoc_dir = tmp_path / "pandoc"
    basic_dir.mkdir()
    pandoc_dir.mkdir()

    converter = MarkdownConverter()
    basic_html = _convert_md(converter, src, basic_dir, use_pandoc=False)
    pandoc_html = _convert_md(converter, src, pandoc_dir, use_pandoc=True)

    assert "pandoc" not in basic_html, "basic 分支不应引入 pandoc 标记"
    assert "-apple-system" in basic_html, "basic 分支应含自定义 CSS 模板"

    assert 'content="pandoc' in pandoc_html, (
        f"pandoc 分支未走 pandoc，产出与 basic 同源：{pandoc_html[:200]!r}"
    )
    assert "-apple-system" not in pandoc_html, "pandoc 分支不应套 basic 的 CSS 模板"


def test_markdown_pandoc_branch_reports_failure_when_binary_missing(tmp_path, monkeypatch):
    """负向：勾了 pandoc 但路径取不到时应计入 fail，而不是静默成功。"""
    converter = MarkdownConverter()
    monkeypatch.setattr(converter, "is_pandoc_available", lambda: True)
    monkeypatch.setattr(converter.pandoc_tool, "get_path", lambda: None)

    src = tmp_path / "x.md"
    src.write_text("x\n", encoding="utf-8")
    events = []
    converter.convert_markdown_to_html(
        [str(src)],
        output_dir=str(tmp_path),
        use_pandoc=True,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], f"pandoc 路径取不到应计入 fail：{events}"
