import os
import shutil
import platform
import subprocess
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

    def get_source(self) -> Optional[str]:
        return self._find()["source"]

    def _find(self) -> dict:
        """查找 Ghostscript 安装路径 (带缓存)"""
        if self._cache is not None:
            return self._cache

        result = {
            "found": False,
            "path": None,
            "version": None,
            "source": None
        }
        
        system = platform.system().lower()
        
        # 1. 优先检查 libs 目录 (便携模式)
        libs_path = self.get_libs_path()
        portable_gs_dir = os.path.join(libs_path, "ghostscript")
        
        # 检查 libs/ghostscript 下的 exe
        portable_exes = ["gswin64c.exe", "gswin32c.exe", "gs"]
        for exe_name in portable_exes:
            portable_exe = os.path.join(portable_gs_dir, exe_name)
            if os.path.exists(portable_exe):
                # 找到便携版
                result["found"] = True
                result["path"] = portable_exe
                result["source"] = "portable"
                result["version"] = self._get_version_from_exe(portable_exe)
                self._cache = result
                
                # 设置 GS_LIB 环境变量，指向便携版的 lib 目录
                lib_dir = os.path.join(portable_gs_dir, "lib")
                if os.path.exists(lib_dir):
                    os.environ["GS_LIB"] = lib_dir
                    
                return result

        # 2. 检查环境变量
        if system == 'windows':
            path = shutil.which("gswin64c") or shutil.which("gswin32c")
        else:
            path = shutil.which("gs")
            
        if path:
            result["found"] = True
            result["path"] = path
            result["source"] = "env"
            result["version"] = self._get_version_from_exe(path)
            self._cache = result
            return result
            
        # 3. Windows 搜索常见安装目录
        if system == 'windows':
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
                result["source"] = "system"
                result["version"] = best_ver_str or ".".join(map(str, latest_version))
        
        self._cache = result
        return result

    def _get_version_from_exe(self, path: str) -> Optional[str]:
        """从 exe 获取版本号"""
        try:
            res = subprocess.run([path, "--version"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
            if res.returncode == 0:
                # Ghostscript 输出通常是 "10.03.1"
                return res.stdout.strip().split('\n')[0]
        except:
            pass
        return None
