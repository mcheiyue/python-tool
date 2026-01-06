import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout
from PyQt6.QtGui import QFont
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton, 
                            TextEdit, LineEdit, InfoBar, FluentIcon as FIF,
                            ComboBox, SpinBox)

from core.pdf_page_renderer import PDFPageRenderer
from ui.widgets import DragDropListWidget
from ui.threads import PDFRenderThread

class PDFRenderInterface(QWidget):
    """PDF 页面渲染界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("pdf_render_interface")
        self.renderer = PDFPageRenderer()
        
        # 检查 PyMuPDF 是否可用
        if not PDFPageRenderer.is_available():
            self._show_unavailable_ui()
            return
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        # 标题和描述
        self.title = SubtitleLabel("PDF 页面渲染", self)
        self.desc = BodyLabel("将 PDF 页面渲染为高清图片（支持矢量图形）", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 内容区域：文件列表 + 日志
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self)
        self.list_widget.files_dropped.connect(self.on_files_dropped)
        
        self.log_text = TextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        
        self.content_layout.addWidget(self.list_widget, 6)
        self.content_layout.addWidget(self.log_text, 4)
        self.vbox.addLayout(self.content_layout)

        # 设置区域
        self.settings_layout = QGridLayout()
        
        # DPI 设置
        self.dpi_label = BodyLabel("渲染质量:", self)
        self.dpi_combo = ComboBox(self)
        # 只添加显示文本，DPI 值通过字典查询获取
        for name in PDFPageRenderer.DPI_OPTIONS.keys():
            self.dpi_combo.addItem(name)
        self.dpi_combo.setCurrentIndex(2)  # 默认 300 DPI
        
        # 输出格式
        self.format_label = BodyLabel("输出格式:", self)
        self.format_combo = ComboBox(self)
        self.format_combo.addItems(['PNG', 'JPG', 'JPEG', 'WebP'])
        self.format_combo.setCurrentIndex(0)  # 默认 PNG
        
        # 页面范围
        self.range_label = BodyLabel("页面范围:", self)
        self.range_combo = ComboBox(self)
        self.range_combo.addItems(['全部页面', '指定范围'])
        self.range_combo.currentTextChanged.connect(self.on_range_changed)
        
        self.start_page_spin = SpinBox(self)
        self.start_page_spin.setMinimum(1)
        self.start_page_spin.setMaximum(9999)
        self.start_page_spin.setValue(1)
        self.start_page_spin.setPrefix("从第 ")
        self.start_page_spin.setSuffix(" 页")
        self.start_page_spin.setEnabled(False)
        
        self.end_page_spin = SpinBox(self)
        self.end_page_spin.setMinimum(1)
        self.end_page_spin.setMaximum(9999)
        self.end_page_spin.setValue(10)
        self.end_page_spin.setPrefix("到第 ")
        self.end_page_spin.setSuffix(" 页")
        self.end_page_spin.setEnabled(False)
        
        # 添加到网格布局
        self.settings_layout.addWidget(self.dpi_label, 0, 0)
        self.settings_layout.addWidget(self.dpi_combo, 0, 1)
        self.settings_layout.addWidget(self.format_label, 0, 2)
        self.settings_layout.addWidget(self.format_combo, 0, 3)
        
        self.settings_layout.addWidget(self.range_label, 1, 0)
        self.settings_layout.addWidget(self.range_combo, 1, 1)
        self.settings_layout.addWidget(self.start_page_spin, 1, 2)
        self.settings_layout.addWidget(self.end_page_spin, 1, 3)
        
        self.vbox.addLayout(self.settings_layout)

        # 底部按钮区域
        self.bottom_layout = QHBoxLayout()
        self.out_label = BodyLabel("输出目录:", self)
        self.out_edit = LineEdit(self)
        self.browse_btn = PushButton(FIF.FOLDER, "浏览", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        self.add_btn = PushButton(FIF.ADD, "添加 PDF", self)
        self.add_btn.clicked.connect(self.add_files)
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始渲染", self)
        self.start_btn.clicked.connect(self.start_render)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.out_label)
        self.bottom_layout.addWidget(self.out_edit)
        self.bottom_layout.addWidget(self.browse_btn)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addWidget(self.start_btn)
        
        self.vbox.addLayout(self.bottom_layout)

        # 初始化状态
        self.files = []
        self.thread = None
        self.renderer.log.connect(self.log_text.append)
        self.renderer.finished.connect(self.on_finished)
        self.renderer.progress.connect(self.update_progress)

    def _show_unavailable_ui(self):
        """显示不可用提示"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = SubtitleLabel("PDF 页面渲染", self)
        desc = BodyLabel("⚠️ PyMuPDF 模块未安装，此功能不可用", self)
        desc.setTextColor("#FF0000", "#FF6666")
        
        hint = BodyLabel("请运行以下命令安装：\npip install PyMuPDF>=1.23.0", self)
        hint.setFont(QFont("Consolas", 10))
        
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(hint)
        layout.addStretch(1)

    def on_range_changed(self, text):
        """页面范围选择改变"""
        is_custom = (text == '指定范围')
        self.start_page_spin.setEnabled(is_custom)
        self.end_page_spin.setEnabled(is_custom)

    def add_files(self):
        """添加PDF文件"""
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF (*.pdf)")
        if paths:
            self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        """处理拖放的文件"""
        for p in paths:
            if p.lower().endswith('.pdf') and p not in self.files:
                self.files.append(p)
                self.list_widget.addItem(os.path.basename(p))
        
        # 自动设置输出目录
        if self.files and not self.out_edit.text():
            self.out_edit.setText(os.path.dirname(self.files[0]))
        self.check_state()

    def browse_output(self):
        """浏览输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.out_edit.setText(path)
            self.check_state()

    def clear_files(self):
        """清空文件列表"""
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.check_state()

    def check_state(self):
        """检查按钮状态"""
        self.start_btn.setEnabled(bool(self.files) and bool(self.out_edit.text()))

    def start_render(self):
        """开始渲染"""
        out_dir = self.out_edit.text()
        if not self.files or not out_dir:
            return
        
        # 获取设置
        dpi_name = self.dpi_combo.currentText()
        dpi = PDFPageRenderer.DPI_OPTIONS[dpi_name]
        output_format = self.format_combo.currentText().lower()
        
        # 页面范围
        page_range = None
        if self.range_combo.currentText() == '指定范围':
            start = self.start_page_spin.value() - 1  # 转为 0-based
            end = self.end_page_spin.value()
            page_range = (start, end)
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        
        # 创建并启动线程
        self.thread = PDFRenderThread(
            self.renderer,
            self.files,
            out_dir,
            dpi,
            output_format,
            page_range
        )
        self.thread.start()

    def update_progress(self, curr, total, msg):
        """更新进度"""
        self.start_btn.setText(f"渲染中... {curr}/{total}")

    def on_finished(self, success, fail):
        """渲染完成"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始渲染")
        InfoBar.success("完成", f"成功渲染 {success} 个文件", duration=3000, parent=self)