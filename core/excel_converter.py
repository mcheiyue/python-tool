import os
import comtypes.client
from PyQt6.QtCore import QObject, pyqtSignal

# xlTypePDF = 0
xlTypePDF = 0

class ExcelConverter(QObject):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = False

    def convert(self, file_paths):
        self._is_running = True
        total = len(file_paths)
        success = 0
        fail = 0
        excel_app = None

        try:
            comtypes.CoInitialize()
            self.log.emit("启动 Excel...")
            
            # 使用 dynamic=True 以获得更好的兼容性
            excel_app = comtypes.client.CreateObject("Excel.Application", dynamic=True)
            try:
                # 保持 Excel 不可见可以加快处理速度
                excel_app.Visible = False
                excel_app.DisplayAlerts = False
            except:
                pass

            for idx, path in enumerate(file_paths):
                if not self._is_running:
                    self.log.emit("任务停止")
                    break

                name = os.path.basename(path)
                self.progress.emit(idx + 1, total, name)
                self.log.emit(f"转换中 ({idx + 1}/{total}): {name}")

                try:
                    abs_path = os.path.abspath(path)
                    pdf_path = os.path.splitext(abs_path)[0] + ".pdf"

                    # 打开工作簿 (ReadOnly=True)
                    wb = excel_app.Workbooks.Open(abs_path, ReadOnly=True)
                    
                    # 导出为 PDF
                    # xlTypePDF = 0
                    wb.ExportAsFixedFormat(xlTypePDF, pdf_path)
                    
                    # 关闭工作簿，不保存更改
                    wb.Close(False)

                    success += 1
                    self.log.emit(f"✅ 成功: {name}")
                except Exception as e:
                    fail += 1
                    self.log.emit(f"❌ 失败 {name}: {e}")

        except Exception as e:
            self.log.emit(f"🔥 错误: {e}")
        finally:
            if excel_app:
                try:
                    excel_app.Quit()
                except:
                    pass
            comtypes.CoUninitialize()
            self.finished.emit(success, fail)
            self._is_running = False

    def stop(self):
        self._is_running = False
