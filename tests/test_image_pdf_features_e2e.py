"""Image + Pdf 家族功能级 E2E（真实输入 → 跑一遍 → 断言产出物）。

清单：.omo/feature-e2e-plan.md 批 3。本批四个模块此前零测试覆盖
（pdf_page_renderer 只有单页 smoke）。

本机实测：pypdf / PIL / PyMuPDF 全可用；Ghostscript 未装
→ use_ghostscript=True 应静默回退 PyMuPDF 而非报错。
"""
import re

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from core.engines.pdf.ghostscript import GhostscriptCompressor
from core.features.image.color_extractor import ColorExtractor
from core.features.image.image_converter import ImageConverter
from core.features.pdf.image_to_pdf_converter import ImageToPdfConverter
from core.features.pdf.pdf_page_renderer import PDFPageRenderer


def _make_png(path, color):
    Image.new("RGB", (8, 8), color).save(path)
    return str(path)


def _make_pdf(path, pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)
    return str(path)


# ---------- 10. ImageConverter：单文件格式转换 ----------


def test_image_converter_png_to_jpg(tmp_path):
    src = _make_png(tmp_path / "a.png", (255, 0, 0))
    out = tmp_path / "a.jpg"

    events = []
    ImageConverter().convert(
        src, str(out), "JPG", on_finished=lambda ok, msg: events.append((ok, msg))
    )

    assert events[0][0] is True, f"转换失败：{events}"
    assert events[0][1] == str(out), "成功时 msg 应为产出路径"
    assert Image.open(out).format == "JPEG", "实际格式与请求不符"


def test_image_converter_reports_missing_input(tmp_path):
    out = tmp_path / "nope.jpg"
    events = []
    ImageConverter().convert(
        str(tmp_path / "missing.png"),
        str(out),
        "JPG",
        on_finished=lambda ok, msg: events.append((ok, msg)),
    )

    assert events[0][0] is False, f"缺输入应报失败：{events}"
    assert not out.exists(), "失败时不应产出文件"


# ---------- 11. ImageToPdfConverter：合并模式页数 = 图片数 ----------


def test_image_to_pdf_merge_page_count(tmp_path):
    paths = [
        _make_png(tmp_path / "a.png", (255, 0, 0)),
        _make_png(tmp_path / "b.png", (0, 255, 0)),
        _make_png(tmp_path / "c.jpg", (0, 0, 255)),
    ]
    out = tmp_path / "merged.pdf"

    events = []
    ImageToPdfConverter().convert(
        paths, str(out), True, on_finished=lambda ok, msg: events.append((ok, msg))
    )

    assert events[0][0] is True, f"转换失败：{events}"
    assert events[0][1] == str(out), "成功时 msg 应为产出路径"
    assert len(PdfReader(str(out)).pages) == 3, "PDF 页数必须等于图片数"
    assert out.read_bytes()[:4] == b"%PDF", "魔数应为 %PDF"


def test_image_to_pdf_empty_input_reports_failure(tmp_path):
    events = []
    ImageToPdfConverter().convert(
        [], str(tmp_path / "x.pdf"), on_finished=lambda ok, msg: events.append((ok, msg))
    )

    assert events == [(False, "没有输入文件")], f"空输入载荷异常：{events}"
    assert not (tmp_path / "x.pdf").exists()


def test_image_to_pdf_single_mode_one_file_per_image(tmp_path):
    paths = [
        _make_png(tmp_path / "one.png", (1, 2, 3)),
        _make_png(tmp_path / "two.png", (4, 5, 6)),
    ]
    out_dir = tmp_path / "single"

    events = []
    ImageToPdfConverter().convert(
        paths, str(out_dir), False, on_finished=lambda ok, msg: events.append((ok, msg))
    )

    assert events[0][0] is True, f"单图模式失败：{events}"
    assert (out_dir / "one.pdf").exists() and (out_dir / "two.pdf").exists(), (
        "单图模式应每图一个 PDF"
    )
    assert "成功转换 2 个文件" in events[0][1], f"计数消息：{events[0][1]}"


# ---------- 12. ColorExtractor：纯色图取主色（内存分析，无产出文件） ----------


def test_color_extractor_dominant_color_of_solid_image(tmp_path):
    src = _make_png(tmp_path / "solid.png", (255, 0, 0))

    events = []
    ColorExtractor().extract(
        src, n_colors=4, on_finished=lambda res, err: events.append((res, err))
    )

    assert len(events) == 1, "on_finished 必须恰好一次"
    results, err = events[0]
    assert err == "", f"不应报错：{err}"
    assert results, "纯色图必须能提出颜色"

    assert len(results) <= 4, "结果数不得超过 n_colors"
    for item in results:
        assert re.fullmatch(r"#[0-9a-f]{6}", item["hex"]), f"hex 格式非法：{item}"
        assert 0 < item["proportion"] <= 1, f"占比越界：{item}"

    # 纯色图：主色应占绝对多数，且就是红色系
    assert results[0]["proportion"] > 0.9, f"主色占比异常：{results}"
    assert results[0]["hex"].startswith("#ff"), f"主色不是红色系：{results[0]}"


def test_color_extractor_reports_missing_image(tmp_path):
    events = []
    ColorExtractor().extract(
        str(tmp_path / "nope.png"), on_finished=lambda res, err: events.append((res, err))
    )

    assert len(events) == 1
    results, err = events[0]
    assert results == [] and err, f"缺图应报空结果+错误：{(results, err)}"


# ---------- 13. PDFPageRenderer：多页命名 + 页范围截断 + GS 回退 ----------


def test_render_multi_page_naming(tmp_path):
    if not PDFPageRenderer.is_available():
        pytest.skip("PyMuPDF 缺失")

    src = _make_pdf(tmp_path / "multi.pdf", 3)
    out = tmp_path / "out"

    events = []
    PDFPageRenderer().render_all(
        [src],
        str(out),
        dpi=72,
        output_format="png",
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"载荷异常：{events}"
    names = sorted(p.name for p in (out / "multi_pages").glob("page_*.png"))
    assert names == ["page_0001.png", "page_0002.png", "page_0003.png"], (
        f"命名/页数不符：{names}"
    )
    assert all((out / "multi_pages" / n).stat().st_size > 0 for n in names), "有空图片"


def test_render_page_range_is_zero_based_half_open(tmp_path):
    """page_range 契约：0 基半开区间 [start, end)，文件名仍 1 基补零。

    这里锁死语义——若有人改成闭区间或 1 基，文件集合会变。
    """
    if not PDFPageRenderer.is_available():
        pytest.skip("PyMuPDF 缺失")

    src = _make_pdf(tmp_path / "range.pdf", 4)
    out = tmp_path / "out"

    events = []
    PDFPageRenderer().render_all(
        [src],
        str(out),
        dpi=72,
        output_format="png",
        page_range=(1, 3),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"载荷异常：{events}"
    names = sorted(p.name for p in (out / "range_pages").glob("page_*.png"))
    assert names == ["page_0002.png", "page_0003.png"], (
        f"page_range=(1,3) 应只出第 2、3 页，实得 {names}"
    )


def test_render_with_ghostscript_flag_falls_back_to_pymupdf(tmp_path):
    """本机无 Ghostscript：开启 GS 应静默回退 PyMuPDF 并成功，而非整体失败。"""
    if not PDFPageRenderer.is_available():
        pytest.skip("PyMuPDF 缺失")

    renderer = PDFPageRenderer()
    if renderer.is_gs_available():
        pytest.skip("本机已装 Ghostscript，本回退用例不适用")

    src = _make_pdf(tmp_path / "fb.pdf", 2)
    out = tmp_path / "out"
    logs, events = [], []
    renderer.render_all(
        [src],
        str(out),
        dpi=72,
        output_format="png",
        use_ghostscript=True,
        on_log=logs.append,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"GS 缺失应回退并成功，实得：{events}"
    names = sorted(p.name for p in (out / "fb_pages").glob("page_*.png"))
    assert len(names) == 2, f"回退渲染页数不足：{names}"


def test_render_with_ghostscript_produces_png_when_installed(tmp_path):
    renderer = PDFPageRenderer()
    if not renderer.is_gs_available():
        pytest.skip("Ghostscript 未装，正向用例不适用")

    src = _make_pdf(tmp_path / "gs.pdf", 2)
    out = tmp_path / "page0.png"
    ok = renderer.render_with_ghostscript(src, 0, str(out), dpi=72)

    assert ok, "GS 渲染应返回 True"
    assert out.exists() and out.stat().st_size > 0, "未产出图片"
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG"


def test_ghostscript_compresses_pdf_when_installed(tmp_path):
    renderer = PDFPageRenderer()
    if not renderer.is_gs_available():
        pytest.skip("Ghostscript 未装，正向用例不适用")

    pdf = _make_pdf(tmp_path / "doc.pdf", 2)
    compressor = GhostscriptCompressor()
    events = []
    compressor.finished.connect(lambda ok, fail: events.append((ok, fail)))
    compressor.compress([pdf], "/screen", gs_path=renderer.gs_tool.get_path())

    assert events == [(1, 0)], f"载荷异常：{events}"
    out = tmp_path / "Compressed" / "doc_compressed.pdf"
    assert out.exists() and out.stat().st_size > 0, "未产出压缩产物"
    assert out.read_bytes()[:4] == b"%PDF", "产物不是 PDF"


def test_render_empty_input_reports_zero(tmp_path):
    events = []
    PDFPageRenderer().render_all(
        [],
        str(tmp_path / "out"),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 0)], f"空输入应报 (0,0)：{events}"
