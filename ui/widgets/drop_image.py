import os
from PyQt6.QtWidgets import QVBoxLayout, QFileDialog
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtCore import pyqtSignal, Qt
from qfluentwidgets import CardWidget, IconWidget, BodyLabel, FluentIcon as FIF

class DropImageWidget(CardWidget):
    image_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(150)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon = IconWidget(FIF.PHOTO)
        self.icon.setFixedSize(48, 48)
        
        self.label = BodyLabel("拖拽图片到此处，或点击选择")
        self.label.setFont(QFont("Microsoft YaHei", 12))
        
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.image_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.image_dropped.emit(path)
                return
