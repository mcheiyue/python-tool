# API 参考文档

本文档面向开发者，详细介绍了 AI Office Tool 的核心架构、接口定义及插件开发规范。

## 目录

1. [核心架构](#核心架构)
2. [插件系统](#插件系统)
3. [核心工具类](#核心工具类)
4. [UI 组件](#ui-组件)

---

## 核心架构

项目采用分层架构设计：

- **UI 层 (`ui/`)**: 基于 PyQt6 和 QFluentWidgets 的用户界面。
- **核心层 (`core/`)**: 业务逻辑与底层功能的实现。
- **适配层 (`ui/interfaces/`)**: 连接 UI 与 Core 的中间层，负责数据传递与线程管理。

### 依赖注入容器
`app/container.py` 实现了简单的依赖注入容器 `AppContainer`，用于管理全局单例服务（如配置加载器、插件管理器、外部工具管理器）。

```python
from app.container import AppContainer

container = AppContainer()
plugin_manager = container.plugin_manager
```

---

## 插件系统

插件系统允许开发者在不修改核心代码的情况下扩展功能。Python 能力插件位于 `core/plugins/`；
外部二进制工具（Ghostscript/Pandoc/LibreOffice）由 `core/tools/package_store.py`
按 `plugins/manifest.json`（官方 URL + SHA256）供给，安全解压在 `core/bundles/loader.py`，
规格见 `docs/PLUGIN_GUIDE.md`。

### 插件结构
一个标准的插件包 (.opk, 本质是 .tar.gz) 结构如下：

```text
plugin_name/
├── manifest.json   # 插件元数据
├── __init__.py     # 入口文件
└── ...             # 其他资源
```

### Manifest 规范 (`manifest.json`)
```json
{
    "name": "My Plugin",
    "version": "1.0.0",
    "entry_point": "my_plugin.PluginClass",
    "description": "A sample plugin"
}
```

### 开发接口
插件类需继承自 `BasePlugin` (尚未严格强制，但建议遵循以下协议)：

```python
class MyPlugin:
    def __init__(self, context):
        """
        初始化插件
        :param context: 应用上下文，提供访问主程序功能的能力
        """
        self.context = context

    def install(self):
        """插件安装时的回调"""
        pass
        
    def uninstall(self):
        """插件卸载时的回调"""
        pass
```

---

## 核心工具类

### PDF 引擎 (`core/engines/pdf/`)
封装了 PDF 处理的底层逻辑，主要基于 `pypdf` 和 `Ghostscript`。

#### `PDFMerger`
```python
from core.features.pdf.pdf_merger import PDFMerger

merger = PDFMerger()
# 合并文件
merger.merge(input_paths=["1.pdf", "2.pdf"], output_path="merged.pdf")
```

#### `PDFCompressor` (Ghostscript)
```python
from core.external_tools.ghostscript_tool import GhostscriptTool

gs = GhostscriptTool()
# 压缩 PDF
gs.compress_pdf(input_path="input.pdf", output_path="output.pdf", quality="screen")
```

### Office 引擎 (`core/engines/office/`)
处理 Office 文档转换。

#### `LibreOfficeTool`
```python
from core.external_tools.libreoffice_tool import LibreOfficeTool

lo = LibreOfficeTool()
if lo.check_installed():
    # 转换为 PDF
    lo.convert_to_pdf(input_path="doc.docx", output_dir="output/")
```

---

## UI 组件

### 懒加载机制 (`core/utils/lazy_loader.py`)
为了优化启动性能，所有功能界面均通过 `UILazyLoader` 进行按需加载。

```python
from core.utils.lazy_loader import UILazyLoader

# 定义加载器
self.ppt_interface = UILazyLoader(
    module_name="ui.interfaces.office.ppt_interface",
    class_name="PPTInterface", 
    parent=self
)

# 添加到 UI (此时尚未实例化)
self.stackedWidget.addWidget(self.ppt_interface)
```

### 工作线程 (`ui/threads.py`)
所有耗时操作必须在 `WorkThread` 中执行，避免阻塞主线程。

```python
from ui.threads import WorkThread

class MyInterface(QWidget):
    def start_task(self):
        self.worker = WorkThread(self.do_heavy_work, arg1, arg2)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()