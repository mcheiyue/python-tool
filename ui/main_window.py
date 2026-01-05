from PyQt6.QtCore import Qt, QSize, QByteArray, QTimer, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QIconEngine
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QCompleter
from qfluentwidgets import FluentWindow, NavigationItemPosition, SearchLineEdit, isDarkTheme, TitleLabel, qconfig


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

from core.utils.lazy_loader import UILazyLoader
from core.utils.resource_path import get_resource_path
from ui.widgets import CategoryHomePage

class MainWindow(FluentWindow):
    def __init__(self, container=None):
        super().__init__()
        self.container = container
        self.initWindow()
        
        # 存储所有功能界面，用于搜索 {name: interface}
        self.interfaces = {}
        # 存储图标路径映射，用于主题切换时更新图标 {objectName: iconPath}
        self.icon_mapping = {}
        # 存储分类首页 {category_name: CategoryHomePage}
        self.category_homes = {}
        
        # 初始化功能描述数据
        self._init_feature_descriptions()
        
        # 监听主题变化
        qconfig.themeChanged.connect(self.updateNavigationIcons)
        
        # 延迟初始化导航，确保主题已正确加载
        QTimer.singleShot(50, self.initDelayed)

    def updateNavigationIcons(self):
        """主题切换时刷新导航栏，重新设置所有图标"""
        # QIcon 会缓存 pixmap，所以需要为每个导航项创建全新的 QIcon 实例
        # 尝试访问 NavigationInterface 的内部项
        nav_panel = getattr(self.navigationInterface, 'panel', self.navigationInterface)
        items_dict = getattr(nav_panel, '_items', {})
        
        for object_name, icon_path in self.icon_mapping.items():
            if object_name in items_dict:
                item = items_dict[object_name]
                if hasattr(item, 'setIcon'):
                    # 创建全新的图标实例
                    new_icon = self.get_icon(icon_path)
                    item.setIcon(new_icon)
        
        # 强制重绘整个导航栏
        self.navigationInterface.update()
        self.navigationInterface.repaint()

    def initDelayed(self):
        self.initNavigation()
        self.initTitleBar()

    def initWindow(self):
        self.setWindowTitle("AI Office Tool")
        self.setWindowIcon(QIcon(get_resource_path("assets/processed_icons/icon_transparent.ico")))
        self.resize(900, 700)
        self.setMinimumSize(800, 600)
        
        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width()-self.width())//2, (screen.height()-self.height())//2)

    def get_icon(self, path):
        """获取主题感知的 SVG 图标"""
        # 使用 ThemedSvgIconEngine，图标会在每次绘制时根据当前主题动态着色
        return QIcon(ThemedSvgIconEngine(path))
    
    def _init_feature_descriptions(self):
        """初始化功能描述数据"""
        self.feature_descriptions = {
            # Office 工具
            "PPT 转 PDF": "将 PowerPoint 文件转换为 PDF 格式",
            "PPT 转图片": "导出 PPT 为图片格式",
            "Word 转 PDF": "将 Word 文档转换为 PDF",
            "Doc 转 Docx": "升级旧版 .doc 为 .docx 格式",
            "Excel 转 PDF": "将 Excel 表格转换为 PDF",
            
            # PDF 工具
            "PDF 合并": "将多个 PDF 文件合并为一个",
            "PDF 压缩": "压缩 PDF 文件大小",
            "PDF 拆分/提取": "拆分或提取 PDF 页面",
            "PDF 图片提取": "从 PDF 中提取所有图片",
            
            # 图片工具
            "图片取色": "提取图片中的主要颜色",
            "PNG 转 SVG": "将 PNG 图片转为矢量 SVG",
            "图片格式转换": "在多种图片格式间转换",
            "图片转 PDF": "将图片转换为 PDF 文档",
            
            # 文本工具
            "Markdown 转 PDF": "将 Markdown 文档转为 PDF",
            "TXT 转 PDF": "将文本文件转换为 PDF",
            "代码提取": "从文件中提取代码块"
        }

    def initNavigation(self):
        # 1. Office 转换组
        self.office_home = self.createCategoryInterface("Office 工具", "office_home")
        self.icon_mapping["office_home"] = get_resource_path("assets/icons/presentation.svg")
        self.addSubInterface(self.office_home, self.get_icon(get_resource_path("assets/icons/presentation.svg")), "Office 转换")

        # 1.1 PPT 转 PDF（添加到stackedWidget但不在导航栏显示）
        self.ppt_interface = UILazyLoader("ui.interfaces.ppt_interface", "PPTInterface", self)
        self.stackedWidget.addWidget(self.ppt_interface)
        self.interfaces["PPT 转 PDF"] = self.ppt_interface

        # 1.2 PPT 转图片
        self.ppt_img_interface = UILazyLoader("ui.interfaces.ppt_image_interface", "PPTImageInterface", self)
        self.stackedWidget.addWidget(self.ppt_img_interface)
        self.interfaces["PPT 转图片"] = self.ppt_img_interface

        # 1.3 Word 转 PDF
        self.word_interface = UILazyLoader("ui.interfaces.word_interface", "WordInterface", self)
        self.stackedWidget.addWidget(self.word_interface)
        self.interfaces["Word 转 PDF"] = self.word_interface

        # 1.4 Doc 转 Docx
        self.doc_to_docx_interface = UILazyLoader("ui.interfaces.doc_to_docx_interface", "DocToDocxInterface", self)
        self.stackedWidget.addWidget(self.doc_to_docx_interface)
        self.interfaces["Doc 转 Docx"] = self.doc_to_docx_interface

        # 1.5 Excel 转 PDF
        self.excel_interface = UILazyLoader("ui.interfaces.excel_interface", "ExcelInterface", self)
        self.stackedWidget.addWidget(self.excel_interface)
        self.interfaces["Excel 转 PDF"] = self.excel_interface

        # 2. PDF 处理组
        self.pdf_home = self.createCategoryInterface("PDF 工具箱", "pdf_home")
        self.icon_mapping["pdf_home"] = get_resource_path("assets/icons/pdf.svg")
        self.addSubInterface(self.pdf_home, self.get_icon(get_resource_path("assets/icons/pdf.svg")), "PDF 处理")

        # 2.1 PDF 合并
        self.pdf_merge_interface = UILazyLoader("ui.interfaces.pdf_merge_interface", "PDFMergeInterface", self)
        self.stackedWidget.addWidget(self.pdf_merge_interface)
        self.interfaces["PDF 合并"] = self.pdf_merge_interface

        # 2.2 PDF 压缩
        self.compress_interface = UILazyLoader("ui.interfaces.pdf_compress_interface", "PDFCompressInterface", self, container=self.container)
        self.stackedWidget.addWidget(self.compress_interface)
        self.interfaces["PDF 压缩"] = self.compress_interface

        # 2.3 PDF 拆分/提取
        self.pdf_split_interface = UILazyLoader("ui.interfaces.pdf_split_interface", "PDFSplitInterface", self)
        self.stackedWidget.addWidget(self.pdf_split_interface)
        self.interfaces["PDF 拆分/提取"] = self.pdf_split_interface

        # 2.4 PDF 图片提取
        self.pdf_img_extract_interface = UILazyLoader("ui.interfaces.pdf_image_extract_interface", "PDFImageExtractInterface", self)
        self.stackedWidget.addWidget(self.pdf_img_extract_interface)
        self.interfaces["PDF 图片提取"] = self.pdf_img_extract_interface
        
        # 3. 图片工具组
        self.image_home = self.createCategoryInterface("图片工具箱", "image_home")
        self.icon_mapping["image_home"] = get_resource_path("assets/icons/image.svg")
        self.addSubInterface(self.image_home, self.get_icon(get_resource_path("assets/icons/image.svg")), "图片工具")

        # 3.1 图片取色
        self.color_interface = UILazyLoader("ui.interfaces.color_interface", "ColorInterface", self)
        self.stackedWidget.addWidget(self.color_interface)
        self.interfaces["图片取色"] = self.color_interface

        # 3.2 PNG 转 SVG
        self.image_vector_interface = UILazyLoader("ui.interfaces.image_vector_interface", "ImageVectorInterface", self)
        self.stackedWidget.addWidget(self.image_vector_interface)
        self.interfaces["PNG 转 SVG"] = self.image_vector_interface

        # 3.3 图片格式转换
        self.image_convert_interface = UILazyLoader("ui.interfaces.image_convert_interface", "ImageConvertInterface", self)
        self.stackedWidget.addWidget(self.image_convert_interface)
        self.interfaces["图片格式转换"] = self.image_convert_interface

        # 3.4 图片转 PDF
        self.image_pdf_interface = UILazyLoader("ui.interfaces.image_pdf_interface", "ImagePdfInterface", self)
        self.stackedWidget.addWidget(self.image_pdf_interface)
        self.interfaces["图片转 PDF"] = self.image_pdf_interface

        # 4. 文本工具组
        self.text_home = self.createCategoryInterface("文本工具箱", "text_home")
        self.icon_mapping["text_home"] = get_resource_path("assets/icons/text.svg")
        self.addSubInterface(self.text_home, self.get_icon(get_resource_path("assets/icons/text.svg")), "文本工具")

        # 4.1 Markdown 转 PDF
        self.markdown_interface = UILazyLoader("ui.interfaces.markdown_interface", "MarkdownInterface", self, container=self.container)
        self.stackedWidget.addWidget(self.markdown_interface)
        self.interfaces["Markdown 转 PDF"] = self.markdown_interface

        # 4.2 TXT 转 PDF
        self.txt_pdf_interface = UILazyLoader("ui.interfaces.txt_pdf_interface", "TxtPdfInterface", self)
        self.stackedWidget.addWidget(self.txt_pdf_interface)
        self.interfaces["TXT 转 PDF"] = self.txt_pdf_interface

        # 4.3 代码提取
        self.code_extract_interface = UILazyLoader("ui.interfaces.code_extract_interface", "CodeExtractInterface", self)
        self.stackedWidget.addWidget(self.code_extract_interface)
        self.interfaces["代码提取"] = self.code_extract_interface

        # 5. 设置界面 (底部)
        self.settings_interface = UILazyLoader("ui.interfaces.settings_interface", "SettingsInterface", self)
        self.addSubInterface(self.settings_interface, self.get_icon(get_resource_path("assets/icons/settings.svg")), "设置", position=NavigationItemPosition.BOTTOM)
        self.interfaces["设置"] = self.settings_interface

        # 默认显示第一个分类的卡片首页
        self.navigationInterface.setCurrentItem(self.office_home.objectName())

    def initTitleBar(self):
        """初始化标题栏"""
        # 隐藏标题栏的软件图标
        if hasattr(self.titleBar, 'iconLabel'):
            self.titleBar.iconLabel.hide()
        
        # 隐藏导航栏左上角的返回按钮
        self.navigationInterface.setReturnButtonVisible(False)

    def createCategoryInterface(self, text, objectName):
        """创建分类界面的辅助函数（返回卡片首页）"""
        # 收集该分类下的所有功能
        features = []
        category_mapping = {
            "office_home": ["PPT 转 PDF", "PPT 转图片", "Word 转 PDF", "Doc 转 Docx", "Excel 转 PDF"],
            "pdf_home": ["PDF 合并", "PDF 压缩", "PDF 拆分/提取", "PDF 图片提取"],
            "image_home": ["图片取色", "PNG 转 SVG", "图片格式转换", "图片转 PDF"],
            "text_home": ["Markdown 转 PDF", "TXT 转 PDF", "代码提取"]
        }
        
        # 图标映射（与实际界面的图标保持一致）
        icon_mapping_dict = {
            "PPT 转 PDF": "presentation.svg",
            "PPT 转图片": "image.svg",
            "Word 转 PDF": "word.svg",
            "Doc 转 Docx": "word.svg",
            "Excel 转 PDF": "excel.svg",
            "PDF 合并": "merge.svg",
            "PDF 压缩": "compress.svg",
            "PDF 拆分/提取": "split.svg",
            "PDF 图片提取": "image.svg",
            "图片取色": "color_picker.svg",
            "PNG 转 SVG": "vector.svg",
            "图片格式转换": "convert.svg",
            "图片转 PDF": "pdf.svg",
            "Markdown 转 PDF": "markdown.svg",
            "TXT 转 PDF": "text.svg",
            "代码提取": "code.svg"
        }
        
        feature_names = category_mapping.get(objectName, [])
        for name in feature_names:
            icon_file = icon_mapping_dict.get(name, "magic.svg")
            features.append({
                "name": name,
                "icon": get_resource_path(f"assets/icons/{icon_file}"),
                "description": self.feature_descriptions.get(name, "")
            })
        
        # 创建卡片首页
        category_home = CategoryHomePage(text, features, self)
        category_home.setObjectName(objectName)
        
        # 连接卡片点击事件
        category_home.feature_clicked.connect(self.on_category_feature_clicked)
        
        # 存储分类首页
        self.category_homes[text] = category_home
        
        return category_home
    
    def on_category_feature_clicked(self, feature_name: str):
        """分类首页的功能卡片被点击"""
        if feature_name in self.interfaces:
            self.switchTo(self.interfaces[feature_name])

    def switch_to_settings(self):
        """跳转到设置界面"""
        if hasattr(self, 'settings_interface'):
            self.switchTo(self.settings_interface)
