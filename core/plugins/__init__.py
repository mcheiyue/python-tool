from typing import Dict, Type, List, Optional
from .base import PluginBase

# 导入插件类
from .pandoc_plugin import PandocPlugin
from .mathjax_plugin import MathJaxPlugin
from .highlight_plugin import HighlightPlugin

class PluginManager:
    """插件管理器 - 单例模式"""
    
    _instance = None
    _plugins: Dict[str, PluginBase] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_plugins()
        return cls._instance
    
    def _load_plugins(self):
        """加载所有已注册的插件"""
        # 注册插件
        self.register(PandocPlugin())
        self.register(MathJaxPlugin())
        self.register(HighlightPlugin())
    
    def register(self, plugin: PluginBase):
        self._plugins[plugin.name] = plugin
    
    def get(self, name: str) -> Optional[PluginBase]:
        return self._plugins.get(name)
    
    def get_all(self) -> List[PluginBase]:
        return list(self._plugins.values())
    
    def get_available(self) -> List[PluginBase]:
        return [p for p in self._plugins.values() if p.is_available]
    
    def get_status_all(self) -> List[Dict]:
        """获取所有插件状态，用于设置界面展示"""
        return [p.get_status_info() for p in self._plugins.values()]
