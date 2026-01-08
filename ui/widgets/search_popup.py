from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QIcon
from qfluentwidgets import isDarkTheme, FluentIcon

from core.utils.fuzzy_search import SearchResult

class SearchResultItem(QWidget):
    """自定义搜索结果项组件"""
    def __init__(self, result: SearchResult, icon: QIcon, parent=None):
        super().__init__(parent)
        self.result = result
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        
        # 标题行
        self.title_label = QLabel(result.name)
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        
        # 描述行
        self.desc_label = QLabel(result.description)
        self.desc_label.setFont(QFont("Segoe UI", 9))
        self.desc_label.setStyleSheet("color: #808080;")
        self.desc_label.setWordWrap(True)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
        
        # 匹配高亮逻辑 (简单实现，可扩展)
        if isDarkTheme():
            self.title_label.setStyleSheet("color: white;")
            self.hover_bg = "#333333"
        else:
            self.title_label.setStyleSheet("color: black;")
            self.hover_bg = "#f0f0f0"

class SearchResultPopup(QListWidget):
    """搜索结果弹出窗口"""
    
    itemClicked = pyqtSignal(str)  # 发送功能名称
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 样式
        self.updateStyle()
        
    def updateStyle(self):
        if isDarkTheme():
            bg_color = "#2b2b2b"
            border_color = "#454545"
            item_hover = "#3a3a3a"
            item_sel = "#404040"
            text_color = "#ffffff"
        else:
            bg_color = "#ffffff"
            border_color = "#e5e5e5"
            item_hover = "#f5f5f5"
            item_sel = "#e8e8e8"
            text_color = "#000000"
            
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }}
            QListWidget::item {{
                background-color: transparent;
                border-radius: 4px;
                padding: 4px;
                color: {text_color};
            }}
            QListWidget::item:hover {{
                background-color: {item_hover};
            }}
            QListWidget::item:selected {{
                background-color: {item_sel};
            }}
        """)

    def show_results(self, results: list[SearchResult], icons: dict[str, QIcon], parent_width: int):
        """显示搜索结果"""
        self.clear()
        
        if not results:
            self.hide()
            return
            
        for res in results:
            item = QListWidgetItem(self)
            # 设置数据
            item.setData(Qt.ItemDataRole.UserRole, res.name)
            
            # 创建自定义 Widget
            icon = icons.get(res.name)
            widget = SearchResultItem(res, icon)
            
            item.setSizeHint(QSize(parent_width - 20, 60))
            self.addItem(item)
            self.setItemWidget(item, widget)
            
        # 调整大小
        height = min(len(results) * 60 + 20, 400)
        self.resize(parent_width, height)
        self.setCurrentRow(0)
        self.show()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if self.currentItem():
                self.itemClicked.emit(self.currentItem().data(Qt.ItemDataRole.UserRole))
                self.hide()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
            
    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.itemClicked.emit(item.data(Qt.ItemDataRole.UserRole))
            self.hide()
        super().mouseReleaseEvent(event)