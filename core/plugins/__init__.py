import importlib
import pkgutil
import inspect
import os
from typing import Dict, Type, List, Optional
from .base import PluginBase

class PluginManager:
    """插件管理器 - 单例模式 (支持自动发现)"""
    
    _instance = None
    _plugins: Dict[str, PluginBase] = {}
    _discovered = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 首次初始化时自动发现插件
            if not cls._instance._discovered:
                cls._instance._discover_plugins()
                cls._instance._discovered = True
        return cls._instance
    
    def _discover_plugins(self):
        """扫描当前目录下的所有插件并加载"""
        package_path = os.path.dirname(__file__)
        package_name = __name__
        
        # 遍历当前目录下的所有模块
        for _, name, _ in pkgutil.iter_modules([package_path]):
            # 跳过 base.py 和私有模块
            if name == "base" or name.startswith("_"):
                continue
                
            try:
                # 动态导入模块
                module = importlib.import_module(f"{package_name}.{name}")
                
                # 查找继承自 PluginBase 的类
                for attr_name, attr_value in inspect.getmembers(module):
                    if (inspect.isclass(attr_value) and 
                        issubclass(attr_value, PluginBase) and 
                        attr_value is not PluginBase):
                        
                        # 实例化并注册
                        try:
                            plugin_instance = attr_value()
                            self.register(plugin_instance)
                        except Exception as e:
                            print(f"Error initializing plugin class {attr_name} in {name}: {e}")
                            
            except Exception as e:
                print(f"Error discovering plugin module {name}: {e}")
    
    def register(self, plugin: PluginBase):
        """注册插件实例"""
        self._plugins[plugin.name] = plugin
        # print(f"Plugin registered: {plugin.name}")
    
    def get(self, name: str) -> Optional[PluginBase]:
        """获取插件实例"""
        return self._plugins.get(name)
    
    def get_all(self) -> List[PluginBase]:
        """获取所有已加载的插件"""
        return list(self._plugins.values())
    
    def get_available(self) -> List[PluginBase]:
        """获取所有当前可用的插件"""
        return [p for p in self._plugins.values() if p.is_available]
    
    def get_status_all(self) -> List[Dict]:
        """获取所有插件状态，用于设置界面展示"""
        return [p.get_status_info() for p in self._plugins.values()]

    def get_by_capability(self, capability: str) -> List[PluginBase]:
        """
        获取所有具有指定能力的插件，按优先级排序 (数值越小优先级越高)
        """
        plugins = [p for p in self._plugins.values() 
                   if capability in getattr(p, 'capabilities', []) and p.is_available]
        return sorted(plugins, key=lambda p: getattr(p, 'priority', 100))
    
    def get_preferred_plugin(self, capability: str, config: dict = None) -> Optional[PluginBase]:
        """
        获取用户首选或自动选择的插件
        
        策略:
        1. 检查 config["preferred_plugins"][capability] 是否有指定插件
        2. 如果没有或指定的插件不可用，则自动选择优先级最高的可用插件
        """
        # 1. 检查用户明确配置
        if config:
            preferred_name = config.get("preferred_plugins", {}).get(capability)
            if preferred_name:
                plugin = self.get(preferred_name)
                # 检查插件是否存在、可用且具备该能力
                if (plugin and 
                    plugin.is_available and 
                    capability in getattr(plugin, 'capabilities', [])):
                    return plugin
        
        # 2. 自动选择
        candidates = self.get_by_capability(capability)
        return candidates[0] if candidates else None
