import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt6.QtGui import QFont, QAction, QKeySequence, QDesktopServices
from PyQt6.QtCore import QUrl
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton, 
                            ToolButton, TextEdit, LineEdit, ProgressBar, InfoBar, 
                            CardWidget, FluentIcon as FIF)

from core.pdf_merger import PDFMerger
from ui.widgets import DragDropListWidget
from ui.threads import MergeThread

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
        self.add_btn.setToolTip("添加 PDF 文件 (Ctrl+O)")
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空列表", self)
        self.clear_btn.setToolTip("清空所有文件")
        self.clear_btn.clicked.connect(self.clear_files)

        self.toolbar_layout.addWidget(self.add_btn)
        self.toolbar_layout.addWidget(self.clear_btn)
        self.toolbar_layout.addStretch(1)

        self.up_btn = ToolButton(FIF.UP, self)
        self.up_btn.setToolTip("上移选中项 (Ctrl+Up)")
        self.up_btn.clicked.connect(self.move_up)
        
        self.down_btn = ToolButton(FIF.DOWN, self)
        self.down_btn.setToolTip("下移选中项 (Ctrl+Down)")
        self.down_btn.clicked.connect(self.move_down)
        
        self.remove_btn = ToolButton(FIF.REMOVE, self)
        self.remove_btn.setToolTip("移除选中项 (Delete)")
        self.remove_btn.clicked.connect(self.remove_selected)

        self.toolbar_layout.addWidget(self.up_btn)
        self.toolbar_layout.addSpacing(5)
        self.toolbar_layout.addWidget(self.down_btn)
        self.toolbar_layout.addSpacing(15)
        self.toolbar_layout.addWidget(self.remove_btn)

        self.vbox.addLayout(self.toolbar_layout)

        # 主要内容区域 (列表 + 日志) - 使用卡片容器
        self.content_card = CardWidget(self)
        self.content_layout = QHBoxLayout(self.content_card)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        
        self.list_widget = DragDropListWidget(self, "拖拽 PDF 文件到此处，\n支持拖拽调整顺序")
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

        # 底部区域 (输出路径 + 开始按钮)
        self.bottom_layout = QHBoxLayout()
        
        self.out_label = BodyLabel("输出文件:", self)
        self.out_edit = LineEdit(self)
        self.out_edit.setPlaceholderText("选择或输入保存路径...")
        
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始合并", self)
        self.start_btn.setToolTip("开始合并 (Ctrl+Enter)")
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
        
        # 快捷键
        self.add_action = QAction(self)
        self.add_action.setShortcut(QKeySequence("Ctrl+O"))
        self.add_action.triggered.connect(self.add_files)
        self.addAction(self.add_action)
        
        self.run_action = QAction(self)
        self.run_action.setShortcut(QKeySequence("Ctrl+Return"))
        self.run_action.triggered.connect(self.start_merge)
        self.addAction(self.run_action)
        
        self.del_action = QAction(self)
        self.del_action.setShortcut(QKeySequence("Delete"))
        self.del_action.triggered.connect(self.remove_selected)
        self.addAction(self.del_action)
        
        self.up_action = QAction(self)
        self.up_action.setShortcut(QKeySequence("Ctrl+Up"))
        self.up_action.triggered.connect(self.move_up)
        self.addAction(self.up_action)
        
        self.down_action = QAction(self)
        self.down_action.setShortcut(QKeySequence("Ctrl+Down"))
        self.down_action.triggered.connect(self.move_down)
        self.addAction(self.down_action)

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
            bar = InfoBar.success(
                title="合并成功",
                content=msg,
                duration=5000,
                parent=self
            )
            
            output_path = self.out_edit.text().strip()
            if output_path and os.path.exists(output_path):
                # 打开文件
                open_btn = PushButton("打开文件")
                open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(output_path)))
                bar.addWidget(open_btn)
                
                # 打开文件夹
                folder_btn = PushButton("打开文件夹")
                folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(output_path))))
                bar.addWidget(folder_btn)
            
            bar.show()
        else:
            InfoBar.error("错误", msg, duration=5000, parent=self)
