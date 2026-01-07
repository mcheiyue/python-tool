import os
from typing import Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal
from pypdf import PdfReader, PdfWriter
from core.utils.logger import AppLogger, timed_operation


class PDFMetadataEditor(QObject):
    """PDF 元数据编辑器"""
    
    finished = pyqtSignal(bool, str)  # success, message
    log = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = AppLogger()
    
    def read_metadata(self, pdf_path: str) -> Dict[str, str]:
        """
        读取 PDF 元数据
        
        :param pdf_path: PDF 文件路径
        :return: 元数据字典
        """
        try:
            self.logger.info(f"读取 PDF 元数据: {pdf_path}")
            reader = PdfReader(pdf_path)
            
            if reader.metadata is None:
                self.logger.warning(f"PDF 文件没有元数据: {pdf_path}")
                return {}
            
            # 转换为普通字典，移除 PDF 特有的前缀
            metadata = {}
            for key, value in reader.metadata.items():
                # 移除 '/' 前缀
                clean_key = key.lstrip('/')
                metadata[clean_key] = str(value) if value else ''
            
            self.logger.debug(f"元数据读取成功，包含 {len(metadata)} 个字段")
            return metadata
            
        except Exception as e:
            error_msg = f"读取元数据失败: {str(e)}"
            self.logger.error(error_msg)
            self.log.emit(f"❌ {error_msg}")
            return {}
    
    @timed_operation("PDF 元数据写入")
    def write_metadata(self, pdf_path: str, output_path: str, metadata: Dict[str, str]) -> bool:
        """
        写入 PDF 元数据
        
        :param pdf_path: 源 PDF 文件路径
        :param output_path: 输出 PDF 文件路径
        :param metadata: 元数据字典
        :return: 是否成功
        """
        try:
            self.log.emit(f"正在处理: {os.path.basename(pdf_path)}")
            self.logger.info(f"写入 PDF 元数据: {pdf_path} -> {output_path}")
            
            # 读取源 PDF
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 构建元数据（添加 '/' 前缀）
            pdf_metadata = {}
            
            # 标准元数据字段
            if 'Title' in metadata and metadata['Title']:
                pdf_metadata['/Title'] = metadata['Title']
            if 'Author' in metadata and metadata['Author']:
                pdf_metadata['/Author'] = metadata['Author']
            if 'Subject' in metadata and metadata['Subject']:
                pdf_metadata['/Subject'] = metadata['Subject']
            if 'Keywords' in metadata and metadata['Keywords']:
                pdf_metadata['/Keywords'] = metadata['Keywords']
            
            # 添加创建者信息
            pdf_metadata['/Creator'] = metadata.get('Creator', 'Office Toolkit')
            pdf_metadata['/Producer'] = metadata.get('Producer', 'Office Toolkit PDF Metadata Editor')
            
            # 写入元数据
            writer.add_metadata(pdf_metadata)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 保存文件
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            success_msg = f"元数据写入成功: {os.path.basename(output_path)}"
            self.logger.info(success_msg)
            self.log.emit(f"✅ {success_msg}")
            self.finished.emit(True, output_path)
            return True
            
        except Exception as e:
            error_msg = f"写入元数据失败: {str(e)}"
            self.logger.error(error_msg)
            self.log.emit(f"❌ {error_msg}")
            self.finished.emit(False, str(e))
            return False
    
    def batch_write_metadata(self, files: list, metadata: Dict[str, str], output_dir: Optional[str] = None):
        """
        批量写入元数据
        
        :param files: PDF 文件列表
        :param metadata: 要写入的元数据
        :param output_dir: 输出目录（None 则覆盖原文件）
        """
        total = len(files)
        success = 0
        fail = 0
        
        self.log.emit(f"开始批量处理 {total} 个文件")
        
        for i, file_path in enumerate(files):
            file_name = os.path.basename(file_path)
            self.log.emit(f"[{i+1}/{total}] 处理: {file_name}")
            
            # 确定输出路径
            if output_dir:
                output_path = os.path.join(output_dir, file_name)
            else:
                # 创建备份
                name_root, ext = os.path.splitext(file_path)
                output_path = f"{name_root}_metadata{ext}"
            
            # 写入元数据
            if self.write_metadata(file_path, output_path, metadata):
                success += 1
            else:
                fail += 1
        
        self.log.emit(f"批量处理完成: 成功 {success} 个，失败 {fail} 个")
        self.finished.emit(success > 0, f"完成 {success}/{total}")