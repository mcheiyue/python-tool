"""DOCX 后处理器 - 用于处理 Pandoc 生成的 DOCX 文件的样式"""

import io
import sys
from typing import Optional

# 尝试导入 python-docx，如果缺失则提供降级处理
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("Warning: python-docx not installed. DOCX post-processing will be skipped.")

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
        target_style: str = "Body Text"
    ) -> bool:
        """
        直接处理 DOCX 文件
        """
        if not HAS_DOCX:
            return False

        try:
            doc = Document(file_path)
            
            if disable_first_para_indent and doc.paragraphs:
                if target_style in doc.styles:
                    first_para = doc.paragraphs[0]
                    if first_para.style.name == "Normal" or first_para.style.name == "Body Text":
                        first_para.style = doc.styles[target_style]
            
            doc.save(file_path)
            return True
        except Exception as e:
            print(f"Error processing DOCX file {file_path}: {e}")
            return False
