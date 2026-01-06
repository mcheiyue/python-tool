from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QLabel
from qfluentwidgets import TitleLabel, FlowLayout, isDarkTheme, qconfig
from .feature_card import FeatureCard


class CategoryHomePage(QScrollArea):
    """分类首页组件
    
    显示某个功能分类下所有功能的卡片网格
    """
    feature_clicked = pyqtSignal(str)  # 功能名称
    
    def __init__(self, category_name: str, features: list, parent=None):
        """
        Args:
            category_name: 分类名称，如 "Office 工具"
            features: 功能列表，格式为 [{"name": "PPT 转 PDF", "icon": "path", "description": "描述", "interface": interface_obj}, ...]
        """
        super().__init__(parent)
        self.category_name = category_name
        self.features = features
        
        self._init_ui()
        self._update_background()
        
        # 监听主题变化
        qconfig.themeChanged.connect(self._update_background)
        
    def _init_ui(self):
        """初始化 UI"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 容器 widget
        container = QWidget()
        self.setWidget(container)
        
        # 主布局
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(30)
        
        # 标题
        title_label = TitleLabel(self.category_name, container)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(title_label)
        
        # 卡片网格容器
        grid_container = QWidget()
        grid_layout = FlowLayout(grid_container, needAni=True)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(20)
        
        # 创建功能卡片
        for feature in self.features:
            card = FeatureCard(
                icon_path=feature["icon"],
                title=feature["name"],
                description=feature["description"],
                parent=grid_container
            )
            # 连接点击信号
            card.clicked.connect(lambda name=feature["name"]: self.on_feature_clicked(name))
            grid_layout.addWidget(card)
        
        main_layout.addWidget(grid_container)
        main_layout.addStretch()
    
    def _update_background(self):
        """更新背景色以跟随主题"""
        if isDarkTheme():
            bg_color = "#202020"  # 深色模式背景
        else:
            bg_color = "#f5f5f5"  # 浅色模式背景
        
        # 设置 QScrollArea 的背景色
        self.setStyleSheet(f"""
            CategoryHomePage {{
                background-color: {bg_color};
                border: none;
            }}
        """)
        
        # 设置内部容器的背景色
        if self.widget():
            self.widget().setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_color};
                }}
            """)
    
    def on_feature_clicked(self, feature_name: str):
        """功能卡片被点击"""
        self.feature_clicked.emit(feature_name)
