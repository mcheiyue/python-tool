import os
import comtypes.client
from abc import abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal

from core.batch import run as batch_run
from core.utils.office_security import macros_disabled

class BaseOfficeConverter(QObject):
    """Office 文档转换器基类 (Template Method Pattern)"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    log = pyqtSignal(str)

    def __init__(self, tool_manager=None):
        super().__init__()
        self._is_running = False
        self._app = None
        self._tool_manager = tool_manager
        self._fallback = None
        self.backend = None

    def convert(self, file_paths):
        """执行转换任务的模板方法"""
        self._is_running = True
        self.backend = self.app_name
        total = len(file_paths)
        success = 0
        fail = 0

        try:
            # 1. 初始化 COM 环境
            comtypes.CoInitialize()
            self.log.emit(f"正在启动 {self.app_name}...")
            
            # 2. 创建应用实例
            try:
                self._app = self._create_app()
            except (OSError, comtypes.COMError):
                if self._tool_manager is None:
                    raise
                from .libreoffice import LibreOfficeEngine
                self._fallback = LibreOfficeEngine(self._tool_manager)
                self._fallback.log.connect(self.log.emit)
                self._fallback.progress.connect(self.progress.emit)
                self.backend = "LibreOffice"
                self.log.emit("MS Office 不可用，尝试 LibreOffice")
                success, fail = self._fallback.convert(file_paths)
                return success, fail

            def worker(path):
                file_name = os.path.basename(path)
                self.log.emit(f"正在转换: {file_name}")
                doc = None
                try:
                    abs_path = os.path.abspath(path)
                    pdf_path = os.path.splitext(abs_path)[0] + ".pdf"

                    # 3. 打开文档
                    with macros_disabled(self._app):
                        doc = self._open_document(self._app, abs_path)
                    
                    # 4. 另存为 PDF
                    self._save_as_pdf(doc, pdf_path)
                    
                    self.log.emit(f"✅ 成功: {file_name}")
                finally:
                    # 5. 关闭文档
                    if doc:
                        try:
                            self._close_document(doc)
                        except Exception as e:
                            self.log.emit(f"⚠️ 关闭文档失败: {str(e)}")

            success, fail = batch_run(
                file_paths,
                worker,
                on_progress=lambda c, t, p: self.progress.emit(c, t, os.path.basename(p)),
                on_log=self.log.emit,
                should_stop=lambda: not self._is_running,
            )

        except Exception as e:
            self.log.emit(f"🔥 严重错误: {str(e)}")
            fail = total - success
        
        finally:
            # 6. 清理应用实例
            if self._app:
                try:
                    self._quit_app(self._app)
                except Exception as e:
                    self.log.emit(f"⚠️ 退出应用失败: {str(e)}")
                self._app = None
            
            try:
                comtypes.CoUninitialize()
            except Exception as e:
                self.log.emit(f"⚠️ COM 反初始化失败: {str(e)}")
            
            self.finished.emit(success, fail)
            self._is_running = False
            self._fallback = None
        return success, fail

    def stop(self):
        """停止当前任务"""
        self._is_running = False
        if self._fallback is not None:
            self._fallback.stop()

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
