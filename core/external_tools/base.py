from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

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
            "download_url": self.download_url,
            "is_required": self.is_required
        }
