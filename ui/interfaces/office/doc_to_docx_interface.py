import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, IconWidget, 
                            PrimaryPushButton, PushButton, TextEdit,
                            InfoBar, FluentIcon as FIF, CheckBox, LineEdit, MessageDialog)

from app.container import AppContainer
from ui.widgets import DragDropListWidget
from ui.widgets.enhanced_progress import EnhancedProgressBar
from ui.threads import WorkerThread
from ui.design_system import Margins, Spacing

class DocToDocxInterface(QWidget):
    # 桥接信号：转换回调在工作线程触发，经此排队回主线程
    _log_bridged = pyqtSignal(str)
    _progress_bridged = pyqtSignal(int, int, str)
    _finished_bridged = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("doc_to_docx_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)

        self.title = SubtitleLabel("Doc 转 Docx", self)
        self.desc = BodyLabel("将旧版 Word 文档 (.doc) 转换为新版格式 (.docx)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 顶部工具栏
        self.card = CardWidget(self)
        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(*Margins.CARD)

        self.icon = IconWidget(FIF.TILES)
        self.icon.setFixedSize(48, 48)
        self.tip = BodyLabel("请添加 .doc 文件 (支持拖拽)...")
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

        # 设置区域：输出目录
        self.settings_card = CardWidget(self)
        self.settings_layout = QHBoxLayout(self.settings_card)
        self.settings_layout.setContentsMargins(*Margins.CARD)

        self.same_dir_cb = CheckBox("输出到同目录", self)
        self.same_dir_cb.setChecked(True)
        self.same_dir_cb.stateChanged.connect(self.toggle_output_dir)

        self.output_dir_edit = LineEdit(self)
        self.output_dir_edit.setPlaceholderText("选择输出目录...")
        self.output_dir_edit.setEnabled(False)

        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output_dir)
        self.browse_btn.setEnabled(False)

        self.settings_layout.addWidget(self.same_dir_cb)
        self.settings_layout.addWidget(self.output_dir_edit)
        self.settings_layout.addWidget(self.browse_btn)

        self.vbox.addWidget(self.settings_card)

        # 内容区域
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
        
        self.vbox.addWidget(self.content_card, 1)

        # 底部控制栏
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

        self.files = []
        self.converter = AppContainer().doc_to_docx_converter
        self.thread = None

        self._log_bridged.connect(self.append_log)
        self._progress_bridged.connect(self.update_progress)
        self._finished_bridged.connect(self.on_finished)

    def toggle_output_dir(self, state):
        enabled = not self.same_dir_cb.isChecked()
        self.output_dir_edit.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)

    def browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_dir_edit.setText(path)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选文件", "", "Word 97-2003 (*.doc)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        count = 0
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext == '.doc':
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
                    count += 1
        if count > 0:
            self.tip.setText(f"已选 {len(self.files)} 个文件")
            self.start_btn.setEnabled(True)

    def clear_files(self):
        self.files = []
        self.list_widget.clear()
        self.tip.setText("请添加 .doc 文件 (支持拖拽)...")
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
        if not self.files: return

        # 确定输出目录
        output_dir = None
        if not self.same_dir_cb.isChecked():
            output_dir = self.output_dir_edit.text().strip()
            if not output_dir:
                InfoBar.error("错误", "请选择输出目录", parent=self)
                return

        # 检查文件冲突 (覆盖前咨询)
        conflicts = []
        for path in self.files:
            abs_path = os.path.abspath(path)
            
            if output_dir:
                out_path_dir = output_dir
            else:
                out_path_dir = os.path.dirname(abs_path)
            
            base_name = os.path.splitext(os.path.basename(abs_path))[0]
            docx_path = os.path.join(out_path_dir, base_name + ".docx")
            
            if os.path.exists(docx_path):
                conflicts.append(os.path.basename(docx_path))
        
        if conflicts:
            msg = f"发现 {len(conflicts)} 个已存在文件:\n"
            msg += "\n".join(conflicts[:5])
            if len(conflicts) > 5:
                msg += f"\n...等共 {len(conflicts)} 个文件"
            msg += "\n\n是否覆盖这些文件？"
            
            w = MessageDialog("文件冲突", msg, self)
            w.yesButton.setText("覆盖")
            w.cancelButton.setText("取消")
            
            if not w.exec():
                return

        self.start_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.list_widget.setEnabled(False)
        self.settings_card.setEnabled(False)
        self.log_text.clear()
        
        self.thread = WorkerThread(
            self.converter.convert, self.files, output_dir,
            on_log=self._log_bridged.emit,
            on_progress=self._progress_bridged.emit,
            on_finished=self._finished_bridged.emit,
        )
        self.thread.error.connect(lambda msg: self.on_finished(0, 1))
        self.thread.start()

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.list_widget.setEnabled(True)
        self.settings_card.setEnabled(True)
        self.start_btn.setText("开始转换")
        self.progress.stop()
        self.progress.hide()
        if fail > 0: InfoBar.warning("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
        else: InfoBar.success("完成", f"成功 {success}", duration=3000, parent=self)
