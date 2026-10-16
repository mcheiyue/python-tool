import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PushButton, 
                            PrimaryPushButton, TextEdit, LineEdit, InfoBar, 
                            FluentIcon as FIF)

from core.features.text.code_extractor import CodeExtractor
from ui.threads import WorkerThread

class CodeExtractInterface(QWidget):
    # 桥接信号：WorkerThread 回调在工作线程触发，经此排队回主线程
    _log_bridged = pyqtSignal(str)
    _finished_bridged = pyqtSignal(bool, str)

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

        self._log_bridged.connect(self.log_text.append)
        self._finished_bridged.connect(self.on_finished)

        # 按钮
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始提取", self)
        self.start_btn.clicked.connect(self.start_extract)
        self.vbox.addWidget(self.start_btn, 0, Qt.AlignmentFlag.AlignRight)

        self.thread = None

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
        if not exts:
            InfoBar.error("错误", "扩展名不能为空，如 .py,.c", parent=self)
            return

        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.thread = WorkerThread(
            self.extractor.extract, root, exts, out,
            on_log=self._log_bridged.emit,
            on_finished=self._finished_bridged.emit,
        )
        self.thread.error.connect(lambda msg: self.on_finished(False, msg))
        self.thread.start()

    def on_finished(self, success, msg):
        self.start_btn.setEnabled(True)
        if success:
            InfoBar.success("完成", msg, parent=self)
        else:
            InfoBar.error("错误", msg, parent=self)
