import os
import markdown
import html2text
from typing import Optional

from core.external_tools.manager import ExternalToolManager

class MarkdownConverter:
    """
    Markdown ↔ HTML 转换器
    支持使用基础库 (markdown, html2text) 和 Pandoc (增强功能)
    """

    def __init__(self):
        self._is_running = True
        self.pandoc_tool = ExternalToolManager().get_tool("pandoc")

    def stop(self):
        self._is_running = False

    def is_pandoc_available(self) -> bool:
        return self.pandoc_tool.check_installed()

    def convert_markdown_to_html(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        use_pandoc: bool = False,
        include_css: bool = True,
        *,
        on_log=None,
        on_progress=None,
        on_finished=None
    ):
        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, fail):
            if on_finished:
                on_finished(ok, fail)

        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)

        log(f"开始 Markdown -> HTML 转换任务，共 {total} 个文件")

        for i, file_path in enumerate(files):
            if not self._is_running:
                break

            file_name = os.path.basename(file_path)
            progress(i, total, f"正在处理: {file_name}")

            try:
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".html")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".html"

                if use_pandoc and self.is_pandoc_available():
                    result = self._md_to_html_pandoc(file_path, out_path, log)
                else:
                    result = self._md_to_html_basic(file_path, out_path, include_css, log)

                if result:
                    success_count += 1
                    log(f"✅ 成功: {file_name} -> {os.path.basename(out_path)}")
                else:
                    fail_count += 1

            except Exception as e:
                fail_count += 1
                log(f"❌ 失败 {file_name}: {str(e)}")

        progress(total, total, "完成")
        finished(success_count, fail_count)
        self._is_running = False

    def convert_html_to_markdown(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        use_pandoc: bool = False,
        *,
        on_log=None,
        on_progress=None,
        on_finished=None
    ):
        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, fail):
            if on_finished:
                on_finished(ok, fail)

        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)

        log(f"开始 HTML -> Markdown 转换任务，共 {total} 个文件")

        for i, file_path in enumerate(files):
            if not self._is_running:
                break

            file_name = os.path.basename(file_path)
            progress(i, total, f"正在处理: {file_name}")

            try:
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".md")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".md"

                if use_pandoc and self.is_pandoc_available():
                    result = self._html_to_md_pandoc(file_path, out_path, log)
                else:
                    result = self._html_to_md_basic(file_path, out_path, log)

                if result:
                    success_count += 1
                    log(f"✅ 成功: {file_name} -> {os.path.basename(out_path)}")
                else:
                    fail_count += 1

            except Exception as e:
                fail_count += 1
                log(f"❌ 失败 {file_name}: {str(e)}")

        progress(total, total, "完成")
        finished(success_count, fail_count)
        self._is_running = False

    def _md_to_html_basic(self, input_path: str, output_path: str, include_css: bool, log) -> bool:
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
            log(f"Basic MD->HTML Error: {e}")
            return False

    def _html_to_md_basic(self, input_path: str, output_path: str, log) -> bool:
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
            log(f"Basic HTML->MD Error: {e}")
            return False

    def _md_to_html_pandoc(self, input_path: str, output_path: str, log) -> bool:
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
            log(f"Pandoc Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            log(f"Pandoc Execution Error: {e}")
            return False

    def _html_to_md_pandoc(self, input_path: str, output_path: str, log) -> bool:
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
            log(f"Pandoc Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            log(f"Pandoc Execution Error: {e}")
            return False