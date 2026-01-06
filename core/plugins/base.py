from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class PluginBase(ABC):
    """插件基类"""
    
    # 插件元信息 - 子类必须覆盖这些属性
    name: str = "base"
    display_name: str = "基础插件"
    description: str = ""
    version: str = "1.0.0"
    
    # 能力与优先级
    capabilities: List[str] = []  # 插件提供的能力列表，如 ["markdown_to_pdf", "ocr"]
    priority: int = 100           # 优先级 (数字越小优先级越高，默认 100)
    
    # 依赖信息
    requires_external: bool = False  # 是否需要外部程序
    external_tool: Optional[str] = None  # 外部工具名称 (对应 ExternalToolManager 中的名称)
    download_url: str = ""
    
    def __init__(self):
        self._available = None
    
    def check_availability(self) -> Dict[str, Any]:
        """
        检查插件是否可用
        默认实现：如果需要外部工具，则使用 AppContainer 检查该工具
        """
        if self.requires_external and self.external_tool:
            return self._check_external_tool_availability()
            
        return {"available": True, "message": "内置插件"}
    
    def _check_external_tool_availability(self) -> Dict[str, Any]:
        """检查外部工具可用性的辅助方法"""
        try:
            # 延迟导入以避免循环依赖
            from app.container import AppContainer
            manager = AppContainer().external_tool_manager
            tool = manager.get_tool(self.external_tool)
            
            if not tool:
                 return {
                    "available": False,
                    "path": "",
                    "version": "",
                    "message": f"未知的外部工具依赖: {self.external_tool}"
                }

            is_available = tool.is_available()
            version = tool.get_version() if is_available else ""
            
            return {
                "available": is_available,
                "path": tool.get_executable_path() if is_available else "",
                "version": version,
                "message": f"已安装 {tool.name} {version}" if is_available else f"未找到 {tool.name}，请下载安装"
            }
        except ImportError:
            # 兼容测试环境或非容器环境
            return {
                "available": False,
                "message": "无法访问应用容器"
            }
        except Exception as e:
            return {
                "available": False,
                "message": f"依赖检查出错: {str(e)}"
            }

    @property
    def is_available(self) -> bool:
        # 移除缓存，每次实时检查，以便响应 ExternalToolManager 的状态变更
        result = self.check_availability()
        return result.get("available", False)
    
    def get_executable_path(self) -> Optional[str]:
        """获取关联外部工具的可执行路径"""
        if not self.requires_external or not self.external_tool:
            return None
            
        try:
            from app.container import AppContainer
            manager = AppContainer().external_tool_manager
            tool = manager.get_tool(self.external_tool)
            return tool.get_executable_path() if tool else None
        except Exception:
            return None
            
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
            "tool_path": check_result.get("path", ""),
            "capabilities": self.capabilities,
            "priority": self.priority
        }
