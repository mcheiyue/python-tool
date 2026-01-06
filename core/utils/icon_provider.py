from PyQt6.QtCore import Qt, QByteArray, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QIconEngine
from PyQt6.QtSvg import QSvgRenderer
from qfluentwidgets import isDarkTheme


class ThemedSvgIconEngine(QIconEngine):
    """主题感知的 SVG 图标引擎，每次绘制时根据当前主题动态替换颜色"""
    
    def __init__(self, svg_path):
        super().__init__()
        self.svg_path = svg_path
        self._svg_content = None
        self._load_svg()
        
    def _load_svg(self):
        """加载 SVG 内容"""
        try:
            with open(self.svg_path, 'r', encoding='utf-8') as f:
                self._svg_content = f.read()
        except Exception as e:
            print(f"Error loading SVG {self.svg_path}: {e}")
            self._svg_content = ""
            
    def _get_colored_svg(self):
        """根据当前主题获取着色后的 SVG 内容"""
        if not self._svg_content:
            return ""
        # 深色主题用白色，浅色主题用黑色
        color = "#FFFFFF" if isDarkTheme() else "#000000"
        return self._svg_content.replace('currentColor', color)
        
    def paint(self, painter, rect, mode, state):
        """绘制图标"""
        colored_svg = self._get_colored_svg()
        if not colored_svg:
            return
            
        renderer = QSvgRenderer(QByteArray(colored_svg.encode('utf-8')))
        renderer.render(painter, QRectF(rect.x(), rect.y(), rect.width(), rect.height()))
        
    def pixmap(self, size, mode, state):
        """生成 Pixmap"""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRectF(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pixmap
        
    def clone(self):
        """克隆图标引擎"""
        return ThemedSvgIconEngine(self.svg_path)
