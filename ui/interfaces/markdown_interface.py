import markdown
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QSplitter, QFileDialog, QMenu
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, TextEdit, InfoBar, 
                            FluentIcon as FIF, isDarkTheme, qconfig, ComboBox, ToolButton)

from core.plugins import PluginManager
from core.utils.md_normalizer import normalize_markdown
from ui.threads import WorkerThread

class MarkdownInterface(QWidget):
    def __init__(self, container, parent=None):
        super().__init__(parent=parent)
        self.container = container
        self.setObjectName("markdown_interface")
        
        # 初始化插件管理器
        self.plugin_manager = container.plugin_manager
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(20, 20, 20, 20)
        self.vbox.setSpacing(15)

        self.title = SubtitleLabel("Markdown 转 PDF", self)
        self.desc = BodyLabel("实时预览 Markdown 并导出为 PDF", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 工具栏
        self.toolbar = QHBoxLayout()
        
        # 背景选择
        self.bg_combo = ComboBox(self)
        self.bg_combo.addItems(["跟随主题", "白色背景"])
        self.bg_combo.setFixedWidth(120)
        
        # 导出引擎选择
        self.engine_combo = ComboBox(self)
        self.engine_combo.setFixedWidth(140)
        self.engine_combo.addItem("内置转换 (基础)", "builtin")
        
        # 检查 Pandoc 插件
        self.pandoc = self.plugin_manager.get("pandoc")
        if self.pandoc and self.pandoc.is_available:
            self.engine_combo.addItem("Pandoc (专业)", "pandoc")
            # 默认选用 Pandoc
            self.engine_combo.setCurrentIndex(1)
        
        self.export_btn = PrimaryPushButton(FIF.SAVE, "导出 PDF", self)
        self.export_btn.clicked.connect(self.export_pdf)
        
        self.toolbar.addWidget(self.bg_combo)
        self.toolbar.addWidget(self.engine_combo)
        self.toolbar.addWidget(self.export_btn)
        self.toolbar.addStretch(1)
        self.vbox.addLayout(self.toolbar)

        # 分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 编辑器
        self.editor = TextEdit(self)
        self.editor.setPlaceholderText("在此输入 Markdown 内容...")
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.textChanged.connect(self.update_preview)
        
        # 预览容器
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)

        # 占位符
        self.placeholder_widget = QWidget()
        self.placeholder_layout = QVBoxLayout(self.placeholder_widget)
        self.placeholder_layout.addStretch(1)
        self.placeholder_label = BodyLabel("点击加载预览 (使用轻量级 QTextBrowser)", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_btn = PrimaryPushButton("加载预览 / 启用导出", self)
        self.load_btn.clicked.connect(self.init_webview)
        self.placeholder_layout.addWidget(self.placeholder_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.placeholder_layout.addWidget(self.load_btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.placeholder_layout.addStretch(1)
        
        self.preview_layout.addWidget(self.placeholder_widget)
        
        self.webview = None
        
        # 监听主题变更
        qconfig.themeChanged.connect(self.update_style)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([450, 450])
        
        self.vbox.addWidget(self.splitter, 1)
        
        # 初始化样式
        self.update_style()
        
        # 默认文本
        default_text = "# Hello World\n\n欢迎使用 **Markdown 转 PDF** 工具！\n\n"
        if self.pandoc and self.pandoc.is_available:
             default_text += "### 数学公式示例 (Pandoc)\n\nEinstein's $E=mc^2$\n\n$$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$\n\n"
             
        default_text += "### 代码示例\n\n```python\ndef hello():\n    print('Hello')\n```"
        self.editor.setText(default_text)

    def get_css_style(self, force_light=False):
        """根据主题返回对应的 CSS 样式"""
        is_dark = isDarkTheme() and not force_light
        
        # 获取高亮插件 CSS
        highlight_css = ""
        hl_plugin = self.plugin_manager.get("highlight")
        if hl_plugin and hl_plugin.is_available:
            # 深色模式使用 monokai，浅色模式使用 default
            style_name = "monokai" if is_dark else "default"
            highlight_css = hl_plugin.get_css(style_name)

        base_css = """
            body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; }
            h1, h2, h3 { margin-top: 20px; border-bottom: 1px solid #eee; }
            a { text-decoration: none; }
            code { padding: 2px 4px; border-radius: 4px; font-family: Consolas; }
            pre { padding: 10px; border: 1px solid #e0e0e0; margin: 10px 0; border-radius: 6px; }
            blockquote { border-left: 4px solid #ddd; padding-left: 10px; margin: 10px 0; }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #e0e0e0; }
            th, td { border: 1px solid #e0e0e0; padding: 8px; }
            ul, ol { padding-left: 20px; }
            img { max-width: 100%; border-radius: 4px; }
        """
        
        if is_dark:
            theme_css = """
            body { color: #e0e0e0; background-color: #2b2b2b; }
            h1, h2, h3 { color: #9cdcfe; border-bottom: 1px solid #444; }
            a { color: #4ec9b0; }
            code { background-color: #3c3c3c; color: #ce9178; }
            pre { background-color: #1e1e1e; border: 1px solid #444; }
            blockquote { border-left: 4px solid #444; color: #888; }
            table { border: 1px solid #444; }
            th, td { border: 1px solid #444; }
            th { background-color: #333; font-weight: bold; color: #ddd; }
            """
        else:
            theme_css = """
            body { color: #333; background-color: #ffffff; }
            h1, h2, h3 { color: #2c3e50; border-bottom: 1px solid #eee; }
            a { color: #007acc; }
            code { background-color: #f3f3f3; color: #c7254e; }
            pre { background-color: #f8f8f8; border: 1px solid #e0e0e0; }
            blockquote { border-left: 4px solid #ddd; color: #777; }
            th { background-color: #f9f9f9; font-weight: bold; color: #444; }
            """
            
        return f"<style>{base_css}\n{theme_css}\n{highlight_css}</style>"

    def update_style(self):
        """更新组件样式以适配主题"""
        dark = isDarkTheme()
        border_color = "#3d3d3d" if dark else "#e0e0e0"
        focus_color = "#555555" if dark else "#b0b0b0"
        bg_color = "#202020" if dark else "#ffffff"
        text_color = "#e0e0e0" if dark else "#333333"
        
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: {bg_color};
                color: {text_color};
                padding: 5px;
            }}
            QTextEdit:focus {{
                border: 1px solid {focus_color};
            }}
        """)
        
        if self.webview:
            web_bg = "#2b2b2b" if dark else "#ffffff"
            self.webview.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {web_bg};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            self.update_preview()

    def init_webview(self):
        try:
            self.webview = QTextBrowser()
            self.webview.setOpenExternalLinks(True)
            self.update_style()
            self.preview_layout.removeWidget(self.placeholder_widget)
            self.placeholder_widget.deleteLater()
            self.preview_layout.addWidget(self.webview)
            self.update_preview()
        except Exception as e:
            InfoBar.error("初始化失败", f"无法加载预览组件: {e}", parent=self)

    def update_preview(self):
        if not self.webview: return
        
        text = self.editor.toPlainText()
        extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.extra']
        
        # 如果有高亮插件，使用 codehilite 扩展
        hl_plugin = self.plugin_manager.get("highlight")
        if hl_plugin and hl_plugin.is_available:
            extensions.append('markdown.extensions.codehilite')
        
        try:
            html_content = markdown.markdown(text, extensions=extensions)
            
            # 注入 MathJax 脚本
            math_plugin = self.plugin_manager.get("mathjax")
            math_header = ""
            if math_plugin and math_plugin.is_available:
                math_header = math_plugin.get_header_code()
            
            css = self.get_css_style(force_light=False)
            
            final_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                {css}
                {math_header}
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            self.webview.setHtml(final_html)
        except Exception as e:
            print(f"Markdown Parsing Error: {e}")

    def export_pdf(self):
        if not self.webview and self.engine_combo.currentData() == "builtin":
            InfoBar.warning("未就绪", "请先点击'加载预览'以初始化组件", parent=self)
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "markdown_output.pdf", "PDF Files (*.pdf)")
        if not path:
            return
            
        engine = self.engine_combo.currentData()
        
        if engine == "pandoc":
            if not self.pandoc or not self.pandoc.is_available:
                InfoBar.error("错误", "Pandoc 插件未安装或不可用", parent=self)
                return

            # 显示进度条或 Loading 状态
            InfoBar.info("正在导出", "正在使用 Pandoc 生成 PDF，请稍候...", duration=2000, parent=self)
            self.export_btn.setEnabled(False) # 防止重复点击
            
            # 获取并规范化内容
            raw_content = self.editor.toPlainText()
            normalized_content = normalize_markdown(raw_content)

            # 定义耗时任务
            def pandoc_task(content, output_path):
                self.pandoc.convert(
                    content=content,
                    output_path=output_path,
                    extra_args=["--pdf-engine=xelatex"]
                )
                return output_path

            # 使用线程执行
            self.worker = WorkerThread(pandoc_task, normalized_content, path)
            self.worker.finished.connect(lambda p: self.on_export_finished(True, p))
            self.worker.error.connect(lambda e: self.on_export_finished(False, str(e)))
            self.worker.start()
            
        else:
            try:
                # 内置导出 (QPrinter)
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                
                force_light = self.bg_combo.currentText() == "白色背景"
                
                if force_light:
                    temp_browser = QTextBrowser()
                    css = self.get_css_style(force_light=True)
                    text = self.editor.toPlainText()
                    # 这里重复逻辑有点多，但为了隔离打印样式，暂时这样
                    extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.extra']
                    hl_plugin = self.plugin_manager.get("highlight")
                    if hl_plugin and hl_plugin.is_available:
                        extensions.append('markdown.extensions.codehilite')
                        
                    html_content = markdown.markdown(text, extensions=extensions)
                    final_html = f"<!DOCTYPE html><html><head>{css}</head><body>{html_content}</body></html>"
                    temp_browser.setHtml(final_html)
                    temp_browser.print(printer)
                    temp_browser.deleteLater()
                else:
                    self.webview.print(printer)
                    
                InfoBar.success("导出成功", f"PDF 已保存到: {path}", duration=3000, parent=self)
            
            except Exception as e:
                InfoBar.error("导出失败", f"错误详情: {e}", parent=self)

    def on_export_finished(self, success, message):
        self.export_btn.setEnabled(True)
        if success:
            InfoBar.success("导出成功", f"文件已保存: {message}", parent=self)
        else:
            InfoBar.error("导出失败", message, parent=self)
