import os
import sys
import shutil
import platform
import subprocess
from typing import Optional
from .base import ExternalTool

class LibreOfficeTool(ExternalTool):
    """LibreOffice 办公套件检测工具"""
    
    name = "libreoffice"
    display_name = "LibreOffice"
    description = "开源办公套件，可作为 Microsoft Office 的免费替代品"
    features = "支持 Word、Excel、PowerPoint 文档转换和处理"
    download_url = "https://www.libreoffice.org/download/download/"
    is_required = False  # Office 转换的可选依赖
    
    _cache = None

    def check_installed(self) -> bool:
        return self._find()["found"]
    
    def get_version(self) -> Optional[str]:
        return self._find()["version"]
    
    def get_path(self) -> Optional[str]:
        return self._find()["path"]

    def get_source(self) -> Optional[str]:
        return self._find()["source"]

    def _find(self) -> dict:
        """查找 LibreOffice 安装路径 (带缓存)
        
        跨平台检测策略：
        - Windows: 查找 soffice.exe 或 soffice.com
        - Linux: 查找 soffice 或 libreoffice
        - macOS: 查找 /Applications/LibreOffice.app/Contents/MacOS/soffice
        """
        if self._cache is not None:
            return self._cache

        result = {
            "found": False,
            "path": None,
            "version": None,
            "source": None
        }
        
        # 0. 如果已禁用，直接返回未找到
        if self.is_disabled:
            return result
        
        system = platform.system().lower()
        
        # 1. 检查环境变量 (PATH 中的 soffice)
        soffice_names = []
        if system == 'windows':
            soffice_names = ["soffice.exe", "soffice.com"]
        else:
            soffice_names = ["soffice", "libreoffice"]
        
        for exe_name in soffice_names:
            path = shutil.which(exe_name)
            if path:
                result["found"] = True
                result["path"] = path
                result["source"] = "env"
                result["version"] = self._get_version_from_exe(path)
                self._cache = result
                return result
        
        # 2. 平台特定的常见安装位置
        if system == 'windows':
            # Windows 常见安装路径
            search_paths = [
                # 标准安装路径
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            
            # 也检查环境变量中的路径
            program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            
            search_paths.extend([
                os.path.join(program_files, "LibreOffice", "program", "soffice.exe"),
                os.path.join(program_files_x86, "LibreOffice", "program", "soffice.exe"),
            ])
            
            for path in search_paths:
                if os.path.exists(path):
                    result["found"] = True
                    result["path"] = path
                    result["source"] = "system"
                    result["version"] = self._get_version_from_exe(path)
                    self._cache = result
                    return result
                    
        elif system == 'darwin':
            # macOS 应用程序路径
            mac_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                os.path.expanduser("~/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            ]
            
            for path in mac_paths:
                if os.path.exists(path):
                    result["found"] = True
                    result["path"] = path
                    result["source"] = "system"
                    result["version"] = self._get_version_from_exe(path)
                    self._cache = result
                    return result
                    
        elif system == 'linux':
            # Linux 常见安装路径
            linux_paths = [
                "/usr/bin/soffice",
                "/usr/bin/libreoffice",
                "/usr/local/bin/soffice",
                "/usr/local/bin/libreoffice",
                "/opt/libreoffice/program/soffice",
            ]
            
            for path in linux_paths:
                if os.path.exists(path):
                    result["found"] = True
                    result["path"] = path
                    result["source"] = "system"
                    result["version"] = self._get_version_from_exe(path)
                    self._cache = result
                    return result
        
        self._cache = result
        return result

    def _get_version_from_exe(self, path: str) -> Optional[str]:
        """从可执行文件获取 LibreOffice 版本号"""
        try:
            # LibreOffice 使用 --version 参数
            startupinfo = None
            creationflags = 0
            
            if platform.system() == 'Windows':
                # Windows: 隐藏控制台窗口
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            if result.returncode == 0:
                # LibreOffice 输出格式示例:
                # "LibreOffice 7.6.4.1 30(Build:1)"
                # "LibreOffice 24.2.0.0.alpha0+ 02b2acce88a210515b4a5bb2e46cbfb63fe97d0c"
                output = result.stdout.strip()
                
                # 尝试提取版本号
                if "LibreOffice" in output:
                    parts = output.split()
                    # 通常版本号是第二个词
                    if len(parts) >= 2:
                        version = parts[1]
                        # 去除可能的 alpha/beta 后缀
                        version = version.split('.alpha')[0].split('.beta')[0].split('.rc')[0]
                        return version
                
                # 如果格式不符合预期，返回整行
                return output.split('\n')[0]
                
        except subprocess.TimeoutExpired:
            # 版本检测超时
            pass
        except Exception as e:
            # 其他错误（如文件不存在、权限不足等）
            pass
        
        return None

    def get_program_dir(self) -> Optional[str]:
        """获取 LibreOffice 程序目录（用于查找其他组件）"""
        exe_path = self.get_path()
        if not exe_path:
            return None
        
        # Windows: soffice.exe 在 program 目录下
        # Linux/Mac: 可能在 bin 或 MacOS 目录下
        return os.path.dirname(exe_path)