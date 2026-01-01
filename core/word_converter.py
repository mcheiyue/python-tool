import os
import comtypes.client
from PyQt6.QtCore import QObject, pyqtSignal

wdFormatPDF = 17

class WordConverter(QObject):
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
        word_app = None

        try:
            comtypes.CoInitialize()
            self.log.emit("启动 Word...")
            
            # 使用 dynamic=True 以获得更好的兼容性
            word_app = comtypes.client.CreateObject("Word.Application", dynamic=True)
            try:
                # 保持 Word 不可见可以加快处理速度，但在某些系统上可能需要可见
                word_app.Visible = False 
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

                    # 打开文档
                    doc = word_app.Documents.Open(abs_path)
                    
                    # 另存为 PDF
                    # 使用 ExportAsFixedFormat 替代 SaveAs2，兼容性更好
                    # 注意：comtypes dynamic dispatch 可能不支持关键字参数，改用位置参数
                    doc.ExportAsFixedFormat(pdf_path, wdFormatPDF)
                    
                    # 关闭文档，不保存更改
                    # 改用位置参数以兼容 comtypes dynamic dispatch
                    doc.Close(0)

                    success += 1
                    self.log.emit(f"✅ 成功: {name}")
                except Exception as e:
                    fail += 1
                    self.log.emit(f"❌ 失败 {name}: {e}")

        except Exception as e:
            self.log.emit(f"🔥 错误: {e}")
        finally:
            if word_app:
                try:
                    word_app.Quit()
                except:
                    pass
            comtypes.CoUninitialize()
            self.finished.emit(success, fail)
            self._is_running = False

    def stop(self):
        self._is_running = False
