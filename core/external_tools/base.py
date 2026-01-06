from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os
import sys

class ExternalTool(ABC):
    """外部工具抽象基类"""
    
    # 唯一标识符 (例如: 'pandoc', 'ghostscript')
    name: str = ""
    
    # 显示名称 (例如: 'Pandoc')
    display_name: str = ""
    
    # 功能描述
    description: str = ""
    
    # 功能用途说明（用于界面提示）
    features: str = ""
    
    # 官方下载地址
    download_url: str = ""
    
    # 是否是应用程序的核心依赖
    is_required: bool = False
    
    # 引用管理器实例
    _manager = None

    def clear_cache(self):
        """清除缓存，强制重新检测"""
        if hasattr(self, '_cache'):
            self._cache = None

    @property
    def is_disabled(self) -> bool:
        """检查工具是否被禁用"""
        if self._manager:
            return self._manager.is_tool_disabled(self.name)
        return False

    @abstractmethod
    def check_installed(self) -> bool:
        """检查工具是否已安装"""
        pass
    
    def uninstall(self) -> bool:
        """卸载工具（删除相关文件）"""
        return False

    @abstractmethod
    def get_version(self) -> Optional[str]:
        """获取已安装版本"""
        pass
    
    @abstractmethod
    def get_path(self) -> Optional[str]:
        """获取可执行文件路径"""
        pass
    
    def get_source(self) -> Optional[str]:
        """获取安装来源 (portable/system/env)"""
        # 默认返回 None，子类可以在 _find 结果中包含此信息
        return None

    # 别名，为了更好的语义兼容性
    def is_available(self) -> bool:
        return self.check_installed() and not self.is_disabled
        
    def get_executable_path(self) -> Optional[str]:
        if self.is_disabled:
            return None
        return self.get_path()
        
    def get_status_info(self) -> Dict[str, Any]:
        """获取工具状态信息"""
        installed = self.check_installed()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "features": self.features,
            "installed": installed,
            "disabled": self.is_disabled,
            "version": self.get_version() if installed else None,
            "path": self.get_path() if installed else None,
            "source": self.get_source() if installed else None,
            "download_url": self.download_url,
            "is_required": self.is_required
        }

    @staticmethod
    def get_libs_path() -> str:
        """获取便携 libs 目录路径"""
        from core.utils.resource_path import get_app_root
        return os.path.join(get_app_root(), "libs")
