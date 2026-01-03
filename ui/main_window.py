from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QCompleter
from qfluentwidgets import FluentWindow, NavigationItemPosition, SearchLineEdit, isDarkTheme, TitleLabel

from ui.interfaces import (
    PPTInterface, PPTImageInterface, WordInterface, ExcelInterface, PDFMergeInterface, PDFCompressInterface,
    PDFSplitInterface, PDFImageExtractInterface, ColorInterface, MarkdownInterface,
    ImageVectorInterface, ImageConvertInterface, ImagePdfInterface, TxtPdfInterface, CodeExtractInterface, SettingsInterface
)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()
        
        # 存储所有功能界面，用于搜索 {name: interface}
        self.interfaces = {}
        
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
        """根据当前主题获取图标（动态替换currentColor）"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据主题替换颜色
            # 深色主题用白色(#FFFFFF)，浅色主题用黑色(#000000)
            color = "#FFFFFF" if isDarkTheme() else "#000000"
            content = content.replace('currentColor', color)
            
            # 渲染 SVG 到 Pixmap
            renderer = QSvgRenderer(QByteArray(content.encode('utf-8')))
            # 渲染为 48x48 (2x @ 24px) 以支持高分屏，QIcon 会自动处理缩放
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error loading icon {path}: {e}")
            return QIcon(path)

    def initNavigation(self):
        # 1. Office 转换组
        self.office_home = self.createCategoryInterface("Office 工具", "office_home")
        self.addSubInterface(self.office_home, self.get_icon("assets/icons/presentation.svg"), "Office 转换")

        # 1.1 PPT 转 PDF
        self.ppt_interface = PPTInterface(self)
        self.addSubInterface(self.ppt_interface, self.get_icon("assets/icons/presentation.svg"), "PPT 转 PDF", parent=self.office_home)
        self.interfaces["PPT 转 PDF"] = self.ppt_interface

        # 1.2 PPT 转图片
        self.ppt_img_interface = PPTImageInterface(self)
        self.addSubInterface(self.ppt_img_interface, self.get_icon("assets/icons/image.svg"), "PPT 转图片", parent=self.office_home)
        self.interfaces["PPT 转图片"] = self.ppt_img_interface

        # 1.3 Word 转 PDF
        self.word_interface = WordInterface(self)
        self.addSubInterface(self.word_interface, self.get_icon("assets/icons/word.svg"), "Word 转 PDF", parent=self.office_home)
        self.interfaces["Word 转 PDF"] = self.word_interface

        # 1.4 Excel 转 PDF
        self.excel_interface = ExcelInterface(self)
        self.addSubInterface(self.excel_interface, self.get_icon("assets/icons/excel.svg"), "Excel 转 PDF", parent=self.office_home)
        self.interfaces["Excel 转 PDF"] = self.excel_interface

        # 2. PDF 处理组
        self.pdf_home = self.createCategoryInterface("PDF 工具箱", "pdf_home")
        self.addSubInterface(self.pdf_home, self.get_icon("assets/icons/pdf.svg"), "PDF 处理")

        # 2.1 PDF 合并
        self.pdf_merge_interface = PDFMergeInterface(self)
        self.addSubInterface(self.pdf_merge_interface, self.get_icon("assets/icons/merge.svg"), "PDF 合并", parent=self.pdf_home)
        self.interfaces["PDF 合并"] = self.pdf_merge_interface

        # 2.2 PDF 压缩
        self.compress_interface = PDFCompressInterface(self)
        self.addSubInterface(self.compress_interface, self.get_icon("assets/icons/compress.svg"), "PDF 压缩", parent=self.pdf_home)
        self.interfaces["PDF 压缩"] = self.compress_interface

        # 2.3 PDF 拆分/提取
        self.pdf_split_interface = PDFSplitInterface(self)
        self.addSubInterface(self.pdf_split_interface, self.get_icon("assets/icons/split.svg"), "PDF 拆分/提取", parent=self.pdf_home)
        self.interfaces["PDF 拆分/提取"] = self.pdf_split_interface

        # 2.4 PDF 图片提取
        self.pdf_img_extract_interface = PDFImageExtractInterface(self)
        self.addSubInterface(self.pdf_img_extract_interface, self.get_icon("assets/icons/image.svg"), "PDF 图片提取", parent=self.pdf_home)
        self.interfaces["PDF 图片提取"] = self.pdf_img_extract_interface
        
        # 3. 图片工具组
        self.image_home = self.createCategoryInterface("图片工具箱", "image_home")
        self.addSubInterface(self.image_home, self.get_icon("assets/icons/image.svg"), "图片工具")

        # 3.1 图片取色
        self.color_interface = ColorInterface(self)
        self.addSubInterface(self.color_interface, self.get_icon("assets/icons/color_picker.svg"), "图片取色", parent=self.image_home)
        self.interfaces["图片取色"] = self.color_interface

        # 3.2 PNG 转 SVG
        self.image_vector_interface = ImageVectorInterface(self)
        self.addSubInterface(self.image_vector_interface, self.get_icon("assets/icons/vector.svg"), "PNG 转 SVG", parent=self.image_home)
        self.interfaces["PNG 转 SVG"] = self.image_vector_interface

        # 3.3 图片格式转换
        self.image_convert_interface = ImageConvertInterface(self)
        self.addSubInterface(self.image_convert_interface, self.get_icon("assets/icons/convert.svg"), "图片格式转换", parent=self.image_home)
        self.interfaces["图片格式转换"] = self.image_convert_interface

        # 3.4 图片转 PDF
        self.image_pdf_interface = ImagePdfInterface(self)
        self.addSubInterface(self.image_pdf_interface, self.get_icon("assets/icons/pdf.svg"), "图片转 PDF", parent=self.image_home)
        self.interfaces["图片转 PDF"] = self.image_pdf_interface

        # 4. 文本工具组
        self.text_home = self.createCategoryInterface("文本工具箱", "text_home")
        self.addSubInterface(self.text_home, self.get_icon("assets/icons/text.svg"), "文本工具")

        # 4.1 Markdown 转 PDF
        self.markdown_interface = MarkdownInterface(self)
        self.addSubInterface(self.markdown_interface, self.get_icon("assets/icons/markdown.svg"), "Markdown 转 PDF", parent=self.text_home)
        self.interfaces["Markdown 转 PDF"] = self.markdown_interface

        # 4.2 TXT 转 PDF
        self.txt_pdf_interface = TxtPdfInterface(self)
        self.addSubInterface(self.txt_pdf_interface, self.get_icon("assets/icons/text.svg"), "TXT 转 PDF", parent=self.text_home)
        self.interfaces["TXT 转 PDF"] = self.txt_pdf_interface

        # 4.3 代码提取
        self.code_extract_interface = CodeExtractInterface(self)
        self.addSubInterface(self.code_extract_interface, self.get_icon("assets/icons/code.svg"), "代码提取", parent=self.text_home)
        self.interfaces["代码提取"] = self.code_extract_interface

        # 5. 设置界面 (底部)
        self.settings_interface = SettingsInterface(self)
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
