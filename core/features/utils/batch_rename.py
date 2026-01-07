"""
批量文件重命名引擎
支持模板变量的批量重命名功能
"""
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple
from PyQt6.QtCore import QObject, pyqtSignal


class BatchRenamer(QObject):
    """
    批量文件重命名引擎
    
    支持的模板变量:
    - {name}: 原文件名（不含扩展名）
    - {ext}: 扩展名（不含点号）
    - {index}: 序号 (01, 02, ...)
    - {index3}: 三位序号 (001, 002, ...)
    - {date}: 日期 (YYYYMMDD)
    - {time}: 时间 (HHMMSS)
    - {datetime}: 日期时间 (YYYYMMDD_HHMMSS)
    """
    
    # 信号
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)  # current, total, message
    
    def __init__(self):
        super().__init__()
    
    def preview(self, files: List[str], template: str, start_index: int = 1) -> List[Dict]:
        """
        预览重命名结果
        
        :param files: 文件路径列表
        :param template: 重命名模板
        :param start_index: 起始序号
        :return: 重命名计划列表
        """
        results = []
        
        for i, path in enumerate(files):
            try:
                new_name = self._apply_template(path, template, start_index + i)
                dir_path = os.path.dirname(path)
                new_path = os.path.join(dir_path, new_name)
                
                # 检查冲突
                conflict = False
                conflict_msg = ""
                
                if new_path == path:
                    conflict = True
                    conflict_msg = "与原文件名相同"
                elif os.path.exists(new_path):
                    conflict = True
                    conflict_msg = "目标文件已存在"
                
                results.append({
                    'original': path,
                    'original_name': os.path.basename(path),
                    'new_name': new_name,
                    'new_path': new_path,
                    'conflict': conflict,
                    'conflict_msg': conflict_msg
                })
            except Exception as e:
                results.append({
                    'original': path,
                    'original_name': os.path.basename(path),
                    'new_name': f"错误: {str(e)}",
                    'new_path': '',
                    'conflict': True,
                    'conflict_msg': str(e)
                })
        
        return results
    
    def execute(self, rename_plan: List[Dict]) -> Tuple[int, int]:
        """
        执行重命名
        
        :param rename_plan: 由 preview() 生成的重命名计划
        :return: (成功数, 失败数)
        """
        success, fail = 0, 0
        total = len(rename_plan)
        
        for i, item in enumerate(rename_plan):
            try:
                # 跳过有冲突的项
                if item.get('conflict', False):
                    self.log.emit(f"⏭️ 跳过: {item['original_name']} ({item['conflict_msg']})")
                    self.progress.emit(i + 1, total, f"跳过: {item['original_name']}")
                    fail += 1
                    continue
                
                # 执行重命名
                os.rename(item['original'], item['new_path'])
                self.log.emit(f"✅ {item['original_name']} → {item['new_name']}")
                self.progress.emit(i + 1, total, f"已重命名: {item['new_name']}")
                success += 1
                
            except Exception as e:
                self.log.emit(f"❌ 失败: {item['original_name']} - {str(e)}")
                self.progress.emit(i + 1, total, f"失败: {item['original_name']}")
                fail += 1
        
        return success, fail
    
    def _apply_template(self, path: str, template: str, index: int) -> str:
        """
        应用重命名模板
        
        :param path: 文件路径
        :param template: 模板字符串
        :param index: 当前序号
        :return: 新文件名
        """
        # 分离文件名和扩展名
        basename = os.path.basename(path)
        name, ext = os.path.splitext(basename)
        ext_clean = ext.lstrip('.')  # 移除扩展名前的点
        
        # 获取当前时间
        now = datetime.now()
        
        # 构建替换字典
        replacements = {
            '{name}': name,
            '{ext}': ext_clean,
            '{index}': f"{index:02d}",
            '{index3}': f"{index:03d}",
            '{date}': now.strftime('%Y%m%d'),
            '{time}': now.strftime('%H%M%S'),
            '{datetime}': now.strftime('%Y%m%d_%H%M%S'),
        }
        
        # 应用替换
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        # 如果模板中没有扩展名，自动添加
        if '{ext}' not in template and not result.endswith(ext):
            result += ext
        
        # 清理非法字符（Windows 文件名限制）
        illegal_chars = r'[<>:"/\\|?*]'
        result = re.sub(illegal_chars, '_', result)
        
        return result
    
    def validate_template(self, template: str) -> Tuple[bool, str]:
        """
        验证模板格式
        
        :param template: 模板字符串
        :return: (是否有效, 错误信息)
        """
        if not template or template.strip() == '':
            return False, "模板不能为空"
        
        # 检查是否包含至少一个变量
        valid_vars = ['{name}', '{ext}', '{index}', '{index3}', '{date}', '{time}', '{datetime}']
        has_var = any(var in template for var in valid_vars)
        
        if not has_var:
            return False, "模板必须包含至少一个变量"
        
        # 检查未闭合的花括号
        open_count = template.count('{')
        close_count = template.count('}')
        if open_count != close_count:
            return False, "花括号不匹配"
        
        return True, ""