import os
import platform

class FontFinder:
    @staticmethod
    def find_cjk_font() -> tuple[str, str] | None:
        """
        自动查找系统中可用的中文字体 (CJK)
        返回: (font_path, font_name) 或 None
        """
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows 字体目录
            font_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
            
            # 优先级列表
            candidates = [
                ("msyh.ttc", "Microsoft YaHei"),     # 微软雅黑 (TTC)
                ("msyh.ttf", "Microsoft YaHei"),     # 微软雅黑 (TTF - 少见但可能)
                ("simhei.ttf", "SimHei"),            # 黑体
                ("simsun.ttc", "SimSun"),            # 宋体
                ("simkai.ttf", "KaiTi"),             # 楷体
            ]
            
            for filename, font_name in candidates:
                path = os.path.join(font_dir, filename)
                if os.path.exists(path):
                    return (path, font_name)
                    
        elif system == 'darwin': # macOS
            candidates = [
                ("/System/Library/Fonts/PingFang.ttc", "PingFang SC"),
                ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti"),
                ("/Library/Fonts/Arial Unicode.ttf", "Arial Unicode MS"),
            ]
            for path, name in candidates:
                if os.path.exists(path):
                    return (path, name)
                    
        else: # Linux
            # Linux 字体路径不统一，简单检查几个常见位置
            common_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return (path, "CJK Font")
                    
        return None
