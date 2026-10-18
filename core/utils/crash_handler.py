import sys
import os
import traceback
import platform
import logging
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt
from core.utils.version import get_app_version

class CrashHandler:
    def __init__(self, app_name="Office Toolkit", app_version=None):
        self.app_name = app_name
        self.app_version = app_version or get_app_version()
        self.log_dir = os.path.join(os.getcwd(), "logs")
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.log_file = os.path.join(self.log_dir, "crash.log")
        
        # 配置 Logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def install(self):
        """安装全局异常钩子"""
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """处理未捕获的异常"""
        # 忽略键盘中断 (Ctrl+C)
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 收集系统信息
        system_info = {
            "Time": datetime.now().isoformat(),
            "App": f"{self.app_name} v{self.app_version}",
            "OS": f"{platform.system()} {platform.release()} ({platform.version()})",
            "Python": sys.version,
        }
        
        # 格式化堆栈信息
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)
        
        error_msg = f"""
{'='*50}
崩溃报告 (Crash Report)
{'='*50}
"""
        # 中文标签映射
        labels = {
            "Time": "时间",
            "App": "应用",
            "OS": "系统",
            "Python": "Python版本"
        }

        for k, v in system_info.items():
            label = labels.get(k, k)
            error_msg += f"{label}: {v}\n"
            
        error_msg += f"\n错误信息 (Error):\n{exc_type.__name__}: {str(exc_value)}\n"
        error_msg += f"\n堆栈跟踪 (Traceback):\n{tb_text}"
        error_msg += f"{'='*50}\n"
        
        # 写入日志
        print(error_msg, file=sys.stderr) # 同时也输出到控制台
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(error_msg)
            
        # 显示错误弹窗
        self.show_crash_dialog(exc_type.__name__, str(exc_value), tb_text)

    def show_crash_dialog(self, error_type, error_msg, traceback_text):
        """显示崩溃对话框"""
        # 确保有一个 QApplication 实例
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
            
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(f"{self.app_name} 发生错误")
        msg_box.setText(f"抱歉，程序遇到了一个未处理的错误并需要关闭。\n\n类型: {error_type}\n信息: {error_msg}")
        msg_box.setInformativeText(f"错误日志已保存至:\n{self.log_file}")
        msg_box.setDetailedText(traceback_text)
        
        # 添加自定义按钮
        copy_btn = msg_box.addButton("复制详细信息", QMessageBox.ButtonRole.ActionRole)
        open_dir_btn = msg_box.addButton("打开日志文件夹", QMessageBox.ButtonRole.ActionRole)
        close_btn = msg_box.addButton("关闭程序", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == copy_btn:
            cb = QApplication.clipboard()
            cb.setText(traceback_text)
            # 复制后可能还需要再次显示或者直接退出，这里简单处理直接退出
        elif msg_box.clickedButton() == open_dir_btn:
            os.startfile(self.log_dir)
            
        # 强制退出
        sys.exit(1)