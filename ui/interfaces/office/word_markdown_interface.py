import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (CardWidget, PushButton, PrimaryPushButton, 
                          SubtitleLabel, CaptionLabel, ComboBox, LineEdit)

from core.features.office.word_converter import WordConverter
from ui.widgets.drag_drop_list import DragDropListWidget
from core.external_tools.manager import ExternalToolManager
from ui.threads import WorkerThread

class WordMarkdownInterface(QWidget):
    """Word ↔ Markdown 转换界面"""

    # 桥接信号：转换回调在工作线程触发，经此排队回主线程
    _log_bridged = pyqtSignal(str)
    _progress_bridged = pyqtSignal(int, int, str)
    _finished_bridged = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.converter = WordConverter()
        self.init_ui()
        self.connect_signals()
        
        # 监听工具状态变化
        ExternalToolManager().signals.tool_status_changed.connect(self.on_tool_status_changed)
        
    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 1. 标题
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        self.title_label = SubtitleLabel("Word ↔ Markdown 互转", self)
        self.desc_label = CaptionLabel("基于 Pandoc 实现的高质量文档转换", self)
        self.desc_label.setTextColor("#606060", "#d0d0d0")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.desc_label)
        main_layout.addLayout(title_layout)
        
        # 警告：检查 Pandoc
        self.error_label = QLabel("⚠️ 警告：未检测到或未启用 Pandoc，此功能不可用。请在设置中安装或启用。", self)
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.hide() # 默认隐藏，由 update_ui 控制
        main_layout.addWidget(self.error_label)
        
        # 2. 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("转换模式:"))
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["Word (docx) 转 Markdown", "Markdown 转 Word (docx)"])
        self.mode_combo.setFixedWidth(250)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)
        
        # 3. 文件列表
        list_card = CardWidget(self)
        list_layout = QVBoxLayout(list_card)
        
        tool_bar = QHBoxLayout()
        self.add_btn = PushButton("添加文件", self)
        self.clear_btn = PushButton("清空列表", self)
        
        tool_bar.addWidget(self.add_btn)
        tool_bar.addWidget(self.clear_btn)
        tool_bar.addStretch()
        list_layout.addLayout(tool_bar)
        
        self.file_list = DragDropListWidget(self)
        self.file_list.setPlaceholderText("拖拽 Word (.docx) 文件到此处")
        list_layout.addWidget(self.file_list)
        
        main_layout.addWidget(list_card)
        
        # 4. 参考文档选项 (仅 MD->Docx 有效)
        self.ref_card = CardWidget(self)
        self.ref_card.hide() # 默认隐藏
        ref_layout = QVBoxLayout(self.ref_card)
        
        ref_header = QHBoxLayout()
        ref_header.addWidget(QLabel("样式参考文档 (可选):"))
        self.ref_path_edit = LineEdit()
        self.ref_path_edit.setPlaceholderText("选择一个 .docx 文件作为样式模板...")
        self.ref_browse_btn = PushButton("浏览", self)
        
        ref_header.addWidget(self.ref_path_edit)
        ref_header.addWidget(self.ref_browse_btn)
        ref_layout.addLayout(ref_header)
        ref_layout.addWidget(CaptionLabel("生成的 Word 文档将采用此文件的样式（字体、页边距等）", self))
        
        main_layout.addWidget(self.ref_card)
        
        # 5. 底部操作栏
        bottom_layout = QHBoxLayout()
        self.status_label = CaptionLabel("", self)
        self.convert_btn = PrimaryPushButton("开始转换", self)
        self.convert_btn.setFixedWidth(150)
        
        # 初始化状态
        self.update_pandoc_status()
        
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.convert_btn)
        
        main_layout.addLayout(bottom_layout)
        
    def connect_signals(self):
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn.clicked.connect(self.file_list.clear)
        self.convert_btn.clicked.connect(self.start_convert)
        self.ref_browse_btn.clicked.connect(self.browse_ref_doc)
        
        self._progress_bridged.connect(self.on_progress)
        self._finished_bridged.connect(self.on_finished)
        self._log_bridged.connect(self.on_log)
        
        # 拖拽文件支持
        self.file_list.files_dropped.connect(self.add_dropped_files)
        
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_mode_changed(self, index):
        is_docx_to_md = (index == 0)
        valid_exts = ('.docx',) if is_docx_to_md else ('.md', '.markdown')
        
        if is_docx_to_md:
            self.file_list.setPlaceholderText("拖拽 Word (.docx) 文件到此处")
            self.ref_card.hide()
        else:
            self.file_list.setPlaceholderText("拖拽 Markdown (.md) 文件到此处")
            self.ref_card.show()
            
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
        is_docx_to_md = (self.mode_combo.currentIndex() == 0)
        valid_files = []
        
        for f in files:
            if is_docx_to_md:
                if f.lower().endswith('.docx'):
                    valid_files.append(f)
            else:
                if f.lower().endswith(('.md', '.markdown')):
                    valid_files.append(f)
                    
        if valid_files:
            self.file_list.add_files(valid_files)
            
    def browse_ref_doc(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择样式参考文档", "", "Word Files (*.docx)"
        )
        if file_path:
            self.ref_path_edit.setText(file_path)
            
    def add_files(self):
        is_docx_to_md = self.mode_combo.currentIndex() == 0
        if is_docx_to_md:
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择 Word 文件", "", "Word Files (*.docx);;All Files (*)"
            )
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择 Markdown 文件", "", "Markdown Files (*.md *.markdown);;All Files (*)"
            )
            
        if files:
            self.file_list.add_files(files)
            
    def start_convert(self):
        files = self.file_list.get_files()
        if not files:
            self.status_label.setText("请先添加文件")
            return
            
        if not self.converter.is_pandoc_available():
            self.status_label.setText("Pandoc 未安装，无法转换")
            return
            
        self.convert_btn.setEnabled(False)
        self.status_label.setText("正在转换...")
        
        is_docx_to_md = self.mode_combo.currentIndex() == 0
        output_dir = os.path.dirname(files[0])
        
        if is_docx_to_md:
            self.thread = WorkerThread(
                self.converter.convert_docx_to_markdown, files, output_dir=output_dir,
                on_log=self._log_bridged.emit,
                on_progress=self._progress_bridged.emit,
                on_finished=self._finished_bridged.emit,
            )
        else:
            ref_doc = self.ref_path_edit.text()
            self.thread = WorkerThread(
                self.converter.convert_markdown_to_docx, files,
                output_dir=output_dir, reference_doc=ref_doc,
                on_log=self._log_bridged.emit,
                on_progress=self._progress_bridged.emit,
                on_finished=self._finished_bridged.emit,
            )
        self.thread.error.connect(lambda msg: self.on_finished(0, 1))
        self.thread.start()
            
    def on_progress(self, current, total, msg):
        self.status_label.setText(f"[{current}/{total}] {msg}")
        
    def on_finished(self, success, fail):
        self.convert_btn.setEnabled(True)
        self.status_label.setText(f"任务完成: 成功 {success}, 失败 {fail}")
        
    def on_log(self, msg):
        print(f"[WordMarkdown] {msg}")
        
    def on_tool_status_changed(self, name):
        if name == "pandoc":
            self.update_pandoc_status()
            
    def update_pandoc_status(self):
        """更新 Pandoc 状态"""
        is_available = self.converter.is_pandoc_available()
        self.convert_btn.setEnabled(is_available)
        if is_available:
            self.error_label.hide()
        else:
            self.error_label.show()
