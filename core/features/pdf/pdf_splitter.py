import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
from pypdf import PdfReader, PdfWriter

class PDFSplitter(QObject):
    progress = pyqtSignal(int, int, str)  # curr, total, message
    log = pyqtSignal(str)                 # log message
    finished = pyqtSignal(bool, str)      # success, message

    def split(self, file_path, ranges_text, output_dir):
        """
        根据范围拆分 PDF
        :param file_path: 源 PDF 文件路径
        :param ranges_text: 范围字符串，如 "1-5, 8, 10-end"
        :param output_dir: 输出目录
        """
        self.log.emit(f"开始处理文件: {os.path.basename(file_path)}")
        
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            self.log.emit(f"文件总页数: {total_pages}")

            # 解析范围
            ranges = self._parse_ranges(ranges_text, total_pages)
            if not ranges:
                self.finished.emit(False, "无效的页码范围")
                return

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            for i, (start, end) in enumerate(ranges):
                writer = PdfWriter()
                
                # pypdf 索引从 0 开始，用户输入从 1 开始
                # range 也是左闭右开，所以 end 不需要减 1 (如果要包含 end)
                # start 是 1-based，需要减 1 转为 0-based
                
                # 调整逻辑: start, end 都是 1-based
                # 如果是单页 start=end
                
                # 遍历页码
                page_indices = range(start - 1, end) # end 已经是包含的页码，所以 range 需要 +1，但这里 end 来自 _parse_ranges 假设是 inclusive
                
                target_pages = []
                for p_idx in range(start - 1, end):
                    if 0 <= p_idx < total_pages:
                        writer.add_page(reader.pages[p_idx])
                        target_pages.append(p_idx + 1)
                
                if not target_pages:
                    self.log.emit(f"⚠️ 跳过无效范围: {start}-{end}")
                    continue
                    
                output_filename = f"{base_name}_part{i+1}_{start}-{end}.pdf"
                output_path = os.path.join(output_dir, output_filename)
                
                with open(output_path, "wb") as f_out:
                    writer.write(f_out)
                
                self.log.emit(f"✅ 已生成: {output_filename} ({len(target_pages)} 页)")
                self.progress.emit(i + 1, len(ranges), f"正在导出第 {i+1} 部分...")

            self.finished.emit(True, "拆分完成")

        except Exception as e:
            error_trace = traceback.format_exc()
            self.log.emit(f"❌ 错误:\n{error_trace}")
            self.finished.emit(False, str(e))

    def _parse_ranges(self, text, total_pages):
        """
        解析范围字符串，返回 [(start, end), ...] 列表
        支持格式: "1-5, 8, 10-end"
        """
        ranges = []
        parts = text.replace('，', ',').split(',')
        
        for part in parts:
            part = part.strip().lower()
            if not part: continue
            
            try:
                if '-' in part:
                    start_str, end_str = part.split('-')
                    start = int(start_str)
                    
                    if end_str == 'end':
                        end = total_pages
                    else:
                        end = int(end_str)
                else:
                    start = int(part)
                    end = int(part)
                
                # 简单验证
                if start > end:
                    start, end = end, start
                
                if start < 1: start = 1
                
                ranges.append((start, end))
            except ValueError:
                self.log.emit(f"⚠️ 无法解析范围格式: '{part}'")
                return None
                
        return ranges
