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
    
    for line in lines:
        # 修复标题格式: #标题 -> # 标题
        # 只有当行首是标题标记且后面没有空格时才处理
        match = header_pattern.match(line)
        if match:
            # 在#和内容之间插入空格
            line = f"{match.group(1)} {line[len(match.group(1)):]}"
            
        result.append(line)
        
    return '\n'.join(result)
