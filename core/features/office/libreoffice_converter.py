"""LibreOffice 通用格式转换器

支持的格式转换：
- 文档: ODT ↔ DOCX, DOC → DOCX, PDF → DOCX
- 表格: ODS ↔ XLSX, XLS → XLSX
- 演示: ODP ↔ PPTX, PPT → PPTX
- 通用: 各种格式 → PDF
"""

import os
import subprocess
import platform
from typing import List, Optional

from core.external_tools.manager import ExternalToolManager
from core.utils.logger import AppLogger, timed_operation


class LibreOfficeFormatConverter:
    """LibreOffice 通用格式转换器"""
    
    # 支持的格式映射 (输入格式 -> 可选输出格式)
    SUPPORTED_FORMATS = {
        # 文档格式
        'odt': ['docx', 'pdf', 'doc', 'html', 'txt'],
        'docx': ['odt', 'pdf', 'html', 'txt'],
        'doc': ['docx', 'odt', 'pdf', 'html', 'txt'],
        
        # 表格格式
        'ods': ['xlsx', 'pdf', 'xls', 'csv', 'html'],
        'xlsx': ['ods', 'pdf', 'csv', 'html'],
        'xls': ['xlsx', 'ods', 'pdf', 'csv', 'html'],
        
        # 演示格式
        'odp': ['pptx', 'pdf', 'ppt', 'html'],
        'pptx': ['odp', 'pdf', 'html'],
        'ppt': ['pptx', 'odp', 'pdf', 'html'],
        
        # 其他支持的输入格式
        'rtf': ['docx', 'odt', 'pdf', 'txt'],
        'txt': ['pdf', 'docx', 'odt'],
        'html': ['pdf', 'docx', 'odt'],
    }

    def __init__(self):
        self._is_running = False
        self._tool_manager = ExternalToolManager()
        self._logger = AppLogger()
        
    def is_available(self) -> bool:
        """检查 LibreOffice 是否可用"""
        tool = self._tool_manager.get_tool("libreoffice")
        return tool and tool.is_available()
    
    def get_executable_path(self) -> Optional[str]:
        """获取 LibreOffice 可执行文件路径"""
        tool = self._tool_manager.get_tool("libreoffice")
        if tool and tool.is_available():
            return tool.get_executable_path()
        return None
    
    def get_supported_output_formats(self, input_ext: str) -> List[str]:
        """获取输入格式支持的输出格式列表
        
        Args:
            input_ext: 输入文件扩展名（不含点号，如 'odt'）
            
        Returns:
            支持的输出格式列表
        """
        return self.SUPPORTED_FORMATS.get(input_ext.lower(), [])
    
    def is_format_supported(self, input_ext: str, output_ext: str) -> bool:
        """检查格式转换是否支持
        
        Args:
            input_ext: 输入格式扩展名
            output_ext: 输出格式扩展名
            
        Returns:
            是否支持该转换
        """
        supported = self.get_supported_output_formats(input_ext)
        return output_ext.lower() in supported
    
    @timed_operation("LibreOffice 批量格式转换")
    def convert_batch(self, file_paths: List[str], output_format: str, 
                     output_dir: Optional[str] = None, *,
                     on_log=None, on_progress=None, on_finished=None):
        """批量转换文件格式
        
        Args:
            file_paths: 要转换的文件路径列表
            output_format: 目标格式（如 'pdf', 'docx', 'odt'）
            output_dir: 输出目录（None = 与源文件同目录）
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

        self._is_running = True
        total = len(file_paths)
        success = 0
        fail = 0
        
        soffice_path = self.get_executable_path()
        if not soffice_path:
            log("❌ LibreOffice 未安装或不可用")
            self._logger.error("LibreOffice 不可用")
            finished(0, total)
            return
        
        log(f"📦 使用 LibreOffice: {soffice_path}")
        log(f"🎯 目标格式: {output_format.upper()}")
        self._logger.info(f"开始批量转换 {total} 个文件到 {output_format}")
        
        for idx, path in enumerate(file_paths):
            if not self._is_running:
                log("⏹️ 任务已停止")
                self._logger.info("用户停止任务")
                break
            
            file_name = os.path.basename(path)
            input_ext = os.path.splitext(path)[1][1:].lower()  # 去掉点号
            
            progress(idx + 1, total, file_name)
            log(f"📄 正在转换 ({idx + 1}/{total}): {file_name}")
            
            # 检查格式支持
            if not self.is_format_supported(input_ext, output_format):
                fail += 1
                msg = f"❌ 不支持 {input_ext.upper()} → {output_format.upper()} 转换"
                log(f"   {msg}: {file_name}")
                self._logger.warning(f"{msg}: {path}")
                continue
            
            try:
                result = self._convert_single_file(
                    path, output_format, output_dir, soffice_path
                )
                
                if result['success']:
                    success += 1
                    log(f"   ✅ 成功: {file_name}")
                    self._logger.info(f"转换成功: {path} -> {result.get('output_path', 'N/A')}")
                else:
                    fail += 1
                    error_msg = result.get('error', '未知错误')
                    log(f"   ❌ 失败: {file_name} ({error_msg})")
                    self._logger.error(f"转换失败: {path} - {error_msg}")
                    
            except Exception as e:
                fail += 1
                log(f"   ❌ 异常: {file_name} ({str(e)})")
                self._logger.exception(f"转换异常: {path}")
        
        # 完成统计
        log("")
        log(f"✨ 转换完成！成功: {success}, 失败: {fail}")
        self._logger.info(f"批量转换完成 - 成功: {success}, 失败: {fail}")
        finished(success, fail)
        self._is_running = False
    
    def _convert_single_file(self, input_path: str, output_format: str,
                            output_dir: Optional[str], soffice_path: str) -> dict:
        """转换单个文件
        
        Returns:
            {'success': bool, 'error': str, 'output_path': str}
        """
        abs_input = os.path.abspath(input_path)
        
        # 确定输出目录
        if output_dir:
            target_dir = os.path.abspath(output_dir)
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = os.path.dirname(abs_input)
        
        # 构建命令
        # soffice --headless --convert-to <format> --outdir <dir> <input>
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to", output_format,
            "--outdir", target_dir,
            abs_input
        ]
        
        # 执行转换
        startupinfo = None
        creationflags = 0
        
        if platform.system() == 'Windows':
            # Windows: 隐藏控制台窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 分钟超时
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            if result.returncode == 0:
                # 验证输出文件是否生成
                base_name = os.path.splitext(os.path.basename(abs_input))[0]
                expected_output = os.path.join(target_dir, f"{base_name}.{output_format}")
                
                if os.path.exists(expected_output):
                    return {
                        'success': True,
                        'output_path': expected_output
                    }
                else:
                    return {
                        'success': False,
                        'error': '输出文件未生成'
                    }
            else:
                error_msg = result.stderr.strip() if result.stderr else '转换失败'
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '转换超时 (>120秒)'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop(self):
        """停止当前任务"""
        self._is_running = False
        self._logger.info("用户请求停止转换任务")