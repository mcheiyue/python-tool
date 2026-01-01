import os
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

class PDFCompressor(QObject):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = False

    def compress(self, files, quality, gs_path):
        """
        :param files: List of file paths
        :param quality: Ghostscript quality setting (/screen, /ebook, /printer, /prepress, /default)
        :param gs_path: Path to gswin64c.exe
        """
        self._is_running = True
        total = len(files)
        success = 0
        fail = 0

        if not os.path.exists(gs_path):
            self.log.emit(f"❌ Ghostscript 路径无效: {gs_path}")
            self.finished.emit(0, total)
            return

        for idx, path in enumerate(files):
            if not self._is_running:
                self.log.emit("任务停止")
                break

            name = os.path.basename(path)
            self.progress.emit(idx + 1, total, name)
            self.log.emit(f"正在压缩 ({idx + 1}/{total}): {name}")

            try:
                # 准备输出路径
                parent_dir = os.path.dirname(path)
                output_dir = os.path.join(parent_dir, "Compressed")
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                name_root, _ = os.path.splitext(name)
                output_path = os.path.join(output_dir, f"{name_root}_compressed.pdf")

                # 构建 Ghostscript 命令
                cmd = [
                    gs_path,
                    "-sDEVICE=pdfwrite",
                    "-dCompatibilityLevel=1.4",
                    f"-dPDFSETTINGS={quality}",
                    "-dNOPAUSE",
                    "-dQUIET",
                    "-dBATCH",
                    f"-sOutputFile={output_path}",
                    path
                ]

                # 执行命令 (Windows 下隐藏控制台窗口)
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    success += 1
                    self.log.emit(f"✅ 成功: {os.path.basename(output_path)}")
                else:
                    fail += 1
                    err_msg = stderr.decode('gbk', errors='ignore') if stderr else "未知错误"
                    self.log.emit(f"❌ 失败 {name}: {err_msg}")

            except Exception as e:
                fail += 1
                self.log.emit(f"🔥 异常 {name}: {str(e)}")

        self.finished.emit(success, fail)
        self._is_running = False

    def stop(self):
        self._is_running = False
