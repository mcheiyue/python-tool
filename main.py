import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings
from qfluentwidgets import setTheme, Theme

# 导入主窗口
from ui.main_window import MainWindow

if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1.25"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 加载主题设置
    settings = QSettings("AI_Office_Tool", "Config")
    mode = settings.value("themeMode", "Auto")
    if mode == "Light":
        setTheme(Theme.LIGHT)
    elif mode == "Dark":
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.AUTO)
    
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
