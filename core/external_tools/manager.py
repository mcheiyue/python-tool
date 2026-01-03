import importlib
from typing import Dict, List, Optional
from .base import ExternalTool

# 工具注册表：名称 -> (模块路径, 类名)
TOOL_REGISTRY = {
    "ghostscript": ("core.external_tools.ghostscript_tool", "GhostscriptTool"),
    "pandoc": ("core.external_tools.pandoc_tool", "PandocTool"),
    # 未来可扩展 Tesseract, Whisper 等
    # "tesseract": ("core.external_tools.tesseract_tool", "TesseractTool"),
}

class ExternalToolManager:
    """外部工具管理器 - 单例模式"""
    
    _instance = None
    _tools: Dict[str, ExternalTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_tool(self, name: str) -> Optional[ExternalTool]:
        """内部方法：动态加载指定工具"""
        if name in self._tools:
            return self._tools[name]
            
        if name not in TOOL_REGISTRY:
            return None
            
        try:
            module_path, class_name = TOOL_REGISTRY[name]
            module = importlib.import_module(module_path)
            tool_cls = getattr(module, class_name)
            tool_instance = tool_cls()
            self.register(tool_instance)
            return tool_instance
        except Exception as e:
            print(f"Error loading external tool {name}: {e}")
            return None

    def _ensure_all_loaded(self):
        """加载所有注册的工具"""
        for name in TOOL_REGISTRY:
            if name not in self._tools:
                self._load_tool(name)
    
    def register(self, tool: ExternalTool):
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[ExternalTool]:
        """获取指定工具实例"""
        if name not in self._tools:
            return self._load_tool(name)
        return self._tools.get(name)
    
    # 兼容旧代码或简写
    get = get_tool
    
    def get_all(self) -> List[ExternalTool]:
        """获取所有工具"""
        self._ensure_all_loaded()
        return list(self._tools.values())
    
    def get_status_all(self) -> List[Dict]:
        """获取所有工具的状态信息"""
        self._ensure_all_loaded()
        return [t.get_status_info() for t in self._tools.values()]
