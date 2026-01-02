import os
from PyQt6.QtWidgets import QListWidget, QAbstractItemView
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtCore import pyqtSignal

class DragDropListWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        
        # 美化样式 - 增强对比度
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 8px;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                height: 36px;
                padding-left: 10px;
                margin: 2px 4px;
                border-radius: 4px;
                color: rgba(0, 0, 0, 0.8);
            }
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.06);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                color: #0078d4;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path): files.append(path)
        if files: self.files_dropped.emit(files)
