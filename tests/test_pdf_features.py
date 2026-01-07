import os
import pytest
from pypdf import PdfReader
from core.features.pdf.pdf_security import PDFSecurity

class TestPDFFeatures:
    
    def test_pdf_encrypt(self, sample_pdf, tmp_path):
        """测试 PDF 加密功能"""
        security = PDFSecurity()
        output_path = tmp_path / "encrypted.pdf"
        password = "test_password"
        
        # 执行加密
        security.encrypt(sample_pdf, str(output_path), password)
        
        # 验证文件已创建
        assert output_path.exists()
        
        # 验证文件确实被加密
        reader = PdfReader(str(output_path))
        assert reader.is_encrypted
        
        # 验证使用错误密码无法读取（pypdf 可能会抛出错误或返回 False）
        # 注意：不同版本的 pypdf 行为可能不同，这里仅验证加密状态
        
        # 验证使用正确密码可以解密
        assert reader.decrypt(password) > 0

    def test_pdf_decrypt(self, sample_pdf, tmp_path):
        """测试 PDF 解密功能"""
        security = PDFSecurity()
        encrypted_path = tmp_path / "encrypted_for_decrypt.pdf"
        decrypted_path = tmp_path / "decrypted.pdf"
        password = "secret_password"
        
        # 先加密一个文件用于测试
        security.encrypt(sample_pdf, str(encrypted_path), password)
        assert encrypted_path.exists()
        
        # 执行解密
        security.decrypt(str(encrypted_path), str(decrypted_path), password)
        
        # 验证文件已创建
        assert decrypted_path.exists()
        
        # 验证文件不再加密
        reader = PdfReader(str(decrypted_path))
        assert not reader.is_encrypted