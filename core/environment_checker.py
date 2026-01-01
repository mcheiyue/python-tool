import os
import sys
import shutil
import platform

class EnvironmentChecker:
    @staticmethod
    def find_ghostscript() -> dict:
        """
        查找 Ghostscript 安装路径
        返回: {"found": bool, "path": str, "version": str, "download_url": str}
        """
        result = {
            "found": False,
            "path": "",
            "version": "",
            "download_url": "https://ghostscript.com/releases/gsdnld.html"
        }
        
        system = platform.system().lower()
        
        # Windows 搜索逻辑
        if system == 'windows':
            # 1. 检查环境变量
            path = shutil.which("gswin64c") or shutil.which("gswin32c")
            if path:
                result["found"] = True
                result["path"] = path
                return result
                
            # 2. 搜索常见安装目录
            search_roots = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            ]
            
            latest_version = (0, 0)
            best_path = ""
            
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
                            except:
                                continue
                except:
                    continue
            
            if best_path:
                result["found"] = True
                result["path"] = best_path
                result["version"] = ".".join(map(str, latest_version))
                
        # Linux/macOS 简单检查
        else:
            path = shutil.which("gs")
            if path:
                result["found"] = True
                result["path"] = path
            
            if system == 'darwin':
                result["download_url"] = "brew install ghostscript"
            elif system == 'linux':
                result["download_url"] = "sudo apt install ghostscript"
                
        return result

    @staticmethod
    def get_gs_download_url():
        return "https://ghostscript.com/releases/gsdnld.html"
