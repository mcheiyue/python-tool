"""批量文件重命名界面"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QThread
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, PrimaryPushButton,
                            PushButton, TextEdit, InfoBar, LineEdit,
                            FluentIcon as FIF)

from core.features.utils import BatchRenamer
from ui.widgets.enhanced_progress import EnhancedProgressBar
from ui.design_system import Margins, Spacing


class RenameThread(QThread):
    """重命名执行线程"""
    
    def __init__(self, renamer, rename_plan):
        super().__init__()
        self.renamer = renamer
        self.rename_plan = rename_plan
    
    def run(self):
        self.renamer.execute(self.rename_plan)


class BatchRenameInterface(QWidget):
    """批量文件重命名界面"""
    
    # 预设模板
    PRESET_TEMPLATES = [
        ("{name}_{index}", "原名_序号"),
        ("{date}_{name}", "日期_原名"),
        ("{index}_{name}", "序号_原名"),
        ("文件_{index3}", "文件_三位序号"),
        ("{name}_{datetime}", "原名_日期时间"),
    ]
    
    MAX_FILES = 10000      # 最大文件数
    MAX_DEPTH = 10         # 最大递归深度

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("batch_rename_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)
        
        # 标题
        self.title = SubtitleLabel("批量文件重命名", self)
        self.desc = BodyLabel("支持模板变量的批量重命名工具 ({name}, {index}, {date}, {time} 等)", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)
        
        # 模板设置卡片
        self.template_card = CardWidget(self)
        self.template_layout = QVBoxLayout(self.template_card)
        self.template_layout.setContentsMargins(*Margins.CARD)
        
        # 模板输入行
        self.template_input_layout = QHBoxLayout()
        self.template_label = BodyLabel("重命名模板:", self)
        self.template_edit = LineEdit(self)
        self.template_edit.setPlaceholderText("例如: {name}_{index} 或 文件_{date}_{index3}")
        self.template_edit.setText("{name}_{index}")
        self.template_edit.textChanged.connect(self.on_template_changed)
        
        self.template_input_layout.addWidget(self.template_label)
        self.template_input_layout.addWidget(self.template_edit, 1)
        
        # 预设模板按钮行
        self.preset_layout = QHBoxLayout()
        self.preset_label = BodyLabel("快速模板:", self)
        self.preset_layout.addWidget(self.preset_label)
        
        for template, name in self.PRESET_TEMPLATES:
            btn = PushButton(name, self)
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda checked, t=template: self.template_edit.setText(t))
            self.preset_layout.addWidget(btn)
        
        self.preset_layout.addStretch(1)
        
        # 起始序号
        self.index_layout = QHBoxLayout()
        self.index_label = BodyLabel("起始序号:", self)
        self.index_edit = LineEdit(self)
        self.index_edit.setText("1")
        self.index_edit.setFixedWidth(80)
        self.index_layout.addWidget(self.index_label)
        self.index_layout.addWidget(self.index_edit)
        self.index_layout.addStretch(1)
        
        self.template_layout.addLayout(self.template_input_layout)
        self.template_layout.addSpacing(Spacing.MD)
        self.template_layout.addLayout(self.preset_layout)
        self.template_layout.addSpacing(Spacing.MD)
        self.template_layout.addLayout(self.index_layout)
        
        self.vbox.addWidget(self.template_card)
        
        # 工具栏
        self.toolbar = QHBoxLayout()
        self.add_btn = PrimaryPushButton(FIF.ADD, "添加文件", self)
        self.add_btn.clicked.connect(self.add_files)
        
        self.add_folder_btn = PushButton(FIF.FOLDER_ADD, "添加文件夹", self)
        self.add_folder_btn.clicked.connect(self.add_folder)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.preview_btn = PrimaryPushButton(FIF.VIEW, "预览", self)
        self.preview_btn.clicked.connect(self.preview_rename)
        self.preview_btn.setEnabled(False)
        
        self.toolbar.addWidget(self.add_btn)
        self.toolbar.addWidget(self.add_folder_btn)
        self.toolbar.addWidget(self.clear_btn)
        self.toolbar.addStretch(1)
        self.toolbar.addWidget(self.preview_btn)
        
        self.vbox.addLayout(self.toolbar)
        
        # 预览表格
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["原文件名", "新文件名", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        self.vbox.addWidget(self.table)
        
        # 底部
        self.bottom_layout = QHBoxLayout()
        
        self.progress = EnhancedProgressBar(self)
        self.progress.hide()
        
        self.execute_btn = PrimaryPushButton(FIF.ACCEPT, "执行重命名", self)
        self.execute_btn.clicked.connect(self.execute_rename)
        self.execute_btn.setEnabled(False)
        
        self.bottom_layout.addWidget(self.progress)
        self.bottom_layout.addSpacing(Spacing.LG)
        self.bottom_layout.addWidget(self.execute_btn)
        
        self.vbox.addLayout(self.bottom_layout)
        
        # 初始化
        self.files = []
        self.rename_plan = []
        self.renamer = BatchRenamer()
        self.thread = None
        
        # 连接信号
        self.renamer.log.connect(self.append_log)
        self.renamer.progress.connect(self.update_progress)
    
    def add_files(self):
        """添加文件"""
        paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "所有文件 (*.*)")
        if paths:
            self.on_files_added(paths)
    
    def add_folder(self):
        """添加文件夹中的所有文件"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return

        files = []
        depth_exceeded = False
        max_exceeded = False
        
        for root, dirs, filenames in os.walk(folder, followlinks=False):  # 不跟随符号链接
            # 计算当前深度
            depth = root.replace(folder, '').count(os.sep)
            
            if depth >= self.MAX_DEPTH:
                depth_exceeded = True
                dirs.clear()  # 阻止继续深入
                continue
            
            for filename in filenames:
                if len(files) >= self.MAX_FILES:
                    max_exceeded = True
                    break
                files.append(os.path.join(root, filename))
            
            if max_exceeded:
                break
        
        if files:
            self.on_files_added(files)
            
            # 显示警告信息
            if max_exceeded:
                InfoBar.warning(
                    "文件数量限制",
                    f"已达到最大文件数限制 ({self.MAX_FILES})，部分文件未添加",
                    duration=5000,
                    parent=self
                )
            elif depth_exceeded:
                InfoBar.info(
                    "深度限制",
                    f"已达到最大递归深度 ({self.MAX_DEPTH} 层)，更深层级的文件未添加",
                    duration=3000,
                    parent=self
                )
        else:
            InfoBar.warning("提示", "该文件夹中没有文件", parent=self)
    
    def on_files_added(self, paths):
        """处理添加的文件"""
        count = 0
        for p in paths:
            if p not in self.files and os.path.isfile(p):
                self.files.append(p)
                count += 1
        
        if count > 0:
            InfoBar.success("成功", f"已添加 {count} 个文件", duration=2000, parent=self)
            self.update_file_list()
            self.preview_btn.setEnabled(len(self.files) > 0)
    
    def clear_files(self):
        """清空文件列表"""
        self.files = []
        self.rename_plan = []
        self.table.setRowCount(0)
        self.preview_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
    
    def update_file_list(self):
        """更新文件列表显示"""
        self.table.setRowCount(len(self.files))
        for i, path in enumerate(self.files):
            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(path)))
            self.table.setItem(i, 1, QTableWidgetItem(""))
            self.table.setItem(i, 2, QTableWidgetItem("待预览"))
    
    def on_template_changed(self):
        """模板改变时，清空预览"""
        if len(self.files) > 0:
            for i in range(self.table.rowCount()):
                self.table.setItem(i, 1, QTableWidgetItem(""))
                self.table.setItem(i, 2, QTableWidgetItem("模板已更改，请重新预览"))
            self.execute_btn.setEnabled(False)
    
    def preview_rename(self):
        """预览重命名结果"""
        if not self.files:
            InfoBar.warning("提示", "请先添加文件", parent=self)
            return
        
        template = self.template_edit.text()
        
        # 验证模板
        valid, msg = self.renamer.validate_template(template)
        if not valid:
            InfoBar.error("模板错误", msg, parent=self)
            return
        
        # 获取起始序号
        try:
            start_index = int(self.index_edit.text())
        except ValueError:
            InfoBar.error("错误", "起始序号必须是数字", parent=self)
            return
        
        # 生成预览
        self.rename_plan = self.renamer.preview(self.files, template, start_index)
        
        # 更新表格
        conflict_count = 0
        for i, plan in enumerate(self.rename_plan):
            # 原文件名
            self.table.setItem(i, 0, QTableWidgetItem(plan['original_name']))
            
            # 新文件名
            new_name_item = QTableWidgetItem(plan['new_name'])
            if plan['conflict']:
                new_name_item.setForeground(QColor("#C42B1C"))  # 红色
            self.table.setItem(i, 1, new_name_item)
            
            # 状态
            if plan['conflict']:
                status_item = QTableWidgetItem(f"⚠️ {plan['conflict_msg']}")
                status_item.setForeground(QColor("#C42B1C"))
                conflict_count += 1
            else:
                status_item = QTableWidgetItem("✅ 就绪")
                status_item.setForeground(QColor("#107C10"))  # 绿色
            
            self.table.setItem(i, 2, status_item)
        
        # 显示结果
        if conflict_count > 0:
            InfoBar.warning(
                "警告", 
                f"预览完成，发现 {conflict_count} 个冲突，这些文件将被跳过",
                duration=3000,
                parent=self
            )
        else:
            InfoBar.success("成功", "预览完成，无冲突", duration=2000, parent=self)
        
        self.execute_btn.setEnabled(True)
    
    def execute_rename(self):
        """执行重命名"""
        if not self.rename_plan:
            InfoBar.warning("提示", "请先预览重命名结果", parent=self)
            return
        
        # 禁用按钮
        self.execute_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        
        # 创建并启动线程
        self.thread = RenameThread(self.renamer, self.rename_plan)
        self.thread.finished.connect(self.on_rename_finished)
        self.thread.start()
    
    def append_log(self, text):
        """追加日志（通过表格状态显示）"""
        # 这里可以扩展为独立的日志区域
        pass
    
    def update_progress(self, curr, total, msg):
        """更新进度"""
        self.progress.update_progress(curr, total, msg)
        self.execute_btn.setText(f"重命名中... ({curr}/{total})")
    
    def on_rename_finished(self):
        """重命名完成"""
        self.execute_btn.setEnabled(True)
        self.execute_btn.setText("执行重命名")
        self.preview_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.progress.stop()
        self.progress.hide()
        
        InfoBar.success("完成", "批量重命名已完成", duration=3000, parent=self)
        
        # 清空列表，重新开始
        self.clear_files()