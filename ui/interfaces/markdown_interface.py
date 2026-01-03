import markdown
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QSplitter, QFileDialog
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, TextEdit, InfoBar, 
                            FluentIcon as FIF, isDarkTheme, qconfig, ComboBox)

class MarkdownInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdown_interface")
        
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
        # self.bg_combo.currentIndexChanged.connect(self.update_preview) # 预览不再随背景选项变化
        self.bg_combo.setFixedWidth(120)
        
        self.export_btn = PrimaryPushButton(FIF.SAVE, "导出 PDF", self)
        self.export_btn.clicked.connect(self.export_pdf)
        
        self.toolbar.addWidget(self.bg_combo)
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
        
        # 预览容器 (懒加载 WebEngine 以避免 GPU 问题)
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        # self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # 移除居中对齐，让其填满

        # 占位符
        self.placeholder_widget = QWidget()
        self.placeholder_layout = QVBoxLayout(self.placeholder_widget)
        self.placeholder_layout.addStretch(1)
        self.placeholder_label = BodyLabel("点击加载预览 (使用轻量级 QTextBrowser)", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_btn = PrimaryPushButton("加载预览 / 启用导出", self)
        self.load_btn.clicked.connect(self.init_webview)
        self.placeholder_layout.addWidget(self.placeholder_label, 0, Qt.AlignmentFlag.AlignCenter) # 确保 Label 居中
        self.placeholder_layout.addWidget(self.load_btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.placeholder_layout.addStretch(1)
        
        self.preview_layout.addWidget(self.placeholder_widget)
        
        self.webview = None
        
        # 监听主题变更
        qconfig.themeChanged.connect(self.update_style)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([450, 450])
        
        # 使用 stretch=1 让 splitter 占满剩余垂直空间
        self.vbox.addWidget(self.splitter, 1)
        
        # 初始化样式
        self.update_style()
        
        # 默认文本
        self.editor.setText("# Hello World\\n\\n欢迎使用 **Markdown 转 PDF** 工具！")

    def get_css_style(self, force_light=False):
        """根据主题返回对应的 CSS 样式"""
        is_dark = isDarkTheme() and not force_light

        if is_dark:
            # 深色模式样式
            return """
            <style>
                body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; color: #e0e0e0; background-color: #2b2b2b; }
                h1, h2, h3 { color: #9cdcfe; margin-top: 20px; border-bottom: 1px solid #444; }
                a { color: #4ec9b0; text-decoration: none; }
                code { background-color: #3c3c3c; color: #ce9178; padding: 2px 4px; border-radius: 4px; font-family: Consolas; }
                pre { background-color: #1e1e1e; padding: 10px; border: 1px solid #444; margin: 10px 0; border-radius: 6px; }
                blockquote { border-left: 4px solid #444; padding-left: 10px; color: #888; margin: 10px 0; }
                table { border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #444; }
                th, td { border: 1px solid #444; padding: 8px; }
                th { background-color: #333; font-weight: bold; color: #ddd; }
                ul, ol { padding-left: 20px; }
                img { max-width: 100%; border-radius: 4px; }
            </style>
            """
        else:
            # 浅色模式样式
            return """
            <style>
                body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; color: #333; background-color: #ffffff; }
                h1, h2, h3 { color: #2c3e50; margin-top: 20px; border-bottom: 1px solid #eee; }
                a { color: #007acc; text-decoration: none; }
                code { background-color: #f3f3f3; color: #c7254e; padding: 2px 4px; border-radius: 4px; font-family: Consolas; }
                pre { background-color: #f8f8f8; padding: 10px; border: 1px solid #e0e0e0; margin: 10px 0; border-radius: 6px; }
                blockquote { border-left: 4px solid #ddd; padding-left: 10px; color: #777; margin: 10px 0; }
                table { border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #e0e0e0; }
                th, td { border: 1px solid #e0e0e0; padding: 8px; }
                th { background-color: #f9f9f9; font-weight: bold; color: #444; }
                ul, ol { padding-left: 20px; }
                img { max-width: 100%; border-radius: 4px; }
            </style>
            """

    def update_style(self):
        """更新组件样式以适配主题"""
        dark = isDarkTheme()
        
        # 1. 设置编辑器边框样式
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
        
        # 2. 如果预览组件存在，也更新其样式
        if self.webview:
            # 设置 QTextBrowser 的容器样式 (主要是背景色和边框)
            web_bg = "#2b2b2b" if dark else "#ffffff"
            self.webview.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {web_bg};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            
            # 重新渲染内容以应用新的 CSS
            self.update_preview()

    def init_webview(self):
        try:
            self.webview = QTextBrowser()
            self.webview.setOpenExternalLinks(True)
            
            # 初始化时应用当前样式
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
        try:
            html_content = markdown.markdown(text, extensions=extensions)
            # 获取当前主题对应的 CSS (不强制浅色，始终跟随主题)
            css = self.get_css_style(force_light=False)
            final_html = f"<!DOCTYPE html><html><head>{css}</head><body>{html_content}</body></html>"
            self.webview.setHtml(final_html)
        except Exception as e:
            print(f"Markdown Parsing Error: {e}")

    def export_pdf(self):
        if not self.webview:
            InfoBar.warning("未就绪", "请先点击'加载预览'以初始化组件", parent=self)
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "markdown_output.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                
                # 判断是否需要强制白色背景
                force_light = self.bg_combo.currentText() == "白色背景"
                
                if force_light:
                    # 如果需要白色背景，创建一个临时的 QTextBrowser 进行打印
                    temp_browser = QTextBrowser()
                    # 获取强制浅色的 CSS
                    css = self.get_css_style(force_light=True)
                    
                    text = self.editor.toPlainText()
                    extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.extra']
                    html_content = markdown.markdown(text, extensions=extensions)
                    final_html = f"<!DOCTYPE html><html><head>{css}</head><body>{html_content}</body></html>"
                    
                    temp_browser.setHtml(final_html)
                    # 打印临时组件
                    temp_browser.print(printer)
                    temp_browser.deleteLater()
                else:
                    # 否则直接打印当前的预览组件
                    self.webview.print(printer)
                
                InfoBar.success("任务完成", f"PDF 已保存到: {path}", duration=3000, parent=self)
            except Exception as e:
                InfoBar.error("导出失败", f"无法生成 PDF: {e}", parent=self)
