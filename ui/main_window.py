from PyQt6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, FluentIcon as FIF, NavigationItemPosition

from ui.interfaces import (
    PPTInterface, PPTImageInterface, WordInterface, ExcelInterface, PDFMergeInterface, PDFCompressInterface,
    PDFSplitInterface, PDFImageExtractInterface, ColorInterface, MarkdownInterface,
    ImageVectorInterface, ImageConvertInterface, ImagePdfInterface, TxtPdfInterface, CodeExtractInterface, SettingsInterface
)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Office Tool")
        self.resize(900, 700)
        self.setMinimumSize(800, 600)
        
        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width()-self.width())//2, (screen.height()-self.height())//2)

        # 1. PPT 转换界面
        self.ppt_interface = PPTInterface(self)
        self.addSubInterface(self.ppt_interface, FIF.TILES, "PPT 转 PDF")

        # 1.1 PPT 转图片
        self.ppt_img_interface = PPTImageInterface(self)
        self.addSubInterface(self.ppt_img_interface, FIF.PHOTO, "PPT 转图片")

        # 2. Word 转换界面
        self.word_interface = WordInterface(self)
        self.addSubInterface(self.word_interface, FIF.DOCUMENT, "Word 转 PDF")

        # 3. Excel 转换界面
        self.excel_interface = ExcelInterface(self)
        self.addSubInterface(self.excel_interface, FIF.TILES, "Excel 转 PDF")

        # 4. PDF 合并界面
        self.pdf_merge_interface = PDFMergeInterface(self)
        self.addSubInterface(self.pdf_merge_interface, FIF.FOLDER, "PDF 合并")

        # 5. PDF 压缩界面
        self.compress_interface = PDFCompressInterface(self)
        self.addSubInterface(self.compress_interface, FIF.ZIP_FOLDER, "PDF 压缩")

        # 6. PDF 拆分界面
        self.pdf_split_interface = PDFSplitInterface(self)
        self.addSubInterface(self.pdf_split_interface, FIF.CUT, "PDF 拆分/提取")

        # 7. PDF 图片提取界面
        self.pdf_img_extract_interface = PDFImageExtractInterface(self)
        self.addSubInterface(self.pdf_img_extract_interface, FIF.PHOTO, "PDF 图片提取")

        # 8. 图片取色界面
        self.color_interface = ColorInterface(self)
        self.addSubInterface(self.color_interface, FIF.PALETTE, "图片取色")

        # 9. Markdown 转 PDF
        self.markdown_interface = MarkdownInterface(self)
        self.addSubInterface(self.markdown_interface, FIF.EDIT, "Markdown 转 PDF")

        # 10. PNG 转 SVG
        self.image_vector_interface = ImageVectorInterface(self)
        self.addSubInterface(self.image_vector_interface, FIF.PHOTO, "PNG 转 SVG")

        # 11. TXT 转 PDF
        self.txt_pdf_interface = TxtPdfInterface(self)
        self.addSubInterface(self.txt_pdf_interface, FIF.DOCUMENT, "TXT 转 PDF")

        # 12. 代码提取
        self.code_extract_interface = CodeExtractInterface(self)
        self.addSubInterface(self.code_extract_interface, FIF.CODE, "代码提取")

        # 13. 图片格式转换
        self.image_convert_interface = ImageConvertInterface(self)
        self.addSubInterface(self.image_convert_interface, FIF.PHOTO, "图片格式转换")

        # 14. 图片转 PDF
        self.image_pdf_interface = ImagePdfInterface(self)
        self.addSubInterface(self.image_pdf_interface, FIF.DOCUMENT, "图片转 PDF")

        # 15. 设置界面
        self.settings_interface = SettingsInterface(self)
        self.addSubInterface(self.settings_interface, FIF.SETTING, "设置", position=NavigationItemPosition.BOTTOM)

        self.navigationInterface.setCurrentItem(self.ppt_interface.objectName())
