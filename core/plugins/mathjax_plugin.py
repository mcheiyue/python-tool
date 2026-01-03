from typing import Dict, Any
from .base import PluginBase

class MathJaxPlugin(PluginBase):
    name = "mathjax"
    display_name = "MathJax 数学公式"
    description = "在预览中渲染 LaTeX 数学公式 (使用 CDN)"
    version = "3.2.2"
    
    capabilities = ["math_render"]
    priority = 10

    def check_availability(self) -> Dict[str, Any]:
        # 这是一个 Web 资源插件，假定总是可用（依赖网络）
        return {
            "available": True,
            "path": "CDN",
            "version": self.version,
            "message": "使用 jsDelivr CDN"
        }
    
    def get_header_code(self) -> str:
        """获取注入 HTML 头的代码"""
        return """
        <script>
        MathJax = {
          tex: {
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true
          },
          svg: {
            fontCache: 'global'
          }
        };
        </script>
        <script type="text/javascript" id="MathJax-script" async
          src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
        </script>
        """
