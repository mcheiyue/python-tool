import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog
from PyQt6.QtGui import QFont
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, ComboBox,
                            PushButton, PrimaryPushButton, TextEdit, LineEdit, InfoBar, 
                            FluentIcon as FIF)

from core.features.office.ppt_image_exporter import PPTImageExporter
from ui.widgets import DragDropListWidget
from ui.threads import PPTImageExportThread

class PPTImageInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ppt_image_interface")
        self.exporter = PPTImageExporter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("PPT 转图片", self)
        self.desc = BodyLabel("将 PPT 幻灯片批量导出为图片 (PNG/JPG)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QGridLayout(self.settings_card)
        self.settings_layout.setContentsMargins(20, 20, 20, 20)
        self.settings_layout.setSpacing(15)

        # 输出格式选择
        self.format_label = BodyLabel("图片格式:", self)
        self.format_combo = ComboBox(self)
        self.format_combo.addItems(['PNG', 'JPG', 'BMP'])
        self.format_combo.setCurrentText('PNG')
        
        self.settings_layout.addWidget(self.format_label, 0, 0)
        self.settings_layout.addWidget(self.format_combo, 0, 1)
        self.settings_layout.setColumnStretch(2, 1) # 占位
        
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

        # 底部区域
        self.bottom_layout = QHBoxLayout()
        
        self.out_label = BodyLabel("输出目录:", self)
        self.out_edit = LineEdit(self)
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.add_btn = PushButton(FIF.ADD, "添加 PPT", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_export)
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
        
        # 连接信号
        self.exporter.log.connect(self.log_text.append)
        self.exporter.finished.connect(self.on_finished)
        self.exporter.progress.connect(self.update_progress)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "选择 PPT 文件", 
            "", 
            "PowerPoint (*.ppt *.pptx)"
        )
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p.lower().endswith(('.ppt', '.pptx')) and p not in self.files:
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

    def start_export(self):
        out_dir = self.out_edit.text()
        if not self.files or not out_dir: return
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        
        fmt = self.format_combo.currentText()
        
        self.thread = PPTImageExportThread(self.exporter, self.files, out_dir, fmt)
        self.thread.start()

    def update_progress(self, curr, total, msg):
        self.start_btn.setText(f"处理中... {curr}/{total}")

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始转换")
        InfoBar.success("完成", f"成功处理 {success} 个文件", duration=3000, parent=self)
