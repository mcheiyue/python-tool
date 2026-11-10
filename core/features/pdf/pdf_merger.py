import os
import traceback
from concurrent.futures import CancelledError
from pypdf import PdfWriter, PdfReader

from core.cancellation import check_cancelled
from core.utils.atomic_output import atomic_output

class PDFMerger:
    def merge(self, files, output_path, *, on_log=None, on_progress=None, on_finished=None, should_cancel=None):
        """
        合并 PDF 文件
        :param files: PDF 文件路径列表
        :param output_path: 输出文件路径
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)
            return ok, msg

        check_cancelled(should_cancel)
        if not files:
            return finished(False, "文件列表为空")

        total = len(files)
        log(f"开始任务: 合并 {total} 个文件")
        log(f"输出路径: {output_path}")

        try:
            if os.path.exists(output_path) and any(os.path.samefile(output_path, path) for path in files):
                return finished(False, "输出文件不能覆盖输入 PDF")
            writer = PdfWriter()
            
            for i, file_path in enumerate(files):
                check_cancelled(should_cancel)
                file_name = os.path.basename(file_path)
                log(f"正在读取 [{i+1}/{total}]: {file_name}")
                progress(i, total, f"正在读取: {file_name}")
                
                try:
                    reader = PdfReader(file_path)
                    # 将所有页面添加到 writer
                    for page in reader.pages:
                        check_cancelled(should_cancel)
                        writer.add_page(page)
                except CancelledError:
                    raise
                except Exception as e:
                    err_msg = f"读取文件 {file_name} 失败: {str(e)}"
                    log(f"❌ {err_msg}")
                    # 可以选择跳过或报错，这里选择报错停止
                    return finished(False, err_msg)

            log("正在写入输出文件...")
            progress(total, total, "正在保存...")
            
            with atomic_output(output_path, should_cancel=should_cancel) as f_out:
                writer.write(f_out)
                
            log(f"✅ 合并成功！已保存至: {output_path}")
            return finished(True, f"成功合并 {total} 个文件")

        except CancelledError:
            log("合并已取消，原有输出保持不变")
            raise
        except Exception as e:
            error_trace = traceback.format_exc()
            log(f"❌ 发生未知错误:\n{error_trace}")
            return finished(False, str(e))
