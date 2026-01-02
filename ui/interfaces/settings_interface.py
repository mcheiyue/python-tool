from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QSettings
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, IconWidget, 
                            ComboBox, Theme, setTheme, FluentIcon as FIF)

class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("settings_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("设置", self)
        self.vbox.addWidget(self.title)

        self.card = CardWidget(self)
        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 10, 20, 10)

        self.icon = IconWidget(FIF.BRUSH)
        self.icon.setFixedSize(18, 18)
        
        self.label = BodyLabel("应用主题", self)
        
        self.combo = ComboBox(self)
        self.combo.addItems(["跟随系统", "浅色模式", "深色模式"])
        self.combo.setFixedWidth(150)
        
        # Load saved theme
        self.settings = QSettings("AI_Office_Tool", "Config")
        mode = self.settings.value("themeMode", "Auto")
        if mode == "Light":
            self.combo.setCurrentIndex(1)
        elif mode == "Dark":
            self.combo.setCurrentIndex(2)
        else:
            self.combo.setCurrentIndex(0)
            
        self.combo.currentIndexChanged.connect(self.on_changed)
        
        self.card_layout.addWidget(self.icon)
        self.card_layout.addSpacing(10)
        self.card_layout.addWidget(self.label)
        self.card_layout.addStretch(1)
        self.card_layout.addWidget(self.combo)
        
        self.vbox.addWidget(self.card)
        self.vbox.addStretch(1)

    def on_changed(self, index):
        if index == 0:
            setTheme(Theme.AUTO)
            self.settings.setValue("themeMode", "Auto")
        elif index == 1:
            setTheme(Theme.LIGHT)
            self.settings.setValue("themeMode", "Light")
        elif index == 2:
            setTheme(Theme.DARK)
            self.settings.setValue("themeMode", "Dark")
