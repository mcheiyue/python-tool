from PyQt6.QtWidgets import QVBoxLayout, QApplication, QLabel
from PyQt6.QtCore import Qt
from qfluentwidgets import CardWidget, StrongBodyLabel, BodyLabel, InfoBar

class ColorCard(CardWidget):
    def __init__(self, color_data, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 色块
        self.color_block = QLabel()
        self.color_block.setFixedHeight(100)
        self.color_block.setStyleSheet(f"background-color: {color_data['hex']}; border-radius: 6px;")
        
        # Hex
        self.hex_label = StrongBodyLabel(color_data['hex'])
        self.hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 占比
        prop = color_data['proportion'] * 100
        self.prop_label = BodyLabel(f"{prop:.1f}%")
        self.prop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prop_label.setTextColor("#808080", "#a0a0a0")
        
        layout.addWidget(self.color_block)
        layout.addSpacing(5)
        layout.addWidget(self.hex_label)
        layout.addWidget(self.prop_label)
        
        self.setToolTip("点击复制 Hex 代码")
        self.hex_code = color_data['hex']

    def mousePressEvent(self, event):
        QApplication.clipboard().setText(self.hex_code)
        InfoBar.success("已复制", f"Hex 代码 {self.hex_code} 已复制到剪贴板", duration=1500, parent=self.window())
