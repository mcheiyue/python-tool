import argparse
import json
import os
import signal
import sys
from concurrent.futures import CancelledError
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

    return parser


def _log_callback(json_mode: bool) -> Callable[[str], None] | None:
    if json_mode:
        return None
    return lambda message: print(message, file=sys.stderr)


def _existing(*paths: str | None) -> tuple[str, ...]:
    return tuple(path for path in paths if path and os.path.exists(path))


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


def _execute(args: argparse.Namespace, should_cancel: Callable[[], bool]) -> OperationResult:
    on_log = _log_callback(args.json)

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

    if args.operation in CANCELLABLE:
        signal.signal(signal.SIGINT, request_cancel)
    try:
        try:
            result = _execute(args, cancelled.is_set)
        except (CancelledError, KeyboardInterrupt):
            result = OperationResult.cancelled()
        except Exception as error:
            result = OperationResult.failure(str(error))
        return _emit_result(result, args.json)
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
