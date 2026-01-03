import os
import subprocess
from .base import BasePdfCompressor
from core.environment_checker import EnvironmentChecker

class GhostscriptCompressor(BasePdfCompressor):
    """基于 Ghostscript 的 PDF 压缩实现"""
    
    def check_dependency(self) -> dict:
        """检查 Ghostscript 是否可用"""
        result = EnvironmentChecker.find_ghostscript()
        return {
            "available": result["found"],
            "message": f"Ghostscript {result.get('version', '')}" if result["found"] else "未找到 Ghostscript",
            "path": result.get("path", "")
        }

    def compress(self, files: list, quality: str, **kwargs):
        """
        :param files: 文件列表
        :param quality: 压缩质量 (/screen, /ebook 等)
        :param kwargs: 必须包含 'gs_path'
        """
        gs_path = kwargs.get('gs_path')
        if not gs_path or not os.path.exists(gs_path):
            self.log.emit(f"❌ Ghostscript 路径无效: {gs_path}")
            self.finished.emit(0, len(files))
            return

        self._is_running = True
        total = len(files)
        success = 0
        fail = 0

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
