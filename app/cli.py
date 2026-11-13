import argparse
import json
import os
import signal
import sys
from concurrent.futures import CancelledError
from dataclasses import replace
from threading import Event
from typing import Any, Callable

from core.features.image.color_extractor import ColorExtractor
from core.features.image.image_converter import ImageConverter
from core.features.image.image_vectorizer import ImageVectorizer
from core.features.pdf.image_to_pdf_converter import ImageToPdfConverter
from core.features.pdf.pdf_image_extractor import PDFImageExtractor
from core.features.pdf.pdf_merger import PDFMerger
from core.features.pdf.pdf_splitter import PDFSplitter
from core.features.text.code_extractor import CodeExtractor
from core.features.text.txt_converter import TxtConverter
from core.features.utils.batch_rename import BatchRenamer
from core.operation_result import OperationResult, OperationStatus

CANCELLABLE = frozenset({"merge", "split", "extract-images", "image-convert"})
INTERRUPTIBLE = CANCELLABLE | {"pdf-compress", "office-ppt-to-pdf", "office-word-to-pdf", "office-excel-to-pdf"}
COMPRESS_QUALITIES = ("/screen", "/ebook", "/printer", "/prepress", "/default")
_ACTIVE_STOPPERS: list[Callable[[], None]] = []


def _register_stopper(stop: Callable[[], None]) -> None:
    _ACTIVE_STOPPERS.append(stop)


def _stop_active() -> None:
    for stop in _ACTIVE_STOPPERS:
        try:
            stop()
        except Exception:
            pass
    _ACTIVE_STOPPERS.clear()


def _add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="以 JSON 输出结果",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="office-toolkit")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    commands = parser.add_subparsers(dest="command", required=True)

    merge = commands.add_parser("merge", help="合并多个 PDF")
    merge.add_argument("inputs", nargs="+", help="输入 PDF 文件")
    merge.add_argument("-o", "--output", required=True, help="输出 PDF 文件")
    _add_json_option(merge)
    merge.set_defaults(operation="merge")

    split = commands.add_parser("split", help="按页码范围拆分 PDF")
    split.add_argument("input", help="输入 PDF 文件")
    split.add_argument("ranges", help="页码范围，例如 1-3,5,end")
    split.add_argument("-o", "--output", required=True, help="输出目录")
    _add_json_option(split)
    split.set_defaults(operation="split")

    extract = commands.add_parser("extract-images", help="提取 PDF 内嵌图片")
    extract.add_argument("inputs", nargs="+", help="输入 PDF 文件")
    extract.add_argument("-o", "--output", required=True, help="输出目录")
    _add_json_option(extract)
    extract.set_defaults(operation="extract-images")

    convert = commands.add_parser("image-convert", help="转换图片格式")
    convert.add_argument("input", help="输入图片文件")
    convert.add_argument("-o", "--output", required=True, help="输出图片文件")
    convert.add_argument("-f", "--format", required=True, help="目标格式，例如 JPG")
    convert.add_argument("--quality", type=int, default=90, help="JPEG/WEBP 质量")
    convert.add_argument("--rotate", type=int, choices=(0, 90, 180, 270), default=0)
    convert.add_argument("--flip", choices=("H", "V"), default=None)
    _add_json_option(convert)
    convert.set_defaults(operation="image-convert")

    colors = commands.add_parser("image-colors", help="提取图片主色调")
    colors.add_argument("input", help="输入图片文件")
    colors.add_argument("-n", "--count", type=int, default=8, help="提取颜色数量")
    _add_json_option(colors)
    colors.set_defaults(operation="image-colors")

    vectorize = commands.add_parser("image-vectorize", help="PNG 转 SVG")
    vectorize.add_argument("input", help="输入图片文件")
    vectorize.add_argument("-o", "--output", required=True, help="输出 SVG 文件")
    _add_json_option(vectorize)
    vectorize.set_defaults(operation="image-vectorize")

    to_pdf = commands.add_parser("image-to-pdf", help="图片转 PDF")
    to_pdf.add_argument("inputs", nargs="+", help="输入图片文件")
    to_pdf.add_argument("-o", "--output", required=True, help="输出 PDF 文件或目录")
    to_pdf.add_argument(
        "--single",
        action="store_true",
        help="每张图片各生成一个 PDF；此时 --output 视为输出目录",
    )
    _add_json_option(to_pdf)
    to_pdf.set_defaults(operation="image-to-pdf")

    code = commands.add_parser("text-extract-code", help="提取目录下代码到单个文件")
    code.add_argument("root", help="待扫描的目录")
    code.add_argument(
        "-e",
        "--extensions",
        required=True,
        help="逗号分隔的扩展名，例如 .py,.md",
    )
    code.add_argument("-o", "--output", required=True, help="输出文本文件")
    _add_json_option(code)
    code.set_defaults(operation="text-extract-code")

    txt = commands.add_parser("text-txt-to-pdf", help="TXT 转 PDF")
    txt.add_argument("inputs", nargs="+", help="输入 TXT 文件")
    txt.add_argument("-o", "--output-dir", default=None, help="输出目录，默认与源文件同目录")
    _add_json_option(txt)
    txt.set_defaults(operation="text-txt-to-pdf")

    rename = commands.add_parser("files-rename-preview", help="预览批量重命名结果")
    rename.add_argument("files", nargs="+", help="待重命名的文件")
    rename.add_argument("-t", "--template", required=True, help="重命名模板")
    rename.add_argument("--start-index", type=int, default=1, help="起始序号")
    _add_json_option(rename)
    rename.set_defaults(operation="files-rename-preview")

    compress = commands.add_parser("pdf-compress", help="用 Ghostscript 压缩 PDF")
    compress.add_argument("inputs", nargs="+", help="输入 PDF 文件")
    compress.add_argument(
        "-q",
        "--quality",
        choices=COMPRESS_QUALITIES,
        default="/printer",
        help="压缩质量，默认 /printer",
    )
    _add_json_option(compress)
    compress.set_defaults(operation="pdf-compress")

    render = commands.add_parser("pdf-render", help="将 PDF 页面渲染为图片")
    render.add_argument("inputs", nargs="+", help="输入 PDF 文件")
    render.add_argument("-o", "--output", required=True, help="输出目录")
    render.add_argument("--dpi", type=int, default=150, help="渲染 DPI，默认 150")
    render.add_argument(
        "-f",
        "--format",
        choices=("png", "jpg", "jpeg", "webp"),
        default="png",
        help="输出格式，默认 png",
    )
    render.add_argument("--first-page", type=int, default=None, help="起始页（1 起）")
    render.add_argument("--last-page", type=int, default=None, help="结束页（含）")
    render.add_argument(
        "--engine",
        choices=("auto", "pymupdf", "ghostscript"),
        default="auto",
        help="渲染引擎；默认 auto 优先 PyMuPDF，不可用时回退 Ghostscript",
    )
    _add_json_option(render)
    render.set_defaults(operation="pdf-render")

    md_pdf = commands.add_parser("text-markdown-batch-pdf", help="用 Pandoc 批量将 Markdown 转 PDF")
    md_pdf.add_argument("inputs", nargs="+", help="输入 Markdown 文件")
    md_pdf.add_argument("-o", "--output-dir", default=None, help="输出目录")
    md_pdf.add_argument("--pdf-engine", default="xelatex", help="Pandoc PDF 引擎")
    md_pdf.add_argument("--template", default=None, help="自定义 Pandoc 模板")
    md_pdf.add_argument("--no-math", action="store_true", help="关闭数学公式支持")
    md_pdf.add_argument("--no-highlight", action="store_true", help="关闭代码高亮")
    _add_json_option(md_pdf)
    md_pdf.set_defaults(operation="text-markdown-batch-pdf")

    lo = commands.add_parser("office-libreoffice-convert", help="用 LibreOffice 批量转换格式")
    lo.add_argument("inputs", nargs="+", help="输入文件")
    lo.add_argument("--to", required=True, help="目标格式，例如 pdf")
    lo.add_argument("-o", "--output-dir", default=None, help="输出目录")
    _add_json_option(lo)
    lo.set_defaults(operation="office-libreoffice-convert")

    word_md = commands.add_parser("office-word-markdown", help="Word 与 Markdown 互转")
    word_md.add_argument("inputs", nargs="+", help="输入文件")
    word_md.add_argument(
        "--direction",
        choices=("docx-to-md", "md-to-docx"),
        required=True,
        help="转换方向",
    )
    word_md.add_argument("-o", "--output-dir", default=None, help="输出目录")
    word_md.add_argument("--reference-doc", default=None, help="md-to-docx 的参考文档")
    _add_json_option(word_md)
    word_md.set_defaults(operation="office-word-markdown")

    md_html = commands.add_parser("text-markdown-html", help="Markdown 与 HTML 互转")
    md_html.add_argument("inputs", nargs="+", help="输入文件")
    md_html.add_argument(
        "--direction",
        choices=("md-to-html", "html-to-md"),
        required=True,
        help="转换方向",
    )
    md_html.add_argument("-o", "--output-dir", default=None, help="输出目录")
    md_html.add_argument(
        "--use-pandoc",
        action="store_true",
        help="使用 Pandoc（需已安装），否则用内置库",
    )
    md_html.add_argument("--no-css", action="store_true", help="HTML 输出不内嵌样式")
    _add_json_option(md_html)
    md_html.set_defaults(operation="text-markdown-html")

    for name, help_text, formats in (
        ("office-ppt-to-pdf", "将 PowerPoint 转 PDF", None),
        ("office-word-to-pdf", "将 Word 转 PDF", None),
        ("office-excel-to-pdf", "将 Excel 转 PDF", None),
    ):
        office_pdf = commands.add_parser(name, help=help_text)
        office_pdf.add_argument("inputs", nargs="+", help="输入文件")
        office_pdf.add_argument(
            "--no-libreoffice-fallback",
            action="store_true",
            help="MS Office 不可用时直接失败，不回退 LibreOffice",
        )
        _add_json_option(office_pdf)
        office_pdf.set_defaults(operation=name)

    ppt_img = commands.add_parser("office-ppt-to-images", help="将 PowerPoint 幻灯片导出为图片")
    ppt_img.add_argument("inputs", nargs="+", help="输入 PPT/PPTX 文件")
    ppt_img.add_argument("-o", "--output-dir", required=True, help="输出目录")
    ppt_img.add_argument(
        "-f", "--format", choices=("PNG", "JPG", "BMP"), default="PNG", help="图片格式"
    )
    _add_json_option(ppt_img)
    ppt_img.set_defaults(operation="office-ppt-to-images")

    doc_docx = commands.add_parser("office-doc-to-docx", help="将旧版 .doc 转 .docx")
    doc_docx.add_argument("inputs", nargs="+", help="输入 .doc 文件")
    doc_docx.add_argument("-o", "--output-dir", default=None, help="输出目录")
    _add_json_option(doc_docx)
    doc_docx.set_defaults(operation="office-doc-to-docx")

    watermark = commands.add_parser(
        "image-remove-watermark", help="移除 AI 生成图片的水印（当前支持 Gemini）"
    )
    watermark.add_argument("inputs", nargs="+", help="输入图片")
    watermark.add_argument("-o", "--output-dir", default=None, help="输出目录，默认写在源文件旁")
    _add_json_option(watermark)
    watermark.set_defaults(operation="image-remove-watermark")

    md_pdf = commands.add_parser("text-markdown-to-pdf", help="将 Markdown 内容导出为 PDF")
    md_pdf.add_argument("inputs", nargs="+", help="输入 .md 文件")
    md_pdf.add_argument("-o", "--output-dir", default=None, help="输出目录，默认写在源文件旁")
    md_pdf.add_argument(
        "--engine",
        choices=("auto", "pandoc", "builtin"),
        default="auto",
        help="auto 优先 Pandoc，不可用时用内置渲染",
    )
    _add_json_option(md_pdf)
    md_pdf.set_defaults(operation="text-markdown-to-pdf")

    return parser


def _log_callback(json_mode: bool) -> Callable[[str], None] | None:
    if json_mode:
        return None
    return lambda message: print(message, file=sys.stderr)


class _LogCapture:
    """收集核心日志，使 --json 失败时也能给出原因，而不是只报失败计数。"""

    _ERROR_MARKERS = ("错误", "失败", "Error", "error", "未找到", "不支持", "未安装")

    def __init__(self, echo: bool) -> None:
        self._echo = echo
        self._lines: list[str] = []

    def __call__(self, message: str) -> None:
        text = str(message)
        self._lines.append(text)
        if self._echo:
            print(text, file=sys.stderr)

    def last_error(self) -> str:
        for line in reversed(self._lines):
            stripped = line.strip()
            if stripped and any(marker in stripped for marker in self._ERROR_MARKERS):
                return stripped
        return ""

    def __bool__(self) -> bool:
        return True


def _existing(*paths: str | None) -> tuple[str, ...]:
    return tuple(path for path in paths if path and os.path.exists(path))


def _ensure_dir(path: str | None) -> str | None:
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def _pdf_outputs_for(sources: list[str], output_dir: str | None) -> tuple[str, ...]:
    paths = []
    for source in sources:
        directory = output_dir or os.path.dirname(os.path.abspath(source))
        candidate = os.path.join(
            directory, os.path.splitext(os.path.basename(source))[0] + ".pdf"
        )
        if os.path.exists(candidate):
            paths.append(candidate)
    return tuple(paths)


def _run_ok_msg(
    command: Callable[..., None],
    *,
    collect_outputs: Callable[[], tuple[str, ...]],
) -> OperationResult:
    captured: dict[str, Any] = {}

    def on_finished(ok, msg):
        captured["ok"] = bool(ok)
        captured["msg"] = msg

    command(on_finished=on_finished)
    outputs = collect_outputs()
    if not captured:
        return OperationResult.failure("核心操作未返回完成通知", outputs=outputs)
    if captured["ok"]:
        return OperationResult.success(
            str(captured.get("msg") or "已完成"),
            outputs=outputs,
            succeeded=len(outputs) or 1,
        )
    return OperationResult.failure(str(captured.get("msg") or "失败"), outputs=outputs)


def _run_color_extraction(command: Callable[..., None]) -> OperationResult:
    captured: dict[str, Any] = {}

    def on_finished(results, error_msg):
        captured["results"] = results
        captured["error"] = error_msg

    command(on_finished=on_finished)
    colors = captured.get("results")
    if not colors:
        return OperationResult.failure(str(captured.get("error") or "未提取到颜色"))
    return OperationResult.success(
        f"提取到 {len(colors)} 种颜色",
        succeeded=1,
        data={"colors": list(colors)},
    )


def _run_counts(command: Callable[..., None]) -> tuple[int, int] | None:
    captured: dict[str, Any] = {}

    def on_finished(success, fail):
        captured["success"] = success
        captured["fail"] = fail

    command(on_finished=on_finished)
    if not captured:
        return None
    return captured["success"], captured["fail"]


def _result_from_counts(
    counts: tuple[int, int] | None,
    outputs: tuple[str, ...],
    *,
    success_message: str,
    failure_message: str,
    hint: str = "",
) -> OperationResult:
    if counts is None:
        return OperationResult.failure("核心操作未返回完成通知", outputs=outputs)
    success, fail = counts
    message = (
        failure_message.format(success=success, fail=fail)
        if fail
        else success_message.format(success=success)
    )
    if fail and hint:
        message = f"{message}: {hint}"
    if success == 0:
        return OperationResult.failure(message, succeeded=0, failed=fail)
    if fail:
        return OperationResult.failure(
            message, outputs=outputs, succeeded=success, failed=fail
        )
    return OperationResult.success(message, outputs=outputs, succeeded=success)


def _with_extension(sources: list[str], output_dir: str | None, extension: str) -> tuple[str, ...]:
    paths = []
    for source in sources:
        directory = output_dir or os.path.dirname(os.path.abspath(source))
        candidate = os.path.join(
            directory, os.path.splitext(os.path.basename(source))[0] + extension
        )
        if os.path.exists(candidate):
            paths.append(candidate)
    return tuple(paths)


def _rendered_outputs(sources: list[str], output_dir: str) -> tuple[str, ...]:
    paths = []
    for source in sources:
        folder = os.path.join(
            output_dir, os.path.splitext(os.path.basename(source))[0] + "_pages"
        )
        if os.path.isdir(folder):
            paths.extend(
                sorted(
                    os.path.join(folder, name)
                    for name in os.listdir(folder)
                    if os.path.isfile(os.path.join(folder, name))
                )
            )
    return tuple(paths)


def _exported_images(sources: list[str], output_dir: str) -> tuple[str, ...]:
    paths = []
    for source in sources:
        folder = os.path.join(output_dir, os.path.splitext(os.path.basename(source))[0])
        if os.path.isdir(folder):
            paths.extend(
                sorted(
                    os.path.join(folder, name)
                    for name in os.listdir(folder)
                    if os.path.isfile(os.path.join(folder, name))
                )
            )
    return tuple(paths)


def _ghostscript_path() -> str | None:
    from core.external_tools.manager import ExternalToolManager

    tool = ExternalToolManager().get_tool("ghostscript")
    if tool is None or tool.is_disabled:
        return None
    path = tool.get_path()
    return path if path and os.path.exists(path) else None


def _run_pdf_compress(args: argparse.Namespace, on_log) -> OperationResult:
    from core.engines.pdf.ghostscript import GhostscriptCompressor

    gs_path = _ghostscript_path()
    if not gs_path:
        return OperationResult.failure(
            "未找到 Ghostscript 可执行文件，请先在设置中安装或禁用状态后重试",
            failed=len(args.inputs),
        )

    compressor = GhostscriptCompressor()
    if on_log:
        compressor.log.connect(on_log)
    _register_stopper(compressor.stop)
    counts: dict[str, int] = {}

    def on_finished(success, fail):
        counts["success"] = success
        counts["fail"] = fail

    compressor.finished.connect(on_finished)
    produced = compressor.compress(list(args.inputs), args.quality, gs_path=gs_path)
    outputs = tuple(produced or ())
    return _result_from_counts(
        (counts["success"], counts["fail"]) if counts else None,
        outputs,
        success_message="成功压缩 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
    )


def _run_pdf_render(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.pdf.pdf_page_renderer import PDFPageRenderer

    renderer = PDFPageRenderer()
    pymupdf_ok = PDFPageRenderer.is_available()
    gs_ok = renderer.is_gs_available()

    if args.engine == "pymupdf" and not pymupdf_ok:
        return OperationResult.failure(
            "PyMuPDF 不可用，请改用 --engine ghostscript",
            failed=len(args.inputs),
        )
    if args.engine == "ghostscript" and not gs_ok:
        return OperationResult.failure(
            "未找到可用的 Ghostscript，请改用 --engine pymupdf 或先安装 Ghostscript",
            failed=len(args.inputs),
        )
    if args.engine == "auto" and not (pymupdf_ok or gs_ok):
        return OperationResult.failure(
            "未找到可用的 PDF 渲染引擎（PyMuPDF 或 Ghostscript）",
            failed=len(args.inputs),
        )
    use_ghostscript = args.engine == "ghostscript" or (
        args.engine == "auto" and not pymupdf_ok and gs_ok
    )

    page_range = None
    if args.first_page is not None or args.last_page is not None:
        start = (args.first_page or 1) - 1
        end = args.last_page if args.last_page is not None else start + 10**6
        if start < 0 or end <= start:
            return OperationResult.failure("页码范围无效", failed=len(args.inputs))
        page_range = (start, end)

    counts = _run_counts(
        lambda **kw: renderer.render_all(
            list(args.inputs),
            args.output,
            dpi=args.dpi,
            output_format=args.format,
            page_range=page_range,
            use_ghostscript=use_ghostscript,
            on_log=on_log,
            **kw,
        )
    )
    return _result_from_counts(
        counts,
        _rendered_outputs(list(args.inputs), args.output),
        success_message="成功渲染 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


_OFFICE_ENGINES = {
    "office-ppt-to-pdf": ("powerpoint", "PowerPoint"),
    "office-word-to-pdf": ("word", "Word"),
    "office-excel-to-pdf": ("excel", "Excel"),
}


def _run_office_to_pdf(
    args: argparse.Namespace, on_log, should_cancel: Callable[[], bool]
) -> OperationResult:
    from core.engines.office.selector import create_office_engine
    from core.external_tools.manager import ExternalToolManager

    engine_type, display = _OFFICE_ENGINES[args.operation]
    tool_manager = None if args.no_libreoffice_fallback else ExternalToolManager()
    engine = create_office_engine(engine_type, tool_manager)
    if on_log:
        engine.log.connect(on_log)
    _register_stopper(engine.stop)

    counts: dict[str, int] = {}

    def on_finished(success, fail):
        counts["success"] = success
        counts["fail"] = fail

    engine.finished.connect(on_finished)
    engine.convert(list(args.inputs))

    result = _result_from_counts(
        (counts["success"], counts["fail"]) if counts else None,
        _with_extension(list(args.inputs), None, ".pdf"),
        success_message="成功转换 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )
    result = replace(result, data={"backend": engine.backend or f"MS {display}"})
    # 全部文件已转换完成后的迟到取消不改变结果，与 PDF 各命令的判定保持一致
    if should_cancel() and result.succeeded < len(args.inputs):
        return replace(result, status=OperationStatus.CANCELLED, message="任务已取消")
    return result


def _run_office_ppt_to_images(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.office.ppt_image_exporter import PPTImageExporter

    exporter = PPTImageExporter()
    _register_stopper(exporter.stop)
    counts = _run_counts(
        lambda **kw: exporter.export(
            list(args.inputs), args.output_dir, args.format, on_log=on_log, **kw
        )
    )
    outputs = _exported_images(list(args.inputs), args.output_dir)
    return _result_from_counts(
        counts,
        outputs,
        success_message="成功导出 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _run_remove_watermark(args: argparse.Namespace, on_log) -> OperationResult:
    from core.batch import run as batch_run
    from core.features.image.gemini_watermark_remover import GeminiWatermarkRemover

    remover = GeminiWatermarkRemover()
    created: list[str] = []

    def worker(path):
        target = (
            remover.batch_output_path(path, args.output_dir)
            if args.output_dir
            else remover.default_output_path(path)
        )
        if not remover.process_image(path, target, on_log=on_log):
            raise RuntimeError(f"处理失败: {os.path.basename(path)}")
        created.append(target)

    counts = batch_run(list(args.inputs), worker, on_log=on_log)
    outputs = tuple(path for path in created if os.path.exists(path))
    return _result_from_counts(
        counts,
        outputs,
        success_message="成功处理 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _run_markdown_to_pdf(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.text.markdown_to_pdf import MarkdownToPdf
    from core.plugins import PluginManager

    converter = MarkdownToPdf(PluginManager())
    if args.engine == "pandoc" and not converter.is_pandoc_ready():
        return OperationResult.failure(
            "Pandoc 或 PDF 引擎不可用，请改用 --engine builtin", failed=len(args.inputs)
        )

    result = converter.convert(
        list(args.inputs),
        args.output_dir,
        force_builtin=args.engine == "builtin",
        on_log=on_log,
        should_cancel=lambda: False,
    )
    return replace(result, data={"engine": converter.engine})


def _run_office_doc_to_docx(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.office.doc_to_docx_converter import DocToDocxConverter

    converter = DocToDocxConverter()
    _register_stopper(converter.stop)
    counts = _run_counts(
        lambda **kw: converter.convert(
            list(args.inputs), args.output_dir, on_log=on_log, **kw
        )
    )
    return _result_from_counts(
        counts,
        _with_extension(list(args.inputs), args.output_dir, ".docx"),
        success_message="成功转换 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _run_markdown_batch_pdf(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.text.markdown_pdf_pandoc import PandocMarkdownToPdf

    converter = PandocMarkdownToPdf()
    if not converter.is_available():
        return OperationResult.failure(
            "Pandoc 未安装或已禁用，请先在设置中安装", failed=len(args.inputs)
        )
    counts = _run_counts(
        lambda **kw: converter.convert_batch(
            list(args.inputs),
            args.output_dir,
            enable_math=not args.no_math,
            enable_highlight=not args.no_highlight,
            pdf_engine=args.pdf_engine,
            template=args.template,
            on_log=on_log,
            **kw,
        )
    )
    return _result_from_counts(
        counts,
        _with_extension(list(args.inputs), args.output_dir, ".pdf"),
        success_message="成功转换 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _run_libreoffice_convert(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.office.libreoffice_converter import LibreOfficeFormatConverter

    converter = LibreOfficeFormatConverter()
    if not converter.is_available():
        return OperationResult.failure(
            "LibreOffice 未安装或不可用，请先在设置中安装", failed=len(args.inputs)
        )
    counts = _run_counts(
        lambda **kw: converter.convert_batch(
            list(args.inputs),
            args.to,
            args.output_dir,
            on_log=on_log,
            **kw,
        )
    )
    return _result_from_counts(
        counts,
        _with_extension(list(args.inputs), args.output_dir, "." + args.to.lstrip(".")),
        success_message="成功转换 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _run_word_markdown(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.office.word_converter import WordConverter

    converter = WordConverter()
    if not converter.is_pandoc_available():
        return OperationResult.failure(
            "Pandoc 未安装，Word 与 Markdown 互转需要 Pandoc", failed=len(args.inputs)
        )
    if args.direction == "docx-to-md":
        counts = _run_counts(
            lambda **kw: converter.convert_docx_to_markdown(
                list(args.inputs), args.output_dir, on_log=on_log, **kw
            )
        )
        extension = ".md"
    else:
        counts = _run_counts(
            lambda **kw: converter.convert_markdown_to_docx(
                list(args.inputs),
                args.output_dir,
                args.reference_doc,
                on_log=on_log,
                **kw,
            )
        )
        extension = ".docx"
    return _result_from_counts(
        counts,
        _with_extension(list(args.inputs), args.output_dir, extension),
        success_message="成功转换 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _run_markdown_html(args: argparse.Namespace, on_log) -> OperationResult:
    from core.features.text.markdown_converter import MarkdownConverter

    converter = MarkdownConverter()
    if args.use_pandoc and not converter.is_pandoc_available():
        return OperationResult.failure(
            "指定了 --use-pandoc 但 Pandoc 未安装", failed=len(args.inputs)
        )
    if args.direction == "md-to-html":
        counts = _run_counts(
            lambda **kw: converter.convert_markdown_to_html(
                list(args.inputs),
                args.output_dir,
                use_pandoc=args.use_pandoc,
                include_css=not args.no_css,
                on_log=on_log,
                **kw,
            )
        )
        extension = ".html"
    else:
        counts = _run_counts(
            lambda **kw: converter.convert_html_to_markdown(
                list(args.inputs),
                args.output_dir,
                use_pandoc=args.use_pandoc,
                on_log=on_log,
                **kw,
            )
        )
        extension = ".md"
    return _result_from_counts(
        counts,
        _with_extension(list(args.inputs), args.output_dir, extension),
        success_message="成功转换 {success} 个文件",
        failure_message="成功 {success} 个，失败 {fail} 个",
        hint=on_log.last_error(),
    )


def _execute(args: argparse.Namespace, should_cancel: Callable[[], bool]) -> OperationResult:
    on_log = _LogCapture(echo=not args.json)
    _ensure_dir(getattr(args, "output_dir", None))

    if args.operation == "merge":
        return PDFMerger().merge(
            args.inputs, args.output, on_log=on_log, should_cancel=should_cancel
        )
    if args.operation == "split":
        return PDFSplitter().split(
            args.input,
            args.ranges,
            args.output,
            on_log=on_log,
            should_cancel=should_cancel,
        )
    if args.operation == "extract-images":
        return PDFImageExtractor().extract(
            args.inputs, args.output, on_log=on_log, should_cancel=should_cancel
        )
    if args.operation == "image-convert":
        return ImageConverter().convert(
            args.input,
            args.output,
            args.format,
            quality=args.quality,
            rotate_angle=args.rotate,
            flip_mode=args.flip,
            on_log=on_log,
            should_cancel=should_cancel,
        )

    if args.operation == "image-colors":
        return _run_color_extraction(
            lambda **kw: ColorExtractor().extract(
                args.input, args.count, on_log=on_log, **kw
            )
        )

    if args.operation == "image-vectorize":
        return _run_ok_msg(
            lambda **kw: ImageVectorizer().convert(
                args.input, args.output, on_log=on_log, **kw
            ),
            collect_outputs=lambda: _existing(args.output),
        )

    if args.operation == "image-to-pdf":
        return _run_ok_msg(
            lambda **kw: ImageToPdfConverter().convert(
                args.inputs, args.output, merge=not args.single, on_log=on_log, **kw
            ),
            collect_outputs=lambda: (
                _pdf_outputs_for(args.inputs, args.output)
                if args.single
                else _existing(args.output)
            ),
        )

    if args.operation == "text-extract-code":
        extensions = [e.strip() for e in args.extensions.split(",") if e.strip()]
        return _run_ok_msg(
            lambda **kw: CodeExtractor().extract(
                args.root, extensions, args.output, on_log=on_log, **kw
            ),
            collect_outputs=lambda: _existing(args.output),
        )

    if args.operation == "text-txt-to-pdf":
        counts = _run_counts(
            lambda **kw: TxtConverter().convert(
                args.inputs, args.output_dir, on_log=on_log, **kw
            )
        )
        if counts is None:
            return OperationResult.failure("核心操作未返回完成通知")
        success, fail = counts
        outputs = _pdf_outputs_for(args.inputs, args.output_dir)
        message = (
            f"成功 {success} 个，失败 {fail} 个"
            if fail
            else f"成功转换 {success} 个文件"
        )
        if success == 0:
            return OperationResult.failure(message, succeeded=0, failed=fail)
        if fail:
            return OperationResult.failure(
                message, outputs=outputs, succeeded=success, failed=fail
            )
        return OperationResult.success(message, outputs=outputs, succeeded=success)

    if args.operation == "files-rename-preview":
        plan = BatchRenamer().preview(args.files, args.template, args.start_index)
        conflicts = sum(1 for item in plan if item.get("conflict"))
        message = (
            f"共 {len(plan)} 项，其中 {conflicts} 项存在冲突"
            if conflicts
            else f"共 {len(plan)} 项，无冲突"
        )
        status = OperationResult.failure if conflicts else OperationResult.success
        return status(
            message,
            succeeded=len(plan) - conflicts,
            failed=conflicts,
            data={"plan": plan},
        )

    if args.operation == "pdf-compress":
        return _run_pdf_compress(args, on_log)

    if args.operation == "pdf-render":
        return _run_pdf_render(args, on_log)

    if args.operation == "text-markdown-batch-pdf":
        return _run_markdown_batch_pdf(args, on_log)

    if args.operation == "office-libreoffice-convert":
        return _run_libreoffice_convert(args, on_log)

    if args.operation == "office-word-markdown":
        return _run_word_markdown(args, on_log)

    if args.operation == "text-markdown-html":
        return _run_markdown_html(args, on_log)

    if args.operation in _OFFICE_ENGINES:
        return _run_office_to_pdf(args, on_log, should_cancel)

    if args.operation == "office-ppt-to-images":
        return _run_office_ppt_to_images(args, on_log)

    if args.operation == "office-doc-to-docx":
        return _run_office_doc_to_docx(args, on_log)

    if args.operation == "image-remove-watermark":
        return _run_remove_watermark(args, on_log)

    if args.operation == "text-markdown-to-pdf":
        return _run_markdown_to_pdf(args, on_log)

    raise ValueError(f"未知命令: {args.operation}")


def _emit_result(result: OperationResult, json_mode: bool) -> int:
    if json_mode:
        print(json.dumps(result.to_dict(), ensure_ascii=True))
    else:
        print(result.message)
        for output in result.outputs:
            print(output)

    if result.status is OperationStatus.SUCCESS:
        return 0
    if result.status is OperationStatus.CANCELLED:
        return 130
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cancelled = Event()
    previous_handler = signal.getsignal(signal.SIGINT)

    def request_cancel(_signum, _frame):
        cancelled.set()
        _stop_active()

    if args.operation in INTERRUPTIBLE:
        signal.signal(signal.SIGINT, request_cancel)
    try:
        try:
            result = _execute(args, cancelled.is_set)
        except (CancelledError, KeyboardInterrupt):
            _stop_active()
            result = OperationResult.cancelled()
        except Exception as error:
            _stop_active()
            result = OperationResult.failure(str(error))
        return _emit_result(result, args.json)
    finally:
        _ACTIVE_STOPPERS.clear()
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
