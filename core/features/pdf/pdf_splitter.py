import os
import traceback
from concurrent.futures import CancelledError
from pypdf import PdfReader, PdfWriter

from core.cancellation import check_cancelled
from core.operation_result import OperationResult
from core.utils.atomic_output import atomic_output

class PDFSplitter:
    def split(self, file_path, ranges_text, output_dir, *, on_log=None, on_progress=None, on_finished=None, should_cancel=None):
        """
        根据范围拆分 PDF
        :param file_path: 源 PDF 文件路径
        :param ranges_text: 范围字符串，如 "1-5, 8, 10-end"
        :param output_dir: 输出目录
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(result):
            if on_finished:
                on_finished(result.ok, result.message)
            return result

        log(f"开始处理文件: {os.path.basename(file_path)}")
        
        try:
            check_cancelled(should_cancel)
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            log(f"文件总页数: {total_pages}")

            # 解析范围
            ranges = self._parse_ranges(ranges_text, total_pages, on_log)
            if not ranges:
                return finished(OperationResult.failure("无效的页码范围"))

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            os.makedirs(output_dir, exist_ok=True)
            
            produced = 0
            outputs = []
            for i, (start, end) in enumerate(ranges):
                check_cancelled(should_cancel)
                writer = PdfWriter()
                
                target_pages = []
                for p_idx in range(start - 1, end):
                    check_cancelled(should_cancel)
                    if 0 <= p_idx < total_pages:
                        writer.add_page(reader.pages[p_idx])
                        target_pages.append(p_idx + 1)
                
                if not target_pages:
                    log(f"⚠️ 跳过无效范围: {start}-{end}")
                    continue
                    
                output_filename = f"{base_name}_part{i+1}_{start}-{end}.pdf"
                output_path = os.path.join(output_dir, output_filename)
                
                if os.path.exists(output_path) and os.path.samefile(output_path, file_path):
                    return finished(OperationResult.failure(
                        "输出文件不能覆盖输入 PDF",
                        outputs=tuple(outputs),
                        succeeded=produced,
                    ))
                with atomic_output(output_path, should_cancel=should_cancel) as f_out:
                    writer.write(f_out)
                
                log(f"✅ 已生成: {output_filename} ({len(target_pages)} 页)")
                produced += 1
                outputs.append(output_path)
                progress(i + 1, len(ranges), f"正在导出第 {i+1} 部分...")

            if produced == 0:
                return finished(OperationResult.failure(
                    f"没有可拆分的页面（文件共 {total_pages} 页，范围 {ranges_text}）",
                    outputs=tuple(outputs),
                ))
            return finished(OperationResult.success(
                f"拆分完成，共生成 {produced} 个文件",
                outputs=tuple(outputs),
                succeeded=produced,
            ))

        except CancelledError:
            log("拆分已取消，已完成的文件予以保留")
            return OperationResult.cancelled(
                "拆分已取消，已完成的文件予以保留",
                outputs=tuple(outputs) if "outputs" in locals() else (),
                succeeded=produced if "produced" in locals() else 0,
            )
        except Exception as e:
            error_trace = traceback.format_exc()
            log(f"❌ 错误:\n{error_trace}")
            return finished(OperationResult.failure(
                str(e), outputs=tuple(outputs) if "outputs" in locals() else (),
                succeeded=produced if "produced" in locals() else 0,
            ))

    def _parse_ranges(self, text, total_pages, on_log=None):
        """
        解析范围字符串，返回 [(start, end), ...] 列表
        支持格式: "1-5, 8, 10-end"
        """
        ranges = []
        parts = text.replace('，', ',').split(',')
        
        for part in parts:
            part = part.strip().lower()
            if not part: continue
            
            try:
                if '-' in part:
                    start_str, end_str = part.split('-')
                    start = int(start_str)
                    
                    if end_str == 'end':
                        end = total_pages
                    else:
                        end = int(end_str)
                else:
                    start = int(part)
                    end = int(part)
                
                # 简单验证
                if start > end:
                    start, end = end, start
                
                if start < 1: start = 1
                
                ranges.append((start, end))
            except ValueError:
                if on_log:
                    on_log(f"⚠️ 无法解析范围格式: '{part}'")
                return None
                
        return ranges
