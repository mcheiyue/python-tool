"""
PDF 页面渲染模块 - 使用 PyMuPDF 将 PDF 页面渲染为图片
"""
import os
import traceback
from typing import List, Optional, Tuple
import subprocess
import platform

from core.external_tools.manager import ExternalToolManager

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None


class PDFPageRenderer:
    """PDF 页面渲染器 - 将 PDF 页面转换为图片"""

    # 支持的输出格式
    SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'webp']
    
    # 预设 DPI 选项
    DPI_OPTIONS = {
        '屏幕 (72 DPI)': 72,
        '标准 (150 DPI)': 150,
        '高清 (300 DPI)': 300,
        '印刷 (600 DPI)': 600,
    }
    
    def __init__(self):
        self._is_running = False
        self.gs_tool = ExternalToolManager().get_tool("ghostscript")
    
    @staticmethod
    def is_available() -> bool:
        """检查 PyMuPDF 是否可用"""
        return PYMUPDF_AVAILABLE

    def is_gs_available(self) -> bool:
        """检查 Ghostscript 是否可用"""
        return self.gs_tool.check_installed() and not self.gs_tool.is_disabled
    
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
    
    def render_with_ghostscript(
        self,
        pdf_path: str,
        page_num: int,
        output_path: str,
        dpi: int = 300,
        output_format: str = 'png',
        *,
        on_log=None,
    ) -> bool:
        """
        使用 Ghostscript 渲染单个页面
        """

        def log(msg):
            if on_log:
                on_log(msg)

        gs_path = self.gs_tool.get_path()
        if not gs_path:
            return False

        # 准备设备参数
        device_map = {
            'png': 'png16m',
            'jpg': 'jpeg',
            'jpeg': 'jpeg',
            'webp': 'png16m', # GS 原生不支持 webp，先转 png
        }
        
        fmt = output_format.lower()
        device = device_map.get(fmt, 'png16m')
        
        # 实际输出路径 (如果是 webp，先输出为 png)
        real_output = output_path
        if fmt == 'webp':
            real_output = output_path + ".png"

        # 构建命令
        # -dFirstPage=N -dLastPage=N (GS 页码从 1 开始)
        gs_page = page_num + 1
        
        cmd = [
            gs_path,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            f"-dFirstPage={gs_page}",
            f"-dLastPage={gs_page}",
            f"-sDEVICE={device}",
            f"-r{dpi}",
            f"-sOutputFile={real_output}",
            pdf_path
        ]
        
        try:
            # Windows 下隐藏窗口
            startupinfo = None
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                log(f"Ghostscript 错误: {stderr.decode('utf-8', errors='ignore')}")
                return False

            # 如果目标是 webp，需要转换 (利用 Pillow)
            if fmt == 'webp':
                try:
                    from PIL import Image
                    img = Image.open(real_output)
                    img.save(output_path, 'WEBP')
                    img.close()
                    os.remove(real_output)
                except ImportError:
                    log("缺少 Pillow 库，无法转换为 WebP")
                    return False
                except Exception as e:
                    log(f"WebP 转换失败: {e}")
                    return False
            
            return True
            
        except Exception as e:
            log(f"Ghostscript 执行异常: {e}")
            return False
    
    def render_all(
        self,
        pdf_files: List[str],
        output_dir: str,
        dpi: int = 300,
        output_format: str = 'png',
        page_range: Optional[Tuple[int, int]] = None,
        use_ghostscript: bool = False,
        *,
        on_log=None,
        on_progress=None,
        on_finished=None,
    ):
        """
        批量渲染多个 PDF 的所有页面
        
        Args:
            pdf_files: PDF 文件路径列表
            output_dir: 输出目录
            dpi: 渲染分辨率
            output_format: 输出格式
            page_range: 页面范围 (start, end)，None 表示全部
            use_ghostscript: 是否优先使用 Ghostscript
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, fail):
            if on_finished:
                on_finished(ok, fail)

        # 只要有一个引擎可用就行
        if not PYMUPDF_AVAILABLE and not (use_ghostscript and self.is_gs_available()):
            log("错误: 未找到可用的 PDF 渲染引擎 (PyMuPDF 或 Ghostscript)")
            finished(0, len(pdf_files))
            return
        
        if not pdf_files:
            finished(0, 0)
            return
        
        self._is_running = True
        success_count = 0
        fail_count = 0
        total_files = len(pdf_files)
        
        log(f"开始任务: 处理 {total_files} 个 PDF 文件")
        log(f"渲染设置: DPI={dpi}, 格式={output_format.upper()}")
        
        for file_idx, pdf_path in enumerate(pdf_files):
            if not self._is_running:
                log("任务已停止")
                break
            
            file_name = os.path.basename(pdf_path)
            progress(file_idx, total_files, f"正在处理: {file_name}")
            log(f"\n--- 处理文件 [{file_idx + 1}/{total_files}]: {file_name} ---")
            
            if not pdf_path.lower().endswith('.pdf'):
                log(f"❌ 跳过: 不是有效的 PDF 文件")
                fail_count += 1
                continue
            
            if not os.path.exists(pdf_path):
                log(f"❌ 跳过: 文件不存在")
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
                    
                    # 生成输出文件名
                    output_name = f"page_{page_num + 1:04d}.{output_format}"
                    output_path = os.path.join(file_out_dir, output_name)

                    success = False
                    
                    # 1. 尝试 Ghostscript (如果启用)
                    if use_ghostscript and self.is_gs_available():
                        success = self.render_with_ghostscript(pdf_path, page_num, output_path, dpi, output_format, on_log=on_log)
                    
                    # 2. 回退到 PyMuPDF
                    if not success:
                        if use_ghostscript: # 只有在尝试过 GS 后才提示
                             pass # 静默回退，或者可以在日志里提一句
                             
                        # 渲染页面
                        pix = page.get_pixmap(matrix=mat)
                        
                        # 保存图片
                        if output_format in ['jpg', 'jpeg']:
                            pix.save(output_path, output='jpeg', jpg_quality=95)
                        elif output_format == 'webp':
                             pix.save(output_path)
                        else:
                            pix.save(output_path)
                        success = True

                    if success:
                        rendered_count += 1
                        log(f"  渲染: 第 {page_num + 1} 页 -> {output_name}")
                
                doc.close()
                
                if rendered_count > 0:
                    log(f"✅ 完成: 渲染了 {rendered_count} 页 -> {file_out_dir}")
                    success_count += 1
                else:
                    log(f"ℹ️ 未渲染任何页面")
                    # 删除空目录
                    if os.path.exists(file_out_dir) and not os.listdir(file_out_dir):
                        os.rmdir(file_out_dir)
                    fail_count += 1
                    
            except Exception as e:
                error_trace = traceback.format_exc()
                log(f"❌ 处理失败:\n{error_trace}")
                fail_count += 1
        
        self._is_running = False
        progress(total_files, total_files, "完成")
        finished(success_count, fail_count)