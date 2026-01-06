import os
import subprocess
import platform
from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal
from core.external_tools.manager import ExternalToolManager

class LibreOfficeEngine(QObject):
    """LibreOffice 转 PDF 引擎 (基于 CLI)"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = False
        self._tool_manager = ExternalToolManager()

    def is_available(self) -> bool:
        """检查 LibreOffice 是否可用"""
        tool = self._tool_manager.get_tool("libreoffice")
        return tool and tool.is_available()

    def get_executable_path(self) -> Optional[str]:
        """获取 LibreOffice 可执行文件路径"""
        tool = self._tool_manager.get_tool("libreoffice")
        if tool and tool.is_available():
            return tool.get_executable_path()
        return None

    def convert(self, file_paths: List[str], output_format: str = "pdf"):
        """
        使用 LibreOffice 转换文档
        
        Args:
            file_paths: 要转换的文件路径列表
            output_format: 输出格式 (默认 'pdf')
        """
        self._is_running = True
        total = len(file_paths)
        success = 0
        fail = 0

        soffice_path = self.get_executable_path()
        if not soffice_path:
            self.log.emit("❌ LibreOffice 未安装或不可用")
            self.finished.emit(0, total)
            return

        self.log.emit(f"使用 LibreOffice: {soffice_path}")

        for idx, path in enumerate(file_paths):
            if not self._is_running:
                self.log.emit("任务已停止")
                break

            file_name = os.path.basename(path)
            self.progress.emit(idx + 1, total, file_name)
            self.log.emit(f"正在转换 ({idx + 1}/{total}): {file_name}")

            try:
                abs_path = os.path.abspath(path)
                output_dir = os.path.dirname(abs_path)
                
                # 构建命令
                # soffice --headless --convert-to pdf --outdir <output_dir> <input_file>
                cmd = [
                    soffice_path,
                    "--headless",
                    "--convert-to", output_format,
                    "--outdir", output_dir,
                    abs_path
                ]
                
                # 执行转换
                startupinfo = None
                creationflags = 0
                
                if platform.system() == 'Windows':
                    # Windows: 隐藏控制台窗口
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2分钟超时
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                if result.returncode == 0:
                    # 检查输出文件是否存在
                    base_name = os.path.splitext(os.path.basename(abs_path))[0]
                    output_path = os.path.join(output_dir, f"{base_name}.{output_format}")
                    
                    if os.path.exists(output_path):
                        success += 1
                        self.log.emit(f"✅ 成功: {file_name}")
                    else:
                        fail += 1
                        self.log.emit(f"❌ 失败 {file_name}: 输出文件未生成")
                else:
                    fail += 1
                    error_msg = result.stderr.strip() if result.stderr else "转换失败"
                    self.log.emit(f"❌ 失败 {file_name}: {error_msg}")
                    
            except subprocess.TimeoutExpired:
                fail += 1
                self.log.emit(f"❌ 失败 {file_name}: 转换超时")
            except Exception as e:
                fail += 1
                self.log.emit(f"❌ 失败 {file_name}: {str(e)}")

        self.log.emit(f"\n转换完成！成功: {success}, 失败: {fail}")
        self.finished.emit(success, fail)
        self._is_running = False

    def stop(self):
        """停止当前任务"""
        self._is_running = False


class LibreOfficeWordEngine(LibreOfficeEngine):
    """LibreOffice Word 转 PDF 引擎"""
    
    def convert(self, file_paths: List[str]):
        """转换 Word 文档为 PDF"""
        super().convert(file_paths, output_format="pdf")


class LibreOfficeExcelEngine(LibreOfficeEngine):
    """LibreOffice Excel 转 PDF 引擎"""
    
    def convert(self, file_paths: List[str]):
        """转换 Excel 文档为 PDF"""
        super().convert(file_paths, output_format="pdf")


class LibreOfficePowerPointEngine(LibreOfficeEngine):
    """LibreOffice PowerPoint 转 PDF 引擎"""
    
    def convert(self, file_paths: List[str]):
        """转换 PowerPoint 文档为 PDF"""
        super().convert(file_paths, output_format="pdf")