import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFileDialog
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PushButton,
                            PrimaryPushButton, TextEdit, LineEdit, InfoBar,
                            FluentIcon as FIF)

from core.features.pdf.pdf_splitter import PDFSplitter
from ui.threads import PDFSplitThread
from ui.widgets import CancellableProgressWidget
from ui.design_system import Margins, Spacing

class PDFSplitInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("pdf_split_interface")
        self.splitter = PDFSplitter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)

        self.title = SubtitleLabel("PDF 拆分/提取", self)
        self.desc = BodyLabel("按范围拆分 PDF 或提取特定页面 (如: 1-5, 8, 10-end)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 输入区域
        self.card = CardWidget(self)
        self.card_layout = QGridLayout(self.card)
        self.card_layout.setContentsMargins(*Margins.CARD)
        self.card_layout.setSpacing(Spacing.MD)

        self.file_label = BodyLabel("源文件:", self)
        self.file_edit = LineEdit(self)
        self.file_edit.setPlaceholderText("请选择 PDF 文件...")
        self.file_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.file_btn.clicked.connect(self.browse_file)

        self.range_label = BodyLabel("页码范围:", self)
        self.range_edit = LineEdit(self)
        self.range_edit.setPlaceholderText("示例: 1-5, 8, 10-15 (逗号分隔)")
        
        self.out_label = BodyLabel("输出目录:", self)
        self.out_edit = LineEdit(self)
        self.out_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.out_btn.clicked.connect(self.browse_output)

        self.card_layout.addWidget(self.file_label, 0, 0)
        self.card_layout.addWidget(self.file_edit, 0, 1)
        self.card_layout.addWidget(self.file_btn, 0, 2)
        
        self.card_layout.addWidget(self.range_label, 1, 0)
        self.card_layout.addWidget(self.range_edit, 1, 1, 1, 2)
        
        self.card_layout.addWidget(self.out_label, 2, 0)
        self.card_layout.addWidget(self.out_edit, 2, 1)
        self.card_layout.addWidget(self.out_btn, 2, 2)

        self.vbox.addWidget(self.card)

        # 日志
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.vbox.addWidget(self.log_text)

        # 进度条
        self.progress = CancellableProgressWidget(self)
        self.progress.cancel_clicked.connect(self.on_cancel_task)
        self.progress.hide()
        self.vbox.addWidget(self.progress)

        # 按钮
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始拆分", self)
        self.start_btn.clicked.connect(self.start_split)
        self.start_btn.setEnabled(False)
        self.vbox.addWidget(self.start_btn, 0, Qt.AlignmentFlag.AlignRight)

        self.thread = None
        self.splitter.log.connect(self.log_text.append)
        self.splitter.finished.connect(self.on_finished)
        self.splitter.progress.connect(self.update_progress)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF", "", "PDF (*.pdf)")
        if path:
            self.file_edit.setText(path)
            if not self.out_edit.text():
                self.out_edit.setText(os.path.dirname(path))
            self.check_state()

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.out_edit.setText(path)
            self.check_state()

    def check_state(self):
        self.start_btn.setEnabled(
            bool(self.file_edit.text()) and 
            bool(self.out_edit.text())
        )

    def on_cancel_task(self):
        """处理取消任务请求"""
        if self.thread and self.thread.isRunning():
            self.log_text.append("用户请求取消任务...")
            self.thread.cancel()
    
    def start_split(self):
        file_path = self.file_edit.text()
        ranges = self.range_edit.text()
        output_dir = self.out_edit.text()
        
        if not ranges:
            InfoBar.error("错误", "请输入页码范围", parent=self)
            return

        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.progress.start(100)  # 拆分任务数量未知，使用默认值
        self.progress.show()
        
        self.thread = PDFSplitThread(self.splitter, file_path, ranges, output_dir)
        self.thread.start()

    def update_progress(self, curr, total, msg):
        self.progress.update_progress(curr, total, msg)
        self.start_btn.setText(f"处理中... {curr}/{total}")

    def on_finished(self, success, msg):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始拆分")
        
        # 检查是否被取消
        if self.progress.is_cancelled:
            self.progress.set_complete(success=False)
            InfoBar.warning("已取消", "拆分任务已取消", duration=3000, parent=self)
        else:
            self.progress.set_complete(success=success)
            if success:
                InfoBar.success("完成", msg, parent=self)
            else:
                InfoBar.error("错误", msg, parent=self)
