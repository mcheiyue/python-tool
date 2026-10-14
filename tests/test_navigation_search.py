"""Ctrl+K 搜索激活回归测试。

历史 bug：SearchController.activate 访问不存在的 NavigationInterface.isExpanded，
按 Ctrl+K 必抛 AttributeError，被 CrashHandler 吞掉后功能静默失效。

这里用轻量桩锁定控制器契约（不构造 MainWindow——全量测试序列中 QConfig 会提前
析构，属既有问题）；真实窗口的集成验证见 .omo/smoke_visual.py 的 SEARCH 段。
"""
from types import SimpleNamespace

from qfluentwidgets import NavigationDisplayMode

from ui.navigation_extras import SearchController


class _PanelStub:
    def __init__(self, mode):
        self.displayMode = mode
        self.expanded = False

    def expand(self):
        self.expanded = True


class _NavStub:
    def __init__(self, mode):
        self.panel = _PanelStub(mode)

    def expand(self):
        self.panel.expand()


class _BoxStub:
    def __init__(self):
        self.focused = False
        self.selected = False

    def setFocus(self):
        self.focused = True

    def selectAll(self):
        self.selected = True


def _activate(mode):
    nav = _NavStub(mode)
    box = _BoxStub()
    ctrl = SimpleNamespace(window=SimpleNamespace(navigationInterface=nav), search_box=box)
    SearchController.activate(ctrl)
    return nav, box


def test_activate_expands_collapsed_panel():
    nav, box = _activate(NavigationDisplayMode.MINIMAL)
    assert nav.panel.expanded is True
    assert (box.focused, box.selected) == (True, True)


def test_activate_keeps_expanded_panel():
    nav, box = _activate(NavigationDisplayMode.EXPAND)
    assert nav.panel.expanded is False
    assert box.focused is True
