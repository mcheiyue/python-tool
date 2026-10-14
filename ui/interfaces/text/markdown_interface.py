import markdown
import os
import subprocess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QSplitter, QFileDialog, QMenu, QLabel
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QFont, QAction, QKeySequence, QDesktopServices
# 确保 QPageSize 独立导入，避免因其他导入错误被忽略
try:
    from PyQt6.QtGui import QPageSize
except ImportError:
    QPageSize = None

from PyQt6.QtCore import Qt, QUrl, QTimer
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, TextEdit, InfoBar,
                            FluentIcon as FIF, isDarkTheme, qconfig, ComboBox, ToolButton, PushButton,
                            CaptionLabel, InfoBarPosition)

from core.plugins import PluginManager
from core.utils.md_normalizer import normalize_markdown
from core.utils.docx_processor import DocxProcessor
from ui.threads import WorkerThread
from core.external_tools.manager import ExternalToolManager

class MarkdownInterface(QWidget):
    def __init__(self, parent=None, container=None):
        super().__init__(parent=parent)
        self.container = container
        self.setObjectName("markdown_interface")
        
        # 初始化插件管理器
        self.plugin_manager = container.plugin_manager if container else None
        self.config = container.config if container else None
        
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
        self.format_combo.setToolTip("选择导出的文件格式")
        
        # 引擎状态提示
        self.engine_status_label = CaptionLabel("", self)
        self.engine_status_label.setTextColor("#808080", "#a0a0a0")
        
        # 检查能力插件 (使用新的能力注册机制)
        self.docx_converter = None
        self.pdf_converter = None
        self.refresh_capabilities()
        
        self.export_btn = PrimaryPushButton(FIF.SAVE, "导出文件", self)
        self.export_btn.setToolTip("导出为选中格式 (Ctrl+S)")
        self.export_btn.clicked.connect(self.export_file)
        
        self.toolbar.addWidget(self.bg_combo)
        self.toolbar.addWidget(self.format_combo)
        self.toolbar.addWidget(self.export_btn)
        self.toolbar.addWidget(self.engine_status_label) # 添加状态标签
        self.toolbar.addStretch(1)
        
        # 监听工具状态变更 (优先从容器获取管理器以保持单例一致性)
        if hasattr(self.container, 'external_tool_manager') and self.container.external_tool_manager:
            self.tool_manager = self.container.external_tool_manager
        else:
            self.tool_manager = ExternalToolManager()
            
        self.tool_manager.signals.tool_status_changed.connect(self.on_tool_status_changed)
        
        # 快捷键
        self.save_action = QAction(self)
        self.save_action.setShortcut(QKeySequence("Ctrl+S"))
        self.save_action.triggered.connect(self.export_file)
        self.addAction(self.save_action)
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
        self.load_btn.setToolTip("初始化预览引擎 (Ctrl+R)")
        self.load_btn.clicked.connect(self.init_webview)
        self.placeholder_layout.addWidget(self.placeholder_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.placeholder_layout.addWidget(self.load_btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.placeholder_layout.addStretch(1)
        
        # 刷新/加载快捷键
        self.refresh_action = QAction(self)
        self.refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        self.refresh_action.triggered.connect(self.init_webview)
        self.addAction(self.refresh_action)
        
        self.preview_layout.addWidget(self.placeholder_widget)
        
        self.webview = None
        
        # 监听主题变更
        qconfig.themeChanged.connect(self.update_style)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([450, 450])
        
        self.vbox.addWidget(self.splitter, 1)
        
        # 如果有 DOCX 转换器，自动选择 DOCX 作为默认（因为它通常依赖外部工具，优先级较高）
        # 注意：这会触发 currentIndexChanged，所以必须在连接信号之前设置，或者确保 update_ui_state 能处理未初始化的组件
        if self.docx_converter:
            self.format_combo.setCurrentIndex(1)
            
        # 初始化样式
        self.update_style()
        
        # 延迟连接信号，防止初始化时组件未就绪导致崩溃
        self.format_combo.currentIndexChanged.connect(self.update_ui_state)
        self.update_ui_state() # 初始化 UI 状态
        
        # 默认文本
        default_text = "# Hello World\n\n欢迎使用 **Markdown 转 PDF** 工具！\n\n"
        
        # 如果有数学公式插件，显示示例
        math_plugin = self.plugin_manager.get_preferred_plugin("math_render", self.config)
        if math_plugin:
             default_text += "### 数学公式示例\n\nEinstein's $E=mc^2$\n\n$$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$\n\n"
             
        default_text += "### 代码示例\n\n```python\ndef hello():\n    print('Hello')\n```"
        self.editor.setText(default_text)

    def get_css_style(self, force_light=False):
        """根据主题返回对应的 CSS 样式"""
        is_dark = isDarkTheme() and not force_light
        
        # 获取高亮插件 CSS (通过能力获取)
        highlight_css = ""
        hl_plugin = self.plugin_manager.get_preferred_plugin("syntax_highlight", self.config)
        if hl_plugin:
            # 深色模式使用 monokai，浅色模式使用 default
            style_name = "monokai" if is_dark else "default"
            highlight_css = hl_plugin.get_css(style_name)

        base_css = """
            body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; line-height: 1.6; }
            h1, h2, h3 { margin-top: 20px; border-bottom: 1px solid #eee; }
            a { text-decoration: none; }
            code { padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; font-size: 0.9em; }
            pre {
                padding: 10px;
                border: 1px solid #e0e0e0;
                margin: 10px 0;
                border-radius: 6px;
                white-space: pre-wrap;       /* CSS3 */
                white-space: -moz-pre-wrap;  /* Mozilla */
                white-space: -pre-wrap;      /* Opera 4-6 */
                white-space: -o-pre-wrap;    /* Opera 7 */
                word-wrap: break-word;       /* Internet Explorer 5.5+ */
            }
            blockquote { border-left: 4px solid #ddd; padding-left: 10px; margin: 10px 0; color: #777; }
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
        
        # 获取高亮插件 (通过能力获取)
        hl_plugin = self.plugin_manager.get_preferred_plugin("syntax_highlight", self.config)
        if hl_plugin:
            extensions.append('markdown.extensions.codehilite')
        
        try:
            html_content = markdown.markdown(text, extensions=extensions)
            
            # 注入数学公式脚本 (通过能力获取)
            math_plugin = self.plugin_manager.get_preferred_plugin("math_render", self.config)
            math_header = ""
            if math_plugin:
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
        
        # 1. DOCX 导出
        if fmt == "docx":
            if not self.docx_converter:
                InfoBar.error("组件缺失", "没有可用的 DOCX 转换插件。\n请安装 Pandoc 或其他受支持的转换工具。", parent=self)
                return
                
            path, _ = QFileDialog.getSaveFileName(self, "保存 Word 文档", "markdown_output.docx", "Word Files (*.docx)")
            if not path: return

            plugin_name = self.docx_converter.display_name
            InfoBar.info("正在导出", f"正在使用 {plugin_name} 生成 DOCX...", duration=5000, parent=self)
            self.export_btn.setEnabled(False)
            self.export_btn.setText("正在导出...")

            raw_content = self.editor.toPlainText()
            normalized_content = normalize_markdown(raw_content)

            def docx_task(content, output_path):
                # 统一调用接口
                # 优化：优先使用内存流处理，避免多次文件读写导致的文件损坏或占用问题
                
                # 1. 如果插件支持直接输出字节流，则优先使用
                if hasattr(self.docx_converter, 'convert_to_docx_bytes'):
                    docx_bytes = self.docx_converter.convert_to_docx_bytes(content)
                    
                    # 2. 在内存中进行后处理 (修复首段缩进等)
                    processed_bytes = DocxProcessor.apply_custom_processing(
                        docx_bytes,
                        disable_first_para_indent=True
                    )
                    
                    # 3. 统一进行一次性写入 (原子操作)
                    with open(output_path, 'wb') as f:
                        f.write(processed_bytes)
                        
                else:
                    # 降级方案：旧的文件处理方式 (兼容未实现 bytes 接口的插件)
                    if hasattr(self.docx_converter, 'convert_to_docx'):
                         self.docx_converter.convert_to_docx(content, output_path)
                    else:
                         self.docx_converter.convert(content, output_format="docx", output_path=output_path)
                    
                    # 后处理样式 (修复首段缩进等)
                    DocxProcessor.process_file(output_path, disable_first_para_indent=True)
                    
                return output_path

            self.worker = WorkerThread(docx_task, normalized_content, path)
            self.worker.finished.connect(lambda p: self.on_export_finished(True, p))
            self.worker.error.connect(lambda e: self.on_export_finished(False, str(e)))
            self.worker.start()

        # 2. PDF 导出
        elif fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "markdown_output.pdf", "PDF Files (*.pdf)")
            if not path: return
            
            # 优先使用插件 (Pandoc)，但必须检查是否有 PDF 引擎
            use_plugin = False
            if self.pdf_converter:
                # 检查 has_pdf_engine 属性 (如果插件支持)
                if hasattr(self.pdf_converter, 'has_pdf_engine'):
                    if self.pdf_converter.has_pdf_engine:
                        use_plugin = True
                else:
                    # 旧版本插件，假设可用
                    use_plugin = True

            if use_plugin:
                plugin_name = self.pdf_converter.display_name
                InfoBar.info("正在导出", f"正在使用 {plugin_name} 生成 PDF...", duration=5000, parent=self)
                self.export_btn.setEnabled(False)
                self.export_btn.setText("正在导出...")
                
                raw_content = self.editor.toPlainText()
                normalized_content = normalize_markdown(raw_content)
                
                def pdf_task(content, output_path):
                    # 尝试传递额外的参数以优化 PDF 输出 (如果支持)
                    # 例如: --pdf-engine=xelatex 以支持 UTF-8 (取决于系统环境，这里主要依赖插件默认配置)
                    self.pdf_converter.convert(
                        content=content,
                        output_path=output_path,
                        output_format="pdf"
                    )
                    return output_path
                    
                self.worker = WorkerThread(pdf_task, normalized_content, path)
                self.worker.finished.connect(lambda p: self.on_export_finished(True, p))
                self.worker.error.connect(lambda e: self.on_export_finished(False, str(e)))
                self.worker.start()
            
            # 降级到内置转换 (QPrinter)
            else:
                if self.pdf_converter and hasattr(self.pdf_converter, 'has_pdf_engine') and not self.pdf_converter.has_pdf_engine:
                     InfoBar.warning("PDF 引擎缺失", "Pandoc 已安装但未检测到 PDF 引擎 (如 XeLaTeX)。\n已自动降级使用内置渲染引擎。", duration=5000, parent=self)
                else:
                     InfoBar.info("使用内置引擎", "正在使用内置渲染引擎导出 PDF...", duration=3000, parent=self)
                
                if not self.webview:
                    InfoBar.warning("未就绪", "请先加载预览以使用内置 PDF 导出", parent=self)
                    return
                try:
                    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                    # 显式设置分辨率，防止模糊 (默认 HighResolution 有时在不同 DPI 下表现不一致)
                    printer.setResolution(300)
                    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                    printer.setOutputFileName(path)
                    
                    # 设置页面大小为 A4 (带异常保护，防止旧环境未重启导致的 NameError)
                    try:
                        if 'QPageSize' in globals() and QPageSize:
                            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                    except (NameError, TypeError, AttributeError):
                        print("Warning: QPageSize not available, skipping page size setting. Please restart app.")
                    
                    # 临时渲染一份白色背景的 HTML 用于打印 (如果需要)
                    force_light = self.bg_combo.currentText() == "白色背景"
                    if force_light:
                        temp_browser = QTextBrowser()
                        css = self.get_css_style(force_light=True)
                        text = self.editor.toPlainText()
                        extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.extra']
                        
                        # 获取高亮插件
                        hl_plugin = self.plugin_manager.get_preferred_plugin("syntax_highlight", self.config)
                        if hl_plugin:
                            extensions.append('markdown.extensions.codehilite')
                            
                        html = markdown.markdown(text, extensions=extensions)
                        temp_browser.setHtml(f"<html><head>{css}</head><body>{html}</body></html>")
                        temp_browser.print(printer)
                        temp_browser.deleteLater()
                    else:
                        self.webview.print(printer)
                        
                    self.on_export_finished(True, path)
                except Exception as e:
                    InfoBar.error("导出失败", str(e), parent=self)

        else:
            InfoBar.error("导出失败", f"未知的导出格式: {fmt}\n请重新选择格式。", parent=self)

    def on_export_finished(self, success, message):
        self.export_btn.setEnabled(True)
        self.export_btn.setText("导出文件")
        
        if success:
            path = message
            
            # 修正：InfoBar 添加 Widget 后布局可能需要调整，改用自定义方式或确保正确显示
            # 使用更稳健的方式：直接显示成功信息，按钮稍微精简或使用 addWidget
            # 注意：message 是路径
            
            bar = InfoBar.success(
                title="导出成功",
                content=f"文件已保存到: {os.path.basename(path)}",
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT, # 明确位置
                parent=self
            )
            
            if path and os.path.exists(path):
                # 强制转换为绝对路径，确保系统能正确打开文件
                abs_path = os.path.abspath(path)
                
                def open_file(file_path):
                    """使用最可靠的方式打开文件（避免环境变量继承问题）"""
                    def do_open():
                        try:
                            # 确保文件存在且可读
                            if not os.path.exists(file_path):
                                InfoBar.error("文件不存在", "导出的文件似乎已被删除或移动", parent=self)
                                return
                                
                            if os.name == 'nt':
                                # 使用 explorer.exe 打开文件，避免 Qt 环境变量被子进程继承
                                # explorer.exe 是系统进程，不会继承当前进程的环境变量
                                subprocess.Popen(['explorer', file_path], shell=False)
                            else:
                                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                        except Exception as e:
                            InfoBar.error("打开失败", str(e), parent=self)
                    
                    # 使用 QTimer 延迟执行，确保文件完全写入
                    QTimer.singleShot(300, do_open)

                def open_folder(folder_path):
                    """打开所在目录"""
                    try:
                        if os.name == 'nt':
                            # 使用 explorer.exe 打开目录
                            subprocess.Popen(['explorer', folder_path], shell=False)
                        else:
                            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
                    except Exception as e:
                         InfoBar.error("打开目录失败", str(e), parent=self)

                # 增加样式以确保按钮紧凑
                open_btn = PushButton("打开")
                open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                open_btn.clicked.connect(lambda: open_file(abs_path))
                
                folder_btn = PushButton("目录")
                folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                folder_btn.clicked.connect(lambda: open_folder(os.path.dirname(abs_path)))
                
                bar.addWidget(open_btn)
                bar.addWidget(folder_btn)
            
            bar.show()
        else:
            InfoBar.error("导出失败", message, parent=self)

    def refresh_capabilities(self):
        """重新获取首选插件（单一赋值源）"""
        self.docx_converter = self.plugin_manager.get_preferred_plugin("markdown_to_docx", self.config)
        self.pdf_converter = self.plugin_manager.get_preferred_plugin("markdown_to_pdf", self.config)

    def on_tool_status_changed(self, name):
        """工具/插件状态变更时刷新能力"""
        self.refresh_capabilities()
        
        # 刷新 UI 状态提示
        self.update_ui_state()

    def update_ui_state(self):
        """更新 UI 状态提示"""
        idx = self.format_combo.currentIndex()
        fmt = "docx" if idx == 1 else "pdf" if idx == 0 else None
        
        if fmt == "docx":
            if self.docx_converter:
                plugin_name = self.docx_converter.display_name
                self.engine_status_label.setText(f"引擎: {plugin_name} (增强)")
                self.export_btn.setEnabled(True)
                self.export_btn.setToolTip(f"使用 {plugin_name} 导出 Word 文档")
            else:
                self.engine_status_label.setText("引擎: 不可用 (缺失插件)")
                self.export_btn.setEnabled(False) # 禁用导出按钮
                self.export_btn.setToolTip("需要安装 Pandoc 插件才能导出 Word 文档")
                
        elif fmt == "pdf":
            # 检查插件及其 PDF 引擎状态
            has_engine = False
            if self.pdf_converter:
                if hasattr(self.pdf_converter, 'has_pdf_engine'):
                    has_engine = self.pdf_converter.has_pdf_engine
                else:
                    has_engine = True

            if has_engine:
                plugin_name = self.pdf_converter.display_name
                self.engine_status_label.setText(f"引擎: {plugin_name} (增强)")
                self.export_btn.setEnabled(True)
                self.export_btn.setToolTip(f"使用 {plugin_name} 导出 PDF (支持复杂排版)")
            else:
                reason = "(缺少 PDF 引擎)" if self.pdf_converter else "(内置)"
                self.engine_status_label.setText(f"引擎: 内置组件 {reason}")
                self.export_btn.setEnabled(True)
                self.export_btn.setToolTip("使用内置浏览器引擎导出 PDF (不支持复杂排版)")
