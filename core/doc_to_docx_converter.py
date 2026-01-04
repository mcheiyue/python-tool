import os
import comtypes.client
from PyQt6.QtCore import QObject, pyqtSignal

class DocToDocxConverter(QObject):
    """Doc 转 Docx 转换器"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    log = pyqtSignal(str)
    
    # wdFormatXMLDocument = 12 (.docx)
    # wdFormatDocumentDefault = 16 (.docx default)
    WD_FORMAT_DOCX = 16

    def __init__(self):
        super().__init__()
        self._is_running = False
        self._app = None

    def convert(self, file_paths, output_dir=None):
        """
        执行转换任务
        :param file_paths: 文件路径列表
        :param output_dir: 输出目录，如果为 None 则输出到源文件同目录
        """
        self._is_running = True
        total = len(file_paths)
        success = 0
        fail = 0

        try:
            # 1. 初始化 COM 环境
            comtypes.CoInitialize()
            self.log.emit("正在启动 Microsoft Word...")
            
            # 2. 创建应用实例
            self._app = comtypes.client.CreateObject("Word.Application", dynamic=True)
            try:
                self._app.Visible = False
            except:
                pass
            
            for idx, path in enumerate(file_paths):
                if not self._is_running:
                    self.log.emit("任务已停止")
                    break

                file_name = os.path.basename(path)
                self.progress.emit(idx + 1, total, file_name)
                self.log.emit(f"正在转换 ({idx + 1}/{total}): {file_name}")

                doc = None
                try:
                    abs_path = os.path.abspath(path)
                    
                    # 确定输出路径
                    if output_dir:
                        out_dir = output_dir
                    else:
                        out_dir = os.path.dirname(abs_path)
                        
                    if not os.path.exists(out_dir):
                        os.makedirs(out_dir)
                        
                    base_name = os.path.splitext(os.path.basename(abs_path))[0]
                    docx_path = os.path.join(out_dir, base_name + ".docx")

                    # 3. 打开文档
                    doc = self._app.Documents.Open(abs_path)
                    
                    # 4. 另存为 Docx
                    # SaveAs2(FileName, FileFormat, ...)
                    doc.SaveAs2(docx_path, self.WD_FORMAT_DOCX)
                    
                    success += 1
                    self.log.emit(f"✅ 成功: {os.path.basename(docx_path)}")
                
                except Exception as e:
                    fail += 1
                    self.log.emit(f"❌ 失败 {file_name}: {str(e)}")
                
                finally:
                    # 5. 关闭文档
                    if doc:
                        try:
                            # 0 = wdDoNotSaveChanges
                            doc.Close(0)
                        except:
                            pass

        except Exception as e:
            self.log.emit(f"🔥 严重错误: {str(e)}")
        
        finally:
            # 6. 清理应用实例
            if self._app:
                try:
                    self._app.Quit()
                except:
                    pass
                self._app = None
            
            try:
                comtypes.CoUninitialize()
            except:
                pass
            
            self.finished.emit(success, fail)
            self._is_running = False

    def stop(self):
        """停止当前任务"""
        self._is_running = False
