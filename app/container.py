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
        """
        创建 Office 引擎（自动选择 MS Office 或 LibreOffice）
        
        Args:
            engine_type: 'word', 'excel', 或 'powerpoint'
        
        Returns:
            适用的引擎实例
        """
        # 1. 优先尝试 MS Office（如果可用）
        try:
            if engine_type == 'word':
                from core.engines.office import WordEngine
                engine = WordEngine()
            elif engine_type == 'excel':
                from core.engines.office import ExcelEngine
                engine = ExcelEngine()
            elif engine_type == 'powerpoint':
                from core.engines.office import PowerPointEngine
                engine = PowerPointEngine()
            else:
                raise ValueError(f"Unknown engine type: {engine_type}")
            
            # 简单测试 COM 是否可用（尝试导入 comtypes）
            import comtypes.client
            return engine
            
        except Exception as e:
            # MS Office 不可用，尝试 LibreOffice
            pass
        
        # 2. 降级到 LibreOffice
        tool_manager = self.external_tool_manager
        libreoffice_tool = tool_manager.get_tool("libreoffice")
        
        if libreoffice_tool and libreoffice_tool.is_available():
            if engine_type == 'word':
                from core.engines.office.libreoffice import LibreOfficeWordEngine
                return LibreOfficeWordEngine()
            elif engine_type == 'excel':
                from core.engines.office.libreoffice import LibreOfficeExcelEngine
                return LibreOfficeExcelEngine()
            elif engine_type == 'powerpoint':
                from core.engines.office.libreoffice import LibreOfficePowerPointEngine
                return LibreOfficePowerPointEngine()
        
        # 3. 都不可用，返回 MS Office 引擎（会在使用时报错）
        # 这样可以保持一致的错误处理流程
        if engine_type == 'word':
            from core.engines.office import WordEngine
            return WordEngine()
        elif engine_type == 'excel':
            from core.engines.office import ExcelEngine
            return ExcelEngine()
        else:
            from core.engines.office import PowerPointEngine
            return PowerPointEngine()

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
