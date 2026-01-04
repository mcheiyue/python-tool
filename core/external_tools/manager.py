import importlib
from typing import Dict, List, Optional
from config.loader import ConfigLoader
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
            
            # 注入管理器引用，以便工具可以查询配置
            tool_instance._manager = self
            
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
    
    def is_tool_disabled(self, name: str) -> bool:
        """检查工具是否被禁用"""
        return name in ConfigLoader().get("dependencies.disabled_tools", [])

    def disable_tool(self, name: str):
        """禁用工具"""
        config_loader = ConfigLoader()
        disabled_tools = config_loader.get("dependencies.disabled_tools", [])
        
        if name not in disabled_tools:
            disabled_tools.append(name)
            config_loader.set("dependencies.disabled_tools", disabled_tools)
            
            # 如果工具已加载，更新其状态
            if name in self._tools:
                # 强制重新检查状态
                pass

    def enable_tool(self, name: str):
        """启用工具"""
        config_loader = ConfigLoader()
        disabled_tools = config_loader.get("dependencies.disabled_tools", [])
        
        if name in disabled_tools:
            disabled_tools.remove(name)
            config_loader.set("dependencies.disabled_tools", disabled_tools)

    def uninstall_tool(self, name: str) -> bool:
        """卸载工具（删除物理文件）"""
        tool = self.get_tool(name)
        if tool and hasattr(tool, 'uninstall'):
            success = tool.uninstall()
            # 卸载后自动禁用，防止自动重新解压（特别是临时模式下）
            if success:
                self.disable_tool(name)
            return success
        return False

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
