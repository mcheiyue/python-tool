import os
import sys
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
    features = "提供 PDF 压缩功能"
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
        """查找 Ghostscript 安装路径 (带缓存)

        发现链：便携目录 → .mcy 惰性解压 → PATH → Windows 版本目录扫描。
        步骤 1-3 在基类 ExternalTool._resolve_executable；步骤 4 为 gs 特有。
        """
        if self._cache is not None:
            return self._cache

        result = {
            "found": False,
            "path": None,
            "version": None,
            "source": None
        }
        
        # 0. 如果已禁用，直接返回未找到 (防止自动解压)
        if self.is_disabled:
            return result

        def _set_gs_lib(exe_path):
            # GS_LIB 指向便携版的 lib 目录，供解释器加载资源文件
            lib_dir = os.path.join(os.path.dirname(exe_path), "lib")
            if os.path.exists(lib_dir):
                os.environ["GS_LIB"] = lib_dir

        is_windows = platform.system().lower() == "windows"

        # 1-3. 便携目录 / .mcy 惰性解压 / PATH
        path, source = self._resolve_executable(
            ["gswin64c.exe", "gswin32c.exe", "gs"],
            which_names=["gswin64c", "gswin32c"] if is_windows else ["gs"],
            on_portable=_set_gs_lib,
        )

        # 4. Windows 常见安装目录：Program Files 下的版本目录，取最高版本
        if not path and is_windows:
            scanned = self._scan_windows_gs()
            if scanned:
                exe_path, version = scanned
                result.update(found=True, path=exe_path, source="system", version=version)
                self._cache = result
                return result

        if path:
            result.update(
                found=True,
                path=path,
                source=source,
                version=self.probe_version(path),
            )

        self._cache = result
        return result

    def _scan_windows_gs(self):
        """扫描 Program Files 的 gs 版本目录（如 gs10.06.0），取最高版本。

        返回 (exe 路径, 版本字符串) 或 None。版本取自目录名，不 spawn 进程。
        """
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
                    if not item.startswith("gs"):
                        continue
                    try:
                        ver_str = item[2:]  # 去掉 'gs'
                        version_tuple = tuple(map(int, ver_str.split('.')))
                    except Exception:
                        # 版号解析失败，跳过该版本
                        continue

                    # 检查 bin 目录下的 exe
                    bin_dir = os.path.join(gs_root, item, "bin")
                    exe_path = os.path.join(bin_dir, "gswin64c.exe")
                    if not os.path.exists(exe_path):
                        exe_path = os.path.join(bin_dir, "gswin32c.exe")

                    if os.path.exists(exe_path) and version_tuple > latest_version:
                        latest_version = version_tuple
                        best_path = exe_path
                        best_ver_str = ver_str
            except Exception:
                # 目录列举失败，跳过该根目录
                continue

        if best_path:
            return best_path, best_ver_str or ".".join(map(str, latest_version))
        return None


    def uninstall(self) -> bool:
        """卸载便携版 Ghostscript (删除目录)"""
        # 1. 确保已获取最新状态
        self._cache = None
        if not self.check_installed():
            return False
            
        info = self.get_status_info()
        # 2. 仅允许卸载便携版
        if info.get("source") != "portable":
            return False
            
        exe_path = info.get("path")
        if not exe_path:
            return False
            
        # 3. 确定卸载目录 (exe 所在目录)
        install_dir = os.path.dirname(exe_path)
        
        # 4. 安全检查：必须在 libs 目录下
        libs_path = os.path.abspath(self.get_libs_path())
        abs_install_dir = os.path.abspath(install_dir)
        
        if not abs_install_dir.startswith(libs_path):
            print(f"Refusing to uninstall external directory: {abs_install_dir}")
            return False
            
        try:
            # 5. 删除目录
            shutil.rmtree(install_dir)
            self._cache = None
            return True
        except Exception as e:
            print(f"Ghostscript uninstall failed: {e}")
            return False

    def _get_version_from_exe(self, path: str) -> Optional[str]:
        """从 exe 获取版本号"""
        try:
            res = subprocess.run([path, "--version"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
            if res.returncode == 0:
                # Ghostscript 输出通常是 "10.03.1"
                return res.stdout.strip().split('\n')[0]
        except Exception as e:
            # 获取版本号失败（可能文件不存在或执行出错）
            pass
        return None
