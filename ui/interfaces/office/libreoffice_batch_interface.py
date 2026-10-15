"""LibreOffice 批量格式转换界面"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PushButton, 
                            PrimaryPushButton, TextEdit, InfoBar,
                            ComboBox, IconWidget, FluentIcon as FIF)

from core.features.office.libreoffice_converter import LibreOfficeFormatConverter
from app.container import AppContainer
from ui.widgets import DragDropListWidget
from ui.widgets.enhanced_progress import EnhancedProgressBar
from ui.design_system import Margins, Spacing
from ui.threads import WorkerThread


class LibreOfficeBatchInterface(QWidget):
    """LibreOffice 批量格式转换界面"""

    # 桥接信号：转换回调在工作线程触发，经此排队回主线程
    _log_bridged = pyqtSignal(str)
    _progress_bridged = pyqtSignal(int, int, str)
    _finished_bridged = pyqtSignal(int, int)
    
    # 格式分组显示
    FORMAT_GROUPS = {
        '文档格式': [
            ('PDF 文档', 'pdf'),
            ('Word 文档 (DOCX)', 'docx'),
            ('OpenDocument 文本 (ODT)', 'odt'),
            ('Word 97-2003 (DOC)', 'doc'),
            ('HTML 网页', 'html'),
            ('纯文本 (TXT)', 'txt'),
        ],
        '表格格式': [
            ('Excel 工作簿 (XLSX)', 'xlsx'),
            ('OpenDocument 表格 (ODS)', 'ods'),
            ('Excel 97-2003 (XLS)', 'xls'),
            ('逗号分隔值 (CSV)', 'csv'),
        ],
        '演示格式': [
            ('PowerPoint 演示文稿 (PPTX)', 'pptx'),
            ('OpenDocument 演示 (ODP)', 'odp'),
            ('PowerPoint 97-2003 (PPT)', 'ppt'),
        ],
    }
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("libreoffice_batch_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)
        
        # 标题
        self.title = SubtitleLabel("LibreOffice 格式转换", self)
        self.desc = BodyLabel("批量转换办公文档格式 (ODT↔DOCX, ODS↔XLSX, ODP↔PPTX 等)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)
        
        # 设置卡片
        self.settings_card = CardWidget(self)
        self.settings_layout = QVBoxLayout(self.settings_card)
        self.settings_layout.setContentsMargins(*Margins.CARD)
        
        # 获取工具
        self.lo_tool = AppContainer().external_tool_manager.get_tool("libreoffice")
        
        # 状态指示行
        self.status_layout = QHBoxLayout()
        self.status_icon = IconWidget(FIF.INFO)
        self.status_icon.setFixedSize(18, 18)
        self.status_label = BodyLabel("LibreOffice 状态检查中...", self)
        
        self.action_btn = PushButton(FIF.SETTING, "管理组件", self)
        self.action_btn.clicked.connect(self.open_settings)
        self.action_btn.hide()
        
        self.status_layout.addWidget(self.status_icon)
        self.status_layout.addSpacing(10)
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addStretch(1)
        self.status_layout.addWidget(self.action_btn)
        
        # 输出格式选择行
        self.format_layout = QHBoxLayout()
        self.format_label = BodyLabel("输出格式:", self)
        self.format_combo = ComboBox(self)
        self._populate_format_combo()
        self.format_combo.setCurrentIndex(0)  # 默认 PDF
        
        self.format_layout.addWidget(self.format_label)
        self.format_layout.addWidget(self.format_combo)
        self.format_layout.addStretch(1)
        
        self.settings_layout.addLayout(self.status_layout)
        self.settings_layout.addSpacing(15)
        self.settings_layout.addLayout(self.format_layout)
        
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
        self.progress = EnhancedProgressBar(self)
        self.progress.hide()
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)
        
        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addSpacing(20)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)
        
        # 初始化
        self.files = []
        self.converter = LibreOfficeFormatConverter()
        self.thread = None
        self._status_worker = None
        
        # 连接信号
        self._log_bridged.connect(self.append_log)
        self._progress_bridged.connect(self.update_progress)
        self._finished_bridged.connect(self.on_finished)
        
        # 初始检查
        self.check_lo_status()
    
    def _populate_format_combo(self):
        """填充格式下拉框"""
        for group_name, formats in self.FORMAT_GROUPS.items():
            # 添加分组标题（使用分隔符）
            if self.format_combo.count() > 0:
                self.format_combo.addItem("─" * 30)  # 分隔线
            
            for display_name, ext in formats:
                self.format_combo.addItem(display_name)
    
    def _get_selected_format(self) -> str:
        """获取选中的输出格式扩展名"""
        text = self.format_combo.currentText()
        
        # 从所有格式中查找匹配的扩展名
        for group_name, formats in self.FORMAT_GROUPS.items():
            for display_name, ext in formats:
                if display_name == text:
                    return ext
        
        # 默认返回 pdf
        return 'pdf'
    
    def check_lo_status(self):
        """异步检测 LibreOffice 状态：解压/版本探测可达秒级，不能卡住 UI 线程"""
        if not self.lo_tool:
            self._set_status_error("内部错误: 未找到组件管理器")
            return

        self._set_status_busy("正在准备 LibreOffice…")

        def _apply(status):
            if not status or status.get("disabled"):
                self._set_status_error("LibreOffice 组件已禁用 (点击管理启用)", show_btn=True)
            elif status.get("installed"):
                version = status.get("version") or "未知版本"
                source = "便携版" if status.get("source") == "portable" else "系统版"
                self._set_status_ready(f"LibreOffice 已就绪 ({source} {version})")
            else:
                self._set_status_error("缺少 LibreOffice 组件 (点击管理安装)", show_btn=True)
            self.check_state()

        self._status_worker = self.lo_tool.refresh_status_async(_apply)

    def _set_status_busy(self, text):
        """准备中：既不是就绪也不是错误，避免把耗时解压误报成不可用"""
        self.status_icon.setIcon(FIF.SYNC)
        self.status_icon.setStyleSheet("IconWidget { color: #605E5C; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#605E5C", "#8A8886")
        self.action_btn.hide()

    
    def _set_status_ready(self, text):
        """设置就绪状态"""
        self.status_icon.setIcon(FIF.ACCEPT)
        self.status_icon.setStyleSheet("IconWidget { color: #107C10; }")
        self.status_label.setText(text)
        self.status_label.setTextColor("#107C10", "#107C10")
        self.action_btn.hide()
    
    def _set_status_error(self, text, show_btn=False):
        """设置错误状态"""
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
        window = self.window()
        if hasattr(window, 'switch_to_settings'):
            window.switch_to_settings()
    
    def add_files(self):
        """添加文件"""
        # 支持的输入格式
        filter_parts = [
            "所有支持的文件 (*.odt *.docx *.doc *.ods *.xlsx *.xls *.odp *.pptx *.ppt *.rtf *.txt *.html)",
            "文档格式 (*.odt *.docx *.doc *.rtf *.txt *.html)",
            "表格格式 (*.ods *.xlsx *.xls *.csv)",
            "演示格式 (*.odp *.pptx *.ppt)",
            "所有文件 (*.*)"
        ]
        
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", ";;".join(filter_parts)
        )
        
        if paths:
            self.on_files_dropped(paths)
    
    def on_files_dropped(self, paths):
        """处理拖放的文件"""
        # 支持的输入扩展名
        supported_exts = set()
        for formats in self.FORMAT_GROUPS.values():
            for _, ext in formats:
                supported_exts.add(f'.{ext}')
        
        # 添加额外的输入格式
        supported_exts.update(['.rtf'])
        
        count = 0
        for p in paths:
            if p not in self.files:
                ext = os.path.splitext(p)[1].lower()
                if ext in supported_exts:
                    self.files.append(p)
                    self.list_widget.addItem(os.path.basename(p))
                    count += 1
        
        if count > 0:
            self.append_log(f"📁 已添加 {count} 个文件")
        
        self.check_state()
    
    def clear_files(self):
        """清空文件列表"""
        self.files = []
        self.list_widget.clear()
        self.log_text.clear()
        self.check_state()
    
    def check_state(self):
        """检查状态并更新按钮"""
        has_files = len(self.files) > 0
        has_lo = self.lo_tool and self.lo_tool.is_available()
        self.start_btn.setEnabled(has_files and has_lo)
    
    def append_log(self, text):
        """追加日志"""
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def update_progress(self, curr, total, msg):
        """更新进度"""
        self.progress.update_progress(curr, total, msg)
        self.start_btn.setText(f"处理中... ({curr}/{total})")
    
    def start_conversion(self):
        """开始转换"""
        # UI 状态先在主线程读齐，避免异步回调时控件已被改
        output_format = self._get_selected_format()
        file_count = len(self.files)

        self.start_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self._set_status_busy("正在准备 LibreOffice…")

        def _ready(status):
            if not status or not status.get("installed"):
                InfoBar.error("错误", "LibreOffice 不可用", parent=self)
                self.start_btn.setEnabled(True)
                self.add_btn.setEnabled(True)
                self.clear_btn.setEnabled(True)
                self.check_lo_status()
                return

            self.log_text.clear()
            self.append_log(f"🚀 开始批量转换到 {output_format.upper()} 格式")
            self.append_log(f"📦 共 {file_count} 个文件")
            self.append_log("")

            self.thread = WorkerThread(
                self.converter.convert_batch, self.files, output_format,
                on_log=self._log_bridged.emit,
                on_progress=self._progress_bridged.emit,
                on_finished=self._finished_bridged.emit,
            )
            self.thread.error.connect(lambda msg: self.on_finished(0, 1))
            self.thread.start()

        self._status_worker = self.lo_tool.refresh_status_async(_ready)
    
    def on_finished(self, success, fail):
        """转换完成"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始转换")
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.progress.stop()
        self.progress.hide()
        
        if fail == 0:
            InfoBar.success(
                "完成", f"全部成功！共转换 {success} 个文件", 
                duration=3000, parent=self
            )
        else:
            InfoBar.warning(
                "完成", f"成功 {success} 个，失败 {fail} 个", 
                duration=3000, parent=self
            )
    
    def showEvent(self, event):
        """界面显示时刷新状态"""
        self.check_lo_status()
        super().showEvent(event)