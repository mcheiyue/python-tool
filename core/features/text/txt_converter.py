from fpdf import FPDF
import os
from core.features.text.font_finder import FontFinder

class TxtConverter:
    def __init__(self):
        self._is_running = True

    def stop(self):
        self._is_running = False

    def convert(self, files, output_dir=None, *, on_log=None, on_progress=None, on_finished=None):
        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, fail):
            if on_finished:
                on_finished(ok, fail)

        self._is_running = True
        success = 0
        fail = 0
        total = len(files)

        # 尝试使用系统 CJK 字体
        font_info = FontFinder.find_cjk_font()
        font_path = None
        font_name = "Arial"  # 默认回退

        if font_info:
            font_path, font_name = font_info
            log(f"✅ 使用字体: {font_name}")
        else:
            log("⚠️ 未找到中文字体，中文可能会显示为乱码。")

        for i, file_path in enumerate(files):
            if not self._is_running:
                log("任务已停止")
                break
            try:
                progress(i, total, os.path.basename(file_path))
                
                pdf = FPDF()
                pdf.add_page()
                
                if font_path:
                    try:
                        pdf.add_font(font_name, "", font_path)
                        pdf.set_font(font_name, size=12)
                    except Exception as e:
                        log(f"字体加载失败: {e}")
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
                log(f"成功: {out_name}")
                success += 1
            except Exception as e:
                log(f"失败 {os.path.basename(file_path)}: {str(e)}")
                fail += 1

        progress(total, total, "完成")
        finished(success, fail)
