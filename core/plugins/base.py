from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PluginBase(ABC):
    """插件基类"""
    
    # 插件元信息 - 子类必须覆盖这些属性
    name: str = "base"
    display_name: str = "基础插件"
    description: str = ""
    version: str = "1.0.0"
    
    # 依赖信息
    requires_external: bool = False  # 是否需要外部程序
    external_tool: Optional[str] = None  # 外部工具名称
    download_url: str = ""
    
    def __init__(self):
        self._available = None
    
    @abstractmethod
    def check_availability(self) -> Dict[str, Any]:
        """
        检查插件是否可用
        返回: {"available": bool, "path": str, "version": str, "message": str}
        """
        pass
    
    @property
    def is_available(self) -> bool:
        if self._available is None:
            result = self.check_availability()
            self._available = result.get("available", False)
        return self._available
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取插件状态信息，用于 UI 展示"""
        check_result = self.check_availability()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "available": check_result.get("available", False),
            "external_required": self.requires_external,
            "external_tool": self.external_tool,
            "download_url": self.download_url,
            "message": check_result.get("message", ""),
            "tool_version": check_result.get("version", ""),
            "tool_path": check_result.get("path", "")
        }
