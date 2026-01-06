import os
from PyQt6.QtWidgets import QListWidget, QAbstractItemView
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPainter, QColor
from PyQt6.QtCore import pyqtSignal, Qt
from qfluentwidgets import isDarkTheme, qconfig

class DragDropListWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None, placeholder_text="拖拽文件到此处，或点击添加按钮"):
        super().__init__(parent)
        self.placeholder_text = placeholder_text
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        
        # 应用初始样式
        self.updateStyleSheet()
        
        # 监听主题变化
        qconfig.themeChanged.connect(self.updateStyleSheet)

    def setPlaceholderText(self, text):
        """设置占位文本"""
        self.placeholder_text = text
        self.update()

    def paintEvent(self, e):
        """重写绘制事件以显示占位文本"""
        super().paintEvent(e)
        
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 设置文字颜色
            if isDarkTheme():
                color = QColor(255, 255, 255, 100)
            else:
                color = QColor(0, 0, 0, 100)
                
            painter.setPen(color)
            font = self.font()
            font.setPointSize(12)
            painter.setFont(font)
            
            # 居中绘制文字
            rect = self.viewport().rect()
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.placeholder_text)

    def updateStyleSheet(self):
        """根据当前主题更新样式"""
        is_dark = isDarkTheme()
        
        # 定义主题颜色
        if is_dark:
            text_color = "rgba(255, 255, 255, 0.9)"
            hover_bg = "rgba(255, 255, 255, 0.06)"
            border_color = "rgba(255, 255, 255, 0.12)"
            selected_bg = "rgba(118, 185, 237, 0.2)" # 稍微亮一点的蓝色背景
            selected_color = "#60cdff" # 亮蓝色
        else:
            text_color = "rgba(0, 0, 0, 0.8)"
            hover_bg = "rgba(0, 0, 0, 0.06)"
            border_color = "rgba(0, 0, 0, 0.12)"
            selected_bg = "rgba(0, 120, 212, 0.1)"
            selected_color = "#0078d4"

        self.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: transparent;
                outline: none;
            }}
            QListWidget::item {{
                height: 36px;
                padding-left: 10px;
                margin: 2px 4px;
                border-radius: 4px;
                color: {text_color};
            }}
            QListWidget::item:hover {{
                background-color: {hover_bg};
            }}
            QListWidget::item:selected {{
                background-color: {selected_bg};
                color: {selected_color};
            }}
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

    def add_files(self, files: list):
        """添加文件列表"""
        for path in files:
            if os.path.exists(path):
                # 检查是否已存在
                items = self.findItems(os.path.basename(path), Qt.MatchFlag.MatchExactly)
                if not items:
                    self.addItem(os.path.basename(path))
                    # 可以在 item data 中存储完整路径
                    self.item(self.count()-1).setData(Qt.ItemDataRole.UserRole, path)

    def get_files(self) -> list:
        """获取当前列表中的所有文件路径"""
        files = []
        for i in range(self.count()):
            item = self.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path and os.path.exists(path):
                files.append(path)
        return files
