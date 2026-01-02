from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QImage
from PyQt6.QtCore import Qt, QRect
from qfluentwidgets import InfoBar

class ColorBar(QWidget):
    def __init__(self, color_data=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.color_data = color_data or []
        self.spacing = 2  # 色块间距
        self.setMouseTracking(True)
        self.hovered_index = -1

    def set_colors(self, color_data):
        self.color_data = color_data
        self.update()

    def paintEvent(self, event):
        if not self.color_data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # 计算可用总宽度
        total_spacing = (len(self.color_data) - 1) * self.spacing
        available_width = self.width() - total_spacing
        
        current_x = 0
        for i, data in enumerate(self.color_data):
            # 计算当前色块宽度
            # 最后一个色块占用剩余空间，避免精度问题导致的空隙
            if i == len(self.color_data) - 1:
                block_width = self.width() - current_x
            else:
                block_width = max(1, int(available_width * data['proportion']))
            
            # 绘制色块
            rect = QRect(current_x, 0, block_width, self.height())
            color = QColor(data['hex'])
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)
            
            # 绘制 hover 效果 (边框)
            if i == self.hovered_index:
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(1, 1, -1, -1))
                painter.setPen(Qt.PenStyle.NoPen)
            
            current_x += block_width + self.spacing

    def mouseMoveEvent(self, event):
        # 计算当前鼠标下的色块索引
        if not self.color_data:
            return

        total_spacing = (len(self.color_data) - 1) * self.spacing
        available_width = self.width() - total_spacing
        
        current_x = 0
        new_hover_index = -1
        
        for i, data in enumerate(self.color_data):
            if i == len(self.color_data) - 1:
                block_width = self.width() - current_x
            else:
                block_width = max(1, int(available_width * data['proportion']))
            
            rect = QRect(current_x, 0, block_width, self.height())
            
            if rect.contains(event.pos()):
                new_hover_index = i
                break
            
            current_x += block_width + self.spacing
            
        if new_hover_index != self.hovered_index:
            self.hovered_index = new_hover_index
            self.update()
            
            if new_hover_index != -1:
                color = self.color_data[new_hover_index]
                self.setToolTip(f"{color['hex']} ({color['proportion']*100:.1f}%)")
            else:
                self.setToolTip("")

    def leaveEvent(self, event):
        self.hovered_index = -1
        self.update()

    def mousePressEvent(self, event):
        if self.hovered_index != -1:
            color = self.color_data[self.hovered_index]
            QApplication.clipboard().setText(color['hex'])
            InfoBar.success("已复制", f"Hex 代码 {color['hex']} 已复制到剪贴板", duration=1500, parent=self.window())

    def export_to_image(self, filepath, width=1200, height=80):
        """将色条导出为图片"""
        if not self.color_data:
            return False

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # 计算可用总宽度
        total_spacing = (len(self.color_data) - 1) * self.spacing
        available_width = width - total_spacing
        
        current_x = 0
        for i, data in enumerate(self.color_data):
            # 计算当前色块宽度
            if i == len(self.color_data) - 1:
                block_width = width - current_x
            else:
                block_width = max(1, int(available_width * data['proportion']))
            
            # 绘制色块
            rect = QRect(current_x, 0, block_width, height)
            color = QColor(data['hex'])
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)
            
            current_x += block_width + self.spacing
            
        painter.end()
        return image.save(filepath)
