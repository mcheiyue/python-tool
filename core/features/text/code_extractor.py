import os

class CodeExtractor:
    def extract(self, root_dir, extensions, output_path, *, on_log=None, on_finished=None):
        def log(msg):
            if on_log:
                on_log(msg)

        def finished(ok, msg):
            if on_finished:
                on_finished(ok, msg)

        try:
            total_files = 0
            # extensions example: ['.c', '.h', '.py']
            
            with open(output_path, 'w', encoding='utf-8') as out:
                for root, dirs, files in os.walk(root_dir):
                    for file in files:
                        if any(file.lower().endswith(ext.lower()) for ext in extensions):
                            file_path = os.path.join(root, file)
                            log(f"处理: {file_path}")
                            
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
                            
            if total_files == 0:
                finished(False, "未找到匹配的文件，未写入任何内容")
            else:
                finished(True, f"已合并 {total_files} 个文件到 {output_path}")
        except Exception as e:
            finished(False, str(e))
