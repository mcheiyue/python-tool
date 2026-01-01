import os
import comtypes.client
from PyQt6.QtCore import QObject, pyqtSignal

ppSaveAsPDF = 32

class PPTConverter(QObject):
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
        ppt_app = None

        try:
            comtypes.CoInitialize()
            self.log.emit("启动 PowerPoint...")
            
            ppt_app = comtypes.client.CreateObject("PowerPoint.Application", dynamic=True)
            try:
                ppt_app.Visible = 1
                ppt_app.WindowState = 2 
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

                    deck = ppt_app.Presentations.Open(abs_path, True, False, False)
                    deck.SaveAs(pdf_path, ppSaveAsPDF)
                    deck.Close()

                    success += 1
                    self.log.emit(f"✅ 成功: {name}")
                except Exception as e:
                    fail += 1
                    self.log.emit(f"❌ 失败 {name}: {e}")

        except Exception as e:
            self.log.emit(f"🔥 错误: {e}")
        finally:
            if ppt_app:
                try:
                    ppt_app.Quit()
                except:
                    pass
            comtypes.CoUninitialize()
            self.finished.emit(success, fail)
            self._is_running = False

    def stop(self):
        self._is_running = False
