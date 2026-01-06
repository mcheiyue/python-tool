import os
import markdown
import html2text
from typing import Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

from core.external_tools.manager import ExternalToolManager

class MarkdownConverter(QObject):
    """
    Markdown ↔ HTML 转换器
    支持使用基础库 (markdown, html2text) 和 Pandoc (增强功能)
    """
    
    finished = pyqtSignal(int, int)  # success_count, fail_count
    progress = pyqtSignal(int, int, str) # current, total, message
    log = pyqtSignal(str) # log message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self.pandoc_tool = ExternalToolManager().get_tool("pandoc")
        
    def stop(self):
        """停止当前任务"""
        self._is_running = False

    def is_pandoc_available(self) -> bool:
        """检查 Pandoc 是否可用"""
        return self.pandoc_tool.check_installed()

    def convert_markdown_to_html(
        self, 
        files: list[str], 
        output_dir: Optional[str] = None,
        use_pandoc: bool = False,
        include_css: bool = True
    ):
        """
        批量将 Markdown 转换为 HTML
        """
        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)
        
        self.log.emit(f"开始 Markdown -> HTML 转换任务，共 {total} 个文件")
        
        for i, file_path in enumerate(files):
            if not self._is_running:
                break
                
            file_name = os.path.basename(file_path)
            self.progress.emit(i, total, f"正在处理: {file_name}")
            
            try:
                # 确定输出路径
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".html")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".html"
                
                # 转换逻辑
                result = False
                if use_pandoc and self.is_pandoc_available():
                    result = self._md_to_html_pandoc(file_path, out_path)
                else:
                    result = self._md_to_html_basic(file_path, out_path, include_css)
                    
                if result:
                    success_count += 1
                    self.log.emit(f"✅ 成功: {file_name} -> {os.path.basename(out_path)}")
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
                self.log.emit(f"❌ 失败 {file_name}: {str(e)}")
                
        self.progress.emit(total, total, "完成")
        self.finished.emit(success_count, fail_count)
        self._is_running = False

    def convert_html_to_markdown(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        use_pandoc: bool = False
    ):
        """
        批量将 HTML 转换为 Markdown
        """
        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)
        
        self.log.emit(f"开始 HTML -> Markdown 转换任务，共 {total} 个文件")
        
        for i, file_path in enumerate(files):
            if not self._is_running:
                break
            
            file_name = os.path.basename(file_path)
            self.progress.emit(i, total, f"正在处理: {file_name}")
            
            try:
                # 确定输出路径
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".md")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".md"
                
                # 转换逻辑
                result = False
                if use_pandoc and self.is_pandoc_available():
                    result = self._html_to_md_pandoc(file_path, out_path)
                else:
                    result = self._html_to_md_basic(file_path, out_path)
                    
                if result:
                    success_count += 1
                    self.log.emit(f"✅ 成功: {file_name} -> {os.path.basename(out_path)}")
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
                self.log.emit(f"❌ 失败 {file_name}: {str(e)}")
        
        self.progress.emit(total, total, "完成")
        self.finished.emit(success_count, fail_count)
        self._is_running = False

    def _md_to_html_basic(self, input_path: str, output_path: str, include_css: bool = True) -> bool:
        """使用 Python-Markdown 库转换"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 扩展配置
            extensions = [
                'markdown.extensions.extra',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code'
            ]
            
            html_body = markdown.markdown(text, extensions=extensions)
            
            # 简单的 HTML 模板
            css_style = ""
            if include_css:
                css_style = """
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; padding: 2em; max-width: 900px; margin: 0 auto; color: #333; }
                    code { background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }
                    pre { background-color: #f6f8fa; padding: 1em; border-radius: 5px; overflow: auto; }
                    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
                    th, td { border: 1px solid #dfe2e5; padding: 0.6em 1em; }
                    th { background-color: #f6f8fa; }
                    blockquote { border-left: 4px solid #dfe2e5; color: #6a737d; padding-left: 1em; margin: 1em 0; }
                    img { max-width: 100%; }
                </style>
                """
                
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{os.path.basename(input_path)}</title>
                {css_style}
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
                
            return True
        except Exception as e:
            self.log.emit(f"Basic MD->HTML Error: {e}")
            return False

    def _html_to_md_basic(self, input_path: str, output_path: str) -> bool:
        """使用 html2text 库转换"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0 # 不自动换行
            h.ignore_images = False
            h.ignore_emphasis = False
            
            md_content = h.handle(html_content)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            return True
        except Exception as e:
            self.log.emit(f"Basic HTML->MD Error: {e}")
            return False

    def _md_to_html_pandoc(self, input_path: str, output_path: str) -> bool:
        """使用 Pandoc 转换 (调用 CLI)"""
        pandoc_path = self.pandoc_tool.get_path()
        if not pandoc_path:
            return False
            
        import subprocess
        # 基础命令: pandoc input.md -o output.html --standalone --metadata title="Title"
        cmd = [
            pandoc_path,
            input_path,
            "-o", output_path,
            "--standalone", # 生成完整 HTML
            "--metadata", f"title={os.path.basename(input_path)}"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            self.log.emit(f"Pandoc Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            self.log.emit(f"Pandoc Execution Error: {e}")
            return False

    def _html_to_md_pandoc(self, input_path: str, output_path: str) -> bool:
        """使用 Pandoc 转换 HTML -> Markdown"""
        pandoc_path = self.pandoc_tool.get_path()
        if not pandoc_path:
            return False
            
        import subprocess
        # 基础命令: pandoc input.html -o output.md
        # 可以添加 -f html -t markdown_strict 或 gfm
        cmd = [
            pandoc_path,
            input_path,
            "-f", "html",
            "-t", "gfm", # GitHub Flavored Markdown
            "-o", output_path,
            "--wrap=none" # 不自动换行
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            self.log.emit(f"Pandoc Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            self.log.emit(f"Pandoc Execution Error: {e}")
            return False