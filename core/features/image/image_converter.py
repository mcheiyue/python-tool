from PIL import Image
import os

class ImageConverter:
    def convert(self, input_path, output_path, output_format, quality=90, rotate_angle=0, flip_mode=None, *, on_log=None, on_finished=None):
        """
        :param rotate_angle: 旋转角度 (90, 180, 270)
        :param flip_mode: 翻转模式 ('H' for Horizontal, 'V' for Vertical)
        """
        def log(msg):
            if on_log:
                on_log(msg)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)

        try:
            log(f"正在处理: {os.path.basename(input_path)}")

            with Image.open(input_path) as img:
                # 旋转处理
                if rotate_angle in [90, 180, 270]:
                    img = img.rotate(-rotate_angle, expand=True) # rotate 是逆时针，用户习惯顺时针，所以取反

                # 翻转处理
                if flip_mode == 'H':
                    img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                elif flip_mode == 'V':
                    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

                # 预处理：根据目标格式处理颜色模式
                save_kwargs = {}
                target_format = output_format.upper()

                # ICO 特殊处理
                if target_format == 'ICO':
                    if img.size[0] > 256 or img.size[1] > 256:
                        log("ICO 最大尺寸限制为 256x256，正在调整尺寸...")
                        img.thumbnail((256, 256), Image.Resampling.LANCZOS)
                    save_kwargs['format'] = 'ICO'

                # JPG/BMP 不支持透明度 (RGBA)，需要转换为 RGB
                elif target_format in ['JPEG', 'JPG', 'BMP']:
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        # 创建白色背景
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
                        img = background
                    else:
                        img = img.convert('RGB')

                    if target_format in ['JPEG', 'JPG']:
                        save_kwargs['quality'] = quality
                        save_kwargs['optimize'] = True

                # WEBP 优化
                elif target_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 6  # 最慢但最好的压缩

                # 保存文件
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                img.save(output_path, **save_kwargs)

            log(f"转换成功: {os.path.basename(output_path)}")
            finished(True, output_path)

        except Exception as e:
            error_msg = f"转换失败 {os.path.basename(input_path)}: {str(e)}"
            log(error_msg)
            finished(False, str(e))
