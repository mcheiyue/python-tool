import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from qfluentwidgets import ProgressBar, BodyLabel, CaptionLabel

from ui.design_system import Spacing, Margins, Colors

class EnhancedProgressBar(QWidget):
    """
    增强型进度条组件
    
    功能:
    1. 显示当前进度 (数字/百分比)
    2. 显示状态消息
    3. 估算剩余时间 (ETA)
    4. 显示处理速度
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(*Margins.ZERO)
        self.layout.setSpacing(Spacing.XS)
        
        # 顶部信息行 (状态 + 剩余时间)
        self.info_layout = QHBoxLayout()
        self.status_label = BodyLabel("准备就绪", self)
        self.time_label = CaptionLabel("", self)
        self.time_label.setTextColor(Colors.WARNING_LIGHT, Colors.WARNING_DARK) # 使用警告色突出显示时间
        
        self.info_layout.addWidget(self.status_label)
        self.info_layout.addStretch(1)
        self.info_layout.addWidget(self.time_label)
        
        # 进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.layout.addLayout(self.info_layout)
        self.layout.addWidget(self.progress_bar)
        
        # 内部状态
        self._start_time = None
        self._last_update_time = None
        self._processed_count = 0
        
    def start(self, total: int = 100):
        """开始任务"""
        self._start_time = time.time()
        self._last_update_time = self._start_time
        self._processed_count = 0
        
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.status_label.setText("开始处理...")
        self.time_label.setText("正在估算时间...")
        self.show()
        
    def update_progress(self, current: int, total: int = 0, message: str = ""):
        """更新进度"""
        if self._start_time is None:
            self.start(total)
            
        self.progress_bar.setValue(current)
        if total > 0:
            self.progress_bar.setMaximum(total)
            
        # 更新状态文本
        if message:
            self.status_label.setText(f"{message} ({current}/{total})")
        else:
            self.status_label.setText(f"处理中... ({current}/{total})")
            
        # 估算剩余时间 (每 0.5 秒更新一次计算，避免过于频繁)
        now = time.time()
        if now - self._last_update_time > 0.5 and current > 0:
            elapsed = now - self._start_time
            avg_time_per_item = elapsed / current
            remaining_items = total - current
            remaining_seconds = int(avg_time_per_item * remaining_items)
            
            # 格式化时间
            if remaining_seconds < 60:
                time_str = f"{remaining_seconds} 秒"
            else:
                mins, secs = divmod(remaining_seconds, 60)
                time_str = f"{mins} 分 {secs} 秒"
                
            self.time_label.setText(f"约剩余 {time_str}")
            self._last_update_time = now
            
    def stop(self):
        """停止/完成"""
        self.status_label.setText("已完成")
        self.time_label.setText("")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self._start_time = None
    
    def reset(self):
        """重置状态"""
        self.progress_bar.setValue(0)
        self.status_label.setText("准备就绪")
        self.time_label.setText("")
        self._start_time = None