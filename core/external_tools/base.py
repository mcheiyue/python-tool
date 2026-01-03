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
    
    # 官方下载地址
    download_url: str = ""
    
    # 是否是应用程序的核心依赖
    is_required: bool = False
    
    @abstractmethod
    def check_installed(self) -> bool:
        """检查工具是否已安装"""
        pass
    
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
        return self.check_installed()
        
    def get_executable_path(self) -> Optional[str]:
        return self.get_path()
        
    def get_status_info(self) -> Dict[str, Any]:
        """获取工具状态信息"""
        installed = self.check_installed()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "installed": installed,
            "version": self.get_version() if installed else None,
            "path": self.get_path() if installed else None,
            "source": self.get_source() if installed else None,
            "download_url": self.download_url,
            "is_required": self.is_required
        }

    @staticmethod
    def get_libs_path() -> str:
        """获取便携 libs 目录路径"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后
            base = os.path.dirname(sys.executable)
        else:
            # 开发模式
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            
        return os.path.join(base, "libs")
