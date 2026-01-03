import os
import shutil
import platform
from typing import Optional
from .base import ExternalTool

class GhostscriptTool(ExternalTool):
    """Ghostscript PDF 处理引擎"""
    
    name = "ghostscript"
    display_name = "Ghostscript"
    description = "用于 PDF 压缩和处理的解释器"
    download_url = "https://ghostscript.com/releases/gsdnld.html"
    is_required = True  # PDF 压缩功能的核心依赖
    
    _cache = None

    def check_installed(self) -> bool:
        return self._find()["found"]
    
    def get_version(self) -> Optional[str]:
        return self._find()["version"]
    
    def get_path(self) -> Optional[str]:
        return self._find()["path"]

    def _find(self) -> dict:
        """查找 Ghostscript 安装路径 (带缓存)"""
        if self._cache is not None:
            return self._cache

        result = {
            "found": False,
            "path": None,
            "version": None
        }
        
        system = platform.system().lower()
        
        # Windows 搜索逻辑
        if system == 'windows':
            # 1. 检查环境变量
            path = shutil.which("gswin64c") or shutil.which("gswin32c")
            if path:
                result["found"] = True
                result["path"] = path
                self._cache = result
                return result
                
            # 2. 搜索常见安装目录
            search_roots = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            ]
            
            latest_version = (0, 0)
            best_path = None
            best_ver_str = None
            
            for root in search_roots:
                gs_root = os.path.join(root, "gs")
                if not os.path.exists(gs_root):
                    continue
                    
                # 遍历 gs 目录下的版本文件夹 (如 gs10.06.0)
                try:
                    for item in os.listdir(gs_root):
                        if item.startswith("gs"):
                            # 解析版本号
                            try:
                                ver_str = item[2:] # 去掉 'gs'
                                version_tuple = tuple(map(int, ver_str.split('.')))
                                
                                # 检查 bin 目录下的 exe
                                bin_dir = os.path.join(gs_root, item, "bin")
                                exe_path = os.path.join(bin_dir, "gswin64c.exe")
                                if not os.path.exists(exe_path):
                                    exe_path = os.path.join(bin_dir, "gswin32c.exe")
                                    
                                if os.path.exists(exe_path):
                                    if version_tuple > latest_version:
                                        latest_version = version_tuple
                                        best_path = exe_path
                                        best_ver_str = ver_str
                            except:
                                continue
                except:
                    continue
            
            if best_path:
                result["found"] = True
                result["path"] = best_path
                result["version"] = best_ver_str or ".".join(map(str, latest_version))
                
        # Linux/macOS 简单检查
        else:
            path = shutil.which("gs")
            if path:
                result["found"] = True
                result["path"] = path
                # 尝试获取版本
                try:
                    import subprocess
                    res = subprocess.run([path, "--version"], capture_output=True, text=True)
                    if res.returncode == 0:
                        result["version"] = res.stdout.strip()
                except:
                    pass
        
        self._cache = result
        return result
