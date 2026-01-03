import importlib
from typing import Dict, Type, List, Optional
from .base import PluginBase

# 插件注册表：名称 -> (模块路径, 类名)
PLUGIN_REGISTRY = {
    "pandoc": ("core.plugins.pandoc_plugin", "PandocPlugin"),
    "mathjax": ("core.plugins.mathjax_plugin", "MathJaxPlugin"),
    "highlight": ("core.plugins.highlight_plugin", "HighlightPlugin"),
}

class PluginManager:
    """插件管理器 - 单例模式 (支持延迟加载)"""
    
    _instance = None
    _plugins: Dict[str, PluginBase] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化时不再自动加载所有插件，改为按需加载
        return cls._instance
    
    def _load_plugin(self, name: str) -> Optional[PluginBase]:
        """内部方法：动态加载指定插件"""
        if name in self._plugins:
            return self._plugins[name]
            
        if name not in PLUGIN_REGISTRY:
            return None
            
        try:
            module_path, class_name = PLUGIN_REGISTRY[name]
            # 动态导入模块
            module = importlib.import_module(module_path)
            # 获取插件类
            plugin_cls = getattr(module, class_name)
            # 实例化并注册
            plugin_instance = plugin_cls()
            self.register(plugin_instance)
            return plugin_instance
        except ImportError as e:
            print(f"Error loading plugin {name}: {e}")
            return None
        except Exception as e:
            print(f"Error initializing plugin {name}: {e}")
            return None

    def _ensure_all_loaded(self):
        """内部方法：确保所有注册的插件都被加载（用于遍历场景）"""
        for name in PLUGIN_REGISTRY:
            if name not in self._plugins:
                self._load_plugin(name)
    
    def register(self, plugin: PluginBase):
        self._plugins[plugin.name] = plugin
    
    def get(self, name: str) -> Optional[PluginBase]:
        """
        获取插件实例。
        如果插件尚未加载，会触发动态加载。
        """
        if name not in self._plugins:
            return self._load_plugin(name)
        return self._plugins.get(name)
    
    def get_all(self) -> List[PluginBase]:
        """获取所有插件（会触发所有插件加载）"""
        self._ensure_all_loaded()
        return list(self._plugins.values())
    
    def get_available(self) -> List[PluginBase]:
        """获取所有可用插件（会触发所有插件加载）"""
        self._ensure_all_loaded()
        return [p for p in self._plugins.values() if p.is_available]
    
    def get_status_all(self) -> List[Dict]:
        """获取所有插件状态（会触发所有插件加载），用于设置界面展示"""
        self._ensure_all_loaded()
        return [p.get_status_info() for p in self._plugins.values()]
