import pytest
from pypdf import PdfReader
from core.features.pdf.pdf_metadata import PDFMetadataEditor

class TestPDFMetadata:
    
    def test_read_write_metadata(self, sample_pdf, tmp_path):
        """测试元数据读写"""
        editor = PDFMetadataEditor()
        output_path = tmp_path / "metadata_test.pdf"
        
        # 准备元数据 (注意：PDFMetadataEditor 期望首字母大写的键)
        new_metadata = {
            'Title': 'Test Title',
            'Author': 'Test Author',
            'Subject': 'Unit Testing',
            'Keywords': 'pytest, pdf'
        }
        
        # 写入元数据
        editor.write_metadata(sample_pdf, str(output_path), new_metadata)
        
        assert output_path.exists()
        
        # 读取并验证
        read_metadata = editor.read_metadata(str(output_path))
        
        # read_metadata 方法已经移除了 '/' 前缀
        assert read_metadata.get('Title') == 'Test Title'
        assert read_metadata.get('Author') == 'Test Author'
        assert read_metadata.get('Subject') == 'Unit Testing'
        assert read_metadata.get('Keywords') == 'pytest, pdf'
        assert read_metadata.get('Creator') == 'Office Toolkit'