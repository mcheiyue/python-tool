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
            # extensions example: ['.c', '.h', '.py']
            targets = [
                os.path.join(root, file)
                for root, _, files in os.walk(root_dir)
                for file in files
                if any(file.lower().endswith(ext.lower()) for ext in extensions)
            ]
            if not targets:
                finished(False, "未找到匹配的文件，未写入任何内容")
            else:
                # 非空才开写：0 匹配/遍历早失败时不创建、不截断用户已有输出文件
                with open(output_path, 'w', encoding='utf-8') as out:
                    for file_path in targets:
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
                finished(True, f"已合并 {len(targets)} 个文件到 {output_path}")
        except Exception as e:
            finished(False, str(e))
