from PyQt6.QtCore import Qt, QSize, QTimer, QRectF, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QIconEngine
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QCompleter
from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import (FluentWindow, NavigationItemPosition, SearchLineEdit, 
                          isDarkTheme, TitleLabel, qconfig, NavigationAvatarWidget,
                          NavigationDisplayMode)

class NavigationSearchLineEdit(SearchLineEdit):
    """支持在导航栏中使用的搜索框"""
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 搜索框不需要被选中样式，但需要满足接口要求

    def setSelected(self, isSelected):
        # 必须实现此方法以满足 NavigationInterface 接口
        pass

from core.utils.lazy_loader import UILazyLoader
from core.utils.resource_path import get_resource_path
from core.utils.icon_provider import ThemedSvgIconEngine
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
        
        # 初始隐藏搜索框（默认收起状态）
        self.search_box.hide()
        
        # 监听导航栏显示模式变化
        self.navigationInterface.displayModeChanged.connect(self.on_display_mode_changed)

    def on_display_mode_changed(self, mode: NavigationDisplayMode):
        """导航栏显示模式变化响应"""
        # 只有在展开模式或菜单模式下才显示搜索框
        if mode == NavigationDisplayMode.EXPAND or mode == NavigationDisplayMode.MENU:
            self.search_box.show()
        else:
            self.search_box.hide()

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
            "Word ↔ Markdown": "Word 文档与 Markdown 互转",
            "LibreOffice 格式转换": "批量转换办公文档格式 (ODT↔DOCX, ODS↔XLSX)",
            
            # PDF 工具
            "PDF 合并": "将多个 PDF 文件合并为一个",
            "PDF 压缩": "压缩 PDF 文件大小",
            "PDF 拆分/提取": "拆分或提取 PDF 页面",
            "PDF 图片提取": "从 PDF 中提取所有图片",
            "PDF 页面渲染": "将 PDF 页面渲染为高清图片",
            
            # 图片工具
            "图片取色": "提取图片中的主要颜色",
            "PNG 转 SVG": "将 PNG 图片转为矢量 SVG",
            "图片格式转换": "在多种图片格式间转换",
            "图片转 PDF": "将图片转换为 PDF 文档",
            "图片去水印": "移除 AI 生成图片的水印（当前支持 Gemini）",
            
            # 文本工具
            "Markdown 转 PDF": "将 Markdown 文档转为 PDF",
            "Markdown ↔ HTML": "Markdown 与 HTML 格式互转",
            "Markdown 批量转 PDF": "批量转换 Markdown 文档为 PDF (支持数学公式)",
            "TXT 转 PDF": "将文本文件转换为 PDF",
            "代码提取": "从文件中提取代码块",
            
            # 实用工具
            "批量重命名": "支持模板变量的批量文件重命名工具",
            "剪贴板图片助手": "快速查看、保存剪贴板图片，或复制图片到剪贴板"
        }

    def initNavigation(self):
        # 添加搜索框到导航栏顶部
        self.search_box = NavigationSearchLineEdit()
        self.search_box.setPlaceholderText("搜索功能")
        self.search_box.setFixedWidth(180) # 设置宽度以适应展开状态
        
        # 初始化搜索补全
        self.initSearch()
        
        # 将搜索框添加到导航栏
        # 注意：SearchLineEdit 默认会根据导航栏展开状态调整显示
        # 我们把它添加到导航栏的最顶部 (position=NavigationItemPosition.TOP)
        self.navigationInterface.addWidget(
            routeKey="search_box",
            widget=self.search_box,
            onClick=self.on_search_clicked,
            position=NavigationItemPosition.TOP
        )
        
        # 添加分隔符
        self.navigationInterface.addSeparator()

        # 1. Office 转换组
        self.office_home = self.createCategoryInterface("Office 工具", "office_home")
        self.icon_mapping["office_home"] = get_resource_path("assets/icons/presentation.svg")
        self.addSubInterface(self.office_home, self.get_icon(get_resource_path("assets/icons/presentation.svg")), "Office 转换")

        # 1.1 PPT 转 PDF（添加到stackedWidget但不在导航栏显示）
        self.ppt_interface = UILazyLoader("ui.interfaces.office.ppt_interface", "PPTInterface", self)
        self.stackedWidget.addWidget(self.ppt_interface)
        self.interfaces["PPT 转 PDF"] = self.ppt_interface

        # 1.2 PPT 转图片
        self.ppt_img_interface = UILazyLoader("ui.interfaces.office.ppt_image_interface", "PPTImageInterface", self)
        self.stackedWidget.addWidget(self.ppt_img_interface)
        self.interfaces["PPT 转图片"] = self.ppt_img_interface

        # 1.3 Word 转 PDF
        self.word_interface = UILazyLoader("ui.interfaces.office.word_interface", "WordInterface", self)
        self.stackedWidget.addWidget(self.word_interface)
        self.interfaces["Word 转 PDF"] = self.word_interface

        # 1.4 Doc 转 Docx
        self.doc_to_docx_interface = UILazyLoader("ui.interfaces.office.doc_to_docx_interface", "DocToDocxInterface", self)
        self.stackedWidget.addWidget(self.doc_to_docx_interface)
        self.interfaces["Doc 转 Docx"] = self.doc_to_docx_interface

        # 1.5 Excel 转 PDF
        self.excel_interface = UILazyLoader("ui.interfaces.office.excel_interface", "ExcelInterface", self)
        self.stackedWidget.addWidget(self.excel_interface)
        self.interfaces["Excel 转 PDF"] = self.excel_interface

        # 1.6 Word ↔ Markdown
        self.word_markdown_interface = UILazyLoader("ui.interfaces.office.word_markdown_interface", "WordMarkdownInterface", self)
        self.stackedWidget.addWidget(self.word_markdown_interface)
        self.interfaces["Word ↔ Markdown"] = self.word_markdown_interface

        # 1.7 LibreOffice 格式转换
        self.libreoffice_batch_interface = UILazyLoader("ui.interfaces.office.libreoffice_batch_interface", "LibreOfficeBatchInterface", self)
        self.stackedWidget.addWidget(self.libreoffice_batch_interface)
        self.interfaces["LibreOffice 格式转换"] = self.libreoffice_batch_interface

        # 2. PDF 处理组
        self.pdf_home = self.createCategoryInterface("PDF 工具箱", "pdf_home")
        self.icon_mapping["pdf_home"] = get_resource_path("assets/icons/pdf.svg")
        self.addSubInterface(self.pdf_home, self.get_icon(get_resource_path("assets/icons/pdf.svg")), "PDF 处理")

        # 2.1 PDF 合并
        self.pdf_merge_interface = UILazyLoader("ui.interfaces.pdf.pdf_merge_interface", "PDFMergeInterface", self)
        self.stackedWidget.addWidget(self.pdf_merge_interface)
        self.interfaces["PDF 合并"] = self.pdf_merge_interface

        # 2.2 PDF 压缩
        self.compress_interface = UILazyLoader("ui.interfaces.pdf.pdf_compress_interface", "PDFCompressInterface", self, container=self.container)
        self.stackedWidget.addWidget(self.compress_interface)
        self.interfaces["PDF 压缩"] = self.compress_interface

        # 2.3 PDF 拆分/提取
        self.pdf_split_interface = UILazyLoader("ui.interfaces.pdf.pdf_split_interface", "PDFSplitInterface", self)
        self.stackedWidget.addWidget(self.pdf_split_interface)
        self.interfaces["PDF 拆分/提取"] = self.pdf_split_interface

        # 2.4 PDF 图片提取
        self.pdf_img_extract_interface = UILazyLoader("ui.interfaces.pdf.pdf_image_extract_interface", "PDFImageExtractInterface", self)
        self.stackedWidget.addWidget(self.pdf_img_extract_interface)
        self.interfaces["PDF 图片提取"] = self.pdf_img_extract_interface

        # 2.5 PDF 页面渲染
        self.pdf_render_interface = UILazyLoader("ui.interfaces.pdf.pdf_render_interface", "PDFRenderInterface", self)
        self.stackedWidget.addWidget(self.pdf_render_interface)
        self.interfaces["PDF 页面渲染"] = self.pdf_render_interface
        
        # 3. 图片工具组
        self.image_home = self.createCategoryInterface("图片工具箱", "image_home")
        self.icon_mapping["image_home"] = get_resource_path("assets/icons/image.svg")
        self.addSubInterface(self.image_home, self.get_icon(get_resource_path("assets/icons/image.svg")), "图片工具")

        # 3.1 图片取色
        self.color_interface = UILazyLoader("ui.interfaces.image.color_interface", "ColorInterface", self)
        self.stackedWidget.addWidget(self.color_interface)
        self.interfaces["图片取色"] = self.color_interface

        # 3.2 PNG 转 SVG
        self.image_vector_interface = UILazyLoader("ui.interfaces.image.image_vector_interface", "ImageVectorInterface", self)
        self.stackedWidget.addWidget(self.image_vector_interface)
        self.interfaces["PNG 转 SVG"] = self.image_vector_interface

        # 3.3 图片格式转换
        self.image_convert_interface = UILazyLoader("ui.interfaces.image.image_convert_interface", "ImageConvertInterface", self)
        self.stackedWidget.addWidget(self.image_convert_interface)
        self.interfaces["图片格式转换"] = self.image_convert_interface

        # 3.4 图片转 PDF
        self.image_pdf_interface = UILazyLoader("ui.interfaces.image.image_pdf_interface", "ImagePdfInterface", self)
        self.stackedWidget.addWidget(self.image_pdf_interface)
        self.interfaces["图片转 PDF"] = self.image_pdf_interface

        # 3.5 图片去水印
        self.watermark_remove_interface = UILazyLoader("ui.interfaces.image.watermark_remove_interface", "WatermarkRemoveInterface", self)
        self.stackedWidget.addWidget(self.watermark_remove_interface)
        self.interfaces["图片去水印"] = self.watermark_remove_interface

        # 4. 文本工具组
        self.text_home = self.createCategoryInterface("文本工具箱", "text_home")
        self.icon_mapping["text_home"] = get_resource_path("assets/icons/text.svg")
        self.addSubInterface(self.text_home, self.get_icon(get_resource_path("assets/icons/text.svg")), "文本工具")

        # 4.1 Markdown 转 PDF
        self.markdown_interface = UILazyLoader("ui.interfaces.text.markdown_interface", "MarkdownInterface", self, container=self.container)
        self.stackedWidget.addWidget(self.markdown_interface)
        self.interfaces["Markdown 转 PDF"] = self.markdown_interface

        # 4.2 TXT 转 PDF
        self.txt_pdf_interface = UILazyLoader("ui.interfaces.text.txt_pdf_interface", "TxtPdfInterface", self)
        self.stackedWidget.addWidget(self.txt_pdf_interface)
        self.interfaces["TXT 转 PDF"] = self.txt_pdf_interface

        # 4.3 代码提取
        self.code_extract_interface = UILazyLoader("ui.interfaces.text.code_extract_interface", "CodeExtractInterface", self)
        self.stackedWidget.addWidget(self.code_extract_interface)
        self.interfaces["代码提取"] = self.code_extract_interface

        # 4.4 Markdown ↔ HTML
        self.markdown_html_interface = UILazyLoader("ui.interfaces.text.markdown_html_interface", "MarkdownHtmlInterface", self)
        self.stackedWidget.addWidget(self.markdown_html_interface)
        self.interfaces["Markdown ↔ HTML"] = self.markdown_html_interface

        # 4.5 Markdown 批量转 PDF
        self.markdown_pdf_batch_interface = UILazyLoader("ui.interfaces.text.markdown_pdf_batch_interface", "MarkdownPdfBatchInterface", self)
        self.stackedWidget.addWidget(self.markdown_pdf_batch_interface)
        self.interfaces["Markdown 批量转 PDF"] = self.markdown_pdf_batch_interface

        # 5. 实用工具组
        self.utils_home = self.createCategoryInterface("实用工具箱", "utils_home")
        self.icon_mapping["utils_home"] = get_resource_path("assets/icons/magic.svg")
        self.addSubInterface(self.utils_home, self.get_icon(get_resource_path("assets/icons/magic.svg")), "实用工具")

        # 5.1 批量重命名
        self.batch_rename_interface = UILazyLoader("ui.interfaces.utils.batch_rename_interface", "BatchRenameInterface", self)
        self.stackedWidget.addWidget(self.batch_rename_interface)
        self.interfaces["批量重命名"] = self.batch_rename_interface

        # 5.2 剪贴板图片助手
        self.clipboard_interface = UILazyLoader("ui.interfaces.utils.clipboard_interface", "ClipboardInterface", self)
        self.stackedWidget.addWidget(self.clipboard_interface)
        self.interfaces["剪贴板图片助手"] = self.clipboard_interface

        # 6. 设置界面 (底部)
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

    def initSearch(self):
        """初始化搜索功能"""
        # 获取所有功能名称
        items = list(self.feature_descriptions.keys())
        
        # 设置补全器
        completer = QCompleter(items, self.search_box)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setMaxVisibleItems(10)
        
        # 连接搜索框
        self.search_box.setCompleter(completer)
        # 处理回车或选中
        self.search_box.returnPressed.connect(self.on_search_complete)
        completer.activated.connect(self.on_search_complete)

    def on_search_clicked(self):
        # 搜索框点击时不进行页面切换，仅保持焦点
        self.search_box.setFocus()

    def on_search_complete(self, text=None):
        """搜索完成处理"""
        if not text:
            text = self.search_box.text()
            
        if text in self.feature_descriptions:
            # 跳转到对应功能
            feature_name = text
            if feature_name in self.interfaces:
                self.switchTo(self.interfaces[feature_name])
                # 清空搜索框
                self.search_box.clear()
                # 自动收起侧边栏（使用 panel.collapse() 方法）
                self.navigationInterface.panel.collapse()

    def createCategoryInterface(self, text, objectName):
        """创建分类界面的辅助函数（返回卡片首页）"""
        # 收集该分类下的所有功能
        features = []
        category_mapping = {
            "office_home": ["PPT 转 PDF", "PPT 转图片", "Word 转 PDF", "Doc 转 Docx", "Excel 转 PDF", "Word ↔ Markdown", "LibreOffice 格式转换"],
            "pdf_home": ["PDF 合并", "PDF 压缩", "PDF 拆分/提取", "PDF 图片提取", "PDF 页面渲染"],
            "image_home": ["图片取色", "PNG 转 SVG", "图片格式转换", "图片转 PDF", "图片去水印"],
            "text_home": ["Markdown 转 PDF", "Markdown ↔ HTML", "Markdown 批量转 PDF", "TXT 转 PDF", "代码提取"],
            "utils_home": ["批量重命名", "剪贴板图片助手"]
        }
        
        # 图标映射（与实际界面的图标保持一致）
        icon_mapping_dict = {
            "PPT 转 PDF": "presentation.svg",
            "PPT 转图片": "image.svg",
            "Word 转 PDF": "word.svg",
            "Doc 转 Docx": "word.svg",
            "Excel 转 PDF": "excel.svg",
            "Word ↔ Markdown": "markdown.svg",
            "LibreOffice 格式转换": "convert.svg",
            "PDF 合并": "merge.svg",
            "PDF 压缩": "compress.svg",
            "PDF 拆分/提取": "split.svg",
            "PDF 图片提取": "image.svg",
            "PDF 页面渲染": "convert.svg",
            "图片取色": "color_picker.svg",
            "PNG 转 SVG": "vector.svg",
            "图片格式转换": "convert.svg",
            "图片转 PDF": "pdf.svg",
            "图片去水印": "eraser.svg",
            "Markdown 转 PDF": "markdown.svg",
            "Markdown ↔ HTML": "markdown.svg",
            "Markdown 批量转 PDF": "markdown.svg",
            "TXT 转 PDF": "text.svg",
            "代码提取": "code.svg",
            "批量重命名": "magic.svg",
            "剪贴板图片助手": "image.svg"
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
