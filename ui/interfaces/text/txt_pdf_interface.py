import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
                            TextEdit, LineEdit, InfoBar, FluentIcon as FIF)

from core.features.text.txt_converter import TxtConverter
from ui.widgets import DragDropListWidget, CancellableProgressWidget
from ui.threads import TxtPdfThread

class TxtPdfInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("txt_pdf_interface")
        self.converter = TxtConverter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("TXT 转 PDF", self)
        self.desc = BodyLabel("将文本文件批量转换为 PDF，支持自动换行和中文", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 列表与日志
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 进度条
        self.progress = CancellableProgressWidget(self)
        self.progress.cancel_clicked.connect(self.on_cancel_task)
        self.progress.hide()
        self.vbox.addWidget(self.progress)
        
        # 底部
        self.bottom_layout = QHBoxLayout()
        self.out_label = BodyLabel("输出目录:", self)
        self.out_edit = LineEdit(self)
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.add_btn = PushButton(FIF.ADD, "添加 TXT", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_conversion)
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
        self.converter.log.connect(self.log_text.append)
        self.converter.finished.connect(self.on_finished)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 TXT", "", "Text (*.txt *.md *.py *.log)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p not in self.files:
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
    
    def on_cancel_task(self):
        """处理取消任务请求"""
        if self.thread and self.thread.isRunning():
            self.log_text.append("用户请求取消任务...")
            self.thread.cancel()

    def start_conversion(self):
        out_dir = self.out_edit.text()
        if not self.files or not out_dir: return
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.progress.start(len(self.files))
        self.progress.show()
        
        self.thread = TxtPdfThread(self.converter, self.files, out_dir)
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始转换")
        
        # 检查是否被取消
        if self.progress.is_cancelled:
            self.progress.set_complete(success=False)
            InfoBar.warning("已取消", "转换任务已取消", duration=3000, parent=self)
        else:
            self.progress.set_complete(success=(fail == 0))
            if fail > 0:
                InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
            else:
                InfoBar.success("完成", f"成功 {success}", duration=3000, parent=self)
