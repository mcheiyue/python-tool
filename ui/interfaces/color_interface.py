from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QFileDialog
from PyQt6.QtCore import Qt
from qfluentwidgets import SubtitleLabel, BodyLabel, Slider, InfoBar, PushButton, CardWidget

from core.color_extractor import ColorExtractor
from ui.widgets import DropImageWidget, ColorCard, ColorBar
from ui.threads import ExtractionThread

class ColorInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("color_interface")
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 30, 30, 30)
        self.vbox.setSpacing(20)

        self.title = SubtitleLabel("图片色调提取", self)
        self.desc = BodyLabel("提取图片中的主色调并生成配色方案", self)
        self.desc.setTextColor("#606060", "#d0d0d0")
        self.vbox.addWidget(self.title)
        self.vbox.addWidget(self.desc)

        # 拖拽区域
        self.drop_area = DropImageWidget(self)
        self.drop_area.image_dropped.connect(self.start_extraction)
        self.vbox.addWidget(self.drop_area)

        # 设置栏
        self.settings_layout = QHBoxLayout()
        self.slider_label = BodyLabel("提取数量: 8")
        self.slider = Slider(Qt.Orientation.Horizontal)
        self.slider.setRange(2, 20)
        self.slider.setValue(8)
        self.slider.setFixedWidth(200)
        self.slider.valueChanged.connect(lambda v: self.slider_label.setText(f"提取数量: {v}"))
        
        self.settings_layout.addWidget(self.slider_label)
        self.settings_layout.addWidget(self.slider)
        self.settings_layout.addStretch(1)

        # 导出按钮
        self.export_btn = PushButton("导出色条", self)
        self.export_btn.clicked.connect(self.export_color_bar)
        self.export_btn.hide()
        self.settings_layout.addWidget(self.export_btn)

        self.vbox.addLayout(self.settings_layout)

        # 结果显示区域 (滚动) - 使用卡片包裹
        self.result_card = CardWidget(self)
        self.card_layout = QVBoxLayout(self.result_card)
        self.card_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll = QScrollArea(self.result_card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea {border: none; background: transparent;}")
        
        self.result_container = QWidget()
        self.result_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.result_container)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.result_container)
        self.card_layout.addWidget(self.scroll)
        
        self.vbox.addWidget(self.result_card)

        # 逻辑
        self.extractor = ColorExtractor()
        self.thread = None
        self.extractor.finished.connect(self.on_finished)
        self.extractor.log.connect(self.show_loading) # 简单用log显示状态

    def start_extraction(self, path):
        n_colors = self.slider.value()
        self.drop_area.setEnabled(False)
        self.clear_results()
        self.export_btn.hide()
        
        # 显示加载状态
        self.loading_label = BodyLabel("正在分析图片颜色...", self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(self.loading_label, 0, 0)
        
        self.thread = ExtractionThread(self.extractor, path, n_colors)
        self.thread.start()

    def show_loading(self, msg):
        pass

    def clear_results(self):
        # 清空网格布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_finished(self, results, error):
        self.drop_area.setEnabled(True)
        self.clear_results()
        
        if error:
            InfoBar.error("错误", error, parent=self)
            return

        # 布局结果
        # 添加色条
        self.color_bar = ColorBar(results)
        self.grid_layout.addWidget(self.color_bar, 0, 0, 1, 4) # 跨越4列
        self.export_btn.show()

        row, col = 1, 0
        max_cols = 4 # 每行4个
        
        for data in results:
            card = ColorCard(data)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def export_color_bar(self):
        if not hasattr(self, 'color_bar') or not self.color_bar:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存色条",
            "color_bar.png",
            "PNG Images (*.png)"
        )
        
        if file_path:
            if self.color_bar.export_to_image(file_path):
                InfoBar.success("导出成功", f"色条已保存至 {file_path}", parent=self)
            else:
                InfoBar.error("导出失败", "无法保存图片", parent=self)
