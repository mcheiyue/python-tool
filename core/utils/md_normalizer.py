import re

def normalize_markdown(text: str) -> str:
    """
    规范化 Markdown 格式，确保 Pandoc 正确解析。
    
    主要处理：
    1. 标题格式：#标题 -> # 标题 (Pandoc 要求标题标记后必须有空格)
    """
    lines = text.split('\n')
    result = []
    
    # 标题正则：匹配以1-6个#开头，且紧接着非空白字符的行
    header_pattern = re.compile(r'^(#{1,6})([^\s#])')
    fence_pattern = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
    fence = None

    for line in lines:
        marker = fence_pattern.match(line)
        if marker:
            symbol = marker.group(1)[0]
            if fence is None:
                fence = symbol
            elif fence == symbol:
                fence = None
            result.append(line)
            continue

        # 代码块内的 # 是代码（如 shebang、注释），不能按标题改写
        match = header_pattern.match(line) if fence is None else None
        if match:
            line = f"{match.group(1)} {line[len(match.group(1)):]}"
            
        result.append(line)
        
    return '\n'.join(result)
