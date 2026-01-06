from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from qfluentwidgets import CardWidget, isDarkTheme, qconfig
from core.utils.resource_path import get_resource_path


class FeatureCard(CardWidget):
    """功能卡片组件
    
    包含图标、标题和描述，支持 hover 悬浮效果
    """
    clicked = pyqtSignal()
    
    def __init__(self, icon_path: str, title: str, description: str, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.title_text = title
        self.description_text = description
        
        self._init_ui()
        self._init_animation()
        
        # 监听主题变化
        qconfig.themeChanged.connect(self._update_theme)
        
    def _init_ui(self):
        """初始化 UI"""
        self.setFixedSize(180, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # 图标
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setScaledContents(False)
        
        # 加载 SVG 图标
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtCore import QByteArray
        
        try:
            with open(self.icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            # 根据主题设置图标颜色
            color = "#FFFFFF" if isDarkTheme() else "#000000"
            svg_content = svg_content.replace('currentColor', color)
            
            # 渲染 SVG
            renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            self.icon_label.setPixmap(pixmap)
        except Exception as e:
            print(f"加载图标失败: {e}")
        
        # 移除图标的边框
        self.icon_label.setStyleSheet("QLabel { border: none; background: transparent; }")
        
        # 标题
        self.title_label = QLabel(self.title_text, self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(False)
        font = self.title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label.setFont(font)
        
        # 描述
        self.desc_label = QLabel(self.description_text, self)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        desc_font = self.desc_label.font()
        desc_font.setPointSize(9)
        self.desc_label.setFont(desc_font)
        
        # 设置文字颜色根据主题，并移除边框
        if isDarkTheme():
            self.title_label.setStyleSheet("QLabel { color: rgba(255, 255, 255, 0.9); border: none; background: transparent; }")
            self.desc_label.setStyleSheet("QLabel { color: rgba(255, 255, 255, 0.6); border: none; background: transparent; }")
        else:
            self.title_label.setStyleSheet("QLabel { color: rgba(0, 0, 0, 0.9); border: none; background: transparent; }")
            self.desc_label.setStyleSheet("QLabel { color: rgba(0, 0, 0, 0.6); border: none; background: transparent; }")
        
        # 添加到布局
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        
        # 添加阴影效果
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        
        # 移除边框，保持圆角
        self.setStyleSheet("""
            FeatureCard {
                border: none;
                border-radius: 8px;
            }
        """)
        
    def _update_theme(self):
        """更新主题：重新加载图标、更新文字颜色和边框样式"""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtCore import QByteArray
        
        # 重新加载图标
        try:
            with open(self.icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            # 根据当前主题设置图标颜色
            color = "#FFFFFF" if isDarkTheme() else "#000000"
            svg_content = svg_content.replace('currentColor', color)
            
            # 渲染 SVG
            renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            self.icon_label.setPixmap(pixmap)
        except Exception as e:
            print(f"更新图标失败: {e}")
        
        # 更新标题和描述文字颜色，并移除边框
        if isDarkTheme():
            self.title_label.setStyleSheet("QLabel { color: rgba(255, 255, 255, 0.9); border: none; background: transparent; }")
            self.desc_label.setStyleSheet("QLabel { color: rgba(255, 255, 255, 0.6); border: none; background: transparent; }")
        else:
            self.title_label.setStyleSheet("QLabel { color: rgba(0, 0, 0, 0.9); border: none; background: transparent; }")
            self.desc_label.setStyleSheet("QLabel { color: rgba(0, 0, 0, 0.6); border: none; background: transparent; }")
    
    def _init_animation(self):
        """初始化动画效果"""
        # 位置动画（上浮效果）
        self.pos_animation = QPropertyAnimation(self, b"pos", self)
        self.pos_animation.setDuration(200)
        self.pos_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 记录初始位置
        self._normal_pos = None
        
    def enterEvent(self, event):
        """鼠标进入事件"""
        super().enterEvent(event)
        
        # 记录初始位置
        if self._normal_pos is None:
            self._normal_pos = self.pos()
        
        # 上浮 4px
        hover_pos = QPoint(self._normal_pos.x(), self._normal_pos.y() - 4)
        
        self.pos_animation.stop()
        self.pos_animation.setStartValue(self.pos())
        self.pos_animation.setEndValue(hover_pos)
        self.pos_animation.start()
        
        # 增强阴影效果
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.shadow.setOffset(0, 4)
        
    def leaveEvent(self, event):
        """鼠标离开事件"""
        super().leaveEvent(event)
        
        if self._normal_pos:
            self.pos_animation.stop()
            self.pos_animation.setStartValue(self.pos())
            self.pos_animation.setEndValue(self._normal_pos)
            self.pos_animation.start()
        
        # 恢复阴影效果
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setOffset(0, 2)
        
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
