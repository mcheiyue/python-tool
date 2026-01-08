import importlib
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from qfluentwidgets import (IndeterminateProgressRing, StrongBodyLabel,
                            PushButton, BodyLabel, FluentIcon as FIF)

class UILazyLoader(QWidget):
    """
    UI 懒加载代理组件
    
    用于替代直接实例化的界面类。只有当此组件第一次被显示（showEvent）时，
    才会动态导入并实例化目标界面类。
    """
    
    LOAD_TIMEOUT_MS = 10000  # 10秒超时
    
    def __init__(self, module_path: str, class_name: str, *args, **kwargs):
        """
        :param module_path: 目标模块路径 (如 'ui.interfaces.ppt_interface')
        :param class_name: 目标类名 (如 'PPTInterface')
        :param args: 传递给目标类构造函数的位置参数
        :param kwargs: 传递给目标类构造函数的关键字参数
        """
        super().__init__()
        
        # 存储参数以便延迟加载
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
        
        # 设置 objectName 以便 QFluentWidgets 导航栏可以正确识别
        # 通常导航栏使用 objectName 来跟踪
        # 这里我们预设一个临时的，实际加载后可以同步
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
            # 使用 QTimer.singleShot 确保 UI 先渲染出加载动画，避免卡顿
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
            # 注意：这里假设目标类的 __init__ 接受 *args 和 **kwargs
            # 对于目前的 Interfaces，通常第一个参数是 parent (MainWindow)
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
        QWidget().setLayout(self.layout) # trick to delete layout
        
        # 将实际界面的内容添加到当前 Widget
        # 注意：这里有两种策略
        # A. 将 self._real_interface 作为子控件添加 (推荐)
        # B. 如果 self._real_interface 本身是 QWidget，直接把它塞进布局
        
        new_layout = QVBoxLayout(self)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.addWidget(self._real_interface)
        
        # 同步 objectName，确保主题切换等功能正常工作
        if self._real_interface.objectName():
            self.setObjectName(self._real_interface.objectName())
        
        # 如果目标界面有特定的方法需要暴露，这里可能需要做代理
        # 目前主要用于显示，基本够用

    def __getattr__(self, name):
        """
        代理属性访问
        如果外部代码尝试访问 lazy_loader.some_method，
        尝试转发给真实的 interface 实例
        """
        if self._real_interface:
            return getattr(self._real_interface, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' (Module not loaded yet)")
