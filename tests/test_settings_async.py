from threading import Event, current_thread, main_thread
from types import SimpleNamespace

from PyQt6.QtCore import QTimer
from qfluentwidgets import CaptionLabel

from core.external_tools.base import ExternalTool
import ui.interfaces.settings_interface as settings_module


def test_settings_detects_tools_off_main_thread(qtbot, monkeypatch):
    started, release = Event(), Event()

    class SlowTool(ExternalTool):
        name = "slow"
        display_name = "后台检测组件"

        def check_installed(self):
            assert current_thread() is not main_thread()
            started.set()
            release.wait(timeout=3)
            return False

        def get_path(self):
            return None

        def get_version(self):
            return None

    tool = SlowTool()
    manager = SimpleNamespace(get_all=lambda: [tool], get_status_all=lambda: [tool.get_status_info()])
    monkeypatch.setattr(settings_module, "AppContainer", lambda: SimpleNamespace(external_tool_manager=manager))
    monkeypatch.setattr(settings_module.SettingsInterface, "_manifest_entry", staticmethod(lambda name: None))
    page = None
    try:
        page = settings_module.SettingsInterface()
        qtbot.addWidget(page)
        assert started.wait(timeout=1)
        ticks = []
        QTimer.singleShot(0, lambda: ticks.append(True))
        qtbot.waitUntil(lambda: bool(ticks))
        labels = page.tools_layout.itemAt(0).widget().findChildren(CaptionLabel)
        assert any("检测" in label.text() for label in labels)
    finally:
        release.set()
        resolver = getattr(tool, "_resolver", None)
        if resolver is not None:
            assert resolver.wait(3000)
    assert page is not None
    qtbot.waitUntil(lambda: any("未安装" in label.text() for label in page.tools_layout.itemAt(0).widget().findChildren(CaptionLabel)))
