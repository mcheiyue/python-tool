"""剪贴板图片处理功能测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication
import sys

from core.features.image.clipboard_handler import ClipboardImageHandler


@pytest.fixture(scope="module")
def qapp():
    """创建 QApplication 实例用于测试"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestClipboardImageHandler:
    """测试剪贴板图片处理器"""
    
    @pytest.fixture
    def handler(self, qapp):
        """创建处理器实例"""
        return ClipboardImageHandler()
    
    @pytest.fixture
    def sample_image(self):
        """创建测试图片"""
        img = Image.new('RGB', (100, 100), color='red')
        return img
    
    @pytest.fixture
    def sample_qimage(self):
        """创建测试 QImage"""
        qimage = QImage(100, 100, QImage.Format.Format_RGB32)
        qimage.fill(0xFF0000)  # 红色
        return qimage
    
    def test_get_image_with_image(self, handler, sample_qimage):
        """测试从剪贴板获取图片 - 有图片时"""
        with patch('PyQt6.QtWidgets.QApplication.clipboard') as mock_clipboard_func:
            mock_clipboard = Mock()
            mock_mime_data = Mock()
            mock_mime_data.hasImage.return_value = True
            mock_clipboard.mimeData.return_value = mock_mime_data
            mock_clipboard.image.return_value = sample_qimage
            mock_clipboard_func.return_value = mock_clipboard
            
            result = handler.get_image()
            
            assert result is not None
            assert isinstance(result, Image.Image)
            assert result.size == (100, 100)
    
    def test_get_image_without_image(self, handler):
        """测试从剪贴板获取图片 - 无图片时"""
        with patch('PyQt6.QtWidgets.QApplication.clipboard') as mock_clipboard_func:
            mock_clipboard = Mock()
            mock_mime_data = Mock()
            mock_mime_data.hasImage.return_value = False
            mock_clipboard.mimeData.return_value = mock_mime_data
            mock_clipboard_func.return_value = mock_clipboard
            
            result = handler.get_image()
            
            assert result is None
    
    def test_get_image_null_image(self, handler):
        """测试从剪贴板获取图片 - 空图片"""
        with patch('PyQt6.QtWidgets.QApplication.clipboard') as mock_clipboard_func:
            mock_clipboard = Mock()
            mock_mime_data = Mock()
            mock_mime_data.hasImage.return_value = True
            
            null_qimage = QImage()  # 空图片
            mock_clipboard.image.return_value = null_qimage
            mock_clipboard.mimeData.return_value = mock_mime_data
            mock_clipboard_func.return_value = mock_clipboard
            
            result = handler.get_image()
            
            assert result is None
    
    def test_save_image_png(self, handler, sample_image, tmp_path):
        """测试保存 PNG 格式"""
        output_path = tmp_path / "test.png"
        
        with patch.object(handler, 'get_image', return_value=sample_image):
            result = handler.save_image(str(output_path), format='PNG')
            
            assert result is True
            assert output_path.exists()
            
            # 验证保存的图片
            saved_img = Image.open(output_path)
            assert saved_img.size == (100, 100)
    
    def test_save_image_jpeg(self, handler, tmp_path):
        """测试保存 JPEG 格式（RGBA -> RGB 转换）"""
        # 创建 RGBA 图片
        rgba_img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        output_path = tmp_path / "test.jpg"
        
        with patch.object(handler, 'get_image', return_value=rgba_img):
            result = handler.save_image(str(output_path), format='JPEG', quality=90)
            
            assert result is True
            assert output_path.exists()
            
            # 验证转换为 RGB
            saved_img = Image.open(output_path)
            assert saved_img.mode == 'RGB'
    
    def test_save_image_no_image(self, handler, tmp_path):
        """测试保存图片 - 剪贴板无图片"""
        output_path = tmp_path / "test.png"
        
        with patch.object(handler, 'get_image', return_value=None):
            result = handler.save_image(str(output_path))
            
            assert result is False
            assert not output_path.exists()
    
    def test_save_image_custom_quality(self, handler, sample_image, tmp_path):
        """测试自定义质量参数"""
        output_path = tmp_path / "test.jpg"
        
        with patch.object(handler, 'get_image', return_value=sample_image):
            result = handler.save_image(str(output_path), format='JPEG', quality=50)
            
            assert result is True
            assert output_path.exists()
    
    def test_set_image_success(self, handler, sample_image, tmp_path):
        """测试复制图片到剪贴板 - 成功"""
        # 创建测试图片文件
        img_path = tmp_path / "test.png"
        sample_image.save(img_path)
        
        with patch('PyQt6.QtWidgets.QApplication.clipboard') as mock_clipboard_func:
            mock_clipboard = Mock()
            mock_clipboard_func.return_value = mock_clipboard
            
            result = handler.set_image(str(img_path))
            
            assert result is True
            mock_clipboard.setMimeData.assert_called_once()
    
    def test_set_image_nonexistent_file(self, handler, tmp_path):
        """测试复制图片到剪贴板 - 文件不存在"""
        img_path = tmp_path / "nonexistent.png"
        
        result = handler.set_image(str(img_path))
        
        assert result is False
    
    def test_format_case_insensitive(self, handler, sample_image, tmp_path):
        """测试格式大小写不敏感"""
        output_path1 = tmp_path / "test1.png"
        output_path2 = tmp_path / "test2.png"
        
        with patch.object(handler, 'get_image', return_value=sample_image):
            # 使用小写格式
            result1 = handler.save_image(str(output_path1), format='png')
            assert result1 is True
            assert output_path1.exists()
            
            # 使用大写格式
            result2 = handler.save_image(str(output_path2), format='PNG')
            assert result2 is True
            assert output_path2.exists()
    
    def test_qimage_to_pil_conversion(self, handler, sample_qimage):
        """测试 QImage 到 PIL Image 的转换"""
        pil_image = handler._qimage_to_pil(sample_qimage)
        
        assert pil_image is not None
        assert isinstance(pil_image, Image.Image)
        assert pil_image.size == (100, 100)
