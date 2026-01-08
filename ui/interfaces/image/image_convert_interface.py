import os
import subprocess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog, QListWidgetItem
from PyQt6.QtGui import QFont, QAction, QKeySequence
from PyQt6.QtCore import Qt, QTimer, QThreadPool, QRunnable, QObject, pyqtSignal
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, ComboBox, Slider,
                            PushButton, PrimaryPushButton, TextEdit, InfoBar,
                            FluentIcon as FIF)

from core.features.image.image_converter import ImageConverter
from ui.widgets import DragDropListWidget, CancellableProgressWidget
from ui.design_system import Margins, Spacing

class ConvertTaskSignals(QObject):
    """任务信号类"""
    finished = pyqtSignal(str, bool, str)  # input_path, success, message
    error = pyqtSignal(str, str)  # input_path, error_message

class ConvertTask(QRunnable):
    """单个转换任务"""
    
    def __init__(self, converter, input_path, output_path, target_format, quality, rotate_angle, flip_mode):
        super().__init__()
        self.converter = converter
        self.input_path = input_path
        self.output_path = output_path
        self.target_format = target_format
        self.quality = quality
        self.rotate_angle = rotate_angle
        self.flip_mode = flip_mode
        self.signals = ConvertTaskSignals()
    
    def run(self):
        try:
            success = self.converter.convert(
                self.input_path,
                self.output_path,
                self.target_format,
                self.quality,
                self.rotate_angle,
                self.flip_mode
            )
            self.signals.finished.emit(self.input_path, success, "")
        except Exception as e:
            self.signals.error.emit(self.input_path, str(e))

class ImageConvertInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image_convert_interface")
        self.converter = ImageConverter()
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(*Margins.PAGE)
        self.vbox.setSpacing(Spacing.LG)

        self.title = SubtitleLabel("图片格式转换", self)
        self.desc = BodyLabel("支持 JPG, PNG, WEBP, BMP, ICO 格式互转及旋转/翻转", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 设置区域
        self.settings_card = CardWidget(self)
        self.settings_layout = QGridLayout(self.settings_card)
        self.settings_layout.setContentsMargins(*Margins.CARD)
        self.settings_layout.setSpacing(Spacing.MD)

        # 输出格式选择
        self.format_label = BodyLabel("输出格式:", self)
        self.format_combo = ComboBox(self)
        self.format_combo.addItems(['JPG', 'PNG', 'WEBP', 'BMP', 'ICO'])
        self.format_combo.setCurrentText('PNG')
        
        # 质量选择
        self.quality_label = BodyLabel("质量 (JPG/WEBP):", self)
        self.quality_label.setToolTip("设置 JPG/WEBP 格式的压缩质量\n100 = 最佳质量但文件最大\n90 = 推荐值，肉眼几乎无法区分\n75 = 适合网页使用的平衡点")
        self.quality_slider = Slider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(90)
        self.quality_val = BodyLabel("90")
        self.quality_slider.valueChanged.connect(lambda v: self.quality_val.setText(str(v)))

        self.settings_layout.addWidget(self.format_label, 0, 0)
        self.settings_layout.addWidget(self.format_combo, 0, 1)
        self.settings_layout.addWidget(self.quality_label, 0, 2)
        self.settings_layout.addWidget(self.quality_slider, 0, 3)
        self.settings_layout.addWidget(self.quality_val, 0, 4)

        # 旋转选择
        self.rotate_label = BodyLabel("旋转:", self)
        self.rotate_combo = ComboBox(self)
        self.rotate_combo.addItems(['无', '90° (顺时针)', '180°', '90° (逆时针)'])
        self.rotate_combo.setCurrentIndex(0)
        
        # 翻转选择
        self.flip_label = BodyLabel("翻转:", self)
        self.flip_combo = ComboBox(self)
        self.flip_combo.addItems(['无', '水平翻转', '垂直翻转'])
        self.flip_combo.setCurrentIndex(0)

        self.settings_layout.addWidget(self.rotate_label, 1, 0)
        self.settings_layout.addWidget(self.rotate_combo, 1, 1)
        self.settings_layout.addWidget(self.flip_label, 1, 2)
        self.settings_layout.addWidget(self.flip_combo, 1, 3)

        self.vbox.addWidget(self.settings_card)
        
        # 进度条
        self.progress = CancellableProgressWidget(self)
        self.progress.cancel_clicked.connect(self.on_cancel_task)
        self.progress.hide()
        self.vbox.addWidget(self.progress)

        # 文件列表
        self.content_layout = QHBoxLayout()
        self.list_widget = DragDropListWidget(self, "拖拽图片文件到此处，\n支持批量格式转换")
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
        self.add_btn.setToolTip("添加图片文件 (Ctrl+O)")
        self.add_btn.clicked.connect(self.add_files)
        
        self.clear_btn = PushButton(FIF.DELETE, "清空", self)
        self.clear_btn.setToolTip("清空列表 (Delete)")
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始转换", self)
        self.start_btn.setToolTip("开始转换 (Ctrl+Enter)")
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)

        self.bottom_layout.addWidget(self.add_btn)
        self.bottom_layout.addWidget(self.clear_btn)
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.start_btn)
        self.vbox.addLayout(self.bottom_layout)
        
        # 快捷键
        self.add_action = QAction(self)
        self.add_action.setShortcut(QKeySequence("Ctrl+O"))
        self.add_action.triggered.connect(self.add_files)
        self.addAction(self.add_action)
        
        self.run_action = QAction(self)
        self.run_action.setShortcut(QKeySequence("Ctrl+Return"))
        self.run_action.triggered.connect(self.start_conversion)
        self.addAction(self.run_action)
        
        self.del_action = QAction(self)
        self.del_action.setShortcut(QKeySequence("Delete"))
        self.del_action.triggered.connect(self.remove_selection)
        self.addAction(self.del_action)

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # 限制最大并发数为 4
        
        self.finished_count = 0
        self.total = 0
        self.success_count = 0
        self.error_count = 0
        self._is_cancelling = False  # 取消标志
        
        # 连接日志信号
        self.converter.log.connect(self.log_text.append)
    
    def on_cancel_task(self):
        """处理取消任务请求"""
        if self.finished_count < self.total:
            self._is_cancelling = True
            self.log_text.append("\n用户请求取消任务...")
            self.log_text.append("正在等待当前任务完成...")
            # 清空线程池队列中未执行的任务
            self.thread_pool.clear()

    def _get_all_paths(self) -> list:
        """从列表控件获取所有文件路径"""
        paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        return paths

    def remove_selection(self):
        # 从后往前删
        rows = sorted([item.row() for item in self.list_widget.selectedIndexes()], reverse=True)
        for row in rows:
            self.list_widget.takeItem(row)
        if self.list_widget.count() == 0:
            self.start_btn.setEnabled(False)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.ico)")
        if paths: self.on_files_dropped(paths)

    def on_files_dropped(self, paths):
        current_paths = self._get_all_paths()
        for p in paths:
            if p not in current_paths:
                item = QListWidgetItem(os.path.basename(p))
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.start_btn.setEnabled(True)

    def clear_files(self):
        self.list_widget.clear()
        self.log_text.clear()
        self.start_btn.setEnabled(False)

    def start_conversion(self):
        files = self._get_all_paths()
        if not files: return
        
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.log_text.append(f"开始转换任务... (最大并发: {self.thread_pool.maxThreadCount()})")
        
        target_format = self.format_combo.currentText()
        quality = self.quality_slider.value()

        # 获取旋转参数
        rotate_idx = self.rotate_combo.currentIndex()
        rotate_angle = 0
        if rotate_idx == 1: rotate_angle = 90
        elif rotate_idx == 2: rotate_angle = 180
        elif rotate_idx == 3: rotate_angle = 270
        
        # 获取翻转参数
        flip_idx = self.flip_combo.currentIndex()
        flip_mode = None
        if flip_idx == 1: flip_mode = 'H'
        elif flip_idx == 2: flip_mode = 'V'

        self.total = len(files)
        self.finished_count = 0
        self.success_count = 0
        self.error_count = 0
        self._is_cancelling = False  # 重置取消标志
        
        self.progress.start(self.total)
        self.progress.show()
        
        for input_path in files:
            # 构建输出路径
            dir_name = os.path.dirname(input_path)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = target_format.lower()
            if ext == 'jpeg': ext = 'jpg'
            output_path = os.path.join(dir_name, f"{base_name}.{ext}")
            
            # 创建任务
            task = ConvertTask(
                self.converter, input_path, output_path,
                target_format, quality, rotate_angle, flip_mode
            )
            task.signals.finished.connect(self.on_task_finished)
            task.signals.error.connect(self.on_task_error)
            
            # 提交到线程池
            self.thread_pool.start(task)

    def on_task_finished(self, input_path, success, message):
        self.finished_count += 1
        
        if not self._is_cancelling:
            self.progress.update_progress(self.finished_count, self.total, f"正在转换: {os.path.basename(input_path)}")
            
        if success:
            self.success_count += 1
            if not self._is_cancelling:
                self.log_text.append(f"✅ {os.path.basename(input_path)}")
        else:
            self.error_count += 1
            if not self._is_cancelling:
                self.log_text.append(f"❌ {os.path.basename(input_path)}: {message}")
        
        self._check_all_done()

    def on_task_error(self, input_path, error_message):
        self.finished_count += 1
        
        if not self._is_cancelling:
            self.progress.update_progress(self.finished_count, self.total, f"出错: {os.path.basename(input_path)}")
            
        self.error_count += 1
        if not self._is_cancelling:
            self.log_text.append(f"❌ {os.path.basename(input_path)}: {error_message}")
        self._check_all_done()

    def _check_all_done(self):
        if self.finished_count >= self.total:
            self.start_btn.setEnabled(True)
            
            # 检查是否被取消
            if self._is_cancelling:
                cancelled_count = self.total - self.finished_count
                self.log_text.append(f"\n任务已取消: 已完成 {self.finished_count}/{self.total}, 成功 {self.success_count}, 失败 {self.error_count}")
                self.progress.set_complete(success=False)
                InfoBar.warning("已取消", f"任务已取消，已处理 {self.finished_count} 个文件", duration=5000, parent=self)
                self._is_cancelling = False
            else:
                self.log_text.append(f"\n任务完成: 成功 {self.success_count}, 失败 {self.error_count}")
                self.progress.set_complete(success=(self.error_count == 0))
                
                # InfoBar 通知
                if self.error_count == 0:
                    InfoBar.success("转换完成", f"成功处理 {self.total} 个文件", duration=5000, parent=self)
                else:
                    InfoBar.warning("转换完成", f"成功 {self.success_count}, 失败 {self.error_count}", duration=5000, parent=self)
                
            # 由于可能包含多个输出目录，这里打开第一个文件的目录
            files = self._get_all_paths()
            if files:
                first_dir = os.path.dirname(files[0])
                open_folder_btn = PushButton("打开所在文件夹")
                def open_folder():
                    def do_open():
                        if os.name == 'nt':
                            subprocess.Popen(['explorer', first_dir], shell=False)
                        else:
                            from PyQt6.QtGui import QDesktopServices
                            from PyQt6.QtCore import QUrl
                            QDesktopServices.openUrl(QUrl.fromLocalFile(first_dir))
                    QTimer.singleShot(300, do_open)
                open_folder_btn.clicked.connect(open_folder)
