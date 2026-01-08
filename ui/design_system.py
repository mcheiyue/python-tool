"""
设计系统常量定义
Design System Constants
"""

class Spacing:
    """间距常量"""
    XS = 4    # 超小间距
    SM = 8    # 小间距
    MD = 16   # 中等间距 (标准组件间距)
    LG = 24   # 大间距 (区块间距)
    XL = 32   # 超大间距

class Margins:
    """边距常量"""
    # 主页面边距 (Left, Top, Right, Bottom)
    PAGE = (24, 24, 24, 24)
    
    # 卡片内边距
    CARD = (16, 16, 16, 16)
    
    # 弹窗内边距
    POPUP = (20, 20, 20, 20)
    
    # 无边距
    ZERO = (0, 0, 0, 0)

class FontSize:
    """字体大小"""
    TITLE = 18      # 页面标题
    SUBTITLE = 14   # 副标题/卡片标题
    BODY = 12       # 正文
    CAPTION = 10    # 辅助文字/说明
    CODE = 13       # 代码/等宽字体

class Colors:
    """颜色常量 (Light/Dark 适配需配合 Theme 使用)"""
    # 这里的颜色主要用于特定高亮或警告，常规 UI 应优先使用 QFluentWidgets 的主题色
    ERROR_LIGHT = "#C42B1C"
    ERROR_DARK = "#FF6B6B"
    
    SUCCESS_LIGHT = "#107C10"
    SUCCESS_DARK = "#73C62E"
    
    WARNING_LIGHT = "#9D5D00"
    WARNING_DARK = "#FCE100"

class Dimensions:
    """尺寸常量"""
    ICON_SIZE = 24
    BUTTON_HEIGHT = 32
    INPUT_HEIGHT = 32