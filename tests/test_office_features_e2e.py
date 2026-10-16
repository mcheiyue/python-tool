"""Office 家族功能级 E2E（真实输入 → 跑一遍 → 断言产出物）。

清单：.omo/feature-e2e-plan.md 批 1。
铁律：所有转换器把异常吞进回调，on_finished 收不到值就等于没通过——
每条用例都必须断言载荷，不能只看"没抛异常"。
本机实测（2026-10-16）：MS Office COM 三件可用、pandoc 3.12.1 可用、LibreOffice 未装。
"""
import pytest

from core.features.office.doc_to_docx_converter import DocToDocxConverter
from core.features.office.libreoffice_converter import LibreOfficeFormatConverter
from core.features.office.ppt_image_exporter import PPTImageExporter
from core.features.office.word_converter import WordConverter


# ---------- 缺失工具探测（清单 §2：前置探测，不靠回调值区分） ----------


def _com_available(progid: str) -> bool:
    """COM 可用性探测。

    ppt/doc 转换器没有 is_available API，且其缺失回调是 (0, 0)——与
    "成功 0 失败 0" 不可区分，因此只能前置试启动再退出，不能靠回调判定。
    """
    try:
        import win32com.client
    except Exception:
        return False
    try:
        app = win32com.client.Dispatch(progid)
    except Exception:
        return False
    try:
        if hasattr(app, "Quit"):
            app.Quit()
    except Exception:
        pass
    return True


def _has_pandoc() -> bool:
    tool = __import__(
        "core.external_tools.manager", fromlist=["ExternalToolManager"]
    ).ExternalToolManager().get_tool("pandoc")
    return bool(tool) and tool.check_installed()


@pytest.fixture(scope="module")
def pptx_file(tmp_path_factory):
    """用本机 PowerPoint 造一个真 pptx（仓库内无现成输入夹具）。"""
    if not _com_available("PowerPoint.Application"):
        pytest.skip("PowerPoint 不可用")
    path = tmp_path_factory.mktemp("ppt") / "sample.pptx"
    try:
        _build_pptx(str(path))
    except Exception as e:  # COM 自动化在无人值守环境下可能被策略阻断
        pytest.skip(f"无法用 PowerPoint 构造样例：{e}")
    return str(path)


@pytest.fixture(scope="module")
def doc_file(tmp_path_factory):
    """用本机 Word 造一个真 .doc（doc_to_docx 的唯一合法输入）。"""
    if not _com_available("Word.Application"):
        pytest.skip("Word 不可用")
    path = tmp_path_factory.mktemp("doc") / "sample.doc"
    try:
        _build_doc(str(path))
    except Exception as e:
        pytest.skip(f"无法用 Word 构造样例：{e}")
    return str(path)


def _build_pptx(path: str) -> None:
    import win32com.client

    app = win32com.client.Dispatch("PowerPoint.Application")
    try:
        pres = app.Presentations.Add(WithWindow=False)  # ppLayoutBlank 需真演示文稿对象
        pres.Slides.Add(1, 12)  # 12 = ppLayoutBlank
        pres.SaveAs(path)  # 由扩展名推断 pptx
        pres.Close()
    finally:
        app.Quit()


def _build_doc(path: str) -> None:
    import win32com.client

    app = win32com.client.Dispatch("Word.Application")
    app.Visible = False
    app.DisplayAlerts = 0
    try:
        doc = app.Documents.Add()
        doc.Content.Text = "office e2e fixture"
        doc.SaveAs2(path, FileFormat=0)  # 0 = wdFormatDocument97 (.doc)
        doc.Close(False)
    finally:
        app.Quit()


# ---------- 1. WordConverter：md → docx → md 双向（pandoc，无需 Office） ----------


def _run_cv(run, files, output_dir):
    """收集 (success, fail) 载荷——载荷缺失即失败，绝不静默通过。"""
    events = []
    run(files, output_dir=output_dir, on_finished=lambda ok, fail: events.append((ok, fail)))
    return events


def test_markdown_to_docx_and_back(tmp_path):
    if not _has_pandoc():
        pytest.skip("pandoc 缺失")

    converter = WordConverter()
    src = tmp_path / "doc.md"
    src.write_text("# 标题\n\n正文 **粗体**\n", encoding="utf-8")

    events = _run_cv(converter.convert_markdown_to_docx, [str(src)], str(tmp_path))
    assert events == [(1, 0)], f"md→docx 载荷异常：{events}"

    docx = tmp_path / "doc.docx"
    assert docx.exists(), "md→docx 未产出 docx"
    assert docx.read_bytes()[:2] == b"PK", "docx 是 zip 容器，魔数应为 PK"

    events = _run_cv(converter.convert_docx_to_markdown, [str(docx)], str(tmp_path))
    assert events == [(1, 0)], f"docx→md 载荷异常：{events}"

    back = tmp_path / "doc.md"
    assert back.exists()
    text = back.read_text(encoding="utf-8", errors="replace")
    assert "标题" in text and "粗体" in text, f"回转丢内容：{text!r}"


def test_word_converter_missing_pandoc_reports_failure(tmp_path, monkeypatch):
    """负向：pandoc 缺席必须报 (0, N)，而不是静默成功。"""
    converter = WordConverter()
    monkeypatch.setattr(converter, "is_pandoc_available", lambda: False)

    src = tmp_path / "a.md"
    src.write_text("x\n", encoding="utf-8")
    logs, events = [], []
    converter.convert_markdown_to_docx(
        [str(src)],
        output_dir=str(tmp_path),
        on_log=logs.append,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], f"缺 pandoc 时应报 (0,1)：{events}"
    assert any("Pandoc" in m for m in logs), f"缺少错误日志：{logs}"


# ---------- 2. PPTImageExporter（真 PowerPoint COM） ----------


def test_ppt_export_slides_to_png(pptx_file, tmp_path):
    events = []
    exporter = PPTImageExporter()
    exporter.export(
        [pptx_file],
        str(tmp_path),
        "PNG",
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"导出载荷异常：{events}"

    stem = "sample"
    pngs = sorted((tmp_path / stem).glob("Slide*.png"))
    assert pngs, f"未产出任何幻灯片图片：{list((tmp_path / stem).iterdir())}"
    assert pngs[0].stat().st_size > 0, "产出的图片为空文件"


# ---------- 3. DocToDocxConverter（真 Word COM） ----------


def test_doc_converted_to_docx(doc_file, tmp_path):
    events = []
    converter = DocToDocxConverter()
    converter.convert(
        [doc_file],
        str(tmp_path),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(1, 0)], f"转换载荷异常：{events}"
    out = tmp_path / "sample.docx"
    assert out.exists(), "未产出 docx"
    assert out.read_bytes()[:2] == b"PK", "docx 魔数应为 PK"


# ---------- 3b. COM 启动失败必须报 (0, N)，不得报 (0, 0) ----------
# (0,0) 与"成功0失败0"不可区分——界面按 `if fail > 0` 分支，拿到 (0,0) 会把
# COM 根本没起来显示成"成功处理 0 个文件"；其余转换器一律报 (0, N)，此处对齐。


def _make_com_fail(monkeypatch, message):
    import comtypes.client

    def _boom(*args, **kwargs):
        raise RuntimeError(message)

    monkeypatch.setattr(comtypes.client, "CreateObject", _boom)


def test_ppt_export_reports_all_failed_when_com_unavailable(tmp_path, monkeypatch):
    _make_com_fail(monkeypatch, "PowerPoint 不可用")

    events = []
    PPTImageExporter().export(
        ["a.pptx", "b.pptx"],
        str(tmp_path),
        "PNG",
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 2)], (
        f"COM 启动失败应报 (0, 文件数)，实得 {events}——"
        "(0,0) 会让界面把失败显示成成功"
    )


def test_doc_convert_reports_all_failed_when_com_unavailable(tmp_path, monkeypatch):
    _make_com_fail(monkeypatch, "Word 不可用")

    src = tmp_path / "a.doc"
    src.write_bytes(b"fake")
    events = []
    DocToDocxConverter().convert(
        [str(src)],
        str(tmp_path),
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], (
        f"COM 启动失败应报 (0, 文件数)，实得 {events}"
    )


# ---------- 4. LibreOfficeFormatConverter（本机未装 → 验缺失分支走对） ----------


def test_libreoffice_missing_reports_not_installed(tmp_path):
    converter = LibreOfficeFormatConverter()
    if converter.is_available():
        pytest.skip("本机已装 LibreOffice，本负向用例不适用")

    src = tmp_path / "in.md"
    src.write_text("x\n", encoding="utf-8")
    logs, events = [], []
    converter.convert_batch(
        [str(src)],
        "pdf",
        output_dir=str(tmp_path),
        on_log=logs.append,
        on_finished=lambda ok, fail: events.append((ok, fail)),
    )

    assert events == [(0, 1)], f"缺 LO 时应报 (0,1)：{events}"
    assert any("未安装" in m for m in logs), f"缺少未安装日志：{logs}"
    assert not (tmp_path / "in.pdf").exists(), "缺工具时不应产出文件"


# ---------- 5. OfficeConvertInterface 3 合 1（构造 + 过滤 + 按钮态） ----------


def test_three_in_one_pages_construct_with_live_signals(qapp):
    """三个薄子类构造期即 connect 三信号——任一引擎缺信号则整页崩。"""
    from core.external_tools.manager import ExternalToolManager
    from ui.interfaces.office.office_convert_interface import (
        ExcelInterface,
        PPTInterface,
        WordInterface,
    )

    ExternalToolManager()  # 引擎选择依赖它
    for cls, object_name, title, engine_attr in (
        (WordInterface, "word_interface", "Word 转 PDF", "word_engine"),
        (ExcelInterface, "excel_interface", "Excel 转 PDF", "excel_engine"),
        (PPTInterface, "ppt_interface", "PowerPoint 转 PDF", "ppt_engine"),
    ):
        page = cls()
        assert page.objectName() == object_name, f"{cls.__name__} objectName 漂移"
        assert page.title.text() == title, f"{cls.__name__} 标题漂移"
        assert page.engine_attr == engine_attr, f"{cls.__name__} 引擎属性漂移"

        # 构造期已完成 connect，引擎必须带三个信号（LibreOffice 引擎是独立子类）
        for signal_name in ("log", "progress", "finished"):
            assert hasattr(page.converter, signal_name), (
                f"{cls.__name__} 的 {page.engine_attr} 缺 {signal_name} 信号，"
                "构造期 connect 会崩"
            )
        page.deleteLater()


def test_word_page_filters_extensions_and_toggles_start_button(qapp):
    """拖拽过滤 + 按钮态：文件被拒时不得放行，清空后不得可点。"""
    from ui.interfaces.office.office_convert_interface import WordInterface

    page = WordInterface()
    assert not page.start_btn.isEnabled(), "初始应禁用"

    page.on_files_dropped(["any.docx", "any.txt", "any.doc"])
    assert page.list_widget.count() == 2, "应只收 .doc/.docx，拒 .txt"
    assert page.start_btn.isEnabled(), "有合法文件后应启用"

    page.clear_files()
    assert page.list_widget.count() == 0
    assert not page.start_btn.isEnabled(), "清空后应重新禁用"
    page.deleteLater()
