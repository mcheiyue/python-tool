import os
import webbrowser
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import QSettings, Qt
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, IconWidget, 
                            ComboBox, Theme, setTheme, FluentIcon as FIF,
                            PushButton, ToolButton, CaptionLabel)
from app.container import AppContainer
from core.external_tools.base import ExternalTool
from config.loader import ConfigLoader

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

        # Plugin Mode Card
        self.plugin_card = CardWidget(self)
        self.plugin_layout = QHBoxLayout(self.plugin_card)
        self.plugin_layout.setContentsMargins(20, 10, 20, 10)

        self.plugin_icon = IconWidget(FIF.ZIP_FOLDER)
        self.plugin_icon.setFixedSize(18, 18)
        
        self.plugin_label = BodyLabel("插件加载模式", self)
        
        self.plugin_combo = ComboBox(self)
        self.plugin_combo.addItems(["临时模式 (推荐)", "持久模式"])
        self.plugin_combo.setFixedWidth(150)
        self.plugin_combo.setToolTip("临时模式：退出后清理插件文件（更干净）\n持久模式：保留插件文件（启动更快）")

        # Load plugin mode
        config = ConfigLoader()
        plugin_mode = config.get("app.plugin_mode", "temporary")
        if plugin_mode == "persistent":
            self.plugin_combo.setCurrentIndex(1)
        else:
            self.plugin_combo.setCurrentIndex(0)
            
        self.plugin_combo.currentIndexChanged.connect(self.on_plugin_mode_changed)

        self.plugin_layout.addWidget(self.plugin_icon)
        self.plugin_layout.addSpacing(10)
        self.plugin_layout.addWidget(self.plugin_label)
        
        # Add restart hint
        self.restart_hint = CaptionLabel("(需重启生效)", self)
        self.restart_hint.setStyleSheet("color: #737373;")
        self.restart_hint.hide() # Initially hidden
        
        self.plugin_layout.addStretch(1)
        self.plugin_layout.addWidget(self.restart_hint)
        self.plugin_layout.addSpacing(5)
        self.plugin_layout.addWidget(self.plugin_combo)

        self.vbox.addWidget(self.plugin_card)

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
        card.setFixedHeight(100)  # 增加高度以容纳功能说明
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 10, 20, 10)
        
        is_installed = status["installed"]
        is_disabled = status.get("disabled", False)
        
        # Status Icon
        if is_disabled:
            icon = FIF.CANCEL
            color = "#737373" # Grey
            status_text = "已禁用"
        elif is_installed:
            icon = FIF.ACCEPT
            color = "#107C10" # Green
            source = status.get("source", "system")
            status_text = "已就绪 (便携版)" if source == "portable" else "已就绪 (系统安装)"
        else:
            icon = FIF.INFO
            color = "#C42B1C" # Red
            status_text = "未安装 (功能受限)"

        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(18, 18)
        icon_widget.setStyleSheet(f"IconWidget {{ color: {color}; }}")
        
        layout.addWidget(icon_widget)
        layout.addSpacing(10)
        
        # Info Container
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Tool Name
        name_label = BodyLabel(status["display_name"], self)
        info_layout.addWidget(name_label)
        
        # Status Label
        status_label = CaptionLabel(status_text, self)
        status_label.setStyleSheet(f"color: {color};")
        info_layout.addWidget(status_label)
        
        # Features Label (功能说明)
        if status.get("features"):
            features_label = CaptionLabel(f"💡 {status['features']}", self)
            features_label.setStyleSheet("color: #605E5C;")  # 使用中性灰色
            info_layout.addWidget(features_label)
        
        layout.addLayout(info_layout)
        layout.addStretch(1)
        
        # Actions
        manager = AppContainer().external_tool_manager

        if is_disabled:
            # Enable Button
            enable_btn = PushButton(FIF.RINGER, "启用", self)
            enable_btn.clicked.connect(lambda: self._enable_tool(status["name"]))
            layout.addWidget(enable_btn)
        
        elif is_installed:
            # Uninstall Button (Only for portable)
            if status.get("source") == "portable":
                uninstall_btn = PushButton(FIF.DELETE, "卸载", self)
                uninstall_btn.setToolTip("删除便携版文件")
                # Red style for delete
                # uninstall_btn.setStyleSheet("PushButton { color: white; background-color: #C42B1C; border: 1px solid #C42B1C; }")
                uninstall_btn.clicked.connect(lambda: self._uninstall_tool(status["name"]))
                layout.addWidget(uninstall_btn)

            # Disable Button
            disable_btn = PushButton(FIF.CANCEL, "禁用", self)
            disable_btn.clicked.connect(lambda: self._disable_tool(status["name"]))
            layout.addWidget(disable_btn)
            
        else:
            # Not Installed Actions
            open_libs_btn = PushButton(FIF.FOLDER, "打开目录", self)
            open_libs_btn.setToolTip("打开组件存放目录 (libs)")
            open_libs_btn.clicked.connect(self._open_libs_folder)
            layout.addWidget(open_libs_btn)
            
            if status["download_url"]:
                download_btn = PushButton(FIF.DOWNLOAD, "下载", self)
                download_btn.clicked.connect(lambda: self._open_download_url(status["download_url"]))
                layout.addWidget(download_btn)
            
            # Refresh Button (only useful when checking for installation)
            refresh_btn = ToolButton(FIF.SYNC, self)
            refresh_btn.setToolTip("重新检测")
            refresh_btn.clicked.connect(lambda: self._refresh_single_tool(status["name"]))
            layout.addWidget(refresh_btn)
        
        return card

    def _disable_tool(self, name):
        manager = AppContainer().external_tool_manager
        manager.disable_tool(name)
        self.refresh_tools_ui()

    def _enable_tool(self, name):
        manager = AppContainer().external_tool_manager
        manager.enable_tool(name)
        self.refresh_tools_ui()

    def _uninstall_tool(self, name):
        from qfluentwidgets import MessageBox
        
        # 获取工具的显示名称
        manager = AppContainer().external_tool_manager
        tool = manager.get_tool(name)
        display_name = tool.display_name if tool else name
        
        # 显示确认对话框
        title = "确认卸载"
        content = f"确定要卸载便携版组件吗？\n\n这将删除 {display_name} 的便携版文件。"
        
        w = MessageBox(title, content, self)
        if w.exec():
            if manager.uninstall_tool(name):
                self.refresh_tools_ui()
            else:
                # 卸载失败，显示错误提示
                error_box = MessageBox("卸载失败", f"无法卸载 {display_name}，请检查文件权限。", self)
                error_box.exec()

    def _refresh_single_tool(self, tool_name):
        """Refresh status for a single tool (reloads entire list for simplicity)"""
        # Ideally we would only update the specific card, but reloading all is safer/easier
        # First clear cache for the tool to force re-check
        manager = AppContainer().external_tool_manager
        tool = manager.get_tool(tool_name)
        if tool:
             tool.clear_cache()
             
        self.refresh_tools_ui()

    def _open_download_url(self, url):
        """Open download URL in browser"""
        webbrowser.open(url)

    def _open_libs_folder(self):
        """Open the libs folder"""
        libs_path = ExternalTool.get_libs_path()
        if not os.path.exists(libs_path):
            try:
                os.makedirs(libs_path)
            except:
                pass
        
        if os.path.exists(libs_path):
            os.startfile(libs_path)

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

    def on_plugin_mode_changed(self, index):
        mode = "persistent" if index == 1 else "temporary"
        config_loader = ConfigLoader()
        config_loader.set("app.plugin_mode", mode)
        self.restart_hint.show()
