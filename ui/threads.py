from PyQt6.QtCore import QThread, pyqtSignal
from typing import Callable, Any, Optional


class WorkerThread(QThread):
    """
    通用工作线程，支持任意可调用任务
    
    这是推荐的线程实现方式。新代码应该优先使用此类而非创建专用线程类。
    
    使用示例:
    ```python
    # 方式1: 直接传递方法
    thread = WorkerThread(self.processor.process, file_path, output_dir)
    thread.finished.connect(self.on_finished)
    thread.error.connect(self.on_error)
    thread.start()
    
    # 方式2: 使用 lambda（注意捕获变量）
    thread = WorkerThread(lambda: self.converter.convert(files))
    
    # 方式3: 需要进度回调的任务（processor 需要发射自己的进度信号）
    thread = WorkerThread(self.processor.process_with_progress, files)
    ```
    
    注意事项:
    - 如果任务需要发射进度信号，应该由 task_func 所属的对象（如 processor）自己处理
    - finished 信号会传递任务返回值
    - error 信号会传递异常信息字符串
    """
    finished = pyqtSignal(object)  # 返回结果（任何类型）
    error = pyqtSignal(str)        # 返回错误信息
    
    def __init__(self, task_func: Callable[..., Any], *args, **kwargs):
        """
        初始化工作线程
        
        Args:
            task_func: 要执行的可调用对象（函数、方法、lambda等）
            *args: 传递给 task_func 的位置参数
            **kwargs: 传递给 task_func 的关键字参数
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def run(self):
        """执行任务"""
        try:
            if not self._is_cancelled:
                result = self.task_func(*self.args, **self.kwargs)
                if not self._is_cancelled:
                    self.finished.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
    
    def cancel(self):
        """
        标记任务为已取消
        
        注意: 这不会立即停止正在执行的任务，只是设置取消标志。
        任务函数需要自己检查取消状态（如果支持的话）。
        """
        self._is_cancelled = True


# ============================================================================
# 以下是遗留的专用线程类
#
# 这些类保留是为了向后兼容。新代码应该使用 WorkerThread 代替。
#
# ============================================================================

class ConversionThread(QThread):
    def __init__(self, converter, files):
        super().__init__()
        self.converter = converter
        self.files = files

    def run(self):
        self.converter.convert(self.files)

class CompressThread(QThread):
    def __init__(self, compressor, files, quality, gs_path):
        super().__init__()
        self.compressor = compressor
        self.files = files
        self.quality = quality
        self.gs_path = gs_path
        self._is_cancelled = False

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def run(self):
        # 使用关键字参数传递 gs_path，适配新的引擎接口
        if not self._is_cancelled:
            self.compressor.compress(self.files, self.quality, gs_path=self.gs_path)


