"""
模糊搜索引擎模块

支持：
1. 名称包含匹配
2. 描述包含匹配
3. 拼音首字母匹配
4. 拼音全拼匹配
"""

import re
from typing import List, Dict, NamedTuple

try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False

class SearchResult(NamedTuple):
    name: str
    description: str
    score: int
    match_type: str  # 'name', 'desc', 'pinyin_initial', 'pinyin_full'

class FuzzySearchEngine:
    def __init__(self, items: Dict[str, str]):
        """
        初始化搜索引擎
        
        :param items: 字典 {名称: 描述}
        """
        self.items = items
        self._pinyin_cache = {}
        self._build_cache()
    
    def _build_cache(self):
        """预计算拼音缓存"""
        if not HAS_PYPINYIN:
            return
            
        for name in self.items.keys():
            # 获取拼音首字母 (e.g., "PDF 合并" -> "pdfhb")
            initials = ''.join([p[0] for p in lazy_pinyin(name, style=Style.FIRST_LETTER) if p])
            # 获取全拼 (e.g., "PDF 合并" -> "pdfhebing")
            full = ''.join(lazy_pinyin(name))
            
            self._pinyin_cache[name] = {
                'initials': initials.lower(),
                'full': full.lower()
            }
            
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        执行搜索
        
        :param query: 搜索关键词
        :param limit: 返回结果数量限制
        :return: 排序后的 SearchResult 列表
        """
        if not query:
            return []
            
        query = query.lower().strip()
        results = []
        
        for name, desc in self.items.items():
            name_lower = name.lower()
            desc_lower = desc.lower() if desc else ""
            score = 0
            match_type = ""
            
            # 1. 精确名称匹配 (最高权重)
            if query == name_lower:
                score = 100
                match_type = 'exact_name'
            
            # 2. 名称包含匹配
            elif query in name_lower:
                score = 80
                # 匹配位置越靠前分数越高
                pos = name_lower.find(query)
                score -= pos  # 减去位置偏移
                match_type = 'name'
                
            # 3. 拼音匹配 (如果安装了 pypinyin)
            elif HAS_PYPINYIN and name in self._pinyin_cache:
                cache = self._pinyin_cache[name]
                
                # 首字母匹配
                if query in cache['initials']:
                    score = 60
                    match_type = 'pinyin_initial'
                    
                # 全拼匹配
                elif query in cache['full']:
                    score = 50
                    match_type = 'pinyin_full'
            
            # 4. 描述包含匹配 (最低权重)
            # 独立于上面 elif 链：装了 pypinyin 时拼音分支会短路，若并进 elif
            # 则描述匹配永不可达（历史 bug：search("Merge") 返回空）
            if score == 0 and query in desc_lower:
                score = 40
                match_type = 'desc'
                
            if score > 0:
                results.append(SearchResult(name, desc, score, match_type))
        
        # 按分数降序排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]

    def update_items(self, items: Dict[str, str]):
        """更新搜索项"""
        self.items = items
        self._pinyin_cache.clear()
        self._build_cache()