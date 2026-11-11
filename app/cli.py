import argparse
import json
import signal
import sys
from concurrent.futures import CancelledError
from threading import Event
from typing import Callable

from core.features.image.image_converter import ImageConverter
from core.features.pdf.pdf_image_extractor import PDFImageExtractor
from core.features.pdf.pdf_merger import PDFMerger
from core.features.pdf.pdf_splitter import PDFSplitter
from core.operation_result import OperationResult, OperationStatus


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

    return parser


def _log_callback(json_mode: bool) -> Callable[[str], None] | None:
    if json_mode:
        return None
    return lambda message: print(message, file=sys.stderr)


def _execute(args: argparse.Namespace, should_cancel: Callable[[], bool]) -> OperationResult:
    on_log = _log_callback(args.json)
    if args.operation == "merge":
        return PDFMerger().merge(
            args.inputs,
            args.output,
            on_log=on_log,
            should_cancel=should_cancel,
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
            args.inputs,
            args.output,
            on_log=on_log,
            should_cancel=should_cancel,
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

    signal.signal(signal.SIGINT, request_cancel)
    try:
        try:
            result = _execute(args, cancelled.is_set)
        except CancelledError:
            result = OperationResult.cancelled()
        except Exception as error:
            result = OperationResult.failure(str(error))
        return _emit_result(result, args.json)
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
