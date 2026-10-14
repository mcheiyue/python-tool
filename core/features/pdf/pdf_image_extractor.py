import os
from pypdf import PdfReader

from core.batch import run as batch_run

class PDFImageExtractor:
    def extract(self, files, output_dir, *, on_log=None, on_progress=None, on_finished=None):
        """
        从 PDF 中提取图片
        :param files: PDF 文件列表
        :param output_dir: 输出目录
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def worker(file_path):
            file_name = os.path.basename(file_path)
            if not file_path.lower().endswith('.pdf'):
                raise ValueError("不是有效的 PDF 文件")

            reader = PdfReader(file_path)
            base_name = os.path.splitext(file_name)[0]

            file_out_dir = os.path.join(output_dir, base_name + "_images")
            if not os.path.exists(file_out_dir):
                os.makedirs(file_out_dir)

            img_count = 0
            for p_idx, page in enumerate(reader.pages):
                try:
                    for img_idx, image in enumerate(page.images):
                        img_name = f"page{p_idx+1}_img{img_idx+1}_{image.name}"
                        img_path = os.path.join(file_out_dir, img_name)

                        with open(img_path, "wb") as f_img:
                            f_img.write(image.data)

                        img_count += 1
                        log(f"  提取: {img_name}")
                except Exception as e:
                    log(f"  ⚠️ 第 {p_idx+1} 页提取警告: {str(e)}")

            if img_count > 0:
                log(f"✅ 完成: 提取了 {img_count} 张图片 -> {file_out_dir}")
            else:
                log(f"ℹ️ 该文件未发现图片")
                if os.path.exists(file_out_dir) and not os.listdir(file_out_dir):
                    os.rmdir(file_out_dir)

        log(f"开始任务: 处理 {len(files)} 个文件")
        success, fail = batch_run(files, worker, on_progress=on_progress, on_log=log)
        if on_finished:
            on_finished(success, fail)
