import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSettings # Keep QSettings for backward compatibility if needed, but we prefer ConfigLoader
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PushButton, 
                            PrimaryPushButton, ProgressBar, TextEdit, InfoBar, 
                            LineEdit, ComboBox, IconWidget, FluentIcon as FIF)

from core.engines.pdf.ghostscript import GhostscriptCompressor
from app.container import AppContainer
from ui.widgets import DragDropListWidget
from ui.threads import CompressThread

class PDFCompressInterface(QWidget):
    def __init__(self, parent=None, container=None):
        super().__init__(parent=parent)
        self.container = container
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

        # 获取工具
        self.gs_tool = AppContainer().external_tool_manager.get_tool("ghostscript")

        # 状态指示行
        self.status_layout = QHBoxLayout()
        self.status_icon = IconWidget(FIF.INFO)
        self.status_icon.setFixedSize(18, 18)
        self.status_label = BodyLabel("Ghostscript 状态检查中...", self)
        
        self.action_btn = PushButton(FIF.SETTING, "管理组件", self)
        self.action_btn.clicked.connect(self.open_settings)
        self.action_btn.hide()

        self.status_layout.addWidget(self.status_icon)
        self.status_layout.addSpacing(10)
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addStretch(1)
        self.status_layout.addWidget(self.action_btn)

        # 质量选择行
        self.quality_layout = QHBoxLayout()
        self.quality_label = BodyLabel("压缩质量:", self)
        self.quality_combo = ComboBox(self)
        self.quality_combo.addItems(['/screen (屏幕 - 最小)', '/ebook (电子书 - 中等)', '/printer (打印 - 较高)', '/prepress (印前 - 最高)', '/default (默认)'])
        self.quality_combo.setCurrentIndex(2) # 默认 printer
        self.quality_layout.addWidget(self.quality_label)
        self.quality_layout.addWidget(self.quality_combo)
        self.quality_layout.addStretch(1)

        self.settings_layout.addLayout(self.status_layout)
        self.settings_layout.addSpacing(15) # 增加间距
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
        # 使用新的引擎
        self.compressor = GhostscriptCompressor()
        self.thread = None
        
        self.compressor.log.connect(self.append_log)
        self.compressor.progress.connect(self.update_progress)
        self.compressor.finished.connect(self.on_finished)
        
        # 初始检查
        self.check_gs_status()

    def check_gs_status(self):
        """检查 GS 状态并更新 UI"""
        if not self.gs_tool:
             self._set_status_error("内部错误: 未找到组件管理器")
             return

        if self.gs_tool.is_disabled:
            self._set_status_error("Ghostscript 组件已禁用 (点击管理启用)", show_btn=True)
        elif self.gs_tool.is_available():
            info = self.gs_tool.get_status_info()
            source = "便携版" if info.get("source") == "portable" else "系统版"
            self._set_status_ready(f"Ghostscript 已就绪 ({source})")
        else:
            self._set_status_error("缺少 Ghostscript 组件 (点击管理安装)", show_btn=True)
            
        self.check_state()

    def _set_status_ready(self, text):
        self.status_icon.setIcon(FIF.ACCEPT)
        self.status_icon.setStyleSheet("IconWidget { color: #107C10; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#107C10", "#107C10")
        self.action_btn.hide()

    def _set_status_error(self, text, show_btn=False):
        self.status_icon.setIcon(FIF.CANCEL)
        self.status_icon.setStyleSheet("IconWidget { color: #C42B1C; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#C42B1C", "#FF99A4")
        if show_btn:
            self.action_btn.show()
        else:
            self.action_btn.hide()

    def open_settings(self):
        """跳转到设置页面"""
        # 假设父级有 switch_interface 方法 (Main Window)
        window = self.window()
        if hasattr(window, 'switch_to_settings'):
            window.switch_to_settings()
        else:
            # Fallback if specific method doesn't exist, try finding by object name
            # Assuming main window structure
            pass

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
        has_gs = self.gs_tool and self.gs_tool.is_available()
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
        # 动态获取路径
        gs_path = self.gs_tool.get_executable_path()
        if not gs_path or not os.path.exists(gs_path):
            InfoBar.error("错误", "无法找到 Ghostscript 可执行文件", parent=self)
            self.check_gs_status() # Re-check
            return
            
        quality = self.quality_combo.currentText().split(' ')[0]
        
        self.start_btn.setEnabled(False)
        self.thread = CompressThread(self.compressor, self.files, quality, gs_path)
        self.thread.start()
        
    def showEvent(self, event):
        """界面显示时刷新状态"""
        self.check_gs_status()
        super().showEvent(event)

    def on_finished(self, success, fail):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始压缩")
        self.progress.hide()
        InfoBar.success("完成", f"成功 {success}, 失败 {fail}", duration=3000, parent=self)
