import os
import traceback
from pypdf import PdfWriter, PdfReader

class PDFMerger:
    def merge(self, files, output_path, *, on_log=None, on_progress=None, on_finished=None):
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

        if not files:
            finished(False, "文件列表为空")
            return

        total = len(files)
        log(f"开始任务: 合并 {total} 个文件")
        log(f"输出路径: {output_path}")

        try:
            writer = PdfWriter()
            
            for i, file_path in enumerate(files):
                file_name = os.path.basename(file_path)
                log(f"正在读取 [{i+1}/{total}]: {file_name}")
                progress(i, total, f"正在读取: {file_name}")
                
                try:
                    reader = PdfReader(file_path)
                    # 将所有页面添加到 writer
                    for page in reader.pages:
                        writer.add_page(page)
                except Exception as e:
                    err_msg = f"读取文件 {file_name} 失败: {str(e)}"
                    log(f"❌ {err_msg}")
                    # 可以选择跳过或报错，这里选择报错停止
                    finished(False, err_msg)
                    return

            log("正在写入输出文件...")
            progress(total, total, "正在保存...")
            
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
                
            log(f"✅ 合并成功！已保存至: {output_path}")
            finished(True, f"成功合并 {total} 个文件")

        except Exception as e:
            error_trace = traceback.format_exc()
            log(f"❌ 发生未知错误:\n{error_trace}")
            finished(False, str(e))
