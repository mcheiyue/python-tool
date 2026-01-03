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
from core.utils.docx_processor import DocxProcessor
from ui.threads import WorkerThread

class MarkdownInterface(QWidget):
    def __init__(self, parent=None, container=None):
        super().__init__(parent=parent)
        self.container = container
        self.setObjectName("markdown_interface")
        
        # 初始化插件管理器
        self.plugin_manager = container.plugin_manager if container else None
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(20, 20, 20, 20)
        self.vbox.setSpacing(15)

        self.title = SubtitleLabel("Markdown 工具箱", self)
        self.desc = BodyLabel("实时预览 Markdown 并导出为 PDF/DOCX", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 工具栏
        self.toolbar = QHBoxLayout()
        
        # 背景选择
        self.bg_combo = ComboBox(self)
        self.bg_combo.addItems(["跟随主题", "白色背景"])
        self.bg_combo.setFixedWidth(120)
        
        # 导出格式选择
        self.format_combo = ComboBox(self)
        self.format_combo.setFixedWidth(120)
        self.format_combo.addItem("PDF 文档", "pdf")
        self.format_combo.addItem("Word 文档", "docx")
        
        # 检查 Pandoc 插件
        self.pandoc = self.plugin_manager.get("pandoc")
        self.has_pandoc = self.pandoc and self.pandoc.is_available
        
        # 如果有 Pandoc，自动选择 DOCX 作为默认（因为它只能通过 Pandoc 导出）
        if self.has_pandoc:
            self.format_combo.setCurrentIndex(1)

        self.export_btn = PrimaryPushButton(FIF.SAVE, "导出文件", self)
        self.export_btn.clicked.connect(self.export_file)
        
        self.toolbar.addWidget(self.bg_combo)
        self.toolbar.addWidget(self.format_combo)
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

    def export_file(self):
        # 修复：QFluentWidgets ComboBox currentData() 可能返回 None，改用 currentIndex 判断
        # Index 0: PDF ("pdf")
        # Index 1: Word ("docx")
        idx = self.format_combo.currentIndex()
        fmt = "docx" if idx == 1 else "pdf" if idx == 0 else None
        
        # 1. DOCX 导出 (仅 Pandoc)
        if fmt == "docx":
            if not self.has_pandoc:
                InfoBar.error("组件缺失", "导出 DOCX 需要安装 Pandoc。\n请安装 Pandoc 并重启应用。", parent=self)
                return
                
            path, _ = QFileDialog.getSaveFileName(self, "保存 Word 文档", "markdown_output.docx", "Word Files (*.docx)")
            if not path: return

            InfoBar.info("正在导出", "正在生成 DOCX，请稍候...", duration=5000, parent=self)
            self.export_btn.setEnabled(False)
            self.export_btn.setText("正在导出...")

            raw_content = self.editor.toPlainText()
            normalized_content = normalize_markdown(raw_content)

            def docx_task(content, output_path):
                # 1. 调用 Pandoc 转换
                self.pandoc.convert_to_docx(content, output_path)
                # 2. 后处理样式 (修复首段缩进等)
                DocxProcessor.process_file(output_path, disable_first_para_indent=True)
                return output_path

            self.worker = WorkerThread(docx_task, normalized_content, path)
            self.worker.finished.connect(lambda p: self.on_export_finished(True, p))
            self.worker.error.connect(lambda e: self.on_export_finished(False, str(e)))
            self.worker.start()

        # 2. PDF 导出 (Pandoc 或 内置)
        elif fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "markdown_output.pdf", "PDF Files (*.pdf)")
            if not path: return
            
            # 如果有 Pandoc，优先用 Pandoc
            if self.has_pandoc:
                InfoBar.info("正在导出", "正在使用 Pandoc 生成 PDF...", duration=5000, parent=self)
                self.export_btn.setEnabled(False)
                self.export_btn.setText("正在导出...")
                
                raw_content = self.editor.toPlainText()
                normalized_content = normalize_markdown(raw_content)
                
                def pandoc_pdf_task(content, output_path):
                    self.pandoc.convert(
                        content=content,
                        output_path=output_path,
                        output_format="pdf"
                    )
                    return output_path
                    
                self.worker = WorkerThread(pandoc_pdf_task, normalized_content, path)
                self.worker.finished.connect(lambda p: self.on_export_finished(True, p))
                self.worker.error.connect(lambda e: self.on_export_finished(False, str(e)))
                self.worker.start()
            
            # 否则用内置转换
            else:
                if not self.webview:
                    InfoBar.warning("未就绪", "请先加载预览以使用内置 PDF 导出", parent=self)
                    return
                try:
                    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                    printer.setOutputFileName(path)
                    
                    # 临时渲染一份白色背景的 HTML 用于打印 (如果需要)
                    force_light = self.bg_combo.currentText() == "白色背景"
                    if force_light:
                        temp_browser = QTextBrowser()
                        css = self.get_css_style(force_light=True)
                        text = self.editor.toPlainText()
                        extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.extra']
                        if self.plugin_manager.get("highlight"):
                            extensions.append('markdown.extensions.codehilite')
                        html = markdown.markdown(text, extensions=extensions)
                        temp_browser.setHtml(f"<html><head>{css}</head><body>{html}</body></html>")
                        temp_browser.print(printer)
                        temp_browser.deleteLater()
                    else:
                        self.webview.print(printer)
                        
                    InfoBar.success("导出成功", f"PDF 已保存到: {path}", duration=3000, parent=self)
                except Exception as e:
                    InfoBar.error("导出失败", str(e), parent=self)

        else:
            InfoBar.error("导出失败", f"未知的导出格式: {fmt}\n请重新选择格式。", parent=self)

    def on_export_finished(self, success, message):
        self.export_btn.setEnabled(True)
        self.export_btn.setText("导出文件")
        
        if success:
            InfoBar.success("导出成功", f"文件已保存: {message}", parent=self)
        else:
            InfoBar.error("导出失败", message, parent=self)
