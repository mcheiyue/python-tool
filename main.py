import sys
import time
# 记录启动开始时间 (放在尽可能靠前的位置)
startup_start_time = time.perf_counter()

import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings, QTimer
from qfluentwidgets import setTheme, Theme

# 导入错误追踪系统
from core.utils.crash_handler import CrashHandler

# 导入应用容器
from app.container import AppContainer
# 导入主窗口
from ui.main_window import MainWindow

if __name__ == "__main__":
    # 1. 安装全局异常捕获 (Crash Handler)
    # 尽早安装，以便捕获启动过程中的错误
    crash_handler = CrashHandler()
    crash_handler.install()

    # 设置 AppUserModelID，确保任务栏图标显示正确
    try:
        # AUMID 不带版本号：随版本变化会让任务栏固定项被系统当成另一个应用
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OfficeToolkit.App")
    except Exception:
        pass

    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1.25"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 初始化应用容器
    container = AppContainer()
    
    # 必须先创建 QApplication 实例
    app = QApplication(sys.argv)
    
    # 加载主题设置（使用 QSettings，与设置界面保持一致）
    # 注意：setTheme 必须在 QApplication 创建之后调用，否则主题设置可能被系统主题变化覆盖
    settings = QSettings("AI_Office_Tool", "Config")
    theme_mode = settings.value("themeMode", "Auto")
    
    if theme_mode == "Light":
        setTheme(Theme.LIGHT)
    elif theme_mode == "Dark":
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.AUTO)
    
    # 将容器注入主窗口
    w = MainWindow(container)
    w.show()

    # 基准测试模式：打印启动时间并退出
    if "--benchmark" in sys.argv:
        def report_benchmark():
            # 计算总耗时 (毫秒)
            end_time = time.perf_counter()
            duration_ms = (end_time - startup_start_time) * 1000
            print(f"BENCHMARK_STARTUP_TIME_MS: {duration_ms:.2f}")
            # 退出应用
            app.quit()
        
        # 延迟执行以确保界面已渲染完成 (模拟用户感知到的"就绪")
        # 200ms 通常足够让主事件循环处理完初始的 show() 事件
        QTimer.singleShot(200, report_benchmark)

    sys.exit(app.exec())
