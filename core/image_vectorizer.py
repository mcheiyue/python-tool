import vtracer
from PyQt6.QtCore import QObject, pyqtSignal

class ImageVectorizer(QObject):
    finished = pyqtSignal(bool, str) # success, msg
    log = pyqtSignal(str)

    def convert(self, input_path, output_path, colormode='color', hierarchical='stacked', mode='spline', filter_speckle=4, corner_threshold=60, length_threshold=2, max_iterations=10, splice_threshold=45, path_precision=3):
        try:
            self.log.emit(f"开始转换: {input_path}")
            # vtracer 核心转换
            vtracer.convert_image_to_svg_py(
                input_path,
                output_path,
                colormode=colormode,
                hierarchical=hierarchical,
                mode=mode,
                filter_speckle=filter_speckle,
                corner_threshold=corner_threshold,
                length_threshold=length_threshold,
                max_iterations=max_iterations,
                splice_threshold=splice_threshold,
                path_precision=path_precision
            )
            self.log.emit(f"转换成功: {output_path}")
            self.finished.emit(True, output_path)
        except Exception as e:
            self.log.emit(f"错误: {str(e)}")
            self.finished.emit(False, str(e))
