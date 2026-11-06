import threading

from PyQt6.QtCore import QRunnable, QThread, pyqtSignal
from typing import Callable, Any, Optional, List

_ACTIVE = set()
_ACTIVE_LOCK = threading.Lock()


def active_threads() -> List["WorkerThread"]:
    with _ACTIVE_LOCK:
        return [thread for thread in _ACTIVE if thread.isRunning()]


def cancel_active_threads():
    for thread in active_threads():
        thread.cancel()


def is_busy(owner) -> bool:
    """owner.thread 是否仍在运行；界面用它避免运行期重新放开开始按钮。"""
    thread = getattr(owner, "thread", None)
    return thread is not None and thread.isRunning()


class PoolTask(QRunnable):
    """提交到 QThreadPool 的单个任务：并发上限由池控制，异常转交 on_error。"""

    def __init__(self, func: Callable[..., Any], args, kwargs, on_error: Callable[[str], None]):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._on_error = on_error

    def run(self):
        try:
            self._func(*self._args, **self._kwargs)
        except Exception as e:
            self._on_error(str(e))


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
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE.discard(self)

    def start(self, *args, **kwargs):
        with _ACTIVE_LOCK:
            _ACTIVE.add(self)
        super().start(*args, **kwargs)

    def cancel(self):
        """
        请求取消任务

        置位标志后调用任务所属对象的 stop()：批处理功能都以 stop() 作为协作
        停止点，仅置位本线程标志不会让它们停下来。
        """
        self._is_cancelled = True
        stop = getattr(getattr(self.task_func, "__self__", None), "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass

