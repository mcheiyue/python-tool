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
    features = "提供 Markdown 转 PDF 功能（支持数学公式）"
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
        """查找 Pandoc 安装路径 (带缓存)

        发现链：便携目录 → .mcy 惰性解压 → PATH。
        步骤 1-3 在基类 ExternalTool._resolve_executable；pandoc 无系统路径回退。
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
        
        path, source = self._resolve_executable(["pandoc.exe", "pandoc"])
        if path:
            result.update(
                found=True,
                path=path,
                source=source,
                version=self.probe_version(path),
            )

        self._cache = result
        return result


    def uninstall(self) -> bool:
        """卸载便携版 Pandoc (删除目录)"""
        self._cache = None
        if not self.check_installed():
            return False
            
        info = self.get_status_info()
        if info.get("source") != "portable":
            return False
            
        exe_path = info.get("path")
        if not exe_path:
            return False
            
        install_dir = os.path.dirname(exe_path)
        
        # 安全检查
        libs_path = os.path.abspath(self.get_libs_path())
        abs_install_dir = os.path.abspath(install_dir)
        
        if not abs_install_dir.startswith(libs_path):
            print(f"Refusing to uninstall external directory: {abs_install_dir}")
            return False
            
        try:
            shutil.rmtree(install_dir)
            self._cache = None
            return True
        except Exception as e:
            print(f"Pandoc uninstall failed: {e}")
            return False

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
