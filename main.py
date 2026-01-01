import sys
import os

import markdown
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QListWidget, QAbstractItemView, QFrame, QScrollArea, QGridLayout, QLabel, QSplitter, QCheckBox, QGroupBox

from qfluentwidgets import (FluentWindow, SubtitleLabel, PrimaryPushButton, 
                            PushButton, ProgressBar, TextEdit, InfoBar, 
                            BodyLabel, FluentIcon as FIF, CardWidget, IconWidget,
                            LineEdit, ToolButton, ComboBox, Slider, StrongBodyLabel, CheckBox)
from PyQt6.QtCore import QSettings

from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent, QPixmap, QColor

from core.ppt_converter import PPTConverter
from core.pdf_merger import PDFMerger
from core.word_converter import WordConverter
from core.pdf_compressor import PDFCompressor
from core.color_extractor import ColorExtractor
from core.image_vectorizer import ImageVectorizer
from core.txt_converter import TxtConverter
from core.code_extractor import CodeExtractor
from core.environment_checker import EnvironmentChecker

class ImageVectorThread(QThread):
    def __init__(self, vectorizer, input_path, output_path, **kwargs):
        super().__init__()
        self.vectorizer = vectorizer
        self.input_path = input_path
        self.output_path = output_path
        self.kwargs = kwargs

    def run(self):
        self.vectorizer.convert(self.input_path, self.output_path, **self.kwargs)

class TxtPdfThread(QThread):
    def __init__(self, converter, files, output_dir):
        super().__init__()
        self.converter = converter
        self.files = files
        self.output_dir = output_dir

    def run(self):
        self.converter.convert(self.files, self.output_dir)

class CodeExtractThread(QThread):
    def __init__(self, extractor, root_dir, extensions, output_path):
        super().__init__()
        self.extractor = extractor
        self.root_dir = root_dir
        self.extensions = extensions
        self.output_path = output_path

    def run(self):
        self.extractor.extract(self.root_dir, self.extensions, self.output_path)

class ExtractionThread(QThread):
    def __init__(self, extractor, path, n_colors):
        super().__init__()
        self.extractor = extractor
        self.path = path
        self.n_colors = n_colors

    def run(self):
        self.extractor.extract(self.path, self.n_colors)

class ConversionThread(QThread):
    def __init__(self, converter, files):
        super().__init__()
        self.converter = converter
        self.files = files

    def run(self):
        self.converter.convert(self.files)

class MergeThread(QThread):
    def __init__(self, merger, files, output_path):
        super().__init__()
        self.merger = merger
        self.files = files
        self.output_path = output_path

    def run(self):
        self.merger.merge(self.files, self.output_path)

class CompressThread(QThread):
    def __init__(self, compressor, files, quality, gs_path):
        super().__init__()
        self.compressor = compressor
        self.files = files
        self.quality = quality
        self.gs_path = gs_path

    def run(self):
        self.compressor.compress(self.files, self.quality, self.gs_path)

class DragDropListWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        
        # 美化样式
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
                outline: none;
            }
            QListWidget::item {
                height: 36px;
                padding-left: 10px;
                margin: 2px 4px;
                border-radius: 4px;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.04);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 0, 0, 0.08);
                color: #000000;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path): files.append(path)
        if files: self.files_dropped.emit(files)

class WordInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("word_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("Word 转 PDF", self)
        self.desc = BodyLabel("批量转换 Word 文件 (需安装 MS Word)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        self.card = CardWidget(self)
        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 10, 20, 10)

        self.icon = IconWidget(FIF.TILES)
        self.icon.setFixedSize(48, 48)
        self.tip = BodyLabel("请添加文件 (支持拖拽)...")
        self.tip.setFont(QFont("Microsoft YaHei", 12))

        self.add_btn = PrimaryPushButton(FIF.ADD, "添加文件", self)
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)

        self.card_layout.addWidget(self.icon)
        self.card_layout.addSpacing(15)
        self.card_layout.addWidget(self.tip)
        self.card_layout.addStretch(1)
        self.card_layout.addWidget(self.add_btn)
        self.card_layout.addWidget(self.clear_btn)

        self.vbox.addWidget(self.card)

        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(15)
        
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
                color: #555555;
            }
        """)
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        
        self.vbox.addLayout(self.content_layout)

        self.bottom_layout = QHBoxLayout()
        
        self.progress = ProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.hide()
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.setFixedWidth(200)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.start_btn)
        
        self.vbox.addLayout(self.bottom_layout)

        self.files = []
        self.converter = WordConverter()
        self.thread = None

        self.converter.log.connect(self.append_log)
        self.converter.progress.connect(self.update_progress)
        self.converter.finished.connect(self.on_finished)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选文件", "", "Word (*.doc *.docx)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        count = 0
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext in ['.doc', '.docx']:
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
                    count += 1
        if count > 0:
            self.tip.setText(f"已选 {len(self.files)} 个文件")
            self.start_btn.setEnabled(True)

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.tip.setText("请添加文件 (支持拖拽)...")
        self.start_btn.setEnabled(False)
        self.progress.hide()
        self.log_text.clear()

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_progress(self, curr, total, name):
        self.progress.show()
        self.progress.setMaximum(total)
        self.progress.setValue(curr)
        self.start_btn.setText(f"处理中... ({curr}/{total})")

    def start_conversion(self):
        if not self.files: return
        self.start_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.list_widget.setEnabled(False)
        self.log_text.clear()
        self.thread = ConversionThread(self.converter, self.files)
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.list_widget.setEnabled(True)
        self.start_btn.setText("开始转换")
        self.progress.hide()
        if fail > 0: InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
        else: InfoBar.success("完成", f"成功 {success}", duration=3000, parent=self)


class PPTInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ppt_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("PowerPoint 转 PDF", self)
        self.desc = BodyLabel("批量转换 PPT 文件 (需安装 MS PowerPoint)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        self.card = CardWidget(self)
        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 10, 20, 10)

        self.icon = IconWidget(FIF.TILES)
        self.icon.setFixedSize(48, 48)
        self.tip = BodyLabel("请添加文件 (支持拖拽)...")
        self.tip.setFont(QFont("Microsoft YaHei", 12))

        self.add_btn = PrimaryPushButton(FIF.ADD, "添加文件", self)
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)

        self.card_layout.addWidget(self.icon)
        self.card_layout.addSpacing(15)
        self.card_layout.addWidget(self.tip)
        self.card_layout.addStretch(1)
        self.card_layout.addWidget(self.add_btn)
        self.card_layout.addWidget(self.clear_btn)

        self.vbox.addWidget(self.card)

        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(15)
        
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
                color: #555555;
            }
        """)
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        
        self.vbox.addLayout(self.content_layout)

        self.bottom_layout = QHBoxLayout()
        
        self.progress = ProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.hide()
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.setFixedWidth(200)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.start_btn)
        
        self.vbox.addLayout(self.bottom_layout)

        self.files = []
        self.converter = PPTConverter()
        self.thread = None

        self.converter.log.connect(self.append_log)
        self.converter.progress.connect(self.update_progress)
        self.converter.finished.connect(self.on_finished)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选文件", "", "PPT (*.ppt *.pptx)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        count = 0
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext in ['.ppt', '.pptx']:
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
                    count += 1
        if count > 0:
            self.tip.setText(f"已选 {len(self.files)} 个文件")
            self.start_btn.setEnabled(True)

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.tip.setText("请添加文件 (支持拖拽)...")
        self.start_btn.setEnabled(False)
        self.progress.hide()
        self.log_text.clear()

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_progress(self, curr, total, name):
        self.progress.show()
        self.progress.setMaximum(total)
        self.progress.setValue(curr)
        self.start_btn.setText(f"处理中... ({curr}/{total})")

    def start_conversion(self):
        if not self.files: return
        self.start_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.list_widget.setEnabled(False)
        self.log_text.clear()
        self.thread = ConversionThread(self.converter, self.files)
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.list_widget.setEnabled(True)
        self.start_btn.setText("开始转换")
        self.progress.hide()
        if fail > 0: InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
        else: InfoBar.success("完成", f"成功 {success}", duration=3000, parent=self)


class PDFCompressInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("pdf_compress_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("PDF 压缩工具", self)
        self.desc = BodyLabel("使用 Ghostscript 压缩 PDF 文件体积", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QVBoxLayout(self.settings_card)
        self.settings_layout.setContentsMargins(20, 20, 20, 20)

        # GS 路径行
        self.gs_layout = QHBoxLayout()
        self.gs_label = BodyLabel("GS 路径:", self)
        self.gs_edit = LineEdit(self)
        self.gs_edit.setPlaceholderText("请选择 gswin64c.exe 路径...")
        self.gs_browse = PushButton(FIF.FOLDER, "浏览", self)
        self.gs_browse.clicked.connect(self.browse_gs)
        
        self.gs_layout.addWidget(self.gs_label)
        self.gs_layout.addWidget(self.gs_edit)
        self.gs_layout.addWidget(self.gs_browse)
        
        # GS 环境检测行
        self.env_layout = QHBoxLayout()
        self.check_env_btn = PushButton(FIF.SEARCH, "检测环境", self)
        self.check_env_btn.clicked.connect(self.check_gs_env)
        
        self.env_status = BodyLabel("", self)
        
        self.download_btn = PushButton(FIF.DOWNLOAD, "下载 Ghostscript", self)
        self.download_btn.clicked.connect(lambda: os.startfile(EnvironmentChecker.get_gs_download_url()) if os.name == 'nt' else None)
        self.download_btn.hide()
        
        self.env_layout.addWidget(self.check_env_btn)
        self.env_layout.addWidget(self.env_status)
        self.env_layout.addWidget(self.download_btn)
        self.env_layout.addStretch(1)

        # 质量选择行
        self.quality_layout = QHBoxLayout()
        self.quality_label = BodyLabel("压缩质量:", self)
        self.quality_combo = ComboBox(self)
        self.quality_combo.addItems(['/screen (屏幕 - 最小)', '/ebook (电子书 - 中等)', '/printer (打印 - 较高)', '/prepress (印前 - 最高)', '/default (默认)'])
        self.quality_combo.setCurrentIndex(2) # 默认 printer
        self.quality_layout.addWidget(self.quality_label)
        self.quality_layout.addWidget(self.quality_combo)
        self.quality_layout.addStretch(1)

        self.settings_layout.addLayout(self.gs_layout)
        self.settings_layout.addSpacing(5)
        self.settings_layout.addLayout(self.env_layout) # 添加检测行
        self.settings_layout.addSpacing(10)
        self.settings_layout.addLayout(self.quality_layout)
        
        self.vbox.addWidget(self.settings_card)

        # 工具栏
        self.toolbar = QHBoxLayout()
        self.add_btn = PrimaryPushButton(FIF.ADD, "添加文件", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        self.toolbar.addWidget(self.add_btn)
        self.toolbar.addWidget(self.clear_btn)
        self.toolbar.addStretch(1)
        self.vbox.addLayout(self.toolbar)

        # 列表与日志
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 底部
        self.bottom_layout = QHBoxLayout()
        self.progress = ProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.hide()
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始压缩", self)
        self.start_btn.clicked.connect(self.start_compression)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)

        # 初始化
        self.files = []
        self.compressor = PDFCompressor()
        self.thread = None
        self.settings = QSettings("AI_Office_Tool", "Config")

        # 加载 GS 路径
        last_gs = self.settings.value("gs_path", "")
        if not last_gs:
            # 尝试一些默认路径
            candidates = [
                r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe",
                r"C:\Program Files\gs\gs10.00.0\bin\gswin64c.exe",
            ]
            for c in candidates:
                if os.path.exists(c):
                    last_gs = c
                    break
        self.gs_edit.setText(last_gs)

        self.compressor.log.connect(self.append_log)
        self.compressor.progress.connect(self.update_progress)
        self.compressor.finished.connect(self.on_finished)

    def check_gs_env(self):
        self.env_status.setText("正在搜索...")
        self.download_btn.hide()
        QApplication.processEvents()
        
        result = EnvironmentChecker.find_ghostscript()
        if result['found']:
            self.env_status.setText(f"✅ 已检测到: {result.get('version', '未知版本')}")
            self.env_status.setTextColor("#009900", "#00cc00") # Green
            self.gs_edit.setText(result['path'])
            self.settings.setValue("gs_path", result['path'])
            self.check_state()
        else:
            self.env_status.setText("❌ 未检测到 Ghostscript")
            self.env_status.setTextColor("#cc0000", "#ff3333") # Red
            self.download_btn.show()

    def browse_gs(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 gswin64c.exe", "", "Executable (*.exe)")
        if path:
            self.gs_edit.setText(path)
            self.settings.setValue("gs_path", path)
            self.check_state()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF (*.pdf)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        count = 0
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext == '.pdf':
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
                    count += 1
        self.check_state()

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.check_state()

    def check_state(self):
        has_files = len(self.files) > 0
        has_gs = os.path.exists(self.gs_edit.text())
        self.start_btn.setEnabled(has_files and has_gs)

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_progress(self, curr, total, msg):
        self.progress.show()
        self.progress.setMaximum(total)
        self.progress.setValue(curr)
        self.start_btn.setText(f"处理中... ({curr}/{total})")

    def start_compression(self):
        gs_path = self.gs_edit.text()
        if not os.path.exists(gs_path):
            InfoBar.error("错误", "Ghostscript 路径无效", parent=self)
            return
            
        quality = self.quality_combo.currentText().split(' ')[0]
        
        self.start_btn.setEnabled(False)
        self.thread = CompressThread(self.compressor, self.files, quality, gs_path)
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始压缩")
        self.progress.hide()
        InfoBar.success("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)

class PDFMergeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("pdf_merge_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        # 标题区域
        self.title = SubtitleLabel("PDF 合并工具", self)
        self.desc = BodyLabel("将多个 PDF 文件合并为一个，支持拖拽排序", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 工具栏区域 (添加文件, 清空, 排序)
        self.toolbar_layout = QHBoxLayout()
        
        self.add_btn = PrimaryPushButton(FIF.ADD, "添加 PDF", self)
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空列表", self)
        self.clear_btn.clicked.connect(self.clear_files)

        self.toolbar_layout.addWidget(self.add_btn)
        self.toolbar_layout.addWidget(self.clear_btn)
        self.toolbar_layout.addStretch(1)

        self.up_btn = ToolButton(FIF.UP, self)
        self.up_btn.setToolTip("上移")
        self.up_btn.clicked.connect(self.move_up)
        
        self.down_btn = ToolButton(FIF.DOWN, self)
        self.down_btn.setToolTip("下移")
        self.down_btn.clicked.connect(self.move_down)
        
        self.remove_btn = ToolButton(FIF.REMOVE, self)
        self.remove_btn.setToolTip("移除选中")
        self.remove_btn.clicked.connect(self.remove_selected)

        self.toolbar_layout.addWidget(self.up_btn)
        self.toolbar_layout.addSpacing(5)
        self.toolbar_layout.addWidget(self.down_btn)
        self.toolbar_layout.addSpacing(15)
        self.toolbar_layout.addWidget(self.remove_btn)

        self.vbox.addLayout(self.toolbar_layout)

        # 主要内容区域 (列表 + 日志)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(15)
        
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
                color: #555555;
            }
        """)
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 底部区域 (输出路径 + 开始按钮)
        self.bottom_layout = QHBoxLayout()
        
        self.out_label = BodyLabel("输出文件:", self)
        self.out_edit = LineEdit(self)
        self.out_edit.setPlaceholderText("选择或输入保存路径...")
        
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始合并", self)
        self.start_btn.clicked.connect(self.start_merge)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.out_label)
        self.bottom_layout.addWidget(self.out_edit)
        self.bottom_layout.addWidget(self.browse_btn)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.start_btn)
        
        self.vbox.addLayout(self.bottom_layout)
        
        # 进度条
        self.progress = ProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.hide()
        self.vbox.addWidget(self.progress)

        # 逻辑初始化
        self.files = [] # 存储完整路径
        self.merger = PDFMerger()
        self.thread = None

        self.merger.log.connect(self.append_log)
        self.merger.progress.connect(self.update_progress)
        self.merger.finished.connect(self.on_finished)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 PDF 文件", "", "PDF (*.pdf)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext == '.pdf':
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
        self.check_state()

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.progress.hide()
        self.check_state()

    def remove_selected(self):
        # 从后往前删，避免索引偏移
        rows = sorted([item.row() for item in self.list_widget.selectedIndexes()], reverse=True)
        for row in rows:
            self.files.pop(row)
            self.list_widget.takeItem(row)
        self.check_state()

    def move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            # 数据交换
            self.files[row], self.files[row-1] = self.files[row-1], self.files[row]
            # 列表项交换
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row-1, item)
            self.list_widget.setCurrentRow(row-1)

    def move_down(self):
        row = self.list_widget.currentRow()
        if row < len(self.files) - 1 and row != -1:
            self.files[row], self.files[row+1] = self.files[row+1], self.files[row]
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row+1, item)
            self.list_widget.setCurrentRow(row+1)

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存合并文件", "merged_output.pdf", "PDF (*.pdf)")
        if path:
            self.out_edit.setText(path)
            self.check_state()

    def check_state(self):
        has_files = len(self.files) > 0
        has_out = bool(self.out_edit.text().strip())
        self.start_btn.setEnabled(has_files and has_out)
        
        if has_files and not has_out and not self.out_edit.text():
            # 自动生成一个默认路径
            dir_name = os.path.dirname(self.files[0])
            self.out_edit.setText(os.path.join(dir_name, "merged_output.pdf"))
            self.start_btn.setEnabled(True)

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_progress(self, curr, total, msg):
        self.progress.show()
        self.progress.setMaximum(total)
        self.progress.setValue(curr)
        self.start_btn.setText(f"处理中... {curr}/{total}")

    def start_merge(self):
        output_path = self.out_edit.text().strip()
        if not output_path or not self.files: return
        
        self.start_btn.setEnabled(False)
        self.list_widget.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.log_text.clear()
        
        self.thread = MergeThread(self.merger, self.files, output_path)
        self.thread.start()

    def on_finished(self, success, msg):
        self.start_btn.setEnabled(True)
        self.list_widget.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.start_btn.setText("开始合并")
        self.progress.hide()
        
        if success:
            InfoBar.success("成功", msg, duration=3000, parent=self)
        else:
            InfoBar.error("错误", msg, duration=5000, parent=self)

class DropImageWidget(CardWidget):
    image_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(150)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon = IconWidget(FIF.PHOTO)
        self.icon.setFixedSize(48, 48)
        
        self.label = BodyLabel("拖拽图片到此处，或点击选择")
        self.label.setFont(QFont("Microsoft YaHei", 12))
        
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.image_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.image_dropped.emit(path)
                return

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

class ColorInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("color_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("图片色调提取", self)
        self.desc = BodyLabel("提取图片中的主色调并生成配色方案", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 拖拽区域
        self.drop_area = DropImageWidget(self)
        self.drop_area.image_dropped.connect(self.start_extraction)
        self.vbox.addWidget(self.drop_area)

        # 设置栏
        self.settings_layout = QHBoxLayout()
        self.slider_label = BodyLabel("提取数量: 8")
        self.slider = Slider(Qt.Orientation.Horizontal)
        self.slider.setRange(2, 20)
        self.slider.setValue(8)
        self.slider.setFixedWidth(200)
        self.slider.valueChanged.connect(lambda v: self.slider_label.setText(f"提取数量: {v}"))
        
        self.settings_layout.addWidget(self.slider_label)
        self.settings_layout.addWidget(self.slider)
        self.settings_layout.addStretch(1)
        self.vbox.addLayout(self.settings_layout)

        # 结果显示区域 (滚动)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea {border: none; background: transparent;}")
        
        self.result_container = QWidget()
        self.grid_layout = QGridLayout(self.result_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.result_container)
        self.vbox.addWidget(self.scroll)

        # 逻辑
        self.extractor = ColorExtractor()
        self.thread = None
        self.extractor.finished.connect(self.on_finished)
        self.extractor.log.connect(self.show_loading) # 简单用log显示状态

    def start_extraction(self, path):
        n_colors = self.slider.value()
        self.drop_area.setEnabled(False)
        self.clear_results()
        
        # 显示加载状态
        self.loading_label = BodyLabel("正在分析图片颜色...", self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(self.loading_label, 0, 0)
        
        self.thread = ExtractionThread(self.extractor, path, n_colors)
        self.thread.start()

    def show_loading(self, msg):
        pass

    def clear_results(self):
        # 清空网格布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_finished(self, results, error):
        self.drop_area.setEnabled(True)
        self.clear_results()
        
        if error:
            InfoBar.error("错误", error, parent=self)
            return

        # 布局结果
        row, col = 0, 0
        max_cols = 4 # 每行4个
        
        for data in results:
            card = ColorCard(data)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

class MarkdownInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdown_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("Markdown 转 PDF", self)
        self.desc = BodyLabel("实时预览 Markdown 并导出为 PDF", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 工具栏
        self.toolbar = QHBoxLayout()
        self.export_btn = PrimaryPushButton(FIF.SAVE, "导出 PDF", self)
        self.export_btn.clicked.connect(self.export_pdf)
        self.toolbar.addWidget(self.export_btn)
        self.toolbar.addStretch(1)
        self.vbox.addLayout(self.toolbar)

        # 分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 编辑器
        self.editor = TextEdit(self)
        self.editor.setPlaceholderText("在此输入 Markdown 内容...")
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.textChanged.connect(self.update_preview)
        
        # 预览容器 (懒加载 WebEngine 以避免 GPU 问题)
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 占位符
        self.placeholder_widget = QWidget()
        self.placeholder_layout = QVBoxLayout(self.placeholder_widget)
        self.placeholder_label = BodyLabel("点击加载预览 (使用轻量级 QTextBrowser)", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_btn = PrimaryPushButton("加载预览 / 启用导出", self)
        self.load_btn.clicked.connect(self.init_webview)
        self.placeholder_layout.addWidget(self.placeholder_label)
        self.placeholder_layout.addWidget(self.load_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.preview_layout.addWidget(self.placeholder_widget)
        
        self.webview = None
        
        # CSS 样式 (适配 QTextBrowser 的简化版)
        self.css_style = """
        <style>
            body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; color: #333; }
            h1, h2, h3 { color: #2c3e50; margin-top: 20px; border-bottom: 1px solid #eee; }
            code { background-color: #f0f0f0; color: #c7254e; }
            pre { background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; margin: 10px 0; }
            blockquote { border-left: 4px solid #ddd; padding-left: 10px; color: #777; }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #ddd; }
            th, td { border: 1px solid #ddd; padding: 8px; }
            th { background-color: #f2f2f2; font-weight: bold; }
        </style>
        """

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([450, 450])
        
        self.vbox.addWidget(self.splitter)
        
        # 默认文本
        self.editor.setText("# Hello World\\n\\n欢迎使用 **Markdown 转 PDF** 工具！")

    def init_webview(self):
        try:
            self.webview = QTextBrowser()
            self.webview.setStyleSheet("background-color: white; border: none;")
            self.webview.setOpenExternalLinks(True)
            
            self.preview_layout.removeWidget(self.placeholder_widget)
            self.placeholder_widget.deleteLater()
            self.preview_layout.addWidget(self.webview)
            self.update_preview()
        except Exception as e:
            InfoBar.error("初始化失败", f"无法加载预览组件: {e}", parent=self)

    def update_preview(self):
        if not self.webview: return
        
        text = self.editor.toPlainText()
        extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code', 'markdown.extensions.extra']
        try:
            html_content = markdown.markdown(text, extensions=extensions)
            final_html = f"<!DOCTYPE html><html><head>{self.css_style}</head><body>{html_content}</body></html>"
            self.webview.setHtml(final_html)
        except Exception as e:
            print(f"Markdown Parsing Error: {e}")

    def export_pdf(self):
        if not self.webview:
            InfoBar.warning("未就绪", "请先点击'加载预览'以初始化组件", parent=self)
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "markdown_output.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                
                # 打印 QTextBrowser 的文档
                self.webview.print(printer)
                
                InfoBar.success("任务完成", f"PDF 已保存到: {path}", duration=3000, parent=self)
            except Exception as e:
                InfoBar.error("导出失败", f"无法生成 PDF: {e}", parent=self)

class ImageVectorInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image_vector_interface")
        self.vectorizer = ImageVectorizer()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("PNG 转 SVG (位图转矢量)", self)
        self.desc = BodyLabel("将位图 (PNG/JPG) 转换为 SVG 矢量图，适合Logo和图标", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QGridLayout(self.settings_card)
        self.settings_layout.setContentsMargins(20, 20, 20, 20)
        self.settings_layout.setSpacing(15)

        # 模式选择
        self.mode_label = BodyLabel("采样模式:", self)
        self.mode_combo = ComboBox(self)
        self.mode_combo.addItems(['spline', 'polygon', 'none'])
        self.mode_combo.setToolTip("spline: 平滑曲线 (默认)\npolygon: 多边形\nnone: 无平滑")
        
        # 颜色模式
        self.colormode_label = BodyLabel("颜色模式:", self)
        self.colormode_combo = ComboBox(self)
        self.colormode_combo.addItems(['color', 'binary'])
        
        # 细节过滤
        self.speckle_label = BodyLabel("过滤杂点:", self)
        self.speckle_slider = Slider(Qt.Orientation.Horizontal)
        self.speckle_slider.setRange(0, 16)
        self.speckle_slider.setValue(4)
        self.speckle_val = BodyLabel("4")
        self.speckle_slider.valueChanged.connect(lambda v: self.speckle_val.setText(str(v)))

        # 层次化
        self.hierarchical_chk = CheckBox("层次化堆叠 (Hierarchical)", self)
        self.hierarchical_chk.setChecked(True)
        self.hierarchical_chk.setToolTip("堆叠形状而不是挖空，容易编辑")

        self.settings_layout.addWidget(self.mode_label, 0, 0)
        self.settings_layout.addWidget(self.mode_combo, 0, 1)
        self.settings_layout.addWidget(self.colormode_label, 0, 2)
        self.settings_layout.addWidget(self.colormode_combo, 0, 3)
        self.settings_layout.addWidget(self.speckle_label, 1, 0)
        self.settings_layout.addWidget(self.speckle_slider, 1, 1)
        self.settings_layout.addWidget(self.speckle_val, 1, 2)
        self.settings_layout.addWidget(self.hierarchical_chk, 1, 3)

        self.vbox.addWidget(self.settings_card)

        # 文件列表
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 底部按钮
        self.bottom_layout = QHBoxLayout()
        self.add_btn = PushButton(FIF.ADD, "添加图片", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)

        self.files = []
        self.threads = [] # Keep references

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.list_widget.addItem(os.path.basename(p))
        if self.files: self.start_btn.setEnabled(True)

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.start_btn.setEnabled(False)

    def start_conversion(self):
        if not self.files: return
        self.start_btn.setEnabled(False)
        self.log_text.append("开始转换任务...")
        
        kwargs = {
            'mode': self.mode_combo.currentText(),
            'colormode': self.colormode_combo.currentText(),
            'hierarchical': 'stacked' if self.hierarchical_chk.isChecked() else 'cutout',
            'filter_speckle': self.speckle_slider.value()
        }

        # 简单的串行处理或批量创建线程
        # 为简单起见，这里我们逐个启动转换，实际项目中可以用线程池
        self.total = len(self.files)
        self.finished_count = 0
        
        for input_path in self.files:
            output_path = os.path.splitext(input_path)[0] + ".svg"
            thread = ImageVectorThread(self.vectorizer, input_path, output_path, **kwargs)
            thread.finished.connect(lambda p=output_path: self.on_one_finished(p))
            thread.start()
            self.threads.append(thread) # 防止被垃圾回收

    def on_one_finished(self, path):
        self.log_text.append(f"[完成] 生成: {os.path.basename(path)}")
        self.finished_count += 1
        if self.finished_count >= self.total:
            self.start_btn.setEnabled(True)
            self.log_text.append("所有任务已完成！")
            InfoBar.success("完成", f"成功转换 {self.total} 个文件", parent=self)
            self.threads.clear()

class TxtPdfInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("txt_pdf_interface")
        self.converter = TxtConverter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("TXT 转 PDF", self)
        self.desc = BodyLabel("将文本文件批量转换为 PDF，支持自动换行和中文", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 列表与日志
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 底部
        self.bottom_layout = QHBoxLayout()
        self.out_label = BodyLabel("输出目录:", self)
        self.out_edit = LineEdit(self)
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.add_btn = PushButton(FIF.ADD, "添加 TXT", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.out_label)
        self.bottom_layout.addWidget(self.out_edit)
        self.bottom_layout.addWidget(self.browse_btn)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addWidget(self.start_btn)
        
        self.vbox.addLayout(self.bottom_layout)

        self.files = []
        self.thread = None
        self.converter.log.connect(self.log_text.append)
        self.converter.finished.connect(self.on_finished)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 TXT", "", "Text (*.txt *.md *.py *.log)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.list_widget.addItem(os.path.basename(p))
        
        if self.files and not self.out_edit.text():
            self.out_edit.setText(os.path.dirname(self.files[0]))
        self.check_state()

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.out_edit.setText(path)
            self.check_state()

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.check_state()

    def check_state(self):
        self.start_btn.setEnabled(bool(self.files) and bool(self.out_edit.text()))

    def start_conversion(self):
        out_dir = self.out_edit.text()
        if not self.files or not out_dir: return
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.thread = TxtPdfThread(self.converter, self.files, out_dir)
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始转换")
        if fail > 0:
            InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
        else:
            InfoBar.success("完成", f"成功 {success}", duration=3000, parent=self)

class CodeExtractInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("code_extract_interface")
        self.extractor = CodeExtractor()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("代码提取工具", self)
        self.desc = BodyLabel("遍历目录提取代码文件内容到单个 TXT/Markdown，便于分析", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        self.card = CardWidget(self)
        self.card_layout = QGridLayout(self.card)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        self.card_layout.setSpacing(15)

        # 根目录
        self.dir_label = BodyLabel("项目根目录:", self)
        self.dir_edit = LineEdit(self)
        self.dir_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.dir_btn.clicked.connect(self.browse_dir)

        # 扩展名
        self.ext_label = BodyLabel("文件扩展名:", self)
        self.ext_edit = LineEdit(self)
        self.ext_edit.setPlaceholderText("例如: .py, .java, .cpp (逗号分隔)")
        self.ext_edit.setText(".py, .java, .c, .cpp, .h, .js, .ts, .html, .css") # 默认

        # 输出文件
        self.out_label = BodyLabel("保存到文件:", self)
        self.out_edit = LineEdit(self)
        self.out_btn = PushButton(FIF.SAVE, "浏览", self)
        self.out_btn.clicked.connect(self.browse_output)

        self.card_layout.addWidget(self.dir_label, 0, 0)
        self.card_layout.addWidget(self.dir_edit, 0, 1)
        self.card_layout.addWidget(self.dir_btn, 0, 2)
        
        self.card_layout.addWidget(self.ext_label, 1, 0)
        self.card_layout.addWidget(self.ext_edit, 1, 1)
        
        self.card_layout.addWidget(self.out_label, 2, 0)
        self.card_layout.addWidget(self.out_edit, 2, 1)
        self.card_layout.addWidget(self.out_btn, 2, 2)

        self.vbox.addWidget(self.card)

        # 日志
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.vbox.addWidget(self.log_text)

        # 按钮
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始提取", self)
        self.start_btn.clicked.connect(self.start_extract)
        self.vbox.addWidget(self.start_btn, 0, Qt.AlignmentFlag.AlignRight)

        self.thread = None
        self.extractor.log.connect(self.log_text.append)
        self.extractor.finished.connect(self.on_finished)

    def browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择项目根目录")
        if path:
            self.dir_edit.setText(path)
            # 自动生成输出路径建议
            if not self.out_edit.text():
                self.out_edit.setText(os.path.join(path, "project_code.txt"))

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存提取结果", "project_code.txt", "Text (*.txt)")
        if path:
            self.out_edit.setText(path)

    def start_extract(self):
        root = self.dir_edit.text()
        exts_str = self.ext_edit.text()
        out = self.out_edit.text()

        if not root or not os.path.exists(root):
            InfoBar.error("错误", "无效的根目录", parent=self)
            return
        if not out:
            InfoBar.error("错误", "请指定输出文件路径", parent=self)
            return

        exts = [e.strip() for e in exts_str.split(',') if e.strip()]
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.thread = CodeExtractThread(self.extractor, root, exts, out)
        self.thread.start()

    def on_finished(self, success, msg):
        self.start_btn.setEnabled(True)
        if success:
            InfoBar.success("完成", msg, parent=self)
        else:
            InfoBar.error("错误", msg, parent=self)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Office Tool")
        self.resize(900, 700)
        
        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width()-self.width())//2, (screen.height()-self.height())//2)

        # 1. PPT 转换界面
        self.ppt_interface = PPTInterface(self)
        self.addSubInterface(self.ppt_interface, FIF.TILES, "PPT 转 PDF")

        # 2. Word 转换界面
        self.word_interface = WordInterface(self)
        self.addSubInterface(self.word_interface, FIF.DOCUMENT, "Word 转 PDF")

        # 3. PDF 合并界面
        self.pdf_merge_interface = PDFMergeInterface(self)
        self.addSubInterface(self.pdf_merge_interface, FIF.FOLDER, "PDF 合并")

        # 4. PDF 压缩界面
        self.compress_interface = PDFCompressInterface(self)
        self.addSubInterface(self.compress_interface, FIF.ZIP_FOLDER, "PDF 压缩")

        # 5. 图片取色界面
        self.color_interface = ColorInterface(self)
        self.addSubInterface(self.color_interface, FIF.PALETTE, "图片取色")

        # 6. Markdown 转 PDF
        self.markdown_interface = MarkdownInterface(self)
        self.addSubInterface(self.markdown_interface, FIF.EDIT, "Markdown 转 PDF")

        # 7. PNG 转 SVG
        self.image_vector_interface = ImageVectorInterface(self)
        self.addSubInterface(self.image_vector_interface, FIF.PHOTO, "PNG 转 SVG")

        # 8. TXT 转 PDF
        self.txt_pdf_interface = TxtPdfInterface(self)
        self.addSubInterface(self.txt_pdf_interface, FIF.DOCUMENT, "TXT 转 PDF")

        # 9. 代码提取
        self.code_extract_interface = CodeExtractInterface(self)
        self.addSubInterface(self.code_extract_interface, FIF.CODE, "代码提取")

        self.navigationInterface.setCurrentItem(self.ppt_interface.objectName())

if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1.25"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
