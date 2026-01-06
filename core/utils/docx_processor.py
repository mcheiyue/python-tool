"""DOCX 后处理器 - 用于处理 Pandoc 生成的 DOCX 文件的样式"""

import io
import sys
import os
import shutil
import tempfile
from typing import Optional

# 尝试导入 python-docx，如果缺失则提供降级处理
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    # 仅在需要调试时打印
    # print("Warning: python-docx not installed. DOCX post-processing will be skipped.")

class DocxProcessor:
    """DOCX 处理工具类"""
    
    @staticmethod
    def apply_custom_processing(
        docx_bytes: bytes, 
        disable_first_para_indent: bool = True, 
        target_style: str = "Body Text"
    ) -> bytes:
        """
        对 DOCX 字节流应用自定义处理
        """
        if not HAS_DOCX:
            return docx_bytes

        try:
            # 加载文档
            doc = Document(io.BytesIO(docx_bytes))
            
            # 处理首段缩进
            if disable_first_para_indent and doc.paragraphs:
                # 检查目标样式是否存在
                if target_style in doc.styles:
                    first_para = doc.paragraphs[0]
                    # 只在首段是默认段落样式时修改
                    if first_para.style.name == "Normal" or first_para.style.name == "Body Text":
                        first_para.style = doc.styles[target_style]
            
            # 输出处理后的字节流
            output = io.BytesIO()
            doc.save(output)
            return output.getvalue()
            
        except Exception as e:
            print(f"Error processing DOCX: {e}")
            # 如果处理失败，返回原始字节流
            return docx_bytes

    @staticmethod
    def process_file(
        file_path: str,
        disable_first_para_indent: bool = True,
        target_style: str = "Body Text",
        fix_fonts: bool = True
    ) -> bool:
        """
        直接处理 DOCX 文件
        """
        if not HAS_DOCX:
            return False

        try:
            doc = Document(file_path)
            
            # 1. 修复字体 (可选)
            if fix_fonts:
                from docx.shared import Pt
                from docx.oxml.ns import qn
                
                # 定义默认中西文字体
                DEFAULT_FONT = 'Calibri'
                DEFAULT_EAST_ASIA_FONT = 'Microsoft YaHei' # 微软雅黑
                
                # 更新核心样式的字体
                for style in doc.styles:
                    if hasattr(style, 'font'):
                        # 设置西文字体
                        if not style.font.name:
                            style.font.name = DEFAULT_FONT
                        
                        # 设置中文字体 (需要操作底层 XML)
                        rPr = style.element.get_or_add_rPr()
                        # w:rFonts 负责字体定义
                        rFonts = rPr.find(qn('w:rFonts'))
                        if rFonts is None:
                            rFonts = rPr.makeelement(qn('w:rFonts'))
                            rPr.append(rFonts)
                        
                        # 设置 EastAsia 字体
                        rFonts.set(qn('w:eastAsia'), DEFAULT_EAST_ASIA_FONT)
                        
                        # 确保段落间距适中 (Pandoc 有时会生成过大的间距)
                        if hasattr(style, 'paragraph_format'):
                            # 如果没有特定设置，可以微调行距，这里暂不强制覆盖，避免破坏特定排版
                            pass

            # 2. 处理首段缩进
            if disable_first_para_indent and doc.paragraphs:
                # 很多时候 Pandoc 生成的文档首段格式可能不符合预期
                # 尝试将第一段设为 'Body Text' 或 'Normal'
                first_para = doc.paragraphs[0]
                # 简单的逻辑：如果第一段是标题，通常不需要改；如果是正文，确保样式正确
                if not first_para.style.name.startswith('Heading'):
                     # 确保 Body Text 存在
                    if target_style in doc.styles:
                         first_para.style = doc.styles[target_style]
                    elif 'Normal' in doc.styles:
                         first_para.style = doc.styles['Normal']
            
            # 安全保存：写入临时文件，然后移动
            # 解决文件被占用或写入未完成导致其他程序打开异常的问题
            dir_name = os.path.dirname(file_path)
            temp_fd, temp_path = tempfile.mkstemp(suffix='.docx', dir=dir_name)
            os.close(temp_fd)
            
            doc.save(temp_path)
            
            # 原子替换
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(temp_path, file_path)
            
            return True
        except Exception as e:
            print(f"Error processing DOCX file {file_path}: {e}")
            return False
