import os
from PyQt6.QtCore import QObject, pyqtSignal

class CodeExtractor(QObject):
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)
    
    def extract(self, root_dir, extensions, output_path):
        try:
            total_files = 0
            # extensions example: ['.c', '.h', '.py']
            
            with open(output_path, 'w', encoding='utf-8') as out:
                for root, dirs, files in os.walk(root_dir):
                    for file in files:
                        if any(file.lower().endswith(ext.lower()) for ext in extensions):
                            file_path = os.path.join(root, file)
                            self.log.emit(f"处理: {file_path}")
                            
                            # 写入分隔符和文件名
                            out.write(f"\n{'='*50}\n")
                            out.write(f"File: {file_path}\n")
                            out.write(f"{'='*50}\n\n")
                            
                            # 写入内容
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    out.write(f.read())
                            except Exception as e:
                                out.write(f"Error reading file: {e}")
                                
                            out.write("\n\n")
                            total_files += 1
                            
            self.finished.emit(True, f"已合并 {total_files} 个文件到 {output_path}")
        except Exception as e:
            self.finished.emit(False, str(e))
