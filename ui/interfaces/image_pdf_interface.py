import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog, QButtonGroup
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, RadioButton,
                            PushButton, PrimaryPushButton, TextEdit, InfoBar, 
                            FluentIcon as FIF)

from core.image_to_pdf_converter import ImageToPdfConverter
from ui.widgets import DragDropListWidget
from ui.threads import ImageToPdfThread

class ImagePdfInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image_pdf_interface")
        self.converter = ImageToPdfConverter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("图片转 PDF", self)
        self.desc = BodyLabel("将多张图片合并为一个 PDF，或批量将图片转换为 PDF", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QGridLayout(self.settings_card)
        self.settings_layout.setContentsMargins(20, 20, 20, 20)
        self.settings_layout.setSpacing(15)

        # 模式选择
        self.mode_label = BodyLabel("转换模式:", self)
        self.merge_radio = RadioButton("合并为一个 PDF", self)
        self.single_radio = RadioButton("每张图生成一个 PDF", self)
        self.merge_radio.setChecked(True)
        
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.merge_radio)
        self.mode_group.addButton(self.single_radio)

        self.settings_layout.addWidget(self.mode_label, 0, 0)
        self.settings_layout.addWidget(self.merge_radio, 0, 1)
        self.settings_layout.addWidget(self.single_radio, 0, 2)
        
        self.vbox.addWidget(self.settings_card)

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

        # 底部按钮
        self.bottom_layout = QHBoxLayout()
        self.add_btn = PushButton(FIF.ADD, "添加图片", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)

        self.files = []
        self.thread = None
        
        # 连接日志信号
        self.converter.log.connect(self.log_text.append)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "选择图片", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.list_widget.addItem(os.path.basename(p))
        if self.files: self.start_btn.setEnabled(True)

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.start_btn.setEnabled(False)

    def start_conversion(self):
        if not self.files: return
        
        merge_mode = self.merge_radio.isChecked()
        
        if merge_mode:
            # 合并模式：选择保存文件路径
            output_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存 PDF", 
                "merged.pdf", 
                "PDF Files (*.pdf)"
            )
            if not output_path: return
        else:
            # 单文件模式：选择保存目录
            output_path = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if not output_path: return

        self.start_btn.setEnabled(False)
        self.log_text.append("开始转换任务...")
        
        self.thread = ImageToPdfThread(self.converter, self.files, output_path, merge_mode)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.thread = None
        # 注意：成功提示已在 converter 的 finished 信号中处理（如果有连接的话），
        # 但这里我们主要依赖日志输出，也可以添加一个 InfoBar
        # 由于 ImageToPdfConverter 也发出了 finished 信号，我们可以在那里连接槽函数
        # 但为了简单起见，且 log 已经有输出，这里只恢复按钮状态
        # 我们可以根据最后一条日志判断是否成功，或者修改 ImageToPdfThread 来传递结果
        InfoBar.success("任务结束", "处理完成，请查看日志", parent=self)
