import os
import webbrowser
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import QSettings, Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, IconWidget, 
                            ComboBox, Theme, setTheme, FluentIcon as FIF,
                            PushButton, ToolButton, CaptionLabel)
from app.container import AppContainer

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

        # External Tools Section
        self._init_external_tools_section()

        self.vbox.addStretch(1)

    def _init_external_tools_section(self):
        """Initialize the external tools management section"""
        self.vbox.addSpacing(10)
        self.tools_title = SubtitleLabel("外部工具", self)
        self.vbox.addWidget(self.tools_title)
        
        # Container layout for tools
        self.tools_layout = QVBoxLayout()
        self.tools_layout.setSpacing(10)
        self.vbox.addLayout(self.tools_layout)
        
        self.refresh_tools_ui()

    def refresh_tools_ui(self):
        """Refresh the external tools list"""
        # Clear existing items
        while self.tools_layout.count():
            item = self.tools_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Get tool status
        manager = AppContainer().external_tool_manager
        tools_status = manager.get_status_all()
        
        for status in tools_status:
            card = self._create_tool_card(status)
            self.tools_layout.addWidget(card)

    def _create_tool_card(self, status):
        """Create a card widget for a tool"""
        card = CardWidget(self)
        card.setFixedHeight(80)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Status Icon
        is_installed = status["installed"]
        icon = FIF.ACCEPT if is_installed else FIF.CANCEL
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(18, 18)
        # Set icon color: green for installed, red for missing
        if is_installed:
            icon_widget.setStyleSheet("IconWidget { color: #107C10; }")
        else:
            icon_widget.setStyleSheet("IconWidget { color: #C42B1C; }")
            
        layout.addWidget(icon_widget)
        layout.addSpacing(10)
        
        # Info Container
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Tool Name
        name_label = BodyLabel(status["display_name"], self)
        info_layout.addWidget(name_label)
        
        # Version/Path or "Not Installed"
        if is_installed:
            detail_text = f"版本: {status['version'] or '未知'}"
            if status['path']:
                # Truncate path if too long
                path = status['path']
                if len(path) > 40:
                    path = path[:20] + "..." + path[-17:]
                detail_text += f" | 路径: {path}"
            detail_label = CaptionLabel(detail_text, self)
            detail_label.setTextColor("#666666", "#999999") # Light/Dark mode colors
        else:
            detail_label = CaptionLabel("未检测到安装", self)
            detail_label.setTextColor("#C42B1C", "#FF99A4")
            
        info_layout.addWidget(detail_label)
        layout.addLayout(info_layout)
        layout.addStretch(1)
        
        # Actions
        if not is_installed and status["download_url"]:
            download_btn = PushButton(FIF.DOWNLOAD, "下载", self)
            download_btn.clicked.connect(lambda: self._open_download_url(status["download_url"]))
            layout.addWidget(download_btn)
            
        refresh_btn = ToolButton(FIF.SYNC, self)
        refresh_btn.setToolTip("重新检测")
        refresh_btn.clicked.connect(lambda: self._refresh_single_tool(status["name"]))
        layout.addWidget(refresh_btn)
        
        return card

    def _refresh_single_tool(self, tool_name):
        """Refresh status for a single tool (reloads entire list for simplicity)"""
        # Ideally we would only update the specific card, but reloading all is safer/easier
        # First clear cache for the tool to force re-check
        manager = AppContainer().external_tool_manager
        tool = manager.get_tool(tool_name)
        if tool and hasattr(tool, '_cached_path'):
             # If we implemented caching in tools, we'd clear it here. 
             # Currently tools check on every call, so just refreshing UI is enough.
             pass
             
        self.refresh_tools_ui()

    def _open_download_url(self, url):
        """Open download URL in browser"""
        webbrowser.open(url)

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
