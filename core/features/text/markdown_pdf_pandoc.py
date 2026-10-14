"""
Pandoc Markdown 转 PDF 模块
支持数学公式、代码高亮、中文字体
"""
import os
import subprocess
import platform
from typing import List, Optional

from core.external_tools.manager import ExternalToolManager
from core.utils.logger import AppLogger, timed_operation


class PandocMarkdownToPdf:
    """使用 Pandoc 将 Markdown 转换为 PDF"""

    def __init__(self):
        self._is_running = False
        self.pandoc_tool = ExternalToolManager().get_tool("pandoc")
        self.logger = AppLogger()
    
    def is_available(self) -> bool:
        """检查 Pandoc 是否可用"""
        return self.pandoc_tool.check_installed() and not self.pandoc_tool.is_disabled
    
    def stop(self):
        """停止当前任务"""
        self._is_running = False
    
    @timed_operation("Pandoc Markdown to PDF")
    def convert_batch(
        self,
        files: List[str],
        output_dir: Optional[str] = None,
        enable_math: bool = True,
        enable_highlight: bool = True,
        pdf_engine: str = "xelatex",
        template: Optional[str] = None,
        *,
        on_log=None,
        on_progress=None,
        on_finished=None
    ):
        """
        批量将 Markdown 转换为 PDF
        
        Args:
            files: Markdown 文件路径列表
            output_dir: 输出目录（None 则输出到源文件同目录）
            enable_math: 启用数学公式支持（MathJax）
            enable_highlight: 启用代码高亮
            pdf_engine: PDF 引擎（xelatex/pdflatex/lualatex/wkhtmltopdf）
            template: 自定义模板文件路径
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

        if not self.is_available():
            log("❌ Pandoc 未安装或已禁用")
            finished(0, len(files))
            return
        
        self._is_running = True
        success_count = 0
        fail_count = 0
        total = len(files)
        
        log(f"开始 Markdown → PDF 转换任务，共 {total} 个文件")
        log(f"PDF 引擎: {pdf_engine}")
        self.logger.info(f"Pandoc MD→PDF: {total} files, engine={pdf_engine}")
        
        for i, file_path in enumerate(files):
            if not self._is_running:
                log("任务已停止")
                break
            
            file_name = os.path.basename(file_path)
            progress(i, total, f"正在处理: {file_name}")
            
            try:
                # 确定输出路径
                if output_dir:
                    out_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + ".pdf")
                else:
                    out_path = os.path.splitext(file_path)[0] + ".pdf"
                
                # 执行转换
                success = self._convert_single(
                    file_path, 
                    out_path,
                    enable_math,
                    enable_highlight,
                    pdf_engine,
                    template,
                    log
                )
                
                if success:
                    success_count += 1
                    log(f"✅ 成功: {file_name} → {os.path.basename(out_path)}")
                    self.logger.info(f"Converted: {file_name}")
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
                log(f"❌ 失败 {file_name}: {str(e)}")
                self.logger.error(f"Failed to convert {file_name}: {e}")
        
        self._is_running = False
        progress(total, total, "完成")
        finished(success_count, fail_count)
        self.logger.info(f"Pandoc MD→PDF completed: {success_count} success, {fail_count} failed")
    
    def _convert_single(
        self,
        input_path: str,
        output_path: str,
        enable_math: bool,
        enable_highlight: bool,
        pdf_engine: str,
        template: Optional[str],
        log
    ) -> bool:
        """转换单个文件"""
        pandoc_path = self.pandoc_tool.get_path()
        if not pandoc_path:
            log("错误: 无法获取 Pandoc 路径")
            return False
            
        # 检查 PDF 引擎是否存在
        if not self._check_pdf_engine(pdf_engine):
            log(f"错误: 找不到 PDF 引擎 '{pdf_engine}'。请安装 TeX Live (包含 xelatex) 或 wkhtmltopdf，或者在设置中选择已安装的引擎。")
            return False
        
        # 构建命令
        cmd = [
            pandoc_path,
            input_path,
            "-o", output_path,
            f"--pdf-engine={pdf_engine}",
            "--standalone",  # 生成完整文档
        ]
        
        # 数学公式支持
        if enable_math:
            cmd.extend(["--mathjax"])
        
        # 代码高亮
        if enable_highlight:
            # 使用 --highlight-style=tango
            # 注意: 如果 Pandoc 版本较旧或较新，可能会有警告，但通常这是标准做法
            cmd.extend(["--highlight-style=tango"])
        
        # 中文支持 (XeLaTeX)
        if pdf_engine in ['xelatex', 'lualatex']:
            # 设置中文字体
            if platform.system() == 'Windows':
                cmd.extend([
                    "-V", "mainfont=Microsoft YaHei",
                    "-V", "monofont=Consolas",
                ])
            elif platform.system() == 'Darwin':  # macOS
                cmd.extend([
                    "-V", "mainfont=PingFang SC",
                    "-V", "monofont=Menlo",
                ])
            else:  # Linux
                cmd.extend([
                    "-V", "mainfont=Noto Sans CJK SC",
                    "-V", "monofont=DejaVu Sans Mono",
                ])
            
            # 页边距
            cmd.extend(["-V", "geometry:margin=1in"])
        
        # 自定义模板
        if template and os.path.exists(template):
            cmd.extend(["--template", template])
        
        # 元数据
        cmd.extend([
            "--metadata", f"title={os.path.splitext(os.path.basename(input_path))[0]}"
        ])
        
        try:
            # Windows 下隐藏窗口
            startupinfo = None
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 执行命令（带超时）
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,  # 2 分钟超时
                startupinfo=startupinfo
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                log(f"Pandoc 错误: {error_msg}")
                self.logger.error(f"Pandoc error: {error_msg}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            log("错误: 转换超时（超过 2 分钟）")
            self.logger.error("Pandoc conversion timeout")
            return False
        except Exception as e:
            log(f"执行异常: {str(e)}")
            self.logger.error(f"Pandoc execution error: {e}")
            return False

    def _check_pdf_engine(self, engine_name: str) -> bool:
        """检查 PDF 引擎是否在 PATH 中可用"""
        import shutil
        return shutil.which(engine_name) is not None