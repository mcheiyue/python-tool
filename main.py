import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from qfluentwidgets import setTheme, Theme

# 导入应用容器
from app.container import AppContainer
# 导入主窗口
from ui.main_window import MainWindow

if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1.25"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 初始化应用容器
    container = AppContainer()
    
    # 加载主题设置 (使用新的配置系统)
    # 假设默认配置中有 "app.theme_mode"
    theme_mode = container.config.get("app.theme_mode", "Auto")
    
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
