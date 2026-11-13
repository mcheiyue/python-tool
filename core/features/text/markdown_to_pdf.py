import os
from concurrent.futures import CancelledError
from typing import Callable, Optional

from pypdf import PdfWriter

from core.cancellation import check_cancelled
from core.operation_result import OperationResult
from core.utils.atomic_output import atomic_output

_PAGE_SIZE = (595.28, 841.89)


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )


def _render_lines(lines: list[str]) -> bytes:
    """把纯文本排成单页 PDF；内置路径不追求排版，只保证内容可读、可搜索。"""
    leading = 16
    top = _PAGE_SIZE[1] - 60
    max_chars = 80

    wrapped: list[str] = []
    for line in lines:
        while len(line) > max_chars:
            wrapped.append(line[:max_chars])
            line = line[max_chars:]
        wrapped.append(line)

    body = ["BT", "/F1 11 Tf", f"{leading} TL", f"50 {top:.2f} Td"]
    for text in wrapped:
        body.append(f"({_pdf_escape(text)}) Tj T*")
    body.append("ET")
    stream = "\n".join(body).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE_SIZE[0]:.2f} "
            f"{_PAGE_SIZE[1]:.2f}] /Resources << /Font << /F1 4 0 R >> >> "
            "/Contents 5 0 R >>"
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, payload in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("ascii") + payload + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


class MarkdownToPdf:
    """把 Markdown 内容导出为 PDF。

    引擎顺序与 GUI 一致：优先带 PDF 引擎的 Pandoc 插件，其次内置转换。
    内置路径用单页 Helvetica 排版，非 ASCII 字符会丢失，故只作为降级；
    CLI 通过 data.engine 报告实际使用的引擎，不把降级当增强。
    """

    def __init__(self, plugin_manager=None):
        self._plugin_manager = plugin_manager
        self._is_running = True
        self.engine = ""

    def get_converter(self):
        if self._plugin_manager is None:
            return None
        return self._plugin_manager.get_preferred_plugin("markdown_to_pdf")

    def is_pandoc_ready(self) -> bool:
        converter = self.get_converter()
        if converter is None:
            return False
        return bool(getattr(converter, "has_pdf_engine", True))

    def stop(self) -> None:
        self._is_running = False

    def convert(
        self,
        inputs: list[str],
        output_dir: Optional[str] = None,
        *,
        force_builtin: bool = False,
        on_log: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> OperationResult:
        def log(message: str) -> None:
            if on_log:
                on_log(message)

        if not inputs:
            return OperationResult.failure("文件列表为空")

        converter = self.get_converter()
        use_pandoc = self.is_pandoc_ready() and not force_builtin
        self.engine = "pandoc" if use_pandoc else "builtin"
        if use_pandoc:
            log(f"使用 {converter.display_name} 导出 PDF")
        else:
            log("Pandoc 或 PDF 引擎不可用，使用内置单页渲染；非 ASCII 字符会丢失")

        outputs: list[str] = []
        failed = 0
        total = len(inputs)

        for index, source in enumerate(inputs):
            if should_cancel and should_cancel():
                return OperationResult.cancelled(
                    outputs=tuple(outputs), succeeded=len(outputs), failed=failed
                )
            if on_progress:
                on_progress(index + 1, total, os.path.basename(source))

            try:
                target = self._target_path(source, output_dir)
                os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
                if use_pandoc:
                    with open(source, encoding="utf-8") as handle:
                        converter.convert(
                            content=handle.read(),
                            output_format="pdf",
                            output_path=target,
                        )
                else:
                    with open(source, encoding="utf-8") as handle:
                        lines = handle.read().splitlines()
                    self._write_builtin_pdf(lines, target)
                outputs.append(target)
                log(f"✅ 成功: {os.path.basename(target)}")
            except CancelledError:
                raise
            except Exception as exc:
                failed += 1
                log(f"❌ 失败 {os.path.basename(source)}: {exc}")

        if failed:
            return OperationResult.failure(
                f"成功 {len(outputs)} 个，失败 {failed} 个",
                outputs=tuple(outputs),
                succeeded=len(outputs),
                failed=failed,
            )
        return OperationResult.success(
            f"成功转换 {len(outputs)} 个文件", outputs=tuple(outputs), succeeded=len(outputs)
        )

    def _target_path(self, source: str, output_dir: Optional[str]) -> str:
        name = os.path.splitext(os.path.basename(source))[0] + ".pdf"
        return os.path.join(output_dir, name) if output_dir else os.path.join(
            os.path.dirname(source), name
        )

    def _write_builtin_pdf(self, lines: list[str], target: str) -> None:
        with atomic_output(target) as handle:
            handle.write(_render_lines(lines))
