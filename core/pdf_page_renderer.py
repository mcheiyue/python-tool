"""
PDF 页面渲染模块 - 使用 PyMuPDF 将 PDF 页面渲染为图片
"""
import os
import traceback
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None


class PDFPageRenderer(QObject):
    """PDF 页面渲染器 - 将 PDF 页面转换为图片"""
    
    # 信号定义
    progress = pyqtSignal(int, int, str)  # current, total, message
    log = pyqtSignal(str)                 # log message
    finished = pyqtSignal(int, int)       # success_count, fail_count
    
    # 支持的输出格式
    SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'webp']
    
    # 预设 DPI 选项
    DPI_OPTIONS = {
        '屏幕 (72 DPI)': 72,
        '标准 (150 DPI)': 150,
        '高清 (300 DPI)': 300,
        '印刷 (600 DPI)': 600,
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
    
    @staticmethod
    def is_available() -> bool:
        """检查 PyMuPDF 是否可用"""
        return PYMUPDF_AVAILABLE
    
    def stop(self):
        """停止当前任务"""
        self._is_running = False
    
    def get_page_count(self, pdf_path: str) -> int:
        """获取 PDF 页数"""
        if not PYMUPDF_AVAILABLE:
            return 0
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0
    
    def get_page_info(self, pdf_path: str) -> List[dict]:
        """获取所有页面信息"""
        if not PYMUPDF_AVAILABLE:
            return []
        
        pages = []
        try:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                rect = page.rect
                pages.append({
                    'index': i,
                    'number': i + 1,
                    'width': rect.width,
                    'height': rect.height,
                    'rotation': page.rotation
                })
            doc.close()
        except Exception:
            pass
        return pages
    
    def render_page(
        self,
        pdf_path: str,
        page_num: int,
        output_path: str,
        dpi: int = 300,
        output_format: str = 'png'
    ) -> bool:
        """
        渲染单个页面为图片
        
        Args:
            pdf_path: PDF 文件路径
            page_num: 页码（从 0 开始）
            output_path: 输出文件路径
            dpi: 渲染分辨率
            output_format: 输出格式 (png/jpg/webp)
        
        Returns:
            bool: 是否成功
        """
        if not PYMUPDF_AVAILABLE:
            self.log.emit("错误: PyMuPDF 模块未安装")
            return False
        
        try:
            doc = fitz.open(pdf_path)
            
            if page_num < 0 or page_num >= len(doc):
                self.log.emit(f"错误: 页码 {page_num + 1} 超出范围 (共 {len(doc)} 页)")
                doc.close()
                return False
            
            page = doc[page_num]
            
            # 计算缩放矩阵 (基于 DPI)
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # 渲染页面
            pix = page.get_pixmap(matrix=mat)
            
            # 根据格式保存
            output_format = output_format.lower()
            if output_format in ['jpg', 'jpeg']:
                pix.save(output_path, output='jpeg', jpg_quality=95)
            elif output_format == 'webp':
                # PyMuPDF 不直接支持 WebP，先保存为 PNG 再转换
                pix.save(output_path)
            else:
                pix.save(output_path)
            
            doc.close()
            return True
            
        except Exception as e:
            self.log.emit(f"错误: 渲染页面失败 - {str(e)}")
            return False
    
    def render_all(
        self,
        pdf_files: List[str],
        output_dir: str,
        dpi: int = 300,
        output_format: str = 'png',
        page_range: Optional[Tuple[int, int]] = None
    ):
        """
        批量渲染多个 PDF 的所有页面
        
        Args:
            pdf_files: PDF 文件路径列表
            output_dir: 输出目录
            dpi: 渲染分辨率
            output_format: 输出格式
            page_range: 页面范围 (start, end)，None 表示全部
        """
        if not PYMUPDF_AVAILABLE:
            self.log.emit("错误: PyMuPDF 模块未安装，无法进行渲染")
            self.finished.emit(0, len(pdf_files))
            return
        
        if not pdf_files:
            self.finished.emit(0, 0)
            return
        
        self._is_running = True
        success_count = 0
        fail_count = 0
        total_files = len(pdf_files)
        
        self.log.emit(f"开始任务: 处理 {total_files} 个 PDF 文件")
        self.log.emit(f"渲染设置: DPI={dpi}, 格式={output_format.upper()}")
        
        for file_idx, pdf_path in enumerate(pdf_files):
            if not self._is_running:
                self.log.emit("任务已停止")
                break
            
            file_name = os.path.basename(pdf_path)
            self.progress.emit(file_idx, total_files, f"正在处理: {file_name}")
            self.log.emit(f"\n--- 处理文件 [{file_idx + 1}/{total_files}]: {file_name} ---")
            
            if not pdf_path.lower().endswith('.pdf'):
                self.log.emit(f"❌ 跳过: 不是有效的 PDF 文件")
                fail_count += 1
                continue
            
            if not os.path.exists(pdf_path):
                self.log.emit(f"❌ 跳过: 文件不存在")
                fail_count += 1
                continue
            
            try:
                doc = fitz.open(pdf_path)
                page_count = len(doc)
                
                # 确定页面范围
                start_page = 0
                end_page = page_count
                if page_range:
                    start_page = max(0, page_range[0])
                    end_page = min(page_count, page_range[1])
                
                # 为每个 PDF 创建子目录
                base_name = os.path.splitext(file_name)[0]
                file_out_dir = os.path.join(output_dir, base_name + "_pages")
                if not os.path.exists(file_out_dir):
                    os.makedirs(file_out_dir)
                
                rendered_count = 0
                
                for page_num in range(start_page, end_page):
                    if not self._is_running:
                        break
                    
                    page = doc[page_num]
                    
                    # 计算缩放矩阵
                    zoom = dpi / 72.0
                    mat = fitz.Matrix(zoom, zoom)
                    
                    # 渲染页面
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 生成输出文件名
                    output_name = f"page_{page_num + 1:04d}.{output_format}"
                    output_path = os.path.join(file_out_dir, output_name)
                    
                    # 保存图片
                    if output_format in ['jpg', 'jpeg']:
                        pix.save(output_path, output='jpeg', jpg_quality=95)
                    else:
                        pix.save(output_path)
                    
                    rendered_count += 1
                    self.log.emit(f"  渲染: 第 {page_num + 1} 页 -> {output_name}")
                
                doc.close()
                
                if rendered_count > 0:
                    self.log.emit(f"✅ 完成: 渲染了 {rendered_count} 页 -> {file_out_dir}")
                    success_count += 1
                else:
                    self.log.emit(f"ℹ️ 未渲染任何页面")
                    # 删除空目录
                    if os.path.exists(file_out_dir) and not os.listdir(file_out_dir):
                        os.rmdir(file_out_dir)
                    fail_count += 1
                    
            except Exception as e:
                error_trace = traceback.format_exc()
                self.log.emit(f"❌ 处理失败:\n{error_trace}")
                fail_count += 1
        
        self._is_running = False
        self.progress.emit(total_files, total_files, "完成")
        self.finished.emit(success_count, fail_count)