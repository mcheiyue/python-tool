"""
图标注册表模块

集中管理所有功能图标的映射，避免在多个地方硬编码图标路径。
"""

from typing import Dict, Optional
from PyQt6.QtGui import QIcon
from core.utils.resource_path import get_resource_path
from core.utils.icon_provider import ThemedSvgIconEngine


class IconRegistry:
    """
    图标注册表
    
    提供功能名称到图标的统一映射，支持：
    1. 按功能名称获取图标
    2. 主题感知的 SVG 图标
    3. 集中维护图标配置
    
    使用示例:
    ```python
    registry = IconRegistry()
    icon = registry.get_icon("PDF 合并")
    icon_path = registry.get_icon_path("PDF 合并")
    ```
    """
    
    # 功能名称 -> 图标文件名映射
    _ICON_MAP: Dict[str, str] = {
        # Office 工具
        "PPT 转 PDF": "presentation.svg",
        "PPT 转图片": "image.svg",
        "Word 转 PDF": "word.svg",
        "Doc 转 Docx": "word.svg",
        "Excel 转 PDF": "excel.svg",
        "Word ↔ Markdown": "markdown.svg",
        "LibreOffice 格式转换": "convert.svg",
        
        # PDF 工具
        "PDF 合并": "merge.svg",
        "PDF 压缩": "compress.svg",
        "PDF 拆分/提取": "split.svg",
        "PDF 图片提取": "image.svg",
        "PDF 页面渲染": "convert.svg",
        
        # 图片工具
        "图片取色": "color_picker.svg",
        "PNG 转 SVG": "vector.svg",
        "图片格式转换": "convert.svg",
        "图片转 PDF": "pdf.svg",
        "图片去水印": "eraser.svg",
        
        # 文本工具
        "Markdown 转 PDF": "markdown.svg",
        "Markdown ↔ HTML": "markdown.svg",
        "Markdown 批量转 PDF": "markdown.svg",
        "TXT 转 PDF": "text.svg",
        "代码提取": "code.svg",
        
        # 实用工具
        "批量重命名": "magic.svg",
        "剪贴板图片助手": "image.svg",
        
        # 系统
        "设置": "settings.svg",
    }
    
    # 分类名称 -> 图标文件名映射
    _CATEGORY_ICON_MAP: Dict[str, str] = {
        "Office 工具": "presentation.svg",
        "Office 转换": "presentation.svg",
        "PDF 工具箱": "pdf.svg",
        "PDF 处理": "pdf.svg",
        "图片工具箱": "image.svg",
        "图片工具": "image.svg",
        "文本工具箱": "text.svg",
        "文本工具": "text.svg",
        "实用工具箱": "magic.svg",
        "实用工具": "magic.svg",
    }
    
    # 默认图标（当功能名称未找到时）
    _DEFAULT_ICON = "magic.svg"
    
    # 图标基础路径
    _ICON_BASE_PATH = "assets/icons"
    
    _instance: Optional['IconRegistry'] = None
    
    def __new__(cls) -> 'IconRegistry':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_icon_filename(self, feature_name: str) -> str:
        """
        获取功能对应的图标文件名
        
        Args:
            feature_name: 功能名称，如 "PDF 合并"
            
        Returns:
            图标文件名，如 "merge.svg"
        """
        return self._ICON_MAP.get(feature_name, self._DEFAULT_ICON)
    
    def get_icon_path(self, feature_name: str) -> str:
        """
        获取功能对应的图标完整路径
        
        Args:
            feature_name: 功能名称
            
        Returns:
            图标完整路径
        """
        filename = self.get_icon_filename(feature_name)
        return get_resource_path(f"{self._ICON_BASE_PATH}/{filename}")
    
    def get_icon(self, feature_name: str) -> QIcon:
        """
        获取功能对应的主题感知图标
        
        Args:
            feature_name: 功能名称
            
        Returns:
            QIcon 对象（支持浅色/深色主题自动切换）
        """
        path = self.get_icon_path(feature_name)
        return QIcon(ThemedSvgIconEngine(path))
    
    def get_category_icon_path(self, category_name: str) -> str:
        """
        获取分类对应的图标路径
        
        Args:
            category_name: 分类名称，如 "PDF 工具箱"
            
        Returns:
            图标完整路径
        """
        filename = self._CATEGORY_ICON_MAP.get(category_name, self._DEFAULT_ICON)
        return get_resource_path(f"{self._ICON_BASE_PATH}/{filename}")
    
    def get_category_icon(self, category_name: str) -> QIcon:
        """
        获取分类对应的主题感知图标
        
        Args:
            category_name: 分类名称
            
        Returns:
            QIcon 对象
        """
        path = self.get_category_icon_path(category_name)
        return QIcon(ThemedSvgIconEngine(path))
    
    def register_icon(self, feature_name: str, icon_filename: str) -> None:
        """
        注册新的功能图标映射（用于插件扩展）
        
        Args:
            feature_name: 功能名称
            icon_filename: 图标文件名
        """
        self._ICON_MAP[feature_name] = icon_filename
    
    def get_all_features(self) -> Dict[str, str]:
        """
        获取所有已注册的功能图标映射
        
        Returns:
            功能名称到图标文件名的字典
        """
        return self._ICON_MAP.copy()


# 便捷函数
def get_feature_icon(feature_name: str) -> QIcon:
    """获取功能图标的便捷函数"""
    return IconRegistry().get_icon(feature_name)


def get_feature_icon_path(feature_name: str) -> str:
    """获取功能图标路径的便捷函数"""
    return IconRegistry().get_icon_path(feature_name)