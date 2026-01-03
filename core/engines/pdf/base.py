from abc import ABC, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal

class BasePdfCompressor(QObject, ABC):
    """PDF 压缩引擎抽象基类"""
    
    # 定义标准信号
    progress = pyqtSignal(int, int, str)  # 当前索引(1-based), 总数, 当前文件名
    log = pyqtSignal(str)                 # 日志消息
    finished = pyqtSignal(int, int)       # 成功数量, 失败数量
    
    def __init__(self):
        super().__init__()
        self._is_running = False

    @abstractmethod
    def compress(self, files: list, quality: str, **kwargs):
        """
        执行压缩任务
        :param files: PDF 文件路径列表
        :param quality: 压缩质量设置
        :param kwargs: 其他引擎特定参数
        """
        pass
        
    @abstractmethod
    def check_dependency(self) -> dict:
        """
        检查引擎依赖是否满足
        :return: {"available": bool, "message": str, "path": str}
        """
        pass
        
    def stop(self):
        """停止任务"""
        self._is_running = False
