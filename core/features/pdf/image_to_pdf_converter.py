from PIL import Image
import os

class ImageToPdfConverter:
    def convert(self, image_paths, output_path, merge=True, *, on_log=None, on_finished=None):
        """
        将图片转换为 PDF
        :param image_paths: 图片路径列表
        :param output_path: 输出路径（如果是合并模式则是文件路径，否则是目录路径）
        :param merge: 是否合并为一个 PDF
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)

        try:
            if not image_paths:
                finished(False, "没有输入文件")
                return

            if merge:
                self._convert_merge(image_paths, output_path, on_log, on_finished)
            else:
                self._convert_single(image_paths, output_path, on_log, on_finished)

        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            log(error_msg)
            finished(False, str(e))

    def _convert_merge(self, image_paths, output_file, on_log, on_finished):
        def log(msg):
            if on_log:
                on_log(msg)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)

        try:
            images = []
            first_image = None

            log(f"正在准备合并 {len(image_paths)} 张图片...")

            for path in image_paths:
                log(f"处理图片: {os.path.basename(path)}")
                with Image.open(path) as img:
                    # 转换颜色模式，PDF 不支持 RGBA
                    if img.mode == 'RGBA':
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        converted_img = background
                    elif img.mode != 'RGB':
                        converted_img = img.convert('RGB')
                    else:
                        converted_img = img.copy()
                    
                    if first_image is None:
                        first_image = converted_img
                    else:
                        images.append(converted_img)

            if first_image:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                log("正在生成 PDF 文件...")
                first_image.save(output_file, "PDF", resolution=100.0, save_all=True, append_images=images)
                
                # 关闭所有 Image 对象
                first_image.close()
                for img in images:
                    img.close()
                
                log(f"成功生成: {os.path.basename(output_file)}")
                finished(True, output_file)
            else:
                finished(False, "无法加载任何图片")

        except Exception as e:
            raise e

    def _convert_single(self, image_paths, output_dir, on_log, on_finished):
        def log(msg):
            if on_log:
                on_log(msg)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)

        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            success_count = 0
            for path in image_paths:
                try:
                    log(f"处理图片: {os.path.basename(path)}")
                    with Image.open(path) as img:
                        if img.mode == 'RGBA':
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[3])
                            converted_img = background
                        elif img.mode != 'RGB':
                            converted_img = img.convert('RGB')
                        else:
                            converted_img = img.copy()

                        base_name = os.path.splitext(os.path.basename(path))[0]
                        output_file = os.path.join(output_dir, f"{base_name}.pdf")
                        
                        converted_img.save(output_file, "PDF", resolution=100.0)
                        converted_img.close()
                        success_count += 1
                    
                except Exception as e:
                    log(f"转换 {os.path.basename(path)} 失败: {str(e)}")

            if success_count > 0:
                log(f"完成转换: 成功 {success_count}/{len(image_paths)}")
                finished(True, f"成功转换 {success_count} 个文件")
            else:
                finished(False, "所有文件转换失败")

        except Exception as e:
            raise e
