import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QListWidgetItem
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, IconWidget,
                            PrimaryPushButton, PushButton, TextEdit,
                            InfoBar, FluentIcon as FIF)

from app.container import AppContainer
from ui.widgets import DragDropListWidget
from ui.widgets.enhanced_progress import EnhancedProgressBar
from ui.threads import WorkerThread
from ui.design_system import Margins, Spacing


class OfficeConvertInterface(QWidget):
    """Word/Excel/PPT 转 PDF 三合一页面；子类用类属性参数化差异项。"""
    object_name = ""
    page_title = ""
    page_desc = ""
    file_filter = ""
    allowed_exts = ()
    engine_attr = ""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(self.object_name)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)

        self.title = SubtitleLabel(self.page_title, self)
        self.desc = BodyLabel(self.page_desc, self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        self.card = CardWidget(self)
        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(*Margins.CARD)

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

        # 内容区域容器
        self.content_card = CardWidget(self)
        self.content_layout = QHBoxLayout(self.content_card)
        self.content_layout.setContentsMargins(*Margins.CARD)
        self.content_layout.setSpacing(Spacing.MD)

        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)

        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            TextEdit {
                background-color: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 6px;
            }
        """)

        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)

        self.vbox.addWidget(self.content_card, 1)  # stretch=1 使其占据主要空间

        self.bottom_layout = QHBoxLayout()

        self.progress = EnhancedProgressBar(self)
        self.progress.hide()

        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.setFixedWidth(200)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.start_btn)

        self.vbox.addLayout(self.bottom_layout)

        self.converter = getattr(AppContainer(), self.engine_attr)
        self.thread = None

        self.converter.log.connect(self.append_log)
        self.converter.progress.connect(self.update_progress)
        self.converter.finished.connect(self.on_finished)

    def _get_all_paths(self) -> list:
        """从列表控件获取所有文件路径（单一数据源）"""
        paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        return paths

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选文件", "", self.file_filter)
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        current_paths = self._get_all_paths()
        count = 0
        for p in paths:
            if p not in current_paths:
                ext = os.path.splitext(p)[1].lower()
                if ext in self.allowed_exts:
                    item = QListWidgetItem(os.path.basename(p))
                    item.setData(Qt.ItemDataRole.UserRole, p)
                    self.list_widget.addItem(item)
                    count += 1
        if count > 0:
            total = self.list_widget.count()
            self.tip.setText(f"已选 {total} 个文件")
            self.start_btn.setEnabled(True)

    def clear_files(self):
        self.list_widget.clear()
        self.tip.setText("请添加文件 (支持拖拽)...")
        self.start_btn.setEnabled(False)
        self.progress.hide()
        self.log_text.clear()

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_progress(self, curr, total, name):
        self.progress.update_progress(curr, total, name)
        self.start_btn.setText(f"处理中... ({curr}/{total})")

    def start_conversion(self):
        files = self._get_all_paths()
        if not files: return
        self.start_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.list_widget.setEnabled(False)
        self.log_text.clear()
        self.progress.start(len(files))
        self.progress.show()
        self.thread = WorkerThread(self.converter.convert, files)
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.list_widget.setEnabled(True)
        self.start_btn.setText("开始转换")
        self.progress.stop()
        self.progress.hide()
        if fail > 0: InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
        else: InfoBar.success("完成", f"成功 {success}", duration=3000, parent=self)


class WordInterface(OfficeConvertInterface):
    object_name = "word_interface"
    page_title = "Word 转 PDF"
    page_desc = "批量转换 Word 文件 (支持 MS Word 或 LibreOffice)"
    file_filter = "Word (*.doc *.docx)"
    allowed_exts = (".doc", ".docx")
    engine_attr = "word_engine"


class ExcelInterface(OfficeConvertInterface):
    object_name = "excel_interface"
    page_title = "Excel 转 PDF"
    page_desc = "批量转换 Excel 文件 (支持 MS Excel 或 LibreOffice)"
    file_filter = "Excel (*.xls *.xlsx)"
    allowed_exts = (".xls", ".xlsx")
    engine_attr = "excel_engine"


class PPTInterface(OfficeConvertInterface):
    object_name = "ppt_interface"
    page_title = "PowerPoint 转 PDF"
    page_desc = "批量转换 PPT 文件 (支持 MS PowerPoint 或 LibreOffice)"
    file_filter = "PPT (*.ppt *.pptx)"
    allowed_exts = (".ppt", ".pptx")
    engine_attr = "ppt_engine"
