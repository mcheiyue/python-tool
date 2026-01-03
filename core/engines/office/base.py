import os
import comtypes.client
from abc import abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal

class BaseOfficeConverter(QObject):
    """Office 文档转换器基类 (Template Method Pattern)"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = False
        self._app = None

    def convert(self, file_paths):
        """执行转换任务的模板方法"""
        self._is_running = True
        total = len(file_paths)
        success = 0
        fail = 0

        try:
            # 1. 初始化 COM 环境
            comtypes.CoInitialize()
            self.log.emit(f"正在启动 {self.app_name}...")
            
            # 2. 创建应用实例
            self._app = self._create_app()
            
            for idx, path in enumerate(file_paths):
                if not self._is_running:
                    self.log.emit("任务已停止")
                    break

                file_name = os.path.basename(path)
                self.progress.emit(idx + 1, total, file_name)
                self.log.emit(f"正在转换 ({idx + 1}/{total}): {file_name}")

                doc = None
                try:
                    abs_path = os.path.abspath(path)
                    pdf_path = os.path.splitext(abs_path)[0] + ".pdf"

                    # 3. 打开文档
                    doc = self._open_document(self._app, abs_path)
                    
                    # 4. 另存为 PDF
                    self._save_as_pdf(doc, pdf_path)
                    
                    success += 1
                    self.log.emit(f"✅ 成功: {file_name}")
                
                except Exception as e:
                    fail += 1
                    self.log.emit(f"❌ 失败 {file_name}: {str(e)}")
                
                finally:
                    # 5. 关闭文档
                    if doc:
                        try:
                            self._close_document(doc)
                        except:
                            pass

        except Exception as e:
            self.log.emit(f"🔥 严重错误: {str(e)}")
        
        finally:
            # 6. 清理应用实例
            if self._app:
                try:
                    self._quit_app(self._app)
                except:
                    pass
                self._app = None
            
            try:
                comtypes.CoUninitialize()
            except:
                pass
            
            self.finished.emit(success, fail)
            self._is_running = False

    def stop(self):
        """停止当前任务"""
        self._is_running = False

    @property
    @abstractmethod
    def app_name(self) -> str:
        """返回应用程序名称 (用于日志)"""
        pass

    @abstractmethod
    def _create_app(self):
        """创建并返回 COM 应用实例"""
        pass

    @abstractmethod
    def _open_document(self, app, file_path: str):
        """打开文档并返回文档对象"""
        pass

    @abstractmethod
    def _save_as_pdf(self, doc, output_path: str):
        """将文档对象另存为 PDF"""
        pass

    @abstractmethod
    def _close_document(self, doc):
        """关闭文档对象 (不保存更改)"""
        pass

    @abstractmethod
    def _quit_app(self, app):
        """退出应用程序"""
        pass
