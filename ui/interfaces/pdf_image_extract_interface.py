import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt6.QtGui import QFont
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton, 
                            TextEdit, LineEdit, InfoBar, FluentIcon as FIF)

from core.pdf_image_extractor import PDFImageExtractor
from ui.widgets import DragDropListWidget
from ui.threads import PDFImageExtractThread

class PDFImageExtractInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("pdf_img_extract_interface")
        self.extractor = PDFImageExtractor()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("PDF 图片提取", self)
        self.desc = BodyLabel("批量从 PDF 文件中提取所有嵌入的图片资源", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 文件列表
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
        
        self.add_btn = PushButton(FIF.ADD, "添加 PDF", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始提取", self)
        self.start_btn.clicked.connect(self.start_extract)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.out_label)
        self.bottom_layout.addWidget(self.out_edit)
        self.bottom_layout.addWidget(self.browse_btn)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addWidget(self.start_btn)
        
        self.vbox.addLayout(self.bottom_layout)

        self.files = []
        self.thread = None
        self.extractor.log.connect(self.log_text.append)
        self.extractor.finished.connect(self.on_finished)
        self.extractor.progress.connect(self.update_progress)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF (*.pdf)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p.lower().endswith('.pdf') and p not in self.files:
                self.files.append(p)
                self.list_widget.addItem(os.path.basename(p))
        
        if self.files and not self.out_edit.text():
            self.out_edit.setText(os.path.dirname(self.files[0]))
        self.check_state()

    def browse_output(self):
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
        self.start_btn.setEnabled(bool(self.files) and bool(self.out_edit.text()))

    def start_extract(self):
        out_dir = self.out_edit.text()
        if not self.files or not out_dir: return
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.thread = PDFImageExtractThread(self.extractor, self.files, out_dir)
        self.thread.start()

    def update_progress(self, curr, total, msg):
        self.start_btn.setText(f"处理中... {curr}/{total}")

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始提取")
        InfoBar.success("完成", f"成功处理 {success} 个文件", duration=3000, parent=self)
