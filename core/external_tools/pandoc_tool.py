import shutil
import subprocess
import os
from typing import Optional
from .base import ExternalTool

class PandocTool(ExternalTool):
    """Pandoc 文档转换工具"""
    
    name = "pandoc"
    display_name = "Pandoc"
    description = "专业文档转换工具，支持数学公式和高级排版"
    download_url = "https://pandoc.org/installing.html"
    is_required = False  # Markdown 转 PDF 的可选依赖
    
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
        """查找 Pandoc 安装路径 (带缓存)"""
        if self._cache is not None:
            return self._cache

        result = {
            "found": False,
            "path": None,
            "version": None,
            "source": None
        }
        
        # 1. 优先检查 libs 目录 (便携模式)
        libs_path = self.get_libs_path()
        portable_pandoc = os.path.join(libs_path, "pandoc", "pandoc.exe")
        
        if os.path.exists(portable_pandoc):
            result["found"] = True
            result["path"] = portable_pandoc
            result["source"] = "portable"
            result["version"] = self._get_version_from_exe(portable_pandoc)
            self._cache = result
            return result

        # 2. 检查环境变量
        path = shutil.which("pandoc")
        if path:
            result["found"] = True
            result["path"] = path
            result["source"] = "env"
            result["version"] = self._get_version_from_exe(path)
        
        self._cache = result
        return result

    def _get_version_from_exe(self, path: str) -> Optional[str]:
        """从 exe 获取版本号"""
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            cmd_result = subprocess.run(
                [path, "--version"], 
                capture_output=True, 
                text=True,
                startupinfo=startupinfo,
                encoding='utf-8'
            )
            if cmd_result.returncode == 0:
                # 输出格式: pandoc 3.1.2 ...
                return cmd_result.stdout.split('\n')[0].split(' ')[1]
        except Exception as e:
            print(f"Error checking Pandoc version: {e}")
        return None
