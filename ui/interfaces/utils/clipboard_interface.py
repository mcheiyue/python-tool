import os
import io
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QSizePolicy
from PyQt6.QtGui import QPixmap, QImage, QAction, QKeySequence
from PyQt6.QtCore import Qt, QTimer
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PushButton, PrimaryPushButton, 
                            InfoBar, FluentIcon as FIF, ComboBox, ImageLabel)

from core.features.image.clipboard_handler import ClipboardImageHandler
from ui.widgets import DragDropListWidget

class ClipboardInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("clipboard_interface")
        self.handler = ClipboardImageHandler()
        self.current_image = None
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("剪贴板图片助手", self)
        self.desc = BodyLabel("快速查看、保存剪贴板中的图片，或将本地图片复制到剪贴板", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 主内容区：左侧预览，右侧操作
        self.h_layout = QHBoxLayout()
        self.h_layout.setSpacing(20)
        
        # 左侧：预览卡片
        self.preview_card = CardWidget(self)
        self.preview_layout = QVBoxLayout(self.preview_card)
        
        self.preview_label = ImageLabel(self.preview_card)
        self.preview_label.setBorderRadius(8, 8, 8, 8)
        self.preview_label.setScaledContents(True) # 允许缩放
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setMinimumSize(400, 300)
        
        self.placeholder_label = QLabel("剪贴板无图片", self.preview_card)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #808080; font-size: 16px;")
        
        self.preview_layout.addWidget(self.preview_label)
        self.preview_layout.addWidget(self.placeholder_label)
        
        # 右侧：操作面板
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)
        self.control_layout.setContentsMargins(0, 0, 0, 0)
        self.control_layout.setSpacing(15)
        
        # 1. 获取与保存
        self.section1_title = BodyLabel("获取与保存", self)
        self.refresh_btn = PrimaryPushButton(FIF.SYNC, "刷新剪贴板内容", self)
        self.refresh_btn.clicked.connect(self.refresh_preview)
        
        self.save_fmt_combo = ComboBox(self)
        self.save_fmt_combo.addItems(['PNG', 'JPG', 'BMP', 'WEBP'])
        self.save_fmt_combo.setCurrentText('PNG')
        
        self.save_btn = PushButton(FIF.SAVE, "保存到文件...", self)
        self.save_btn.clicked.connect(self.save_to_file)
        self.save_btn.setEnabled(False)
        
        self.control_layout.addWidget(self.section1_title)
        self.control_layout.addWidget(self.refresh_btn)
        self.control_layout.addWidget(self.save_fmt_combo)
        self.control_layout.addWidget(self.save_btn)
        
        self.control_layout.addSpacing(20)
        
        # 2. 复制到剪贴板
        self.section2_title = BodyLabel("复制到剪贴板", self)
        self.drop_area = DragDropListWidget(self, "拖拽图片文件到此处\n自动复制到剪贴板")
        self.drop_area.files_dropped.connect(self.copy_file_to_clipboard)
        self.drop_area.setFixedHeight(150)
        
        self.pick_btn = PushButton(FIF.FOLDER, "选择图片文件...", self)
        self.pick_btn.clicked.connect(self.pick_file_to_copy)
        
        self.control_layout.addWidget(self.section2_title)
        self.control_layout.addWidget(self.drop_area)
        self.control_layout.addWidget(self.pick_btn)
        self.control_layout.addStretch(1)

        self.h_layout.addWidget(self.preview_card, 2)
        self.h_layout.addWidget(self.control_panel, 1)
        
        self.vbox.addLayout(self.h_layout)
        
        # 初始刷新
        QTimer.singleShot(100, self.refresh_preview)

    def refresh_preview(self):
        """刷新剪贴板预览"""
        try:
            pil_img = self.handler.get_image()
            if pil_img:
                self.current_image = pil_img
                # PIL -> QPixmap
                im_data = io.BytesIO()
                pil_img.save(im_data, format='PNG')
                qimg = QImage.fromData(im_data.getvalue())
                pixmap = QPixmap.fromImage(qimg)
                
                # 调整显示逻辑
                self.preview_label.setImage(pixmap)
                self.preview_label.show()
                self.placeholder_label.hide()
                self.save_btn.setEnabled(True)
                
                # 更新描述
                w, h = pil_img.size
                self.title.setText(f"剪贴板图片 ({w}x{h})")
            else:
                self.current_image = None
                self.preview_label.hide()
                self.placeholder_label.show()
                self.save_btn.setEnabled(False)
                self.title.setText("剪贴板图片助手")
                
                # 提示
                InfoBar.warning(
                    title="无图片",
                    content="剪贴板中没有发现图片数据",
                    parent=self,
                    duration=2000
                )
        except Exception as e:
            InfoBar.error(title="错误", content=str(e), parent=self)

    def save_to_file(self):
        """保存当前图片"""
        if not self.current_image:
            return
            
        fmt = self.save_fmt_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "保存图片", f"clipboard_image.{fmt.lower()}", f"Image (*.{fmt.lower()})")
        
        if path:
            if self.handler.save_image(path, fmt):
                InfoBar.success(title="保存成功", content=f"图片已保存至 {path}", parent=self)
            else:
                InfoBar.error(title="保存失败", content="无法保存图片文件", parent=self)

    def copy_file_to_clipboard(self, paths):
        """将文件复制到剪贴板"""
        if not paths: return
        
        # 仅处理第一个文件
        path = paths[0]
        if self.handler.set_image(path):
            InfoBar.success(
                title="复制成功", 
                content=f"已将 {os.path.basename(path)} 复制到剪贴板", 
                parent=self
            )
            # 顺便刷新预览看看
            self.refresh_preview()
        else:
            InfoBar.error(title="复制失败", content="无法读取图片或格式不支持", parent=self)
            
        # 清空列表，保持区域干净
        self.drop_area.clear()

    def pick_file_to_copy(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self.copy_file_to_clipboard([path])