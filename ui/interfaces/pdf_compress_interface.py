import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSettings # Keep QSettings for backward compatibility if needed, but we prefer ConfigLoader
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PushButton, 
                            PrimaryPushButton, ProgressBar, TextEdit, InfoBar, 
                            LineEdit, ComboBox, FluentIcon as FIF)

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
        
        # 获取工具信息以设置下载链接
        self.gs_tool = AppContainer().external_tool_manager.get_tool("ghostscript")
        
        self.download_btn = PushButton(FIF.DOWNLOAD, "下载 Ghostscript", self)
        self.download_btn.clicked.connect(lambda: os.startfile(self.gs_tool.download_url) if os.name == 'nt' else None)
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
        # 使用新的引擎
        self.compressor = GhostscriptCompressor()
        self.thread = None
        
        # 兼容旧代码，但首选 ConfigLoader
        if self.container:
            self.config = self.container.config
            last_gs = self.config.get("dependencies.ghostscript.path", "")
        else:
            # Fallback for testing without container
            self.settings = QSettings("AI_Office_Tool", "Config")
            last_gs = self.settings.value("gs_path", "")

        # 加载 GS 路径
        if not last_gs and self.gs_tool and self.gs_tool.is_available():
            # 如果配置中没有，尝试从管理器获取自动检测到的路径
            last_gs = self.gs_tool.get_executable_path() or ""
            
        self.gs_edit.setText(last_gs)

        self.compressor.log.connect(self.append_log)
        self.compressor.progress.connect(self.update_progress)
        self.compressor.finished.connect(self.on_finished)

    def check_gs_env(self):
        self.env_status.setText("正在搜索...")
        self.download_btn.hide()
        QApplication.processEvents()
        
        # 使用引擎自带的检测方法
        result = self.compressor.check_dependency()
        
        if result['available']:
            self.env_status.setText(f"✅ {result['message']}")
            self.env_status.setTextColor("#009900", "#00cc00") # Green
            self.gs_edit.setText(result['path'])
            self._save_gs_path(result['path'])
            self.check_state()
        else:
            self.env_status.setText("❌ 未检测到 Ghostscript")
            self.env_status.setTextColor("#cc0000", "#ff3333") # Red
            self.download_btn.show()

    def browse_gs(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 gswin64c.exe", "", "Executable (*.exe)")
        if path:
            self.gs_edit.setText(path)
            self._save_gs_path(path)
            self.check_state()

    def _save_gs_path(self, path):
        """统一保存 GS 路径到配置"""
        if hasattr(self, 'config'):
            self.config.set("dependencies.ghostscript.path", path)
        else:
            self.settings.setValue("gs_path", path)

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
