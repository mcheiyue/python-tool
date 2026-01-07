import sys
import os
import pytest
from pypdf import PdfWriter
import os

# 获取项目根目录 (tests 目录的上一级)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 将项目根目录添加到 sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT

@pytest.fixture
def sample_pdf(tmp_path):
    """创建一个简单的单页 PDF 文件用于测试"""
    pdf_path = tmp_path / "test.pdf"
    
    # 使用 pypdf 创建一个简单的空白 PDF
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)  # Letter size
    
    with open(pdf_path, "wb") as f:
        writer.write(f)
            
    return str(pdf_path)