# Phase 1 紧急修复实施计划

## 概览

本计划涵盖产品审计报告中确定的 4 个高严重度问题的修复方案。

---

## 1. PDF合并列表同步问题

### 问题分析
当前 [`PDFMergeInterface`](ui/interfaces/pdf/pdf_merge_interface.py:145) 使用两个独立的数据结构：
- `self.files`: Python 列表，存储完整文件路径
- `self.list_widget`: QListWidget，显示文件名

问题场景：
- `move_up()` 和 `move_down()` 方法同时更新了两个数据结构 ✅
- 但 `DragDropListWidget` 继承自 `QListWidget`，可能支持内部拖拽排序
- 如果用户直接拖拽列表项，`self.files` 不会同步

### 解决方案
**方案A（推荐）：废弃独立的 `self.files` 列表，使用 `QListWidgetItem.data(Qt.UserRole)` 存储路径**

这样做的好处：
1. 单一数据源，避免同步问题
2. 简化代码
3. 支持未来扩展（如拖拽排序）

### 代码修改

#### 1.1 修改 `PDFMergeInterface`

```python
# ui/interfaces/pdf/pdf_merge_interface.py

# 删除: self.files = [] (第145行)

def on_files_dropped(self, paths):
    for p in paths:
        # 检查是否已存在
        existing_paths = self._get_all_paths()
        if p not in existing_paths:
            ext = os.path.splitext(p)[1].lower()
            if ext == '.pdf':
                item = QListWidgetItem(os.path.basename(p))
                item.setData(Qt.ItemDataRole.UserRole, p)  # 存储完整路径
                self.list_widget.addItem(item)
    self.check_state()

def _get_all_paths(self) -> list:
    """从列表控件获取所有文件路径"""
    paths = []
    for i in range(self.list_widget.count()):
        item = self.list_widget.item(i)
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            paths.append(path)
    return paths

def clear_files(self):
    self.list_widget.clear()
    self.log_text.clear()
    self.progress.hide()
    self.check_state()

def remove_selected(self):
    rows = sorted([item.row() for item in self.list_widget.selectedIndexes()], reverse=True)
    for row in rows:
        self.list_widget.takeItem(row)
    self.check_state()

def move_up(self):
    row = self.list_widget.currentRow()
    if row > 0:
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row-1, item)
        self.list_widget.setCurrentRow(row-1)

def move_down(self):
    row = self.list_widget.currentRow()
    count = self.list_widget.count()
    if row < count - 1 and row != -1:
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row+1, item)
        self.list_widget.setCurrentRow(row+1)

def check_state(self):
    has_files = self.list_widget.count() > 0
    has_out = bool(self.out_edit.text().strip())
    self.start_btn.setEnabled(has_files and has_out)
    
    if has_files and not has_out and not self.out_edit.text():
        # 自动生成默认路径
        first_path = self.list_widget.item(0).data(Qt.ItemDataRole.UserRole)
        if first_path:
            dir_name = os.path.dirname(first_path)
            self.out_edit.setText(os.path.join(dir_name, "merged_output.pdf"))
            self.start_btn.setEnabled(True)

def start_merge(self):
    output_path = self.out_edit.text().strip()
    files = self._get_all_paths()  # 使用新方法获取路径
    if not output_path or not files: 
        return
    
    # ... 其余代码保持不变，将 self.files 替换为 files
    self.thread = MergeThread(self.merger, files, output_path)
    self.thread.start()
```

#### 1.2 需要导入的模块
```python
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtCore import Qt
```

---

## 2. 图片转换线程池限制

### 问题分析
当前 [`ImageConvertInterface.start_conversion()`](ui/interfaces/image/image_convert_interface.py:183) 为每个文件创建独立线程，没有并发限制。

### 解决方案
使用 `QThreadPool` + `QRunnable` 模式，限制并发数。

### 代码修改

#### 2.1 创建可复用的任务类

```python
# ui/interfaces/image/image_convert_interface.py

from PyQt6.QtCore import QThreadPool, QRunnable, QObject, pyqtSignal

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
```

#### 2.2 修改 `ImageConvertInterface`

```python
class ImageConvertInterface(QWidget):
    def __init__(self, parent=None):
        # ... 现有代码 ...
        
        # 替换 self.threads = []
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # 限制最大并发数为 4
        
        self.finished_count = 0
        self.total = 0
        self.success_count = 0
        self.error_count = 0

    def start_conversion(self):
        if not self.files: 
            return
            
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.log_text.append(f"开始转换任务... (最大并发: {self.thread_pool.maxThreadCount()})")
        
        target_format = self.format_combo.currentText()
        quality = self.quality_slider.value()
        
        # 获取旋转参数
        rotate_idx = self.rotate_combo.currentIndex()
        rotate_angle = [0, 90, 180, 270][rotate_idx]
        
        # 获取翻转参数
        flip_idx = self.flip_combo.currentIndex()
        flip_mode = [None, 'H', 'V'][flip_idx]

        self.total = len(self.files)
        self.finished_count = 0
        self.success_count = 0
        self.error_count = 0
        
        for input_path in self.files:
            # 构建输出路径
            dir_name = os.path.dirname(input_path)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = target_format.lower()
            if ext == 'jpeg': 
                ext = 'jpg'
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
        if success:
            self.success_count += 1
            self.log_text.append(f"✅ {os.path.basename(input_path)}")
        else:
            self.error_count += 1
            self.log_text.append(f"❌ {os.path.basename(input_path)}: {message}")
        
        self._check_all_done()

    def on_task_error(self, input_path, error_message):
        self.finished_count += 1
        self.error_count += 1
        self.log_text.append(f"❌ {os.path.basename(input_path)}: {error_message}")
        self._check_all_done()

    def _check_all_done(self):
        if self.finished_count >= self.total:
            self.start_btn.setEnabled(True)
            self.log_text.append(f"\n任务完成: 成功 {self.success_count}, 失败 {self.error_count}")
            
            # InfoBar 通知
            if self.error_count == 0:
                InfoBar.success("转换完成", f"成功处理 {self.total} 个文件", duration=5000, parent=self)
            else:
                InfoBar.warning("转换完成", f"成功 {self.success_count}, 失败 {self.error_count}", duration=5000, parent=self)
```

---

## 3. 批量重命名递归保护

### 问题分析
[`BatchRenameInterface.add_folder()`](ui/interfaces/utils/batch_rename_interface.py:170) 使用 `os.walk()` 无限制递归遍历，可能导致：
- 选择系统根目录时内存溢出
- 符号链接循环导致无限递归

### 解决方案
添加深度限制和文件数量限制，并在 UI 上提供反馈。

### 代码修改

```python
# ui/interfaces/utils/batch_rename_interface.py

# 添加类常量
class BatchRenameInterface(QWidget):
    MAX_FILES = 10000      # 最大文件数
    MAX_DEPTH = 10         # 最大递归深度
    
    # ... 现有代码 ...
    
    def add_folder(self):
        """添加文件夹中的所有文件（带保护）"""
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
```

---

## 4. 懒加载失败处理改进

### 问题分析
[`UILazyLoader._load_target_interface()`](core/utils/lazy_loader.py:86) 加载失败时只显示简单文字，没有恢复机制。

### 解决方案
1. 添加"重试"按钮
2. 显示详细错误信息
3. 添加超时检测

### 代码修改

```python
# core/utils/lazy_loader.py

import importlib
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from qfluentwidgets import (IndeterminateProgressRing, StrongBodyLabel, 
                            PushButton, BodyLabel, FluentIcon as FIF)

class UILazyLoader(QWidget):
    """UI 懒加载代理组件（带错误恢复）"""
    
    LOAD_TIMEOUT_MS = 10000  # 10秒超时
    
    def __init__(self, module_path: str, class_name: str, *args, **kwargs):
        super().__init__()
        
        self.module_path = module_path
        self.class_name = class_name
        self.args = args
        self.kwargs = kwargs
        
        self._is_loaded = False
        self._is_loading = False
        self._real_interface = None
        self._error_message = None
        
        # 初始化加载界面
        self._init_loading_ui()
        
        self.setObjectName(f"lazy_{class_name}")
        
        # 超时定时器
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)

    def _init_loading_ui(self):
        """初始化加载中的占位界面"""
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载动画
        self.loading_ring = IndeterminateProgressRing(self)
        self.loading_ring.setFixedSize(60, 60)
        
        # 提示文本
        self.loading_label = StrongBodyLabel("正在初始化功能模块...", self)
        
        # 错误信息标签（初始隐藏）
        self.error_label = BodyLabel("", self)
        self.error_label.setWordWrap(True)
        self.error_label.setTextColor("#C42B1C", "#FF6B6B")
        self.error_label.hide()
        
        # 重试按钮（初始隐藏）
        self.retry_btn = PushButton(FIF.SYNC, "重试加载", self)
        self.retry_btn.clicked.connect(self._retry_load)
        self.retry_btn.hide()
        
        self.layout.addWidget(self.loading_ring)
        self.layout.addSpacing(16)
        self.layout.addWidget(self.loading_label)
        self.layout.addSpacing(8)
        self.layout.addWidget(self.error_label)
        self.layout.addSpacing(16)
        self.layout.addWidget(self.retry_btn)

    def showEvent(self, event):
        """当界面显示时触发"""
        super().showEvent(event)
        
        if not self._is_loaded and not self._is_loading:
            QTimer.singleShot(50, self._load_target_interface)

    def _load_target_interface(self):
        """加载目标界面"""
        if self._is_loaded or self._is_loading:
            return
        
        self._is_loading = True
        self._show_loading_state()
        
        # 启动超时定时器
        self._timeout_timer.start(self.LOAD_TIMEOUT_MS)

        try:
            # 1. 动态导入模块
            module = importlib.import_module(self.module_path)
            
            # 2. 获取类
            cls = getattr(module, self.class_name)
            
            # 3. 实例化
            self._real_interface = cls(*self.args, **self.kwargs)
            
            # 4. 停止超时定时器
            self._timeout_timer.stop()
            
            # 5. 替换 UI
            self._replace_ui()
            
            self._is_loaded = True
            self._is_loading = False
            
        except Exception as e:
            import traceback
            self._timeout_timer.stop()
            self._is_loading = False
            self._error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self._show_error_state(f"加载失败: {str(e)}")

    def _on_timeout(self):
        """加载超时处理"""
        if self._is_loading and not self._is_loaded:
            self._is_loading = False
            self._show_error_state("加载超时，模块可能存在问题")

    def _show_loading_state(self):
        """显示加载中状态"""
        self.loading_ring.show()
        self.loading_label.setText("正在初始化功能模块...")
        self.loading_label.show()
        self.error_label.hide()
        self.retry_btn.hide()

    def _show_error_state(self, message: str):
        """显示错误状态"""
        self.loading_ring.hide()
        self.loading_label.setText("⚠️ 模块加载失败")
        self.error_label.setText(message)
        self.error_label.show()
        self.retry_btn.show()
        
        # 打印完整错误到控制台
        if self._error_message:
            print(f"[UILazyLoader] 加载 {self.module_path}.{self.class_name} 失败:")
            print(self._error_message)

    def _retry_load(self):
        """重试加载"""
        self._error_message = None
        self._load_target_interface()

    def _replace_ui(self):
        """将当前布局替换为目标界面的布局"""
        # 移除加载组件
        self.loading_ring.deleteLater()
        self.loading_label.deleteLater()
        self.error_label.deleteLater()
        self.retry_btn.deleteLater()
        
        # 移除旧布局
        QWidget().setLayout(self.layout)
        
        # 添加实际界面
        new_layout = QVBoxLayout(self)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self._real_interface)
        
        # 同步 objectName
        if self._real_interface.objectName():
            self.setObjectName(self._real_interface.objectName())

    def __getattr__(self, name):
        """代理属性访问"""
        if self._real_interface:
            return getattr(self._real_interface, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' (Module not loaded yet)")
```

---

## 测试计划

### 1. PDF合并列表同步测试
- [ ] 添加多个 PDF 文件
- [ ] 使用上移/下移按钮调整顺序，验证合并顺序正确
- [ ] 删除选中项，验证不影响其他项
- [ ] 清空列表后重新添加

### 2. 图片转换线程池测试
- [ ] 添加 50+ 图片文件
- [ ] 观察 CPU 使用率是否稳定
- [ ] 验证所有文件都能正确处理
- [ ] 测试中途关闭界面的行为

### 3. 批量重命名递归保护测试
- [ ] 选择一个深层目录结构（>10层）
- [ ] 选择一个包含大量文件的目录（>10000文件）
- [ ] 验证警告信息正确显示
- [ ] 验证程序不会卡死

### 4. 懒加载失败处理测试
- [ ] 模拟模块导入失败（临时重命名依赖模块）
- [ ] 验证显示错误信息
- [ ] 验证重试按钮功能
- [ ] 测试超时情况

---

## 实施顺序

1. **PDF合并列表同步** - 最简单，可先完成
2. **批量重命名递归保护** - 较简单，独立修改
3. **懒加载失败处理** - 中等复杂度
4. **图片转换线程池** - 最复杂，需要重构线程模型

---

*计划创建时间: 2026-01-08*