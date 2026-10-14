# 分层豁免（PERMANENT，见 tests/test_layering.py）：QMimeData/QApplication 剪贴板桥即功能本体，剥离 Qt 需引入无收益抽象
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QBuffer, QIODevice, QMimeData, QUrl
from PIL import Image
import io
import os

class ClipboardImageHandler:
    """剪贴板图片处理器"""
    
    def get_image(self) -> Image.Image:
        """从剪贴板获取图片 (返回 PIL Image)"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasImage():
            qimage = clipboard.image()
            if not qimage.isNull():
                return self._qimage_to_pil(qimage)
        return None
    
    def set_image(self, image_path: str) -> bool:
        """将图片文件复制到剪贴板"""
        if not os.path.exists(image_path):
            return False
            
        try:
            # 同时设置图片数据和文件路径，以支持不同的粘贴场景
            image = QImage(image_path)
            if image.isNull():
                return False
                
            mime_data = QMimeData()
            mime_data.setImageData(image)
            
            # 设置文件路径 (支持在资源管理器中粘贴)
            url = QUrl.fromLocalFile(os.path.abspath(image_path))
            mime_data.setUrls([url])
            
            QApplication.clipboard().setMimeData(mime_data)
            return True
        except Exception:
            return False

    def save_image(self, output_path: str, format: str = 'PNG', quality: int = 95) -> bool:
        """保存剪贴板图片到文件"""
        img = self.get_image()
        if img is None:
            return False
            
        try:
            save_kwargs = {}
            if format.upper() in ['JPEG', 'JPG']:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                save_kwargs['quality'] = quality
                
            img.save(output_path, format=format, **save_kwargs)
            return True
        except Exception:
            return False

    def _qimage_to_pil(self, qimage: QImage) -> Image.Image:
        """QImage 转换为 PIL Image"""
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        qimage.save(buffer, "PNG")
        
        pil_im = Image.open(io.BytesIO(buffer.data()))
        return pil_im