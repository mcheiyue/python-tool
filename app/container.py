from config import ConfigLoader
from core.engines.office import WordEngine, PowerPointEngine, ExcelEngine

class AppContainer:
    """应用容器，负责管理全局依赖和服务的生命周期"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContainer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 初始化核心服务
        self.config = ConfigLoader()
        
        # 服务实例缓存 (懒加载)
        self._word_engine = None
        self._ppt_engine = None
        self._excel_engine = None
        
        self._initialized = True

    @property
    def word_engine(self) -> WordEngine:
        if self._word_engine is None:
            self._word_engine = WordEngine()
        return self._word_engine

    @property
    def ppt_engine(self) -> PowerPointEngine:
        if self._ppt_engine is None:
            self._ppt_engine = PowerPointEngine()
        return self._ppt_engine

    @property
    def excel_engine(self) -> ExcelEngine:
        if self._excel_engine is None:
            self._excel_engine = ExcelEngine()
        return self._excel_engine
