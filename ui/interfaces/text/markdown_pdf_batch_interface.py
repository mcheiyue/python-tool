"""
Markdown 批量转 PDF 界面
使用 Pandoc 引擎，支持数学公式和代码高亮
"""
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout, QCheckBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PrimaryPushButton,
                            PushButton, TextEdit, InfoBar, InfoBarPosition,
                            LineEdit, ComboBox, IconWidget, FluentIcon as FIF)

from core.features.text.markdown_pdf_pandoc import PandocMarkdownToPdf
from app.container import AppContainer
from ui.widgets import DragDropListWidget
from ui.widgets.enhanced_progress import EnhancedProgressBar
from ui.threads import WorkerThread
from ui.design_system import Margins, Spacing


class MarkdownPdfBatchInterface(QWidget):
    """Markdown 批量转 PDF 界面"""
    # 桥接信号：WorkerThread 回调在工作线程触发，经此排队回主线程
    _log_bridged = pyqtSignal(str)
    _progress_bridged = pyqtSignal(int, int, str)
    _finished_bridged = pyqtSignal(int, int)

    def __init__(self, parent=None, container=None):
        super().__init__(parent=parent)
        self.container = container
        self.setObjectName("markdown_pdf_batch_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)

        # 标题
        self.title = SubtitleLabel("Markdown → PDF 批量转换", self)
        self.desc = BodyLabel("使用 Pandoc 引擎批量转换 Markdown 为 PDF（支持数学公式和代码高亮）", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 获取工具
        self.pandoc_tool = AppContainer().external_tool_manager.get_tool("pandoc")

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QVBoxLayout(self.settings_card)
        self.settings_layout.setContentsMargins(*Margins.CARD)

        # 状态指示行
        self.status_layout = QHBoxLayout()
        self.status_icon = IconWidget(FIF.INFO)
        self.status_icon.setFixedSize(18, 18)
        self.status_label = BodyLabel("Pandoc 状态检查中...", self)
        
        self.action_btn = PushButton(FIF.SETTING, "管理组件", self)
        self.action_btn.clicked.connect(self.open_settings)
        self.action_btn.hide()

        self.status_layout.addWidget(self.status_icon)
        self.status_layout.addSpacing(10)
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addStretch(1)
        self.status_layout.addWidget(self.action_btn)

        # PDF 引擎选择
        self.engine_layout = QHBoxLayout()
        self.engine_label = BodyLabel("PDF 引擎:", self)
        self.engine_combo = ComboBox(self)
        self.engine_combo.addItems(['xelatex (推荐 - 支持中文)', 'pdflatex', 'lualatex', 'wkhtmltopdf'])
        self._detect_and_set_default_engine()
        self.engine_layout.addWidget(self.engine_label)
        self.engine_layout.addWidget(self.engine_combo)
        self.engine_layout.addStretch(1)

        # 功能选项
        self.options_layout = QHBoxLayout()
        self.math_check = QCheckBox("启用数学公式 (MathJax)", self)
        self.math_check.setChecked(True)
        self.math_check.setToolTip("支持行内公式 $...$ 和块级公式 $$...$$")
        
        self.highlight_check = QCheckBox("启用代码高亮", self)
        self.highlight_check.setChecked(True)
        self.highlight_check.setToolTip("使用 Tango 风格语法高亮")
        
        self.options_layout.addWidget(self.math_check)
        self.options_layout.addWidget(self.highlight_check)
        self.options_layout.addStretch(1)

        self.settings_layout.addLayout(self.status_layout)
        self.settings_layout.addSpacing(15)
        self.settings_layout.addLayout(self.engine_layout)
        self.settings_layout.addSpacing(10)
        self.settings_layout.addLayout(self.options_layout)
        
        self.vbox.addWidget(self.settings_card)

        # 工具栏
        self.toolbar = QHBoxLayout()
        self.add_btn = PrimaryPushButton(FIF.ADD, "添加文件", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        self.toolbar.addWidget(self.add_btn)
        self.toolbar.addWidget(self.clear_btn)
        self.toolbar.addStretch(1)
        self.vbox.addLayout(self.toolbar)

        # 列表与日志
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 底部
        self.bottom_layout = QHBoxLayout()
        self.out_label = BodyLabel("输出目录:", self)
        self.out_edit = LineEdit(self)
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.progress = EnhancedProgressBar(self)
        self.progress.hide()
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.out_label)
        self.bottom_layout.addWidget(self.out_edit)
        self.bottom_layout.addWidget(self.browse_btn)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)

        # 初始化
        self.files = []
        self.converter = PandocMarkdownToPdf()
        self.thread = None
        self._status_worker = None
        self._has_pdf_engine = False  # 标记是否存在可用的 PDF 引擎
        
        self._log_bridged.connect(self.append_log)
        self._progress_bridged.connect(self.update_progress)
        self._finished_bridged.connect(self.on_finished)
        
        # 初始检查
        self.check_pandoc_status()

    def check_pandoc_status(self):
        """检查 Pandoc 状态和 PDF 引擎状态并更新 UI

        PDF 引擎是 PATH 探测（快），同步完成；Pandoc 可能触发上游包下载解压
        （秒级至数十秒），必须走异步，否则切换页面即冻结。
        """
        # 1. 检查 PDF 引擎
        self._detect_and_set_default_engine()

        if not self._has_pdf_engine:
            self._set_status_error("缺少 PDF 引擎 (xelatex/pdflatex/lualatex/wkhtmltopdf)", show_btn=False)
            self.check_state()
            return

        # 2. 检查 Pandoc（异步）
        if not self.pandoc_tool:
            self._set_status_error("内部错误: 未找到组件管理器")
            return

        self._set_status_busy("正在准备 Pandoc…")

        def _apply(status):
            if not status or status.get("disabled"):
                self._set_status_error("Pandoc 组件已禁用 (点击管理启用)", show_btn=True)
            elif status.get("installed"):
                source = "便携版" if status.get("source") == "portable" else "系统版"
                self._set_status_ready(f"Pandoc 已就绪 ({source})")
            else:
                self._set_status_error("缺少 Pandoc 组件 (点击管理安装)", show_btn=True)
            self.check_state()

        self._status_worker = self.pandoc_tool.refresh_status_async(_apply)

    def _set_status_busy(self, text):
        """准备中：既不是就绪也不是错误，避免把耗时解压误报成不可用"""
        self.status_icon.setIcon(FIF.SYNC)
        self.status_icon.setStyleSheet("IconWidget { color: #605E5C; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#605E5C", "#8A8886")
        self.action_btn.hide()

    def _set_status_ready(self, text):
        self.status_icon.setIcon(FIF.ACCEPT)
        self.status_icon.setStyleSheet("IconWidget { color: #107C10; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#107C10", "#107C10")
        self.action_btn.hide()

    def _set_status_error(self, text, show_btn=False):
        self.status_icon.setIcon(FIF.CANCEL)
        self.status_icon.setStyleSheet("IconWidget { color: #C42B1C; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#C42B1C", "#FF99A4")
        if show_btn:
            self.action_btn.show()
        else:
            self.action_btn.hide()

    def open_settings(self):
        """跳转到设置页面"""
        window = self.window()
        if hasattr(window, 'switch_to_settings'):
            window.switch_to_settings()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 Markdown 文件", "", "Markdown (*.md *.markdown)")
        if paths:
            self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        count = 0
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext in ['.md', '.markdown']:
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
                    count += 1
        
        # 自动设置输出目录
        if self.files and not self.out_edit.text():
            self.out_edit.setText(os.path.dirname(self.files[0]))
        self.check_state()

    def browse_output(self):
        """浏览输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.out_edit.setText(path)
            self.check_state()

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.check_state()

    def check_state(self):
        has_files = len(self.files) > 0
        has_pandoc = self.pandoc_tool and self.pandoc_tool.is_available()
        has_output = bool(self.out_edit.text())
        # 必须同时满足: 有文件 + Pandoc可用 + 输出路径 + 有PDF引擎
        self.start_btn.setEnabled(has_files and has_pandoc and has_output and self._has_pdf_engine)

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_progress(self, curr, total, msg):
        self.progress.update_progress(curr, total, msg)
        self.start_btn.setText(f"转换中... ({curr}/{total})")

    def start_conversion(self):
        out_dir = self.out_edit.text()
        if not self.files or not out_dir:
            return

        # UI 状态先在主线程读齐，避免异步回调时控件已被改
        engine_text = self.engine_combo.currentText()
        pdf_engine = engine_text.split(' ')[0]  # 提取引擎名
        enable_math = self.math_check.isChecked()
        enable_highlight = self.highlight_check.isChecked()

        self.start_btn.setEnabled(False)
        self._set_status_busy("正在准备 Pandoc…")

        def _ready(status):
            pandoc_path = (status or {}).get("path")
            if not pandoc_path or not os.path.exists(pandoc_path):
                InfoBar.error("错误", "无法找到 Pandoc 可执行文件", parent=self)
                self.start_btn.setEnabled(True)
                self.check_pandoc_status()
                return

            self.log_text.clear()

            # 创建并启动线程
            self.thread = WorkerThread(
                self.converter.convert_batch,
                files=self.files,
                output_dir=out_dir,
                enable_math=enable_math,
                enable_highlight=enable_highlight,
                pdf_engine=pdf_engine,
                on_log=self._log_bridged.emit,
                on_progress=self._progress_bridged.emit,
                on_finished=self._finished_bridged.emit,
            )
            self.thread.error.connect(lambda msg: self.on_finished(0, 1))
            self.thread.start()

        self._status_worker = self.pandoc_tool.refresh_status_async(_ready)
        
    def showEvent(self, event):
        """界面显示时刷新状态"""
        self.check_pandoc_status()
        super().showEvent(event)

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始转换")
        self.progress.stop()
        self.progress.hide()
        if fail > 0: InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
        else: InfoBar.success("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)

    def _detect_and_set_default_engine(self):
        """检测可用的 PDF 引擎并设置默认值"""
        import shutil
        
        engines = [
            ('xelatex', 0),
            ('pdflatex', 1),
            ('lualatex', 2),
            ('wkhtmltopdf', 3)
        ]
        
        # 查找第一个可用的引擎
        for engine, index in engines:
            if shutil.which(engine):
                self.engine_combo.setCurrentIndex(index)
                self._has_pdf_engine = True
                return
        
        # 未找到任何引擎
        self._has_pdf_engine = False