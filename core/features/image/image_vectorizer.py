try:
    import vtracer
    VTRACER_AVAILABLE = True
except ImportError:
    VTRACER_AVAILABLE = False
    vtracer = None

class ImageVectorizer:
    def convert(self, input_path, output_path, colormode='color', hierarchical='stacked', mode='spline', filter_speckle=4, corner_threshold=60, length_threshold=2, max_iterations=10, splice_threshold=45, path_precision=3, *, on_log=None, on_finished=None):
        def log(msg):
            if on_log:
                on_log(msg)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)

        if not VTRACER_AVAILABLE:
            finished(False, "错误: vtracer 模块未安装，无法进行转换")
            return

        try:
            log(f"开始转换: {input_path}")
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
            log(f"转换成功: {output_path}")
            finished(True, output_path)
        except BaseException as e:
            # 必须 BaseException：vtracer 的 Rust panic 是 PanicException，非 Exception 子类；
            # 用 except Exception 会漏网，异常逃进 WorkerThread.run 的同款捕获而两个信号都不发
            log(f"错误: {str(e)}")
            finished(False, str(e))
