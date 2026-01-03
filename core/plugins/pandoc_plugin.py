import shutil
import subprocess
import os
import tempfile
from typing import Dict, Any, Optional
from .base import PluginBase

class PandocPlugin(PluginBase):
    name = "pandoc"
    display_name = "Pandoc 转换引擎"
    description = "专业文档转换工具，支持数学公式和高级排版 (需安装 Pandoc)"
    version = "1.0.0"
    
    requires_external = True
    external_tool = "pandoc"
    download_url = "https://pandoc.org/installing.html"
    
    def check_availability(self) -> Dict[str, Any]:
        path = shutil.which("pandoc")
        if path:
            try:
                # 检查版本，防止调用错误的程序
                # Windows 上为了避免弹出窗口，需要 STARTUPINFO (如果不是在控制台运行)
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                result = subprocess.run(
                    [path, "--version"], 
                    capture_output=True, 
                    text=True,
                    startupinfo=startupinfo,
                    encoding='utf-8' # 强制 utf-8 避免中文乱码
                )
                version = result.stdout.split('\n')[0].split(' ')[1]
                return {
                    "available": True,
                    "path": path,
                    "version": version,
                    "message": f"已安装 Pandoc {version}"
                }
            except Exception as e:
                return {
                    "available": False,
                    "path": path,
                    "version": "Unknown",
                    "message": f"Pandoc 运行异常: {e}"
                }
        
        return {
            "available": False,
            "path": "",
            "version": "",
            "message": "未找到 Pandoc，请下载安装"
        }
    
    def convert(self, content: str, input_format: str = "markdown", output_format: str = "pdf", output_path: str = None, extra_args: list = None):
        """
        使用 Pandoc 转换文档
        :param content: 输入内容字符串
        :param input_format: 输入格式 (默认 markdown)
        :param output_format: 输出格式 (默认 pdf)
        :param output_path: 输出文件路径
        :param extra_args: 额外参数列表
        """
        if not self.is_available:
            raise RuntimeError("Pandoc 不可用")
            
        cmd = ["pandoc", "-f", input_format, "-t", output_format]
        
        if output_format == "pdf":
            # 默认使用 xelatex 引擎以支持中文
            cmd.extend(["--pdf-engine=xelatex"])
            # 添加中文支持参数 (需系统有中文字体)
            cmd.extend(["-V", "CJKmainfont=Microsoft YaHei"])
            
        if extra_args:
            cmd.extend(extra_args)
            
        if output_path:
            cmd.extend(["-o", output_path])
            
        # 准备输入
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            subprocess.run(
                cmd,
                input=content,
                text=True,
                check=True,
                startupinfo=startupinfo,
                encoding='utf-8'
            )
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Pandoc 转换失败: {e}")
