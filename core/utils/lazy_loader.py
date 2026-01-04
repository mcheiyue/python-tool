import importlib
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from qfluentwidgets import IndeterminateProgressRing, StrongBodyLabel

class UILazyLoader(QWidget):
    """
    UI 懒加载代理组件
    
    用于替代直接实例化的界面类。只有当此组件第一次被显示（showEvent）时，
    才会动态导入并实例化目标界面类。
    """
    
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
        self._real_interface = None
        
        # 初始化加载界面
        self._init_loading_ui()
        
        # 设置 objectName 以便 QFluentWidgets 导航栏可以正确识别
        # 通常导航栏使用 objectName 来跟踪
        # 这里我们预设一个临时的，实际加载后可以同步
        self.setObjectName(f"lazy_{class_name}")

    def _init_loading_ui(self):
        """初始化加载中的占位界面"""
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载动画
        self.loading_ring = IndeterminateProgressRing(self)
        self.loading_ring.setFixedSize(60, 60)
        
        # 提示文本
        self.loading_label = StrongBodyLabel("正在初始化功能模块...", self)
        
        self.layout.addWidget(self.loading_ring)
        self.layout.addSpacing(16)
        self.layout.addWidget(self.loading_label)

    def showEvent(self, event):
        """当界面显示时触发"""
        super().showEvent(event)
        
        if not self._is_loaded:
            # 使用 QTimer.singleShot 确保 UI 先渲染出加载动画，避免卡顿
            QTimer.singleShot(50, self._load_target_interface)

    def _load_target_interface(self):
        """加载目标界面"""
        if self._is_loaded:
            return

        try:
            # 1. 动态导入模块
            module = importlib.import_module(self.module_path)
            
            # 2. 获取类
            cls = getattr(module, self.class_name)
            
            # 3. 实例化
            # 注意：这里假设目标类的 __init__ 接受 *args 和 **kwargs
            # 对于目前的 Interfaces，通常第一个参数是 parent (MainWindow)
            self._real_interface = cls(*self.args, **self.kwargs)
            
            # 4. 替换 UI
            self._replace_ui()
            
            self._is_loaded = True
            
        except Exception as e:
            import traceback
            error_msg = f"加载模块失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.loading_label.setText("模块加载失败")
            # 可以显示一个错误图标或重试按钮

    def _replace_ui(self):
        """将当前布局替换为目标界面的布局"""
        # 移除加载组件
        self.loading_ring.deleteLater()
        self.loading_label.deleteLater()
        
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
