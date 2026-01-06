import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
from pypdf import PdfWriter, PdfReader

class PDFMerger(QObject):
    progress = pyqtSignal(int, int, str)  # curr, total, message
    log = pyqtSignal(str)                 # log message
    finished = pyqtSignal(bool, str)      # success, message

    def merge(self, files, output_path):
        """
        合并 PDF 文件
        :param files: PDF 文件路径列表
        :param output_path: 输出文件路径
        """
        if not files:
            self.finished.emit(False, "文件列表为空")
            return

        total = len(files)
        self.log.emit(f"开始任务: 合并 {total} 个文件")
        self.log.emit(f"输出路径: {output_path}")

        try:
            writer = PdfWriter()
            
            for i, file_path in enumerate(files):
                file_name = os.path.basename(file_path)
                self.log.emit(f"正在读取 [{i+1}/{total}]: {file_name}")
                self.progress.emit(i, total, f"正在读取: {file_name}")
                
                try:
                    reader = PdfReader(file_path)
                    # 将所有页面添加到 writer
                    for page in reader.pages:
                        writer.add_page(page)
                except Exception as e:
                    err_msg = f"读取文件 {file_name} 失败: {str(e)}"
                    self.log.emit(f"❌ {err_msg}")
                    # 可以选择跳过或报错，这里选择报错停止
                    self.finished.emit(False, err_msg)
                    return

            self.log.emit("正在写入输出文件...")
            self.progress.emit(total, total, "正在保存...")
            
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
                
            self.log.emit(f"✅ 合并成功！已保存至: {output_path}")
            self.finished.emit(True, f"成功合并 {total} 个文件")

        except Exception as e:
            error_trace = traceback.format_exc()
            self.log.emit(f"❌ 发生未知错误:\n{error_trace}")
            self.finished.emit(False, str(e))
