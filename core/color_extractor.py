from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal

class ColorExtractor(QObject):
    finished = pyqtSignal(list, str) # result_list, error_msg
    log = pyqtSignal(str)

    def extract(self, image_path, n_colors=8):
        try:
            self.log.emit(f"正在加载图片: {image_path}")
            with Image.open(image_path) as img:
                # 缩放以加快计算
                img_resized = img.resize((150, 150))
                # 转换为 RGB 模式
                img_rgb = img_resized.convert('RGB')

                self.log.emit(f"正在分析颜色 ({n_colors} 色)...")
                
                # 使用 Pillow 自带的量化方法 (MEDIANCUT) 提取主色调
                # quantize 会返回一个 P 模式图像，其调色板即为主色调
                quantized = img_rgb.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
                
                # 获取调色板 (RGB RGB RGB ...)
                palette = quantized.getpalette()
                
                # 获取每个颜色的像素数量 (count, index)
                # getcolors 返回 [(count, index), ...]
                color_counts = quantized.getcolors(maxcolors=n_colors+1)
                
                if not color_counts:
                    raise Exception("无法提取颜色")

                # 计算总像素数
                total_pixels = sum(count for count, _ in color_counts)
                
                # 整理结果
                results = []
                
                # 按数量降序排序
                sorted_colors = sorted(color_counts, key=lambda x: x[0], reverse=True)
                
                # 取前 n_colors 个 (有些时候 quantize 可能会产生比请求更少的颜色)
                for count, index in sorted_colors[:n_colors]:
                    # 从调色板中获取 RGB 值
                    # 调色板是扁平列表 [r0, g0, b0, r1, g1, b1, ...]
                    r = palette[index * 3]
                    g = palette[index * 3 + 1]
                    b = palette[index * 3 + 2]
                    
                    prop = count / total_pixels
                    hex_code = "#{:02x}{:02x}{:02x}".format(r, g, b)
                    
                    results.append({
                        'rgb': (r, g, b),
                        'hex': hex_code,
                        'proportion': float(prop)
                    })

                self.log.emit("提取完成")
                self.finished.emit(results, "")

        except Exception as e:
            self.log.emit(f"错误: {str(e)}")
            self.finished.emit([], str(e))
