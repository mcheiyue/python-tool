from fpdf import FPDF
import os
from PyQt6.QtCore import QObject, pyqtSignal
from core.font_finder import FontFinder

class TxtConverter(QObject):
    finished = pyqtSignal(int, int) # success, fail
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)

    def convert(self, files, output_dir=None):
        success = 0
        fail = 0
        total = len(files)
        
        # 尝试使用系统 CJK 字体
        font_info = FontFinder.find_cjk_font()
        font_path = None
        font_name = "Arial" # 默认回退
        
        if font_info:
            font_path, font_name = font_info
            self.log.emit(f"✅ 使用字体: {font_name}")
        else:
            self.log.emit("⚠️ 未找到中文字体，中文可能会显示为乱码。")

        for i, file_path in enumerate(files):
            try:
                self.progress.emit(i, total, os.path.basename(file_path))
                
                pdf = FPDF()
                pdf.add_page()
                
                if font_path:
                    try:
                        pdf.add_font(font_name, "", font_path)
                        pdf.set_font(font_name, size=12)
                    except Exception as e:
                        self.log.emit(f"字体加载失败: {e}")
                        pdf.set_font("Arial", size=12)
                else:
                    pdf.set_font("Arial", size=12)

                # 读取文件内容，尝试 UTF-8 然后 GBK
                content = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            content = f.read()
                    except Exception as e:
                        raise Exception(f"无法读取文件编码: {e}")

                # 写入 PDF
                # multi_cell 自动换行
                pdf.multi_cell(0, 10, text=content)
                
                if output_dir:
                    out_name = os.path.join(output_dir, os.path.splitext(os.path.basename(file_path))[0] + ".pdf")
                else:
                    out_name = os.path.splitext(file_path)[0] + ".pdf"
                    
                pdf.output(out_name)
                self.log.emit(f"成功: {out_name}")
                success += 1
            except Exception as e:
                self.log.emit(f"失败 {os.path.basename(file_path)}: {str(e)}")
                fail += 1
                
        self.progress.emit(total, total, "完成")
        self.finished.emit(success, fail)
