import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, ComboBox, Slider, 
                            PushButton, PrimaryPushButton, TextEdit, InfoBar, 
                            FluentIcon as FIF)

from core.image_converter import ImageConverter
from ui.widgets import DragDropListWidget
from ui.threads import ImageConvertThread

class ImageConvertInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image_convert_interface")
        self.converter = ImageConverter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("图片格式转换", self)
        self.desc = BodyLabel("支持 JPG, PNG, WEBP, BMP, ICO 格式互转及旋转/翻转", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QGridLayout(self.settings_card)
        self.settings_layout.setContentsMargins(20, 20, 20, 20)
        self.settings_layout.setSpacing(15)

        # 输出格式选择
        self.format_label = BodyLabel("输出格式:", self)
        self.format_combo = ComboBox(self)
        self.format_combo.addItems(['JPG', 'PNG', 'WEBP', 'BMP', 'ICO'])
        self.format_combo.setCurrentText('PNG')
        
        # 质量选择
        self.quality_label = BodyLabel("质量 (JPG/WEBP):", self)
        self.quality_slider = Slider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(90)
        self.quality_val = BodyLabel("90")
        self.quality_slider.valueChanged.connect(lambda v: self.quality_val.setText(str(v)))

        self.settings_layout.addWidget(self.format_label, 0, 0)
        self.settings_layout.addWidget(self.format_combo, 0, 1)
        self.settings_layout.addWidget(self.quality_label, 0, 2)
        self.settings_layout.addWidget(self.quality_slider, 0, 3)
        self.settings_layout.addWidget(self.quality_val, 0, 4)

        # 旋转选择
        self.rotate_label = BodyLabel("旋转:", self)
        self.rotate_combo = ComboBox(self)
        self.rotate_combo.addItems(['无', '90° (顺时针)', '180°', '90° (逆时针)'])
        self.rotate_combo.setCurrentIndex(0)
        
        # 翻转选择
        self.flip_label = BodyLabel("翻转:", self)
        self.flip_combo = ComboBox(self)
        self.flip_combo.addItems(['无', '水平翻转', '垂直翻转'])
        self.flip_combo.setCurrentIndex(0)

        self.settings_layout.addWidget(self.rotate_label, 1, 0)
        self.settings_layout.addWidget(self.rotate_combo, 1, 1)
        self.settings_layout.addWidget(self.flip_label, 1, 2)
        self.settings_layout.addWidget(self.flip_combo, 1, 3)

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
        self.threads = [] # Keep references
        
        # 连接日志信号
        self.converter.log.connect(self.log_text.append)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.ico)")
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
        self.start_btn.setEnabled(False)
        self.log_text.append("开始转换任务...")
        
        target_format = self.format_combo.currentText()
        quality = self.quality_slider.value()

        # 获取旋转参数
        rotate_idx = self.rotate_combo.currentIndex()
        rotate_angle = 0
        if rotate_idx == 1: rotate_angle = 90
        elif rotate_idx == 2: rotate_angle = 180
        elif rotate_idx == 3: rotate_angle = 270
        
        # 获取翻转参数
        flip_idx = self.flip_combo.currentIndex()
        flip_mode = None
        if flip_idx == 1: flip_mode = 'H'
        elif flip_idx == 2: flip_mode = 'V'

        self.total = len(self.files)
        self.finished_count = 0
        
        for input_path in self.files:
            # 构建输出路径
            dir_name = os.path.dirname(input_path)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = target_format.lower()
            if ext == 'jpeg': ext = 'jpg'
            output_path = os.path.join(dir_name, f"{base_name}.{ext}")
            
            thread = ImageConvertThread(self.converter, input_path, output_path, target_format, quality, rotate_angle, flip_mode)
            thread.finished.connect(lambda: self.on_one_finished())
            thread.start()
            self.threads.append(thread) # 防止被垃圾回收

    def on_one_finished(self):
        self.finished_count += 1
        if self.finished_count >= self.total:
            self.start_btn.setEnabled(True)
            self.log_text.append("所有任务已完成！")
            InfoBar.success("完成", f"成功转换 {self.total} 个文件", parent=self)
            self.threads.clear()
