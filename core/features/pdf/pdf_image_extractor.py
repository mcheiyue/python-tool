import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
from pypdf import PdfReader

class PDFImageExtractor(QObject):
    progress = pyqtSignal(int, int, str)  # curr, total, message
    log = pyqtSignal(str)                 # log message
    finished = pyqtSignal(int, int)       # success_count, fail_count

    def extract(self, files, output_dir):
        """
        从 PDF 中提取图片
        :param files: PDF 文件列表
        :param output_dir: 输出目录
        """
        if not files:
            self.finished.emit(0, 0)
            return

        success_count = 0
        fail_count = 0
        total_files = len(files)

        self.log.emit(f"开始任务: 处理 {total_files} 个文件")
        
        for i, file_path in enumerate(files):
            file_name = os.path.basename(file_path)
            self.progress.emit(i, total_files, f"正在处理: {file_name}")
            self.log.emit(f"\n--- 处理文件 [{i+1}/{total_files}]: {file_name} ---")

            if not file_path.lower().endswith('.pdf'):
                self.log.emit(f"❌ 跳过: 不是有效的 PDF 文件")
                fail_count += 1
                continue

            try:
                reader = PdfReader(file_path)
                base_name = os.path.splitext(file_name)[0]
                
                # 为每个 PDF 创建一个子目录
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
                            self.log.emit(f"  提取: {img_name}")
                    except Exception as e:
                        self.log.emit(f"  ⚠️ 第 {p_idx+1} 页提取警告: {str(e)}")

                if img_count > 0:
                    self.log.emit(f"✅ 完成: 提取了 {img_count} 张图片 -> {file_out_dir}")
                    success_count += 1
                else:
                    self.log.emit(f"ℹ️ 该文件未发现图片")
                    # 如果没有图片也算成功处理了文件，只是结果为空
                    success_count += 1
                    # 删除空文件夹
                    if os.path.exists(file_out_dir) and not os.listdir(file_out_dir):
                        os.rmdir(file_out_dir)

            except Exception as e:
                error_trace = traceback.format_exc()
                self.log.emit(f"❌ 处理失败:\n{error_trace}")
                fail_count += 1

        self.progress.emit(total_files, total_files, "完成")
        self.finished.emit(success_count, fail_count)
