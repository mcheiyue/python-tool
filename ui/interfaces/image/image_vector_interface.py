import os
import subprocess
from functools import partial
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog
from PyQt6.QtGui import QFont, QAction, QKeySequence
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, ComboBox, Slider,
                            CheckBox, PushButton, PrimaryPushButton, TextEdit, InfoBar,
                            FluentIcon as FIF)

from core.features.image.image_vectorizer import ImageVectorizer
from ui.widgets import DragDropListWidget
from ui.threads import WorkerThread

class ImageVectorInterface(QWidget):
    _log_bridged = pyqtSignal(str)

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
        self.mode_label.setToolTip(
            "决定矢量路径的生成方式：\n"
            "• spline (样条曲线): 将边界转换为平滑的曲线，适合图标和插画，边缘光滑自然。\n"
            "• polygon (多边形): 使用直线段连接边界，适合几何图形或硬边缘风格。\n"
            "• none (无): 不进行平滑处理。"
        )
        self.mode_combo = ComboBox(self)
        self.mode_combo.addItems(['spline', 'polygon', 'none'])
        self.mode_combo.setToolTip(self.mode_label.toolTip())
        
        # 颜色模式
        self.colormode_label = BodyLabel("颜色模式:", self)
        self.colormode_label.setToolTip(
            "决定输出 SVG 的颜色策略：\n"
            "• color (彩色): 保留原始颜色，通过聚类生成多个颜色层，还原度高。\n"
            "• binary (二值化): 仅输出黑白两色，适合线稿、文字或高对比度图形。"
        )
        self.colormode_combo = ComboBox(self)
        self.colormode_combo.addItems(['color', 'binary'])
        self.colormode_combo.setToolTip(self.colormode_label.toolTip())
        
        # 细节过滤
        self.speckle_label = BodyLabel("过滤杂点:", self)
        self.speckle_label.setToolTip("过滤掉小于指定像素大小的噪点或微小区域，值越大画面越干净，但可能丢失细节。")
        self.speckle_slider = Slider(Qt.Orientation.Horizontal)
        self.speckle_slider.setRange(0, 16)
        self.speckle_slider.setValue(4)
        self.speckle_val = BodyLabel("4")
        self.speckle_slider.valueChanged.connect(lambda v: self.speckle_val.setText(str(v)))

        # 层次化
        self.hierarchical_chk = CheckBox("层次化堆叠 (Hierarchical)", self)
        self.hierarchical_chk.setChecked(True)
        self.hierarchical_chk.setToolTip("选中时：不同颜色的形状会相互重叠堆积，便于后续编辑移动。\n未选中时：形状之间会进行挖空处理，像拼图一样严丝合缝。")

        self.settings_layout.addWidget(self.mode_label, 0, 0)
        self.settings_layout.addWidget(self.mode_combo, 0, 1)
        self.settings_layout.addWidget(self.colormode_label, 0, 2)
        self.settings_layout.addWidget(self.colormode_combo, 0, 3)
        self.settings_layout.addWidget(self.speckle_label, 1, 0)
        self.settings_layout.addWidget(self.speckle_slider, 1, 1)
        self.settings_layout.addWidget(self.speckle_val, 1, 2)
        self.settings_layout.addWidget(self.hierarchical_chk, 1, 3)
        
        # 添加参数说明提示
        self.hint_label = BodyLabel("💡 提示：鼠标悬停在选项上可查看详细说明", self)
        self.hint_label.setTextColor("#808080", "#a0a0a0")
        self.settings_layout.addWidget(self.hint_label, 2, 0, 1, 4)

        self.vbox.addWidget(self.settings_card)

        # 文件列表
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self, "拖拽 PNG/JPG 图片到此处，\n支持批量处理")
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
        self.add_btn.setToolTip("选择图片文件 (Ctrl+O)")
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.setToolTip("清空列表 (Delete)")
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.setToolTip("开始处理所有图片 (Ctrl+Enter)")
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)
        
        # 快捷键
        self.add_action = QAction(self)
        self.add_action.setShortcut(QKeySequence("Ctrl+O"))
        self.add_action.triggered.connect(self.add_files)
        self.addAction(self.add_action)
        
        self.run_action = QAction(self)
        self.run_action.setShortcut(QKeySequence("Ctrl+Return"))
        self.run_action.triggered.connect(self.start_conversion)
        self.addAction(self.run_action)
        
        self.del_action = QAction(self)
        self.del_action.setShortcut(QKeySequence("Delete"))
        self.del_action.triggered.connect(self.remove_selection)
        self.addAction(self.del_action)

        self.files = []
        self.threads = [] # Keep references
        self._log_bridged.connect(self.log_text.append)

    def remove_selection(self):
        # 从后往前删
        rows = sorted([item.row() for item in self.list_widget.selectedIndexes()], reverse=True)
        for row in rows:
            if row < len(self.files):
                self.files.pop(row)
                self.list_widget.takeItem(row)
        if not self.files:
            self.start_btn.setEnabled(False)

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
            thread = WorkerThread(
                partial(self.vectorizer.convert, input_path, output_path, **kwargs),
                on_log=self._log_bridged.emit,
            )
            thread.finished.connect(lambda p=output_path: self.on_one_finished(p))
            thread.start()
            self.threads.append(thread) # 防止被垃圾回收

    def on_one_finished(self, path):
        self.log_text.append(f"[完成] 生成: {os.path.basename(path)}")
        self.finished_count += 1
        if self.finished_count >= self.total:
            self.start_btn.setEnabled(True)
            self.log_text.append("所有任务已完成！")
            
            # 创建带有操作按钮的 InfoBar
            bar = InfoBar.success(
                title="转换完成",
                content=f"成功处理 {self.total} 个文件",
                duration=5000,
                parent=self
            )
            
            # 添加打开文件夹按钮
            open_folder_btn = PushButton("打开所在文件夹")
            def open_folder():
                def do_open():
                    folder_path = os.path.dirname(path)
                    if os.name == 'nt':
                        subprocess.Popen(['explorer', folder_path], shell=False)
                    else:
                        from PyQt6.QtGui import QDesktopServices
                        from PyQt6.QtCore import QUrl
                        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
                QTimer.singleShot(300, do_open)
            open_folder_btn.clicked.connect(open_folder)
            bar.addWidget(open_folder_btn)
            
            bar.show()
            self.threads.clear()
