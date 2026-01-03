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

    def _find(self) -> dict:
        """查找 Pandoc 安装路径 (带缓存)"""
        if self._cache is not None:
            return self._cache

        result = {
            "found": False,
            "path": None,
            "version": None
        }
        
        path = shutil.which("pandoc")
        if path:
            result["found"] = True
            result["path"] = path
            try:
                # 检查版本
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
                    version = cmd_result.stdout.split('\n')[0].split(' ')[1]
                    result["version"] = version
            except Exception as e:
                print(f"Error checking Pandoc version: {e}")
        
        self._cache = result
        return result
