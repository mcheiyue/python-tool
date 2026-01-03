import os
import comtypes.client
from PyQt6.QtCore import QObject, pyqtSignal

class PPTImageExporter(QObject):
    progress = pyqtSignal(int, int, str)  # curr, total, message
    log = pyqtSignal(str)                 # log message
    finished = pyqtSignal(int, int)       # success_count, fail_count

    def __init__(self):
        super().__init__()
        self._is_running = False

    def export(self, file_paths, output_dir, format='PNG'):
        """
        将 PPT 导出为图片
        :param file_paths: PPT 文件列表
        :param output_dir: 输出目录
        :param format: 图片格式 ('PNG', 'JPG', 'BMP')
        """
        self._is_running = True
        total_files = len(file_paths)
        success_count = 0
        fail_count = 0
        ppt_app = None

        try:
            comtypes.CoInitialize()
            self.log.emit("正在启动 PowerPoint...")
            
            try:
                ppt_app = comtypes.client.CreateObject("PowerPoint.Application", dynamic=True)
                # 尝试设置为不可见，但 PPT 通常需要可见才能工作
                try:
                    ppt_app.Visible = 1 
                except:
                    pass
            except Exception as e:
                self.log.emit(f"无法启动 PowerPoint: {str(e)}")
                self.finished.emit(0, 0)
                return

            for i, path in enumerate(file_paths):
                if not self._is_running:
                    self.log.emit("任务已停止")
                    break

                file_name = os.path.basename(path)
                self.progress.emit(i + 1, total_files, f"正在处理: {file_name}")
                self.log.emit(f"\n--- 处理文件 [{i+1}/{total_files}]: {file_name} ---")

                try:
                    abs_path = os.path.abspath(path)
                    
                    # 为每个 PPT 创建子目录
                    base_name = os.path.splitext(file_name)[0]
                    file_out_dir = os.path.join(output_dir, base_name)
                    if not os.path.exists(file_out_dir):
                        os.makedirs(file_out_dir)

                    presentation = ppt_app.Presentations.Open(abs_path, True, False, False)
                    
                    try:
                        # 导出所有幻灯片
                        # PowerPoint 的 Export 方法可以将整个演示文稿导出为一系列图片
                        # 路径需要指定为一个目录（如果是导出整个演示文稿）或者文件名（如果导出单张）
                        # 这里我们使用 SaveAs 并选择图片格式，它会自动为每张幻灯片创建文件
                        
                        # ppSaveAsPNG = 18, ppSaveAsJPG = 17, ppSaveAsBMP = 19
                        save_format = 18  # Default PNG
                        ext = 'png'
                        
                        fmt_upper = format.upper()
                        if fmt_upper == 'JPG' or fmt_upper == 'JPEG':
                            save_format = 17
                            ext = 'jpg'
                        elif fmt_upper == 'BMP':
                            save_format = 19
                            ext = 'bmp'
                        
                        # SaveAs 会创建一个同名的文件夹（如果目标路径不带扩展名且是图片格式）
                        # 或者我们可以直接指定目标目录
                        # 实际上，PowerPoint 的 SaveAs 如果指定图片格式，会自动创建一个文件夹
                        # 我们指定 file_out_dir 作为目标路径，PowerPoint 可能会在里面再建一个文件夹或者直接保存
                        # 让我们尝试使用 Export 方法，它更灵活
                        
                        self.log.emit(f"正在导出 {presentation.Slides.Count} 张幻灯片...")
                        
                        # 方法 2: 遍历每张幻灯片导出
                        for slide in presentation.Slides:
                            slide_path = os.path.join(file_out_dir, f"Slide{slide.SlideIndex}.{ext}")
                            slide.Export(slide_path, fmt_upper)
                            self.log.emit(f"  已导出: Slide{slide.SlideIndex}.{ext}")

                        success_count += 1
                        self.log.emit(f"✅ 成功完成: {file_name}")
                        
                    finally:
                        presentation.Close()

                except Exception as e:
                    self.log.emit(f"❌ 处理失败 {file_name}: {str(e)}")
                    fail_count += 1

        except Exception as e:
            self.log.emit(f"🔥 系统错误: {str(e)}")
        finally:
            if ppt_app:
                try:
                    ppt_app.Quit()
                except:
                    pass
            comtypes.CoUninitialize()
            self.finished.emit(success_count, fail_count)
            self._is_running = False

    def stop(self):
        self._is_running = False
