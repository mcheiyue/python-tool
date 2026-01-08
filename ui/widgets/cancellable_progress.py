"""
可取消的进度条组件

封装 EnhancedProgressBar + 取消按钮，提供统一的任务控制界面
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import PushButton, FluentIcon

from ui.widgets.enhanced_progress import EnhancedProgressBar
from ui.design_system import Spacing, Margins


class CancellableProgressWidget(QWidget):
    """
    带取消按钮的进度条组件
    
    特性:
    - 封装 EnhancedProgressBar，支持 ETA 显示
    - 提供取消按钮，可以中断长时间任务
    - 自动管理按钮状态（运行中/取消中/已完成）
    
    使用示例:
    ```python
    # 创建组件
    self.progress = CancellableProgressWidget()
    self.progress.cancel_clicked.connect(self.on_cancel_task)
    self.layout.addWidget(self.progress)
    
    # 开始任务
    self.progress.start(total=100)
    self.progress.show()
    
    # 更新进度
    self.progress.update_progress(50, 100, "处理中...")
    
    # 完成任务
    self.progress.set_complete(success=True)
    ```
    """
    
    cancel_clicked = pyqtSignal()
    
    def __init__(self, parent=None, show_eta=True):
        """
        初始化组件
        
        Args:
            parent: 父控件
            show_eta: 是否显示剩余时间（默认 True）
        """
        super().__init__(parent)
        self.show_eta = show_eta
        self._is_cancelled = False
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(*Margins.ZERO)
        layout.setSpacing(Spacing.MD)
        
        # 进度条
        self.progress_bar = EnhancedProgressBar(self)
        
        # 取消按钮
        self.cancel_btn = PushButton("取消", self)
        self.cancel_btn.setIcon(FluentIcon.CANCEL)
        self.cancel_btn.setFixedWidth(80)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        layout.addWidget(self.progress_bar, 1)
        layout.addWidget(self.cancel_btn)
    
    def _on_cancel_clicked(self):
        """取消按钮点击处理"""
        if self._is_cancelled:
            return
            
        self._is_cancelled = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("取消中...")
        self.progress_bar.status_label.setText("正在取消任务...")
        self.cancel_clicked.emit()
    
    def start(self, total: int = 100):
        """
        开始任务
        
        Args:
            total: 总任务数
        """
        self._is_cancelled = False
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("取消")
        self.progress_bar.start(total)
        self.show()
    
    def update_progress(self, current: int, total: int = 0, message: str = ""):
        """
        更新进度
        
        Args:
            current: 当前进度
            total: 总数（可选）
            message: 状态消息（可选）
        """
        if not self._is_cancelled:
            self.progress_bar.update_progress(current, total, message)
    
    def stop(self):
        """停止任务（完成或失败）"""
        self.progress_bar.stop()
        self.cancel_btn.setEnabled(False)
    
    def set_complete(self, success: bool = True):
        """
        设置任务完成状态
        
        Args:
            success: 是否成功完成
        """
        self.stop()
        
        if self._is_cancelled:
            self.cancel_btn.setText("已取消")
            self.progress_bar.status_label.setText("任务已取消")
        elif success:
            self.cancel_btn.setText("完成")
            self.progress_bar.status_label.setText("已完成")
        else:
            self.cancel_btn.setText("失败")
            self.progress_bar.status_label.setText("处理失败")
    
    def reset(self):
        """重置到初始状态"""
        self._is_cancelled = False
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("取消")
        self.progress_bar.reset()
        self.hide()
    
    @property
    def is_cancelled(self) -> bool:
        """
        检查是否已取消
        
        Returns:
            bool: 如果用户点击了取消按钮返回 True
        """
        return self._is_cancelled