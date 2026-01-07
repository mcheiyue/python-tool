import os
from PIL import Image
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QFileDialog, QLabel, QScrollArea, QFrame)
from PyQt6.QtGui import QFont, QAction, QKeySequence, QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, 
                            PushButton, PrimaryPushButton, TextEdit, InfoBar, 
                            FluentIcon as FIF, ImageLabel)

from core.features.image.gemini_watermark_remover import GeminiWatermarkRemover
from ui.widgets import DragDropListWidget

class WatermarkRemoveThread(QThread):
    finished_one = pyqtSignal(bool, str) # success, msg/path
    
    def __init__(self, remover, input_path):
        super().__init__()
        self.remover = remover
        self.input_path = input_path
        
    def run(self):
        try:
            self.remover.process_image(self.input_path)
        except Exception as e:
            self.remover.finished.emit(False, str(e))

class WatermarkRemoveInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("watermark_remove_interface")
        self.remover = GeminiWatermarkRemover()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        # 标题和描述
        self.title = SubtitleLabel("图片去水印", self)
        self.desc = BodyLabel("移除 AI 生成图片的水印（当前支持 Gemini）", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 主内容区域：水平布局，左侧为预览，右侧为列表
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(20)
        
        # === 左侧：预览区域（带滚动） ===
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        
        # 预览标题
        self.preview_title = BodyLabel("效果预览", self)
        self.preview_layout.addWidget(self.preview_title)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 预览卡片（放在滚动区域内）
        self.preview_card = CardWidget()
        self.preview_grid = QGridLayout(self.preview_card)
        self.preview_card.setMinimumWidth(620)  # 确保两列不重叠 (300*2 + 间距)
        
        # 原图
        self.original_label = QLabel("原图")
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_image = ImageLabel()
        self.original_image.setFixedSize(300, 300)
        self.original_image.setBorderRadius(8, 8, 8, 8)
        
        # 处理后
        self.processed_label = QLabel("处理后")
        self.processed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_image = ImageLabel()
        self.processed_image.setFixedSize(300, 300)
        self.processed_image.setBorderRadius(8, 8, 8, 8)
        
        self.preview_grid.addWidget(self.original_label, 0, 0)
        self.preview_grid.addWidget(self.processed_label, 0, 1)
        self.preview_grid.addWidget(self.original_image, 1, 0)
        self.preview_grid.addWidget(self.processed_image, 1, 1)
        
        self.scroll_area.setWidget(self.preview_card)
        self.preview_layout.addWidget(self.scroll_area)
        
        # === 右侧：文件列表和操作 ===
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 文件列表
        self.list_widget = DragDropListWidget(self, "拖拽 Gemini 生成的图片到此处")
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        
        # 日志区域
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(150)
        
        # 按钮区域
        self.btn_layout = QHBoxLayout()
        self.add_btn = PushButton(FIF.ADD, "添加图片", self)
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始处理", self)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        
        self.btn_layout.addWidget(self.add_btn)
        self.btn_layout.addWidget(self.clear_btn)
        self.btn_layout.addStretch(1)
        self.btn_layout.addWidget(self.start_btn)
        
        self.right_layout.addWidget(self.list_widget, 1) # 列表占据主要空间
        self.right_layout.addWidget(self.log_text)
        self.right_layout.addLayout(self.btn_layout)
        
        # 添加左右容器到主布局
        self.content_layout.addWidget(self.preview_container, 4) # 预览占 40%
        self.content_layout.addWidget(self.right_container, 6)   # 列表占 60%
        
        self.vbox.addLayout(self.content_layout)
        
        # 初始化状态
        self.files = []
        self.threads = []
        
        # 连接信号
        self.remover.log.connect(self.log_text.append)
        self.remover.finished.connect(self.on_one_finished)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if paths:
            self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.list_widget.addItem(os.path.basename(p))
        
        if self.files:
            self.start_btn.setEnabled(True)
            # 自动选择第一个文件预览
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                self.update_preview(self.files[0])

    def on_item_clicked(self, item):
        row = self.list_widget.row(item)
        if 0 <= row < len(self.files):
            self.update_preview(self.files[row])

    def update_preview(self, path):
        # 显示原图
        if os.path.exists(path):
            # 调整原图显示
            self.original_image.setImage(path)
            # 根据图片比例自适应
            try:
                with Image.open(path) as img:
                    w, h = img.size
                    if w >= h:
                        self.original_image.scaledToWidth(300)
                    else:
                        self.original_image.scaledToHeight(300)
                    
                    # 生成预览
                    processed_img = self.remover.process_image_data(img)
                    # 将 PIL Image 转换为 QPixmap
                    im_data = processed_img.convert("RGBA").tobytes("raw", "RGBA")
                    qim = QImage(im_data, processed_img.size[0], processed_img.size[1], QImage.Format.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qim)
                    self.processed_image.setImage(pixmap)
                    
                    if w >= h:
                        self.processed_image.scaledToWidth(300)
                    else:
                        self.processed_image.scaledToHeight(300)
                        
            except Exception as e:
                self.log_text.append(f"预览失败: {str(e)}")

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.start_btn.setEnabled(False)
        self.original_image.clear()
        self.processed_image.clear()

    def start_processing(self):
        if not self.files:
            return
            
        self.start_btn.setEnabled(False)
        self.total_count = len(self.files)
        self.finished_count = 0
        self.log_text.append("开始处理任务...")
        
        for path in self.files:
            # 使用 QThread 避免阻塞 UI
            thread = WatermarkRemoveThread(self.remover, path)
            thread.start()
            self.threads.append(thread) # 防止垃圾回收

    def on_one_finished(self, success, result):
        self.finished_count += 1
        
        if success:
            # 如果当前预览的是处理完成的文件，更新预览（虽然预览是实时生成的，但这里可以确认处理结果）
            pass

        if self.finished_count >= self.total_count:
            self.start_btn.setEnabled(True)
            self.log_text.append("所有任务已完成！")
            
            InfoBar.success(
                title="处理完成",
                content=f"成功处理 {self.total_count} 个图片",
                duration=3000,
                parent=self
            )
            self.threads.clear()