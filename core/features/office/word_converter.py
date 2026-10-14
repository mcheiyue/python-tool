import os
import shutil
from typing import Optional

from core.external_tools.manager import ExternalToolManager
# 注意: core/engines/office/word.py 可能已经有部分功能，这里主要通过 Pandoc 实现双向转换

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

class WordConverter:
    """
    DOCX ↔ Markdown 转换器
    主要依赖 Pandoc 进行转换，因 python-docx 仅适合简单文本操作
    """

    def __init__(self):
        self._is_running = False
        self.pandoc_tool = ExternalToolManager().get_tool("pandoc")
        
    def stop(self):
        """停止当前任务"""
        self._is_running = False

    def is_pandoc_available(self) -> bool:
        """检查 Pandoc 是否可用"""
        return self.pandoc_tool.check_installed()

    def convert_docx_to_markdown(
        self, 
        files: list[str], 
        output_dir: Optional[str] = None,
        *,
        on_log=None,
        on_progress=None,
        on_finished=None,
    ):
        """
        批量将 DOCX 转换为 Markdown
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, fail):
            if on_finished:
                on_finished(ok, fail)

        if not self.is_pandoc_available():
            log("错误: 需要安装 Pandoc 才能进行 DOCX 转 Markdown")
            finished(0, len(files))
            return

        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)
        
        log(f"开始 DOCX -> Markdown 转换任务，共 {total} 个文件")
        
        for i, file_path in enumerate(files):
            if not self._is_running:
                break
                
            file_name = os.path.basename(file_path)
            progress(i, total, f"正在处理: {file_name}")
            
            try:
                # 确定输出路径
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".md")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".md"
                
                # 使用 Pandoc 转换
                if self._docx_to_md_pandoc(file_path, out_path, on_log=on_log):
                    success_count += 1
                    log(f"✅ 成功: {file_name} -> {os.path.basename(out_path)}")
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
                log(f"❌ 失败 {file_name}: {str(e)}")
                
        progress(total, total, "完成")
        finished(success_count, fail_count)
        self._is_running = False

    def convert_markdown_to_docx(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        reference_doc: Optional[str] = None,
        *,
        on_log=None,
        on_progress=None,
        on_finished=None,
    ):
        """
        批量将 Markdown 转换为 DOCX
        """

        def log(msg):
            if on_log:
                on_log(msg)

        def progress(curr, total, message):
            if on_progress:
                on_progress(curr, total, message)

        def finished(ok, fail):
            if on_finished:
                on_finished(ok, fail)

        if not self.is_pandoc_available():
            log("错误: 需要安装 Pandoc 才能进行 Markdown 转 DOCX")
            finished(0, len(files))
            return

        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)
        
        log(f"开始 Markdown -> DOCX 转换任务，共 {total} 个文件")
        
        for i, file_path in enumerate(files):
            if not self._is_running:
                break
            
            file_name = os.path.basename(file_path)
            progress(i, total, f"正在处理: {file_name}")
            
            try:
                # 确定输出路径
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".docx")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".docx"
                
                # 使用 Pandoc 转换
                if self._md_to_docx_pandoc(file_path, out_path, reference_doc, on_log=on_log):
                    success_count += 1
                    log(f"✅ 成功: {file_name} -> {os.path.basename(out_path)}")
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
                log(f"❌ 失败 {file_name}: {str(e)}")
        
        progress(total, total, "完成")
        finished(success_count, fail_count)
        self._is_running = False

    def _docx_to_md_pandoc(self, input_path: str, output_path: str, on_log=None) -> bool:
        """使用 Pandoc 转换 DOCX -> MD"""

        def log(msg):
            if on_log:
                on_log(msg)

        pandoc_path = self.pandoc_tool.get_path()
        if not pandoc_path:
            return False
            
        import subprocess
        # 基础命令: pandoc input.docx -o output.md
        cmd = [
            pandoc_path,
            input_path,
            "-f", "docx",
            "-t", "gfm", # GitHub Flavored Markdown
            "-o", output_path,
            "--wrap=none", # 不自动换行
            "--extract-media=." # 提取图片到当前目录 (需要处理路径问题，这里暂时简化)
        ]
        
        # 优化：提取图片到 output_path 同级目录的 media 文件夹
        media_dir = os.path.join(os.path.dirname(output_path), "media")
        cmd[-1] = f"--extract-media={media_dir}"
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            log(f"Pandoc Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            log(f"Pandoc Execution Error: {e}")
            return False

    def _md_to_docx_pandoc(self, input_path: str, output_path: str, reference_doc: Optional[str] = None, on_log=None) -> bool:
        """使用 Pandoc 转换 MD -> DOCX"""

        def log(msg):
            if on_log:
                on_log(msg)

        pandoc_path = self.pandoc_tool.get_path()
        if not pandoc_path:
            return False
            
        import subprocess
        # 基础命令: pandoc input.md -o output.docx
        cmd = [
            pandoc_path,
            input_path,
            "-f", "markdown", # 或 gfm
            "-o", output_path
        ]
        
        # 如果有参考文档 (用于样式)
        if reference_doc and os.path.exists(reference_doc):
            cmd.append(f"--reference-doc={reference_doc}")
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            log(f"Pandoc Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            log(f"Pandoc Execution Error: {e}")
            return False