from config import ConfigLoader

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
        
        # 将来这里会初始化 DependencyManager, ServiceManager 等
        # self.dependency_manager = DependencyManager(self.config)
        # self.ocr_service = OcrService(self.config)
        
        self._initialized = True
