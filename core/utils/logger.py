import logging
import tempfile
import time
from functools import wraps
from datetime import datetime
from pathlib import Path

from core.utils.resource_path import get_log_dir, get_user_data_dir

class AppLogger:
    """应用程序日志管理器（单例模式）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    @staticmethod
    def _open_handler(log_name):
        """依次尝试 日志目录 → 用户数据目录 → 临时目录，全部失败才用空处理器。"""
        candidates = (
            get_log_dir(),
            get_user_data_dir() / "logs",
            Path(tempfile.gettempdir()) / "OfficeToolkit" / "logs",
        )
        for directory in candidates:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                return logging.FileHandler(directory / log_name, encoding='utf-8')
            except OSError:
                continue
        return logging.NullHandler()

    def _init_logger(self):
        """初始化日志系统"""
        log_name = f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 创建 logger
        self.logger = logging.getLogger("OfficeToolkit")
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件处理器：打不开也只能降级，不能让启动失败（控制台已禁用，否则表现为双击无反应）
            fh = self._open_handler(log_name)
            fh.setLevel(logging.DEBUG)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
    
    def info(self, msg):
        """记录 INFO 级别日志"""
        self.logger.info(msg)
    
    def error(self, msg):
        """记录 ERROR 级别日志"""
        self.logger.error(msg)
    
    def debug(self, msg):
        """记录 DEBUG 级别日志"""
        self.logger.debug(msg)
    
    def warning(self, msg):
        """记录 WARNING 级别日志"""
        self.logger.warning(msg)


def timed_operation(operation_name: str):
    """
    装饰器：记录操作耗时
    
    使用示例：
    @timed_operation("PDF 压缩")
    def compress_pdf(file_path):
        # ... 压缩逻辑
        pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = AppLogger()
            start = time.perf_counter()
            logger.info(f"[START] {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[DONE] {operation_name} - {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"[FAIL] {operation_name} - {elapsed:.2f}s - {str(e)}")
                raise
        return wrapper
    return decorator


# 全局日志实例
_logger = AppLogger()

# 导出便捷函数
def log_info(msg): _logger.info(msg)
def log_error(msg): _logger.error(msg)
def log_debug(msg): _logger.debug(msg)
def log_warning(msg): _logger.warning(msg)