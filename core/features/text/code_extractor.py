import os
import tempfile

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
                return
            if os.path.exists(output_path) and any(
                os.path.samefile(output_path, source) for source in targets
            ):
                finished(False, "输出文件不能是待提取的输入文件")
                return
            # 同盘暂存并替换，读取中断时保留用户原有文件。
            with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(output_path))) as staging:
                pending = os.path.join(staging, "merged.txt")
                with open(pending, 'w', encoding='utf-8') as out:
                    for file_path in targets:
                        log(f"处理: {file_path}")

                        # 写入分隔符和文件名
                        out.write(f"\n{'='*50}\n")
                        out.write(f"File: {file_path}\n")
                        out.write(f"{'='*50}\n\n")

                        # 写入内容
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            out.write(f.read())

                        out.write("\n\n")
                os.replace(pending, output_path)
            finished(True, f"已合并 {len(targets)} 个文件到 {output_path}")
        except OSError as e:
            finished(False, str(e))
