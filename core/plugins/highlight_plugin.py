from typing import Dict, Any
from .base import PluginBase

try:
    import pygments
    from pygments.formatters import HtmlFormatter
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

class HighlightPlugin(PluginBase):
    name = "highlight"
    display_name = "代码高亮"
    description = "使用 Pygments 提供代码语法高亮 (需安装 Pygments)"
    version = "1.0.0"
    
    def check_availability(self) -> Dict[str, Any]:
        return {
            "available": HAS_PYGMENTS,
            "path": "Python Lib",
            "version": pygments.__version__ if HAS_PYGMENTS else "",
            "message": "Pygments 库已安装" if HAS_PYGMENTS else "未安装 Pygments 库"
        }
    
    def get_css(self, style: str = "default") -> str:
        """获取高亮 CSS"""
        if not HAS_PYGMENTS:
            return ""
        try:
            return HtmlFormatter(style=style).get_style_defs('.codehilite')
        except:
            return ""
