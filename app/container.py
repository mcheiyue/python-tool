from config import ConfigLoader
from core.plugins import PluginManager
from core.external_tools import ExternalToolManager

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
        self._doc_to_docx_converter = None
        self._plugin_manager = None
        self._external_tool_manager = None
        
        self._initialized = True

    @property
    def doc_to_docx_converter(self):
        if self._doc_to_docx_converter is None:
            from core.features.office.doc_to_docx_converter import DocToDocxConverter
            self._doc_to_docx_converter = DocToDocxConverter()
        return self._doc_to_docx_converter

    def _create_office_engine(self, engine_type: str):
        from core.engines.office.selector import create_office_engine
        return create_office_engine(engine_type, self.external_tool_manager)

    @property
    def word_engine(self):
        if self._word_engine is None:
            self._word_engine = self._create_office_engine('word')
        return self._word_engine

    @property
    def ppt_engine(self):
        if self._ppt_engine is None:
            self._ppt_engine = self._create_office_engine('powerpoint')
        return self._ppt_engine

    @property
    def excel_engine(self):
        if self._excel_engine is None:
            self._excel_engine = self._create_office_engine('excel')
        return self._excel_engine

    @property
    def plugin_manager(self) -> PluginManager:
        if self._plugin_manager is None:
            self._plugin_manager = PluginManager()
        return self._plugin_manager

    @property
    def external_tool_manager(self) -> ExternalToolManager:
        if self._external_tool_manager is None:
            self._external_tool_manager = ExternalToolManager()
        return self._external_tool_manager
