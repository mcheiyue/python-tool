from PyQt6.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    """通用工作线程，支持任意可调用任务"""
    finished = pyqtSignal(object)  # 返回结果
    error = pyqtSignal(str)        # 返回错误信息
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.task_func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

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

    def run(self):
        self.merger.merge(self.files, self.output_path)

class CompressThread(QThread):
    def __init__(self, compressor, files, quality, gs_path):
        super().__init__()
        self.compressor = compressor
        self.files = files
        self.quality = quality
        self.gs_path = gs_path

    def run(self):
        # 使用关键字参数传递 gs_path，适配新的引擎接口
        self.compressor.compress(self.files, self.quality, gs_path=self.gs_path)

class PDFSplitThread(QThread):
    def __init__(self, splitter, file_path, ranges, output_dir):
        super().__init__()
        self.splitter = splitter
        self.file_path = file_path
        self.ranges = ranges
        self.output_dir = output_dir

    def run(self):
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

    def run(self):
        self.renderer.render_all(
            self.files,
            self.output_dir,
            self.dpi,
            self.output_format,
            self.page_range,
            use_ghostscript=self.use_ghostscript
        )
