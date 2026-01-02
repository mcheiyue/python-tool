from PyQt6.QtCore import QThread

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
        self.compressor.compress(self.files, self.quality, self.gs_path)

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
