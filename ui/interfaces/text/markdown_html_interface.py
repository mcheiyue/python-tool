import os
from functools import partial
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (CardWidget, PushButton, PrimaryPushButton, 
                          SubtitleLabel, CaptionLabel, ComboBox, LineEdit)

from core.features.text.markdown_converter import MarkdownConverter
from ui.widgets.drag_drop_list import DragDropListWidget
from core.external_tools.manager import ExternalToolManager
from ui.threads import WorkerThread

class MarkdownHtmlInterface(QWidget):
    """Markdown ↔ HTML 转换界面"""

    _progress_bridged = pyqtSignal(int, int, str)
    _finished_bridged = pyqtSignal(int, int)
    _log_bridged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.converter = MarkdownConverter()
        self.init_ui()
        self.connect_signals()
        
        # 监听工具状态变化
        ExternalToolManager().signals.tool_status_changed.connect(self.on_tool_status_changed)
        
    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 1. 标题和描述
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        self.title_label = SubtitleLabel("Markdown ↔ HTML 互转", self)
        self.desc_label = CaptionLabel("支持普通模式和高级模式(Pandoc)，可双向转换", self)
        self.desc_label.setTextColor("#606060", "#d0d0d0")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.desc_label)
        main_layout.addLayout(title_layout)
        
        # 2. 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("转换模式:"))
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["Markdown 转 HTML", "HTML 转 Markdown"])
        self.mode_combo.setFixedWidth(200)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)
        
        # 3. 文件列表区域
        list_card = CardWidget(self)
        list_layout = QVBoxLayout(list_card)
        
        # 顶部工具栏
        tool_bar = QHBoxLayout()
        self.add_btn = PushButton("添加文件", self)
        self.clear_btn = PushButton("清空列表", self)
        
        tool_bar.addWidget(self.add_btn)
        tool_bar.addWidget(self.clear_btn)
        tool_bar.addStretch()
        
        list_layout.addLayout(tool_bar)
        
        # 文件列表
        self.file_list = DragDropListWidget(self)
        self.file_list.setPlaceholderText("拖拽 Markdown/HTML 文件到此处")
        list_layout.addWidget(self.file_list)
        
        main_layout.addWidget(list_card)
        
        # 4. 选项区域
        options_card = CardWidget(self)
        options_layout = QVBoxLayout(options_card)
        options_layout.addWidget(SubtitleLabel("转换选项", self))
        
        # Pandoc 选项
        self.use_pandoc_check = QCheckBox("使用 Pandoc 引擎 (支持高级排版，需安装 Pandoc)", self)
        self.update_pandoc_ui() # 初始化状态
        options_layout.addWidget(self.use_pandoc_check)
        
        # MD->HTML 样式选项
        self.include_css_check = QCheckBox("内置 CSS 样式 (仅 MD 转 HTML 有效)", self)
        self.include_css_check.setChecked(True)
        options_layout.addWidget(self.include_css_check)
        
        main_layout.addWidget(options_card)
        
        # 5. 底部操作栏
        bottom_layout = QHBoxLayout()
        self.status_label = CaptionLabel("", self)
        self.convert_btn = PrimaryPushButton("开始转换", self)
        self.convert_btn.setFixedWidth(150)
        
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.convert_btn)
        
        main_layout.addLayout(bottom_layout)
        
    def connect_signals(self):
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn.clicked.connect(self.file_list.clear)
        self.convert_btn.clicked.connect(self.start_convert)
        
        self._progress_bridged.connect(self.on_progress)
        self._finished_bridged.connect(self.on_finished)
        self._log_bridged.connect(self.on_log)
        
        # 拖拽文件支持
        self.file_list.files_dropped.connect(self.add_dropped_files)
        
        # 模式切换时更新过滤器
        self.mode_combo.currentIndexChanged.connect(self.update_file_filter)
        
    def update_file_filter(self):
        """根据模式更新文件选择过滤器，并清理不匹配文件"""
        is_md_to_html = self.mode_combo.currentIndex() == 0
        
        if is_md_to_html:
            self.file_list.setPlaceholderText("拖拽 Markdown (.md) 文件到此处")
            valid_exts = ('.md', '.markdown')
        else:
            self.file_list.setPlaceholderText("拖拽 HTML (.html) 文件到此处")
            valid_exts = ('.html', '.htm')
            
        # 检查并移除不符合当前模式的文件
        current_files = self.file_list.get_files()
        invalid_files = [f for f in current_files if not f.lower().endswith(valid_exts)]
        
        if invalid_files:
            # 清空并只重新添加有效文件
            self.file_list.clear()
            valid_files = [f for f in current_files if f.lower().endswith(valid_exts)]
            if valid_files:
                self.file_list.add_files(valid_files)
            
    def add_dropped_files(self, files: list):
        """处理拖拽添加的文件"""
        is_md_to_html = self.mode_combo.currentIndex() == 0
        valid_files = []
        
        for f in files:
            if is_md_to_html:
                if f.lower().endswith(('.md', '.markdown')):
                    valid_files.append(f)
            else:
                if f.lower().endswith(('.html', '.htm')):
                    valid_files.append(f)
                    
        if valid_files:
            self.file_list.add_files(valid_files)
            
    def add_files(self):
        is_md_to_html = self.mode_combo.currentIndex() == 0
        if is_md_to_html:
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择 Markdown 文件", "", "Markdown Files (*.md *.markdown);;All Files (*)"
            )
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择 HTML 文件", "", "HTML Files (*.html *.htm);;All Files (*)"
            )
            
        if files:
            self.file_list.add_files(files)
            
    def start_convert(self):
        files = self.file_list.get_files()
        if not files:
            self.status_label.setText("请先添加文件")
            return
            
        self.convert_btn.setEnabled(False)
        self.status_label.setText("正在转换...")
        
        use_pandoc = self.use_pandoc_check.isChecked()
        include_css = self.include_css_check.isChecked()
        
        # 获取输出目录 (默认与原文件同目录，这里选择第一个文件的目录作为基准)
        output_dir = os.path.dirname(files[0])
        
        is_md_to_html = self.mode_combo.currentIndex() == 0

        if is_md_to_html:
            convert = partial(
                self.converter.convert_markdown_to_html,
                files, output_dir=output_dir, use_pandoc=use_pandoc, include_css=include_css
            )
        else:
            convert = partial(
                self.converter.convert_html_to_markdown,
                files, output_dir=output_dir, use_pandoc=use_pandoc
            )

        self.worker = WorkerThread(
            convert,
            on_progress=self._progress_bridged.emit,
            on_finished=self._finished_bridged.emit,
            on_log=self._log_bridged.emit,
        )
        self.worker.start()
            
    def on_progress(self, current, total, msg):
        self.status_label.setText(f"[{current}/{total}] {msg}")
        
    def on_finished(self, success, fail):
        self.convert_btn.setEnabled(True)
        self.status_label.setText(f"任务完成: 成功 {success}, 失败 {fail}")
        
    def on_log(self, msg):
        print(f"[MarkdownHtml] {msg}")

    def on_tool_status_changed(self, name):
        """工具状态变更"""
        if name == "pandoc":
            self.update_pandoc_ui()
            
    def update_pandoc_ui(self):
        """更新 Pandoc UI 状态"""
        # 注意: 这里需要确保 converter.is_pandoc_available() 已经是实时检查了
        is_available = self.converter.is_pandoc_available()
        self.use_pandoc_check.setEnabled(is_available)
        if not is_available:
            self.use_pandoc_check.setChecked(False)
            self.use_pandoc_check.setText("使用 Pandoc 引擎 (未启用或未安装)")
        else:
            self.use_pandoc_check.setText("使用 Pandoc 引擎 (支持高级排版，需安装 Pandoc)")
