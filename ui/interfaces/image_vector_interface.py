import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, ComboBox, Slider, 
                            CheckBox, PushButton, PrimaryPushButton, TextEdit, InfoBar, 
                            FluentIcon as FIF)

from core.image_vectorizer import ImageVectorizer
from ui.widgets import DragDropListWidget
from ui.threads import ImageVectorThread

class ImageVectorInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image_vector_interface")
        self.vectorizer = ImageVectorizer()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("PNG 转 SVG (位图转矢量)", self)
        self.desc = BodyLabel("将位图 (PNG/JPG) 转换为 SVG 矢量图，适合Logo和图标", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QGridLayout(self.settings_card)
        self.settings_layout.setContentsMargins(20, 20, 20, 20)
        self.settings_layout.setSpacing(15)

        # 模式选择
        self.mode_label = BodyLabel("采样模式:", self)
        self.mode_combo = ComboBox(self)
        self.mode_combo.addItems(['spline', 'polygon', 'none'])
        self.mode_combo.setToolTip("spline: 平滑曲线 (默认)\npolygon: 多边形\nnone: 无平滑")
        
        # 颜色模式
        self.colormode_label = BodyLabel("颜色模式:", self)
        self.colormode_combo = ComboBox(self)
        self.colormode_combo.addItems(['color', 'binary'])
        
        # 细节过滤
        self.speckle_label = BodyLabel("过滤杂点:", self)
        self.speckle_slider = Slider(Qt.Orientation.Horizontal)
        self.speckle_slider.setRange(0, 16)
        self.speckle_slider.setValue(4)
        self.speckle_val = BodyLabel("4")
        self.speckle_slider.valueChanged.connect(lambda v: self.speckle_val.setText(str(v)))

        # 层次化
        self.hierarchical_chk = CheckBox("层次化堆叠 (Hierarchical)", self)
        self.hierarchical_chk.setChecked(True)
        self.hierarchical_chk.setToolTip("堆叠形状而不是挖空，容易编辑")

        self.settings_layout.addWidget(self.mode_label, 0, 0)
        self.settings_layout.addWidget(self.mode_combo, 0, 1)
        self.settings_layout.addWidget(self.colormode_label, 0, 2)
        self.settings_layout.addWidget(self.colormode_combo, 0, 3)
        self.settings_layout.addWidget(self.speckle_label, 1, 0)
        self.settings_layout.addWidget(self.speckle_slider, 1, 1)
        self.settings_layout.addWidget(self.speckle_val, 1, 2)
        self.settings_layout.addWidget(self.hierarchical_chk, 1, 3)

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

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
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
        
        kwargs = {
            'mode': self.mode_combo.currentText(),
            'colormode': self.colormode_combo.currentText(),
            'hierarchical': 'stacked' if self.hierarchical_chk.isChecked() else 'cutout',
            'filter_speckle': self.speckle_slider.value()
        }

        # 简单的串行处理或批量创建线程
        # 为简单起见，这里我们逐个启动转换，实际项目中可以用线程池
        self.total = len(self.files)
        self.finished_count = 0
        
        for input_path in self.files:
            output_path = os.path.splitext(input_path)[0] + ".svg"
            thread = ImageVectorThread(self.vectorizer, input_path, output_path, **kwargs)
            thread.finished.connect(lambda p=output_path: self.on_one_finished(p))
            thread.start()
            self.threads.append(thread) # 防止被垃圾回收

    def on_one_finished(self, path):
        self.log_text.append(f"[完成] 生成: {os.path.basename(path)}")
        self.finished_count += 1
        if self.finished_count >= self.total:
            self.start_btn.setEnabled(True)
            self.log_text.append("所有任务已完成！")
            InfoBar.success("完成", f"成功转换 {self.total} 个文件", parent=self)
            self.threads.clear()
