from PyQt6.QtCore import QThread, pyqtSignal
from typing import Callable, Any, Optional


class WorkerThread(QThread):
    """
    通用工作线程，支持任意可调用任务
    
    这是推荐的线程实现方式。新代码应该优先使用此类而非创建专用线程类。
    
    使用示例:
    ```python
    # 方式1: 直接传递方法
    thread = WorkerThread(self.processor.process, file_path, output_dir)
    thread.finished.connect(self.on_finished)
    thread.error.connect(self.on_error)
    thread.start()
    
    # 方式2: 使用 lambda（注意捕获变量）
    thread = WorkerThread(lambda: self.converter.convert(files))
    
    # 方式3: 需要进度回调的任务（processor 需要发射自己的进度信号）
    thread = WorkerThread(self.processor.process_with_progress, files)
    ```
    
    注意事项:
    - 如果任务需要发射进度信号，应该由 task_func 所属的对象（如 processor）自己处理
    - finished 信号会传递任务返回值
    - error 信号会传递异常信息字符串
    """
    finished = pyqtSignal(object)  # 返回结果（任何类型）
    error = pyqtSignal(str)        # 返回错误信息
    
    def __init__(self, task_func: Callable[..., Any], *args, **kwargs):
        """
        初始化工作线程
        
        Args:
            task_func: 要执行的可调用对象（函数、方法、lambda等）
            *args: 传递给 task_func 的位置参数
            **kwargs: 传递给 task_func 的关键字参数
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def run(self):
        """执行任务"""
        try:
            if not self._is_cancelled:
                result = self.task_func(*self.args, **self.kwargs)
                if not self._is_cancelled:
                    self.finished.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
    
    def cancel(self):
        """
        标记任务为已取消
        
        注意: 这不会立即停止正在执行的任务，只是设置取消标志。
        任务函数需要自己检查取消状态（如果支持的话）。
        """
        self._is_cancelled = True


# ============================================================================
# 以下是遗留的专用线程类
#
# 这些类保留是为了向后兼容。新代码应该使用 WorkerThread 代替。
#
# 迁移示例:
#   旧代码: thread = MergeThread(self.merger, files, output_path)
#   新代码: thread = WorkerThread(self.merger.merge, files, output_path)
# ============================================================================

class ImageVectorThread(QThread):
    def __init__(self, vectorizer, input_path, output_path, **kwargs):
        super().__init__()
        self.vectorizer = vectorizer
        self.input_path = input_path
        self.output_path = output_path
        self.kwargs = kwargs

    def run(self):
        self.vectorizer.convert(self.input_path, self.output_path, **self.kwargs)

class TxtPdfThread(QThread):
    def __init__(self, converter, files, output_dir):
        super().__init__()
        self.converter = converter
        self.files = files
        self.output_dir = output_dir

    def run(self):
        self.converter.convert(self.files, self.output_dir)

class CodeExtractThread(QThread):
    def __init__(self, extractor, root_dir, extensions, output_path):
        super().__init__()
        self.extractor = extractor
        self.root_dir = root_dir
        self.extensions = extensions
        self.output_path = output_path

    def run(self):
        self.extractor.extract(self.root_dir, self.extensions, self.output_path)

class ExtractionThread(QThread):
    def __init__(self, extractor, path, n_colors):
        super().__init__()
        self.extractor = extractor
        self.path = path
        self.n_colors = n_colors

    def run(self):
        self.extractor.extract(self.path, self.n_colors)

class ConversionThread(QThread):
    def __init__(self, converter, files):
        super().__init__()
        self.converter = converter
        self.files = files

    def run(self):
        self.converter.convert(self.files)

class MergeThread(QThread):
    def __init__(self, merger, files, output_path):
        super().__init__()
        self.merger = merger
        self.files = files
        self.output_path = output_path
        self._is_cancelled = False

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def run(self):
        if not self._is_cancelled:
            self.merger.merge(self.files, self.output_path)

class CompressThread(QThread):
    def __init__(self, compressor, files, quality, gs_path):
        super().__init__()
        self.compressor = compressor
        self.files = files
        self.quality = quality
        self.gs_path = gs_path
        self._is_cancelled = False

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def run(self):
        # 使用关键字参数传递 gs_path，适配新的引擎接口
        if not self._is_cancelled:
            self.compressor.compress(self.files, self.quality, gs_path=self.gs_path)

class PDFSplitThread(QThread):
    def __init__(self, splitter, file_path, ranges, output_dir):
        super().__init__()
        self.splitter = splitter
        self.file_path = file_path
        self.ranges = ranges
        self.output_dir = output_dir
        self._is_cancelled = False

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def run(self):
        if not self._is_cancelled:
            self.splitter.split(self.file_path, self.ranges, self.output_dir)

class PDFImageExtractThread(QThread):
    def __init__(self, extractor, files, output_dir):
        super().__init__()
        self.extractor = extractor
        self.files = files
        self.output_dir = output_dir

    def run(self):
        self.extractor.extract(self.files, self.output_dir)

class ImageConvertThread(QThread):
    def __init__(self, converter, input_path, output_path, output_format, quality, rotate_angle=0, flip_mode=None):
        super().__init__()
        self.converter = converter
        self.input_path = input_path
        self.output_path = output_path
        self.output_format = output_format
        self.quality = quality
        self.rotate_angle = rotate_angle
        self.flip_mode = flip_mode

    def run(self):
        self.converter.convert(self.input_path, self.output_path, self.output_format, self.quality, self.rotate_angle, self.flip_mode)

class ImageToPdfThread(QThread):
    def __init__(self, converter, image_paths, output_path, merge):
        super().__init__()
        self.converter = converter
        self.image_paths = image_paths
        self.output_path = output_path
        self.merge = merge

    def run(self):
        self.converter.convert(self.image_paths, self.output_path, self.merge)

class PPTImageExportThread(QThread):
    def __init__(self, exporter, files, output_dir, format):
        super().__init__()
        self.exporter = exporter
        self.files = files
        self.output_dir = output_dir
        self.format = format

    def run(self):
        self.exporter.export(self.files, self.output_dir, self.format)

class DocToDocxThread(QThread):
    def __init__(self, converter, files, output_dir):
        super().__init__()
        self.converter = converter
        self.files = files
        self.output_dir = output_dir

    def run(self):
        self.converter.convert(self.files, self.output_dir)

class PDFRenderThread(QThread):
    """PDF 页面渲染线程"""
    def __init__(self, renderer, files, output_dir, dpi, output_format, page_range=None, use_ghostscript=False):
        super().__init__()
        self.renderer = renderer
        self.files = files
        self.output_dir = output_dir
        self.dpi = dpi
        self.output_format = output_format
        self.page_range = page_range
        self.use_ghostscript = use_ghostscript
        self._is_cancelled = False

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def run(self):
        if not self._is_cancelled:
            self.renderer.render_all(
                self.files,
                self.output_dir,
                self.dpi,
                self.output_format,
                self.page_range,
                use_ghostscript=self.use_ghostscript
            )
