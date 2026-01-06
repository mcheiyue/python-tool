import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings
from qfluentwidgets import setTheme, Theme

# 导入应用容器
from app.container import AppContainer
# 导入主窗口
from ui.main_window import MainWindow

if __name__ == "__main__":
    # 设置 AppUserModelID，确保任务栏图标显示正确
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OfficeToolkit.App.v1.0.0")
    except Exception:
        pass

    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1.25"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 初始化应用容器
    container = AppContainer()
    
    # 加载主题设置（使用 QSettings，与设置界面保持一致）
    settings = QSettings("AI_Office_Tool", "Config")
    theme_mode = settings.value("themeMode", "Auto")
    
    if theme_mode == "Light":
        setTheme(Theme.LIGHT)
    elif theme_mode == "Dark":
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.AUTO)
    
    app = QApplication(sys.argv)
    
    # 将容器注入主窗口
    w = MainWindow(container)
    w.show()
    sys.exit(app.exec())
