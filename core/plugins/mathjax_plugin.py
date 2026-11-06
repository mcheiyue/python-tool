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
        # 预览用的是 QTextBrowser，不执行脚本；注入 CDN 代码不会产生任何渲染效果
        return {
            "available": False,
            "path": None,
            "version": self.version,
            "message": "预览控件不支持 JavaScript，公式无法渲染"
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
