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

class MainWindow(FluentWindow):
    def __init__(self, container=None):
        super().__init__()
        self.container = container
        self.initWindow()
        
        # 存储所有功能界面，用于搜索 {name: interface}
        self.interfaces = {}
        # 存储图标路径映射，用于主题切换时更新图标 {objectName: iconPath}
        self.icon_mapping = {}
        
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
        self.resize(900, 700)
        self.setMinimumSize(800, 600)
        
        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width()-self.width())//2, (screen.height()-self.height())//2)

    def get_icon(self, path):
        """获取主题感知的 SVG 图标"""
        # 使用 ThemedSvgIconEngine，图标会在每次绘制时根据当前主题动态着色
        return QIcon(ThemedSvgIconEngine(path))

    def initNavigation(self):
        # 1. Office 转换组
        self.office_home = self.createCategoryInterface("Office 工具", "office_home")
        self.icon_mapping["office_home"] = "assets/icons/presentation.svg"
        self.addSubInterface(self.office_home, self.get_icon("assets/icons/presentation.svg"), "Office 转换")

        # 1.1 PPT 转 PDF
        self.ppt_interface = UILazyLoader("ui.interfaces.ppt_interface", "PPTInterface", self)
        self.icon_mapping[self.ppt_interface.objectName()] = "assets/icons/presentation.svg"
        self.addSubInterface(self.ppt_interface, self.get_icon("assets/icons/presentation.svg"), "PPT 转 PDF", parent=self.office_home)
        self.interfaces["PPT 转 PDF"] = self.ppt_interface

        # 1.2 PPT 转图片
        self.ppt_img_interface = UILazyLoader("ui.interfaces.ppt_image_interface", "PPTImageInterface", self)
        self.icon_mapping[self.ppt_img_interface.objectName()] = "assets/icons/image.svg"
        self.addSubInterface(self.ppt_img_interface, self.get_icon("assets/icons/image.svg"), "PPT 转图片", parent=self.office_home)
        self.interfaces["PPT 转图片"] = self.ppt_img_interface

        # 1.3 Word 转 PDF
        self.word_interface = UILazyLoader("ui.interfaces.word_interface", "WordInterface", self)
        self.icon_mapping[self.word_interface.objectName()] = "assets/icons/word.svg"
        self.addSubInterface(self.word_interface, self.get_icon("assets/icons/word.svg"), "Word 转 PDF", parent=self.office_home)
        self.interfaces["Word 转 PDF"] = self.word_interface

        # 1.4 Doc 转 Docx
        self.doc_to_docx_interface = UILazyLoader("ui.interfaces.doc_to_docx_interface", "DocToDocxInterface", self)
        self.icon_mapping[self.doc_to_docx_interface.objectName()] = "assets/icons/word.svg"
        self.addSubInterface(self.doc_to_docx_interface, self.get_icon("assets/icons/word.svg"), "Doc 转 Docx", parent=self.office_home)
        self.interfaces["Doc 转 Docx"] = self.doc_to_docx_interface

        # 1.5 Excel 转 PDF
        self.excel_interface = UILazyLoader("ui.interfaces.excel_interface", "ExcelInterface", self)
        self.icon_mapping[self.excel_interface.objectName()] = "assets/icons/excel.svg"
        self.addSubInterface(self.excel_interface, self.get_icon("assets/icons/excel.svg"), "Excel 转 PDF", parent=self.office_home)
        self.interfaces["Excel 转 PDF"] = self.excel_interface

        # 2. PDF 处理组
        self.pdf_home = self.createCategoryInterface("PDF 工具箱", "pdf_home")
        self.icon_mapping["pdf_home"] = "assets/icons/pdf.svg"
        self.addSubInterface(self.pdf_home, self.get_icon("assets/icons/pdf.svg"), "PDF 处理")

        # 2.1 PDF 合并
        self.pdf_merge_interface = UILazyLoader("ui.interfaces.pdf_merge_interface", "PDFMergeInterface", self)
        self.icon_mapping[self.pdf_merge_interface.objectName()] = "assets/icons/merge.svg"
        self.addSubInterface(self.pdf_merge_interface, self.get_icon("assets/icons/merge.svg"), "PDF 合并", parent=self.pdf_home)
        self.interfaces["PDF 合并"] = self.pdf_merge_interface

        # 2.2 PDF 压缩
        # 传递 container 给支持的界面
        self.compress_interface = UILazyLoader("ui.interfaces.pdf_compress_interface", "PDFCompressInterface", self, container=self.container)
        self.icon_mapping[self.compress_interface.objectName()] = "assets/icons/compress.svg"
        self.addSubInterface(self.compress_interface, self.get_icon("assets/icons/compress.svg"), "PDF 压缩", parent=self.pdf_home)
        self.interfaces["PDF 压缩"] = self.compress_interface

        # 2.3 PDF 拆分/提取
        self.pdf_split_interface = UILazyLoader("ui.interfaces.pdf_split_interface", "PDFSplitInterface", self)
        self.icon_mapping[self.pdf_split_interface.objectName()] = "assets/icons/split.svg"
        self.addSubInterface(self.pdf_split_interface, self.get_icon("assets/icons/split.svg"), "PDF 拆分/提取", parent=self.pdf_home)
        self.interfaces["PDF 拆分/提取"] = self.pdf_split_interface

        # 2.4 PDF 图片提取
        self.pdf_img_extract_interface = UILazyLoader("ui.interfaces.pdf_image_extract_interface", "PDFImageExtractInterface", self)
        self.icon_mapping[self.pdf_img_extract_interface.objectName()] = "assets/icons/image.svg"
        self.addSubInterface(self.pdf_img_extract_interface, self.get_icon("assets/icons/image.svg"), "PDF 图片提取", parent=self.pdf_home)
        self.interfaces["PDF 图片提取"] = self.pdf_img_extract_interface
        
        # 3. 图片工具组
        self.image_home = self.createCategoryInterface("图片工具箱", "image_home")
        self.icon_mapping["image_home"] = "assets/icons/image.svg"
        self.addSubInterface(self.image_home, self.get_icon("assets/icons/image.svg"), "图片工具")

        # 3.1 图片取色
        self.color_interface = UILazyLoader("ui.interfaces.color_interface", "ColorInterface", self)
        self.icon_mapping[self.color_interface.objectName()] = "assets/icons/color_picker.svg"
        self.addSubInterface(self.color_interface, self.get_icon("assets/icons/color_picker.svg"), "图片取色", parent=self.image_home)
        self.interfaces["图片取色"] = self.color_interface

        # 3.2 PNG 转 SVG
        self.image_vector_interface = UILazyLoader("ui.interfaces.image_vector_interface", "ImageVectorInterface", self)
        self.icon_mapping[self.image_vector_interface.objectName()] = "assets/icons/vector.svg"
        self.addSubInterface(self.image_vector_interface, self.get_icon("assets/icons/vector.svg"), "PNG 转 SVG", parent=self.image_home)
        self.interfaces["PNG 转 SVG"] = self.image_vector_interface

        # 3.3 图片格式转换
        self.image_convert_interface = UILazyLoader("ui.interfaces.image_convert_interface", "ImageConvertInterface", self)
        self.icon_mapping[self.image_convert_interface.objectName()] = "assets/icons/convert.svg"
        self.addSubInterface(self.image_convert_interface, self.get_icon("assets/icons/convert.svg"), "图片格式转换", parent=self.image_home)
        self.interfaces["图片格式转换"] = self.image_convert_interface

        # 3.4 图片转 PDF
        self.image_pdf_interface = UILazyLoader("ui.interfaces.image_pdf_interface", "ImagePdfInterface", self)
        self.icon_mapping[self.image_pdf_interface.objectName()] = "assets/icons/pdf.svg"
        self.addSubInterface(self.image_pdf_interface, self.get_icon("assets/icons/pdf.svg"), "图片转 PDF", parent=self.image_home)
        self.interfaces["图片转 PDF"] = self.image_pdf_interface

        # 4. 文本工具组
        self.text_home = self.createCategoryInterface("文本工具箱", "text_home")
        self.icon_mapping["text_home"] = "assets/icons/text.svg"
        self.addSubInterface(self.text_home, self.get_icon("assets/icons/text.svg"), "文本工具")

        # 4.1 Markdown 转 PDF
        self.markdown_interface = UILazyLoader("ui.interfaces.markdown_interface", "MarkdownInterface", self, container=self.container)
        self.icon_mapping[self.markdown_interface.objectName()] = "assets/icons/markdown.svg"
        self.addSubInterface(self.markdown_interface, self.get_icon("assets/icons/markdown.svg"), "Markdown 转 PDF", parent=self.text_home)
        self.interfaces["Markdown 转 PDF"] = self.markdown_interface

        # 4.2 TXT 转 PDF
        self.txt_pdf_interface = UILazyLoader("ui.interfaces.txt_pdf_interface", "TxtPdfInterface", self)
        self.icon_mapping[self.txt_pdf_interface.objectName()] = "assets/icons/text.svg"
        self.addSubInterface(self.txt_pdf_interface, self.get_icon("assets/icons/text.svg"), "TXT 转 PDF", parent=self.text_home)
        self.interfaces["TXT 转 PDF"] = self.txt_pdf_interface

        # 4.3 代码提取
        self.code_extract_interface = UILazyLoader("ui.interfaces.code_extract_interface", "CodeExtractInterface", self)
        self.icon_mapping[self.code_extract_interface.objectName()] = "assets/icons/code.svg"
        self.addSubInterface(self.code_extract_interface, self.get_icon("assets/icons/code.svg"), "代码提取", parent=self.text_home)
        self.interfaces["代码提取"] = self.code_extract_interface

        # 5. 设置界面 (底部)
        self.settings_interface = UILazyLoader("ui.interfaces.settings_interface", "SettingsInterface", self)
        self.icon_mapping[self.settings_interface.objectName()] = "assets/icons/settings.svg"
        self.addSubInterface(self.settings_interface, self.get_icon("assets/icons/settings.svg"), "设置", position=NavigationItemPosition.BOTTOM)
        self.interfaces["设置"] = self.settings_interface

        # 默认选中第一个功能的子项
        self.navigationInterface.setCurrentItem(self.ppt_interface.objectName())
        
        # 展开所有组 (可选，根据需求)
        # self.navigationInterface.expandAll()

    def initTitleBar(self):
        """初始化标题栏，添加搜索框"""
        self.searchBar = SearchLineEdit(self)
        self.searchBar.setPlaceholderText("搜索功能...")
        self.searchBar.setFixedWidth(200)
        
        # 配置搜索补全
        self.completer = QCompleter(list(self.interfaces.keys()), self.searchBar)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.searchBar.setCompleter(self.completer)
        
        # 连接信号
        self.completer.activated.connect(self.onCompleterActivated)
        self.searchBar.returnPressed.connect(self.onSearchReturnPressed)
        
        # 添加到标题栏
        self.titleBar.layout().insertWidget(1, self.searchBar, 0, Qt.AlignmentFlag.AlignHCenter)

    def createCategoryInterface(self, text, objectName):
        """创建分类界面的辅助函数"""
        widget = QWidget()
        widget.setObjectName(objectName)
        layout = QVBoxLayout(widget)
        label = TitleLabel(text, widget)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return widget

    def onCompleterActivated(self, text):
        """点击补全项时跳转"""
        if text in self.interfaces:
            self.switchTo(self.interfaces[text])
            self.searchBar.clear()

    def onSearchReturnPressed(self):
        """回车时跳转到第一个匹配项"""
        text = self.searchBar.text()
        # 如果完全匹配
        if text in self.interfaces:
            self.switchTo(self.interfaces[text])
            self.searchBar.clear()
            return
            
        # 否则查找第一个包含的
        for name, interface in self.interfaces.items():
            if text.lower() in name.lower():
                self.switchTo(interface)
                self.searchBar.clear()
                return

    def switch_to_settings(self):
        """跳转到设置界面"""
        if hasattr(self, 'settings_interface'):
            self.switchTo(self.settings_interface)
