import subprocess
import os
import tempfile
import shutil
from typing import Dict, Any, Optional
from .base import PluginBase
from app.container import AppContainer

class PandocPlugin(PluginBase):
    name = "pandoc"
    display_name = "Pandoc 转换引擎"
    description = "专业文档转换工具，支持数学公式和高级排版 (需安装 Pandoc)"
    version = "1.0.0"
    
    requires_external = True
    external_tool = "pandoc"
    download_url = "https://pandoc.org/installing.html"
    
    capabilities = ["markdown_to_pdf", "markdown_to_docx", "html_to_docx"]
    priority = 10  # 高优先级

    @property
    def has_pdf_engine(self) -> bool:
        """检查是否有可用的 PDF 引擎 (如 xelatex)"""
        if not self.is_available:
            return False
        # 优先检查 xelatex (对中文支持最好)
        if shutil.which("xelatex"):
            return True
        # 其次检查 pdflatex
        if shutil.which("pdflatex"):
            return True
        # 检查 wkhtmltopdf
        if shutil.which("wkhtmltopdf"):
            return True
        return False

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
            
        pandoc_exe = self.get_executable_path() or "pandoc"
        cmd = [pandoc_exe, "-f", input_format, "-t", output_format]
        
        if output_format == "pdf":
            # 智能选择 PDF 引擎
            if shutil.which("xelatex"):
                cmd.extend(["--pdf-engine=xelatex"])
                cmd.extend(["-V", "CJKmainfont=Microsoft YaHei"])
            elif shutil.which("pdflatex"):
                # pdflatex 对中文支持较差，但聊胜于无
                pass
            elif shutil.which("wkhtmltopdf"):
                cmd.extend(["--pdf-engine=wkhtmltopdf"])
            else:
                # 如果没有引擎，Pandoc 可能会报错，或者尝试默认。
                # 最好在调用前检查 has_pdf_engine
                pass
            
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

    def convert_to_docx(self, content: str, output_path: str, reference_docx: str = None, filters: list = None, input_format: str = "markdown"):
        """
        转换为 DOCX 文件
        """
        extra_args = []
        if reference_docx:
            extra_args.extend(["--reference-doc", reference_docx])
            
        if filters:
            for f in filters:
                extra_args.extend(["--lua-filter", f] if f.endswith(".lua") else ["--filter", f])
                
        return self.convert(content, input_format=input_format, output_format="docx", output_path=output_path, extra_args=extra_args)

    def convert_to_docx_bytes(self, content: str, reference_docx: str = None, filters: list = None, input_format: str = "markdown") -> bytes:
        """
        转换为 DOCX 并返回字节流
        使用临时文件方式，因为 Pandoc 对于 DOCX 格式不支持直接输出到 stdout
        """
        if not self.is_available:
            raise RuntimeError("Pandoc 不可用")
            
        pandoc_exe = self.get_executable_path() or "pandoc"
        
        # 创建临时文件用于输出
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_out:
            tmp_output_path = tmp_out.name
        
        # 创建临时文件用于输入（避免长内容通过 stdin 传递的问题）
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False, mode='w', encoding='utf-8') as tmp_in:
            tmp_in.write(content)
            tmp_input_path = tmp_in.name
        
        try:
            cmd = [pandoc_exe, tmp_input_path, "-f", input_format, "-t", "docx", "-o", tmp_output_path]
            
            if reference_docx:
                cmd.extend(["--reference-doc", reference_docx])
                
            if filters:
                for f in filters:
                    cmd.extend(["--lua-filter", f] if f.endswith(".lua") else ["--filter", f])

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                startupinfo=startupinfo
            )
            
            # 读取临时文件内容
            with open(tmp_output_path, 'rb') as f:
                return f.read()
                
        except subprocess.CalledProcessError as e:
            # 提供更详细的错误信息，包括标准错误输出
            stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else ''
            raise RuntimeError(f"Pandoc 转换失败:\nCommand: {' '.join(cmd)}\nReturn code: {e.returncode}\nStderr: {stderr}")
        finally:
            # 清理临时文件
            for tmp_path in [tmp_input_path, tmp_output_path]:
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    pass

    def convert_html_to_docx(self, html_content: str, output_path: str, reference_docx: str = None, filters: list = None):
        """
        HTML 转换为 DOCX
        """
        return self.convert_to_docx(html_content, output_path, reference_docx, filters, input_format="html")
    
    def convert_html_to_docx_bytes(self, html_content: str, reference_docx: str = None, filters: list = None) -> bytes:
        """
        HTML 转换为 DOCX 字节流
        """
        return self.convert_to_docx_bytes(html_content, reference_docx, filters, input_format="html")
