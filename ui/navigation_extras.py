from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import SearchLineEdit

from core.utils.resource_path import get_resource_path
from ui.widgets.search_popup import SearchResultPopup


class NavigationSearchLineEdit(SearchLineEdit):
    """支持在导航栏中使用的搜索框"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 搜索框不需要被选中样式，但需要满足接口要求

    def setSelected(self, isSelected):
        # 必须实现此方法以满足 NavigationInterface 接口
        pass


def refresh_navigation_icons(window):
    """主题切换后按 icon_mapping 刷新导航图标（公开 API：panel.widget(routeKey)）"""
    panel = window.navigationInterface.panel
    for object_name, icon_path in window.icon_mapping.items():
        try:
            item = panel.widget(object_name)
        except Exception:
            continue
        if hasattr(item, 'setIcon'):
            item.setIcon(window.get_icon(icon_path))
    window.navigationInterface.update()
    window.navigationInterface.repaint()


class SearchController:
    """Ctrl+K 搜索控制器：弹窗、模糊匹配与页面跳转（从 MainWindow 拆出）"""

    def __init__(self, window, search_box):
        self.window = window
        self.search_box = search_box
        self.search_popup = SearchResultPopup(window)
        self.search_popup.itemClicked.connect(self.on_result_clicked)
        search_box.textChanged.connect(self.on_text_changed)
        search_box.returnPressed.connect(self.on_return_pressed)

    def activate(self):
        """激活搜索框 (Ctrl+K)"""
        if not self.window.navigationInterface.isExpanded:
            self.window.navigationInterface.panel.expand()

        self.search_box.setFocus()
        self.search_box.selectAll()

    def on_text_changed(self, text):
        """搜索文本变化处理"""
        if not text:
            self.search_popup.hide()
            return

        # 执行模糊搜索
        results = self.window.search_engine.search(text)

        if results:
            # 准备图标
            icons = {}
            for res in results:
                icon_file = self.window.icon_name_map.get(res.name, "magic.svg")
                icons[res.name] = self.window.get_icon(get_resource_path(f"assets/icons/{icon_file}"))

            # 显示弹窗（在搜索框下方）
            pos = self.search_box.mapToGlobal(self.search_box.rect().bottomLeft())
            pos = self.window.mapFromGlobal(pos)

            self.search_popup.move(pos.x(), pos.y() + 5)
            self.search_popup.show_results(results, icons, self.search_box.width())
        else:
            self.search_popup.hide()

    def on_return_pressed(self):
        """回车键处理"""
        if self.search_popup.isVisible() and self.search_popup.count() > 0:
            item = self.search_popup.item(0)
            feature_name = item.data(Qt.ItemDataRole.UserRole)
            self.on_result_clicked(feature_name)

    def on_clicked(self):
        # 搜索框点击时不进行页面切换，仅保持焦点
        self.search_box.setFocus()
        if self.search_box.text():
            self.on_text_changed(self.search_box.text())

    def on_result_clicked(self, feature_name):
        """搜索结果点击处理"""
        if feature_name in self.window.interfaces:
            self.window.switchTo(self.window.interfaces[feature_name])
            # 清空搜索框并隐藏弹窗
            self.search_box.clear()
            self.search_popup.hide()
            # 自动收起侧边栏（使用 panel.collapse() 方法）
            self.window.navigationInterface.panel.collapse()
