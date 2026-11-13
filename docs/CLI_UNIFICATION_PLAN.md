# CLI 统一调用方案

> 状态：方案草案，供实现前评审。本文描述目标架构和迁移路线，不代表未接入的功能已经支持 CLI。
> 基线日期：2026-11-12。修订：2026-11-13（两轮源码审查：修正 Qt 分级、完成定义、契约空洞，补 CLI 构建依赖缺口、取消能力三类矩阵、`on_finished` 签名表）。

## 1. 方案摘要

项目已有一个独立命令行入口，覆盖 PDF 合并、拆分、图片提取和图片格式转换。建议继续扩展同一 CLI，让 GUI 中的文件处理功能能够通过路径和参数调用，并继续由 GUI 与 CLI 共用业务处理实现。

“可由 CLI 调用”“不启动应用窗口”“不导入 Qt”“可在无桌面环境运行”“不依赖外部程序”是不同能力，必须分别记录和验收。本方案的目标是让文件处理操作有可脚本化的 CLI 入口；不承诺所有操作都能在服务器、容器或没有用户桌面会话的环境中运行。

建议范围：

- GUI 菜单 24 项逐项定稿：已接入、待接入（含阶段）、需新建核心入口或不接入。当前 **10 项已接入**（阶段 1 的 6 项已完成），11 项待接入，2 项需新建核心入口（#17、#18），1 项不接入（剪贴板）。
- Qt 依赖按第 2.2.1 节分 Q0/Q1 两级验收。已用真实子进程导入断言实测：13 项为 Q0，10 项为 Q1；Q1 不是缺陷，而是成本与承诺的明确标注。
- PDF 元数据与加密/解密等未列入 24 项菜单的核心能力单独评估，不混入本轮菜单覆盖率。

## 2. 目标、定义与非目标

### 2.1 目标

1. 为 24 项菜单功能逐项给出明确决策：已接入、待接入（含所属阶段）、需新建核心入口或明确不接入（含理由）。不允许停留在“待评估”。
2. GUI 与 CLI 调用同一业务实现，不复制转换、文件写入或取消逻辑。
3. 统一结果状态、输出文件、计数、结构化数据和退出码。
4. CLI 不创建主窗口，不调用 UI 控件，不依赖用户通过文件对话框选择输入。
5. 按第 2.2.1 节的两级 Qt 标准分别验收：声明为 Qt-free 的命令必须不导入 PyQt6；声明为“无窗口加载 Qt”的命令只要求不创建主窗口，不得用“没有显示窗口”冒充 Qt-free。
6. 记录每项功能的外部依赖、桌面要求和取消能力，缺少依赖时给出可识别的失败结果。

### 2.2 术语

| 能力 | 含义 | 例子 |
| --- | --- | --- |
| CLI 可调用 | 可通过可执行文件和参数启动操作；不代表没有桌面或外部依赖 | PPT 转 PDF 命令可以解析参数，但仍需可用的 Office 转换后端 |
| 无应用窗口 | 不启动 Office Toolkit 主窗口，也不显示 GUI 功能页 | 当前 `OfficeToolkit_CLI.exe` 的入口目标 |
| Qt-free | 命令导入和执行路径不加载 PyQt6；可用子进程调用系统程序 | 适合自动化、CI 和较小的 CLI 运行时 |
| 无桌面 | 不依赖登录用户的图形会话、剪贴板或可见窗口 | 剪贴板操作不满足；LibreOffice headless 路径可能满足，须实测 |
| 无外部依赖 | 不需要系统安装的 Office、LibreOffice、Pandoc、Ghostscript 等 | 不能由“命令行入口存在”推导出来 |

本文中的“纯 CLI”默认指从命令行传入参数、无 Office Toolkit 窗口，并返回确定的进程结果；是否 Qt-free、无桌面及无外部依赖由各命令的能力标签单独说明。

Qt 级别与桌面依赖是**两个正交维度**：#2 PPT 转图片、#4 Doc 转 Docx 实测不加载 Qt（Q0），但仍需 PowerPoint/Word 与桌面会话。任何验收结论都必须同时给出两者，不能因 Q0 就宣称可无桌面运行。

### 2.2.1 Qt 依赖分级

代码事实决定大部分命令不可能一步做到 Qt-free：`core/external_tools/base.py:8` 与 `core/external_tools/manager.py:3` 在模块顶层直接 `from PyQt6.QtCore import ...`（前者含 `QThread`，后者含 `QObject`、`pyqtSignal`）。任何**导入**了这些模块的命令都会加载 Qt——加载发生在 import 时，不只是 `__init__`，因此延迟到函数内 import 也无效，必须真正解除模块级依赖。

因此本方案把验收标准分为两级，不再用单一的“无 Qt”口径：

| 级别 | 定义 | 验收方式 | 适用命令 |
| --- | --- | --- | --- |
| **Q0（Qt-free）** | 命令执行完成后 `PyQt6` 不在 `sys.modules` | 子进程导入断言 | 纯 Python 库操作，以及不经过 external_tools / Office 基类 / PDF 压缩基类的路径；注意 Q0 不等于无桌面 |
| **Q1（无窗口加载 Qt）** | 允许导入 PyQt6，但不创建 `QApplication`、主窗口或任何可见控件 | 子进程断言未创建窗口，且 CLI 返回码与结果正确 | 依赖 `ExternalToolManager`、`BaseOfficeConverter` 或 `BasePdfCompressor` 的命令 |

`Q1` 是实现成本的分界线：把它当成 `Q0` 会导致阶段估算失真；把它当成阻塞项又会否定 Office/外部工具类命令的全部价值。方案默认接受 `Q1`，但要求每个 `Q1` 命令在能力矩阵中显式标注级别与依赖链。

把 `ExternalToolManager` 与 `BasePdfCompressor` 从 Qt 上解耦，是让部分命令从 `Q1` 升级到 `Q0` 的独立工程，列为阶段 2 的前置决策，不作为本轮默认范围。

### 2.3 非目标

- 重写所有转换算法或更换 Office、PDF、图像处理引擎。
- 把 GUI 控件、预览、拖放、主题、导航和弹窗搬到 CLI。
- 让剪贴板操作在无桌面服务器中可用。
- 将 Microsoft Office、LibreOffice、Pandoc 或 Ghostscript 强行打进 CLI 单文件。
- 在没有真实目标环境验证时宣称 Office COM 可无人值守运行。
- 本轮实现 PDF 加密/解密、元数据编辑等非菜单新增功能；这些作为独立候选记录。

## 3. 当前基线

### 3.1 CLI 已实现

`app/cli.py` 当前提供 16 条根层命令：

| 命令 | 核心实现 | 结果协议 | 阶段 |
| --- | --- | --- | --- |
| `merge` | `PDFMerger` | `OperationResult` | 既有 |
| `split` | `PDFSplitter` | `OperationResult` | 既有 |
| `extract-images` | `PDFImageExtractor` | `OperationResult` | 既有 |
| `image-convert` | `ImageConverter` | `OperationResult` | 既有 |
| `image-colors` | `ColorExtractor` | `OperationResult` + `data.colors` | 1 |
| `image-vectorize` | `ImageVectorizer` | `on_finished(ok, msg)` → `OperationResult` | 1 |
| `image-to-pdf` | `ImageToPdfConverter` | `on_finished(ok, msg)` → `OperationResult` | 1 |
| `text-extract-code` | `CodeExtractor` | `on_finished(ok, msg)` → `OperationResult` | 1 |
| `text-txt-to-pdf` | `TxtConverter` | `on_finished(success, fail)` → `OperationResult` | 1 |
| `files-rename-preview` | `BatchRenamer.preview` | `OperationResult` + `data.plan` | 1 |
| `pdf-compress` | `GhostscriptCompressor`（Qt 信号） | `log`/`finished` → `OperationResult` | 2 |
| `pdf-render` | `PDFPageRenderer` | `on_finished(success, fail)` → `OperationResult` | 2 |
| `text-markdown-batch-pdf` | `PandocMarkdownToPdf` | `on_finished(success, fail)` → `OperationResult` | 2 |
| `office-libreoffice-convert` | `LibreOfficeFormatConverter` | `on_finished(success, fail)` → `OperationResult` | 2 |
| `office-word-markdown` | `WordConverter` | `on_finished(success, fail)` → `OperationResult` | 2 |
| `text-markdown-html` | `MarkdownConverter` | `on_finished(success, fail)` → `OperationResult` | 2 |

全部 16 条支持 `--json`、成功/失败/取消退出码。`app.cli` 导入后 `PyQt6` 不在 `sys.modules`（实测断言见 `tests/test_cli.py`），且真实 `OfficeToolkit_CLI.exe` 运行期未加载任何 Qt DLL——但该产物内含 `QtCore.pyd`/`QtGui.pyd`（PIL 的 `ImageQt` 被 Nuitka 推断带入），因此**“Qt-free”只能按运行期断言，不能按产物内容断言**。

阶段 2 的 6 条命令按设计为 **Q1**：导入即加载 Qt，但既不创建 `QApplication` 也不建主窗口。实测依据：`ExternalToolManager()` 与 `GhostscriptCompressor()` 在无 `QApplication` 环境下可实例化，且 `pyqtSignal` 的 `emit` 在无事件循环时**同步**调用槽函数——`pdf-compress` 正是靠这一点把 `log`/`finished` 信号直接接到 CLI 输出。

取消支持范围：`merge`、`split`、`extract-images`、`image-convert`、`pdf-compress` 接入 Ctrl+C（`pdf-compress` 经 `_register_stopper(compressor.stop)` 杀 GS 子进程）；其余 11 条无 `should_cancel`，见第 6.3 节。

README 现状：`README.md:71-77` 只有 4 条源码调用示例和 1 条 `OfficeToolkit_CLI.exe` 示例，没有退出码、JSON 结构或失败语义说明。用户文档是待补项，不是既有资产。

发行链已有 `cli_main.py` 和 Nuitka CLI onefile 构建（`build_nuitka.bat` Task 3），`build_release.bat` 会检查 CLI 产物并将其放入 Portable 与独立发布产物，`installer.iss:50` 也收录该可执行文件。

**CLI 构建与主构建的收集范围严重不一致，是阶段 1 的前置修复项。** 对照 `build_nuitka.bat` 的两段参数：

| 收集项 | 主构建（`:33-51`） | CLI 构建 | 后果 |
| --- | --- | --- | --- |
| `--include-data-file=VERSION=VERSION` | 有（`:43`） | **已补**（阶段 2） | `get_app_version()` 回落 `0.0.0`。当前只有 `crash_handler` 消费它，CLI 尚无 `--version`；一旦 CLI 加版本输出或崩溃报告即失真 |
| `--include-data-file=plugins/manifest.json` | 有（`:44`） | **无** | 当前 CLI 不读 manifest；若后续提供工具安装命令则必须补 |
| `--include-data-dir=assets=assets` | 有（`:41`） | **无** | #17 去水印读 `assets/watermark/bg_48.png`、`bg_96.png` 时 `FileNotFoundError`（`gemini_watermark_remover.py:13-21`） |
| `--include-data-dir=config=config` | 有（`:42`） | **已补**（阶段 2） | 读配置的命令失效；工具发现可能静默降级为“未安装” |
| `--include-package=comtypes` | 有（`:34`） | **已补**（阶段 2） | #2/#4/#1/#3/#5 的 COM 路径导入失败 |
| `--include-package=core.external_tools.{ghostscript,pandoc,libreoffice}_tool` | 有（`:38-39`） | **已补**（阶段 2） | 外部工具发现走不到具体工具类 |
| `--include-package-data=fpdf` | 有（`:50`） | **已补** | #21 TXT 转 PDF（阶段 1 已加） |
| `--include-package=vtracer` | 有（`:40`） | **已补** | #14 PNG 转 SVG（阶段 1 已加） |
| `pymupdf` 降级策略 | 有（`:45-47`） | **已补**（阶段 2，`--include-package=pymupdf` + 降级两模块） | #12 页面渲染；若只加 `--include-package=pymupdf` 会重新触发 cc1 OOM |
| `--include-package-data=pypinyin` / `pptx` / `docx` | 有（`:48-49,51`） | **无** | #1/#3/#5 与 Markdown 转 PDF 触及即崩 |
| `--include-package=markdown` / `html2text` | 有（经 `core` 连带） | **已补**（阶段 2） | `text-markdown-html` 内置转换路径导入失败 |

**阶段 2 实测发现的打包缺陷（未修，单独立项）**：`--nofollow-import-to=pymupdf.mupdf` 与 `--include-module=pymupdf.mupdf` 互相冲突，Nuitka 报 `Not allowed to include module 'pymupdf.mupdf' due to '... --nofollow-import-to'` 并选择排除。后果是 `pymupdf/__init__.py` 内 `from . import mupdf` 失败，整个包不可导入——产物里 `pymupdf/` 只剩 `_extra.pyd`、`_mupdf.pyd` 两个文件，没有 `__init__.py`。**主构建用同一组参数，因此 GUI 的目录版/单文件版 PDF 渲染同样受影响**；本机源码运行正常，所以此前从未暴露。当前 `pdf-render` 的 `--engine auto`（默认）在 PyMuPDF 不可用时自动回退 Ghostscript，命令可用，但不是修复。

阶段 1 已补齐 `vtracer` 与 `fpdf`，阶段 2 补齐上表标记“已补”的 8 项，并用真实 `OfficeToolkit_CLI.exe` 冒烟通过（见第 9 节）。剩余 `plugins/manifest.json`、`assets`、`pypinyin`/`pptx`/`docx` 三项按所属阶段在用到时补齐——**每新增一个命令都要同步补它的依赖收集**，否则源码通过而产物崩溃。

另外，`.github/workflows/release.yml` 的发行冒烟已改为**校验命令集合 + 实跑 9 条命令**：`--help` 通过不代表各命令的核心模块都被打进产物，因此断言 16 条命令名齐全，并用 Pillow/pypdf 现造输入真实执行 `image-colors`、`image-vectorize`、`image-to-pdf`、`text-txt-to-pdf`、`files-rename-preview`、`merge`、`pdf-compress`、`pdf-render`、`text-markdown-html`，任一返回非 success 即阻断发布。新增命令时须同步把命令名加入该断言。

### 3.2 当前协议差异

核心实现目前混用：

- `OperationResult`，例如 PDF 合并、拆分、提图和图片格式转换。
- Qt `QObject` 信号，例如 Office 引擎（`core/engines/office/base.py`）和 PDF 压缩器（`core/engines/pdf/base.py` 的 `BasePdfCompressor(QObject)`）。
- `on_finished` 回调，例如图片取色、代码提取、各类转换。
- 布尔值、计数元组或隐式 `None`，例如水印处理、LibreOffice 转换和部分批处理。

因此不能只在 `app/cli.py` 增加参数分支；每种返回、错误和取消语义都需要明确适配。

核心入口的完成通知有 5 种形状，第二个位置参数含义不同，逐个适配时必须按表处理：

| 形状 | 模块 | 参数含义 |
| --- | --- | --- |
| `on_finished(results: list, error_msg: str)` | `ColorExtractor` | 颜色数组，必须走 `data` |
| `on_finished(ok: bool, msg: str)` | `CodeExtractor`、`ImageVectorizer`、`ImageToPdfConverter` | 成功时第二参为输出路径或消息，失败时为错误文本；**不能无条件当路径用** |
| `on_finished(ok, fail)`（两个计数） | `TxtConverter`、`PPTImageExporter`、`DocToDocxConverter`、`WordConverter`、`MarkdownConverter`、`PandocMarkdownToPdf`、`LibreOfficeFormatConverter`、`PDFPageRenderer` | 成功数与失败数，须转成 `OperationResult.succeeded`/`failed` |
| 无 `on_finished`，只有 Qt 信号 | `GhostscriptCompressor`、`BasePdfCompressor` 子类 | 由 `log`/`progress`/`finished(int, int)` 信号发布 |
| 无回调，返回 `Tuple[int, int]` | `BatchRenamer.execute` | — |

另有 `ImageConverter.convert` 已返回 `OperationResult`，回调只是兼容层。统一结果时必须逐模块写断言，不可按“都有 on_finished”批量套用。

汇总：23 个可接入项中 4 项已有 `should_cancel`，剩余 18 项（12 项靠 `stop()` 桥接、6 项需改核心代码），另 #18 待抽出后另定。

更关键的是 Qt 的扩散面在**外部工具层**，不在功能模块本身：

| 文件 | 事实 | 波及范围 |
| --- | --- | --- |
| `core/external_tools/base.py:8` | `from PyQt6.QtCore import QObject, QThread, pyqtSignal` | 所有 `ExternalTool` 子类 |
| `core/external_tools/manager.py:3` | `from PyQt6.QtCore import QObject, pyqtSignal` | 导入该模块即加载 Qt，`ExternalToolManager()` 只是使用方 |
| `core/engines/office/base.py` | `BaseOfficeConverter` 使用 `pyqtSignal` | PPT/Word/Excel 转 PDF |
| `core/engines/pdf/base.py:1-4` | `class BasePdfCompressor(QObject)` | PDF 压缩 |

具体受影响：`word_converter.py:5`、`markdown_converter.py:6`、`markdown_pdf_pandoc.py:10`、`libreoffice_converter.py:15` 都在**模块级** `from core.external_tools.manager import ExternalToolManager`，`__init__` 再取实例；`PDFPageRenderer` 经 `GhostscriptTool` 继承 `ExternalTool`。这些命令只能达到 Q1，除非先改造外部工具层。

`core/utils/logger.py` 与 `core/features/office/libreoffice_converter.py` 引用的 `AppLogger` 本身不导入 Qt，可以复用；Qt 的来源是 external_tools 与两个引擎基类。

## 4. 24 项 GUI 功能盘点

表中「状态」列只使用以下取值，避免自由文本无法统计：

| 状态 | 含义 |
| --- | --- |
| 已接入 | 当前已有可用命令，且有真实调用与结果协议 |
| 待接入 | 核心实现已存在，缺 CLI 参数映射与结果适配 |
| 需新建核心入口 | 逻辑只存在于 GUI 内联代码，必须先抽出核心函数 |
| 不接入 | 明确排除本轮范围，并给出理由 |

表中「Qt 级别」按第 2.2.1 节定义。21 个功能模块已逐个子进程实测：模块级 import 后 `PyQt6` 是否进入 `sys.modules`。#2、#4 的模块只导出类、不构造 `ExternalToolManager`，另做类级补测确认。23 个可接入项的级别均已定案，新增或改动模块须补测后再更新本列。

| # | GUI 菜单项 | 现有核心入口 | 建议命令 | Qt 级别 | 状态与运行边界 |
| ---: | --- | --- | --- | --- | --- |
| 1 | PPT 转 PDF | `core/engines/office/powerpoint.py`、`core/engines/office/base.py` | `office-toolkit office ppt-to-pdf` | Q1 | 待接入；Office COM 或 LibreOffice 后端，需按后端分别验证运行环境 |
| 2 | PPT 转图片 | `core/features/office/ppt_image_exporter.py` | `office-toolkit office ppt-to-images` | Q0 | 待接入；纯 comtypes + 回调，实测不加载 Qt；但需 PowerPoint 且设 `Visible=1`，属桌面依赖 |
| 3 | Word 转 PDF | `core/engines/office/word.py`、`core/engines/office/base.py` | `office-toolkit office word-to-pdf` | Q1 | 待接入；同 #1 |
| 4 | Doc 转 Docx | `core/features/office/doc_to_docx_converter.py` | `office-toolkit office doc-to-docx` | Q0 | 待接入；纯 comtypes + 回调，实测不加载 Qt；仍需 Word 与 `Visible=False` |
| 5 | Excel 转 PDF | `core/engines/office/excel.py`、`core/engines/office/base.py` | `office-toolkit office excel-to-pdf` | Q1 | 待接入；同 #1，且须保留宏禁用 |
| 6 | Word ↔ Markdown | `core/features/office/word_converter.py` | `office-toolkit office word-markdown` | Q1 | 待接入；Pandoc 外部依赖，需映射转换方向与参考文档参数 |
| 7 | LibreOffice 格式转换 | `core/features/office/libreoffice_converter.py` | `office-toolkit office libreoffice-convert` | Q1 | 待接入；子进程调用，headless 能力待实测 |
| 8 | PDF 合并 | `core/features/pdf/pdf_merger.py` | `office-toolkit merge`（保留；分组别名 `pdf merge`） | Q0 | 已接入 |
| 9 | PDF 压缩 | `core/engines/pdf/ghostscript.py`、`core/engines/pdf/base.py` | `office-toolkit pdf compress` | Q1 | 待接入；须先把 `BasePdfCompressor(QObject)` 的处理逻辑与信号分开发布，不是简单加参数 |
| 10 | PDF 拆分/提取 | `core/features/pdf/pdf_splitter.py` | `office-toolkit split`（保留；分组别名 `pdf split`） | Q0 | 已接入；页面只有 `start_split` 一条路径（`pdf_split_interface.py:121`），调用 `split(file_path, ranges, output_dir)`，不存在其他提取模式 |
| 11 | PDF 图片提取 | `core/features/pdf/pdf_image_extractor.py` | `office-toolkit extract-images`（保留；分组别名 `pdf extract-images`） | Q0 | 已接入 |
| 12 | PDF 页面渲染 | `core/features/pdf/pdf_page_renderer.py` | `office-toolkit pdf render` | Q1 | 待接入；PyMuPDF 与 Ghostscript 两条路径，后者经 `GhostscriptTool` 引入 Qt |
| 13 | 图片取色 | `core/features/image/color_extractor.py` | `office-toolkit image-colors` | Q0 | 已接入；结果走 `data.colors`（`{rgb, hex, proportion}`） |
| 14 | PNG 转 SVG | `core/features/image/image_vectorizer.py` | `office-toolkit image-vectorize` | Q0 | 已接入；vtracer 已在发行产物中实测可用 |
| 15 | 图片格式转换 | `core/features/image/image_converter.py` | `office-toolkit image-convert`（保留；分组别名 `image convert`） | Q0 | 已接入 |
| 16 | 图片转 PDF | `core/features/pdf/image_to_pdf_converter.py` | `office-toolkit image-to-pdf` | Q0 | 已接入；`--single` 切每图一个 PDF，默认合并 |
| 17 | 图片去水印 | `core/features/image/gemini_watermark_remover.py` | `office-toolkit image remove-watermark` | Q0 | 需新建核心入口；`GeminiWatermarkRemover` 只有单文件 `process_image`，批处理靠 GUI 页面循环；依赖 `assets/watermark/bg_48.png`、`bg_96.png` 与 NumPy |
| 18 | Markdown 转 PDF | 无核心入口，逻辑内联在 `ui/interfaces/text/markdown_interface.py:364-401` | `office-toolkit text markdown-to-pdf` | Q1 | 需新建核心入口；现为 GUI 内联逻辑 + `pdf_converter` 插件 + `has_pdf_engine` 检查 |
| 19 | Markdown ↔ HTML | `core/features/text/markdown_converter.py` | `office-toolkit text markdown-html` | Q1 | 待接入；基础库路径与 Pandoc 路径需显式区分 |
| 20 | Markdown 批量转 PDF | `core/features/text/markdown_pdf_pandoc.py` | `office-toolkit text markdown-batch-pdf` | Q1 | 待接入；Pandoc + PDF 引擎，需映射公式、高亮、模板参数 |
| 21 | TXT 转 PDF | `core/features/text/txt_converter.py` | `office-toolkit text-txt-to-pdf` | Q0 | 已接入；FPDF + `FontFinder.find_cjk_font()`，缺字体时中文可能乱码（不报错，仅日志警告） |
| 22 | 代码提取 | `core/features/text/code_extractor.py` | `office-toolkit text-extract-code` | Q0 | 已接入；同文件拒绝与临时目录替换保护均有回归覆盖 |
| 23 | 批量重命名 | `core/features/utils/batch_rename.py` | `office-toolkit files-rename-preview` | Q0 | 已接入（预览子操作）；`apply` 与 plan 文件机制经决策不在本轮范围（第 12 节第 5 项） |
| 24 | 剪贴板图片助手 | `ui/interfaces/utils/clipboard_interface.py`、`core/features/image/clipboard_handler.py` | 不定义 | — | 不接入；依赖活动桌面剪贴板，不属于文件处理命令 |

覆盖统计：已接入 10 项（#8、#10、#11、#13、#14、#15、#16、#21、#22、#23），待接入 11 项，需新建核心入口 2 项（#17、#18），不接入 1 项（#24）。按 Qt 级别：Q0 共 13 项，Q1 共 10 项，GUI 专属 1 项。

Q0/Q1 判定方式：对每个功能模块在独立子进程中 import 并实例化核心类，检查 `PyQt6` 是否进入 `sys.modules`。已实测 21 个模块，`app.cli` 亦为 CLEAN。实测推翻了按目录推断的两处结论：#2 `ppt_image_exporter` 与 #4 `doc_to_docx_converter` 使用 comtypes + 回调，不经过 `ExternalToolManager`，实际为 Q0。

#18 无核心模块可测，按 GUI 内联路径与插件依赖推定 Q1，阶段 4 抽出核心函数后须复测。

“已接入”按可执行子操作核算，不按菜单卡片数。#10 已核实页面只有页码范围拆分一条路径（见第 12 节），故整体计入“已接入”；若后续新增提取模式，需重新核算为“待接入”。

### 4.1 非菜单候选

`core/features/pdf/pdf_security.py` 的加密/解密和 `core/features/pdf/pdf_metadata.py` 的元数据读写不计入上述 24 项。可在 24 项菜单迁移完成或单独排期后，评估 `pdf encrypt`、`pdf decrypt`、`pdf metadata`。密码不得放进进程参数或日志；若加入 CLI，应定义安全输入方式并单独验收。

## 5. 目标架构

```text
GUI 控件 ──> GUI 适配层 ──┐
                          ├──> 核心操作 ──> Python 库 / 外部程序
CLI 参数 ──> CLI 适配层 ──┘
```

### 5.1 核心操作层

- 只接收业务参数、路径、可选日志/进度回调和取消查询（统称 `should_cancel`）；不读取 QWidget、不显示对话框、不依赖主窗口状态。
- 对承诺 Qt-free 的操作，不导入 `PyQt6`，不继承 `QObject`，不以 Qt signal 作为唯一结果通道。
- 返回结构化操作结果；文件操作负责报告实际生成的路径，不由 CLI 根据文件名猜测。
- 不负责格式化命令行输出，不读取 `argparse.Namespace`。

### 5.2 GUI 适配层

- 将核心回调桥接到现有 Qt 信号、进度条和横幅。现有 GUI 页面已有 `stop()` 调用点，迁移期间不改为 `should_cancel`，避免一次性改动全部页面。
- 迁移期间保留现有 `on_finished` / Qt signal 的调用形式；只有已有调用者逐个迁移并验证后，才考虑删除旧协议。
- 继续遵守 `TaskRegistry`、工作线程和关窗等待规则；不能因为核心返回值统一而绕过任务登记。

### 5.3 CLI 适配层

- 只负责参数解析、参数到核心调用的映射、取消信号、输出格式和退出码。
- 不导入 `ui/`、`MainWindow` 或 `AppContainer`；避免通过包初始化间接加载 GUI。
- 对每个声明为 **Q0** 的命令增加真实子进程导入测试，断言运行后 `PyQt6` 未进入 `sys.modules`。
- 对每个声明为 **Q1** 的命令增加真实子进程测试，断言未创建 `QApplication` 与主窗口，且退出码与结果结构正确。
- 文件参数通过 argv 列表传递给子进程，不拼接 shell 命令字符串。

### 5.4 Qt 耦合的真实主链与处理顺序

把“Office 基类和 PDF 压缩基类”当成全部 Qt 耦合会严重低估工作量。按依赖深度排序，真正的主链是：

| 层级 | 模块 | 耦合形式 | 影响 |
| --- | --- | --- | --- |
| 根 | `core/external_tools/base.py:8`、`core/external_tools/manager.py:3` | 模块级 `from PyQt6.QtCore import ...` | 只要**导入**这两个模块（或导入取用它们的叶模块）就加载 Qt |
| 中层 | `core/engines/office/base.py`、`core/engines/pdf/base.py` | 继承 `QObject` + `pyqtSignal` | 引擎类无法脱离 Qt 实例化 |
| 叶 | `word_converter.py:5`、`markdown_converter.py:6`、`markdown_pdf_pandoc.py:10`、`libreoffice_converter.py:15` | **模块级** `from core.external_tools.manager import ExternalToolManager`，`__init__` 再取实例 | `import` 该模块即加载 Qt；`__init__` 只是再次取用 |

因此仅修 Office/PDF 两个基类不会让任何命令变成 Q0——只要工具发现仍走 `ExternalToolManager`，Qt 一定被加载。反过来，把这 4 个叶模块的顶层 import 改成按需 import 也无效：`ExternalToolManager` 一旦被取用就必须加载，只是把加载点从 import 挪到调用。

处理顺序（仅在决定把某命令从 Q1 升级到 Q0 时才需要）：

1. 先在 `core/external_tools/` 提供不依赖 Qt 的发现/状态查询门面（同步、无信号、无 `ManagedThread`），GUI 现有的异步信号路径保持不动。
2. 再拆 `BaseOfficeConverter`、`BasePdfCompressor` 的处理循环与信号发布；GUI 用薄适配器把回调转成原有信号。
3. 最后才动功能模块的模块级 import 与 `__init__` 依赖注入。

这是独立工程，须单独立项与验收，不作为本方案默认范围。默认方案接受 Q1，不为 Qt 纯度推迟功能交付。

**同时须明确 Office 后端回退语义**：`core/engines/office/base.py:36-47` 在 `CreateObject` 抛 `OSError`/`COMError` 时自动切换 `LibreOfficeEngine` 并转发其信号，`except` 分支直接 `return`，不使用 `batch_run` 的计数。CLI 必须回答三个问题：

- 是否允许自动回退（建议允许，与 GUI 行为一致）；
- 结果里如何暴露实际使用的后端（建议加入 `data.backend`）；
- 回退时 `succeeded`/`failed` 的来源（LibreOffice 分支的计数来自其自身 `convert` 返回值，与 `batch_run` 语义不同，须在适配层归一）。

## 6. 统一结果与进程契约

### 6.1 操作结果

现有 `core/operation_result.py` 有 `status`、`message`、`outputs`、`succeeded`、`failed` 和 `to_dict()`。该结构适合转换型操作，但图片取色、PDF 元数据读取、重命名预览等会返回非文件数据。

建议在保留现有字段和默认行为的前提下，增加可选结构化 `data`：

```json
{
  "status": "success",
  "message": "提取到 5 种颜色",
  "outputs": [],
  "succeeded": 1,
  "failed": 0,
  "data": {
    "colors": []
  }
}
```

约束：

- `status` 只取 `success`、`failed`、`cancelled`。
- `outputs` 只列已确认存在或由核心写入完成的文件。
- `succeeded` / `failed` 按命令声明的处理单位（文件、页面或条目）计数；处理中途取消的单位不能伪装成完整成功。
- 部分成功仍可保留已生成的输出和计数，同时状态为 `failed`；批处理的退出码非零。
- 取消状态保留此前完成计数及已完成输出；部分输出是否列入结果由该操作的输出契约定义。
- 只有返回非文件数据的操作填充 `data`；空 `data` 在 JSON 中省略，以减少现有 JSON 消费者的兼容风险。
- `message` 面向人类，不得作为脚本解析结构化业务数据的唯一途径。

新增 `data` 是需要实施时确认的公共协议扩展。若实现前发现现有消费者要求严格匹配 JSON 键集合，应先更新兼容测试和文档再启用。

### 6.2 标准输出、错误输出和退出码

| 情况 | JSON 模式 stdout | 人类模式 stdout | stderr | 退出码 |
| --- | --- | --- | --- | ---: |
| 成功 | 单个结果 JSON | 简短结果和输出路径 | 诊断/进度日志 | 0 |
| 运行失败或部分失败 | 单个失败结果 JSON | 错误摘要和可用输出 | 诊断/进度日志 | 1 |
| 用户取消 | 单个 cancelled 结果 JSON | 取消摘要和保留的输出 | 诊断/进度日志 | 130 |
| 参数无效 | 单个失败结果 JSON（`status=failed`，`message` 为 argparse 错误文本） | argparse 用法/错误 | 无（错误文本已进 stdout） | 2 |

参数错误当前**不满足**上述契约：`app/cli.py` 使用标准 `ArgumentParser`，`parse_args()` 失败时直接把用法与错误写入 stderr 并 `sys.exit(2)`，`--json` 完全失效。若要脚本能统一解析，须在实现阶段覆写 `ArgumentParser.error()`（或其 `exit()`）改走 `_emit_result`；此前不得在文档或 README 中声称参数错误也输出 JSON。

同时注意 `_add_json_option()` 用 `default=argparse.SUPPRESS`（`app/cli.py:16-22`），目的是让子命令的 `--json` 不覆盖根命令的 `--json`。改成两层子命令（`pdf compress`）后，`--json` 出现在第一层、第二层还是根层都要重新定义默认值传递，否则会出现“写了 `--json` 却没有 JSON 输出”的静默失败。这是 parser 重构的具体风险点，不是自然延伸。

`--json` 模式 stdout 必须只有最终 JSON；日志不得混入 stdout。Windows 上 JSON 使用 ASCII 转义，保证输出字节可按 UTF-8/ASCII 安全解析。当前 CLI 已按该原则处理，新增命令应复用同一输出函数。

### 6.3 取消

现有核心入口的取消能力**极不统一**。按菜单项逐个核对 23 个可接入项（#24 不接入；#18 无核心入口，另计），分三类：

| 类型 | 菜单项 | 核心入口 | CLI 侧动作 |
| --- | --- | --- | --- |
| **已有 `should_cancel`**（4 项） | #8、#10、#11、#15 | `PDFMerger.merge`、`PDFSplitter.split`、`PDFImageExtractor.extract`、`ImageConverter.convert` | 直接传入取消查询函数 |
| **只有 `stop()`**（12 项） | #1、#3、#5（共用 `BaseOfficeConverter.convert`）、#2、#4、#6、#7、#9、#12、#19、#20、#21 | `BaseOfficeConverter`、`PPTImageExporter`、`DocToDocxConverter`、`WordConverter`、`LibreOfficeFormatConverter`、`GhostscriptCompressor`、`PDFPageRenderer`、`MarkdownConverter`、`PandocMarkdownToPdf`、`TxtConverter` | 适配层把 `stop()` 接到取消事件 || **两者都没有**（6 项） | #13、#14、#16、#17、#22、#23 | `ColorExtractor`、`ImageVectorizer`、`ImageToPdfConverter`、`GeminiWatermarkRemover`、`CodeExtractor`、`BatchRenamer` | **须修改核心代码**新增检查点 |

（#18 无核心入口，抽出后按新实现另定。）

阶段 2 已为 `pdf-compress`（#9）接上取消：`BasePdfCompressor.stop()` 现在除置位 `_is_running` 外还会 `kill()` 当前 `_process`，CLI 侧通过 `_register_stopper()` 在收到 SIGINT 时调用它。理由是 Ghostscript 单文件超时上限 60 秒，纯靠文件边界检查会让 Ctrl+C 最多等满一个 GS 进程；其余 11 项仍是文件边界粒度。

因此“给每项补齐取消”不是参数映射工作：6 项的取消是核心代码改动，须各自立小项并回归。这批入口的实测签名高度一致——`extract(self, root_dir, extensions, output_path, *, on_log=None, on_finished=None)`、`convert(self, ...)`、`execute(self, rename_plan, *, on_log=None, on_progress=None)`——都只有 `on_log`/`on_progress`，没有可中断点，新增 `should_cancel` 属同一手术：在循环入口加检查、在 `on_finished` 前返回取消态。

统一迁移契约：

- 新增取消一律采用 `should_cancel: Callable[[], bool] | None = None` 关键字参数，与现有 4 个入口保持一致。
- 保留各自已有的 `stop()`，GUI 现有调用点不改；CLI 适配层同时支持两种方式，避免一次性改动全部页面。
- 检查点位置：批处理在每个文件/页面/图片进入前检查；单文件操作在打开输入后、写出前各检查一次。
- CLI 捕获 Ctrl+C 后设置取消事件，通过 `should_cancel` 传入；对仅有 `stop()` 的模块，在同一取消事件上注册 `stop()` 调用。
- 长时间子进程须明确如何观察取消和清理子进程；不能留下仍运行的 Ghostscript、Pandoc 或 LibreOffice 进程。
- 不可安全中断的 Office COM 调用需定义其取消粒度；不能宣传即时取消。
- 取消不应删除已完成产物，也不能覆盖未完成输出。
- 末项已经成功完成后才收到的迟到取消，不得把最终状态从成功改成取消。沿用已有 PDF 取消回归语义。

## 7. 命令组织建议

命令分两批引入，**阶段 1 只用根层命令**，避免在 parser 重构未定前引入两层子命令（第 9 节阶段 0 末段）。

```text
# 现有根命令（保持不变）
office-toolkit merge input-a.pdf input-b.pdf --output merged.pdf
office-toolkit split input.pdf "1-3,5" --output parts --json
office-toolkit extract-images input.pdf --output images --json
office-toolkit image-convert input.png --output output.jpg --format JPG

# 阶段 1 新增（根层，与现有命令同级）
office-toolkit image-colors <input> --count 8 --json
office-toolkit image-vectorize <input> --output <svg>
office-toolkit image-to-pdf <inputs...> --output <pdf>
office-toolkit text-extract-code <root-dir> --extensions .py --output <file>
office-toolkit text-txt-to-pdf <inputs...> --output-dir <dir>
office-toolkit files-rename-preview <files...> --template '{index3}_{name}{ext}' --json

# 阶段 2 起新增（分组形式，须先定死 --json 继承规则）
office-toolkit pdf compress <inputs...> --preset ebook
office-toolkit pdf render <inputs...> --output-dir <dir> --dpi 300 --engine pymupdf
office-toolkit text markdown-to-pdf <inputs...> --output-dir <dir>
office-toolkit office libreoffice-convert <inputs...> --to pdf --output-dir <dir>
```

`files rename apply` 不在本轮范围（第 12 节第 5 项：首版不做 plan 文件机制）。

兼容原则：

- 当前 `merge`、`split`、`extract-images`、`image-convert` 命令不删除、不静默改变参数或结果语义。
- 新分组命令与旧根命令可以并存；是否为旧命令增加分组别名，待 parser 设计时决定。
- 输入多文件的命令使用明确的多个路径参数或响应文件；不得依赖 Windows PowerShell 对通配符的自动展开。
- 转换命令显式提供输出目录/文件，或记录稳定、可预测且兼容当前 GUI 的默认输出规则。

参数取值的三个具体约束：

1. **不要用斜杠开头的值**。Ghostscript 的质量档位是 `/ebook`、`/screen`，但 PowerShell 会把 `/ebook` 当成路径或开关解析。CLI 侧改为无斜杠的 `--preset ebook`，由核心补回 `/` 前缀。
2. **`files-rename-preview` 需自行定义目录展开**。`BatchRenamer.preview(self, files: List[str], template: str, start_index: int = 1)` 收的是文件列表而非目录，CLI 须定义是否递归、扩展名过滤与排序规则。`execute(self, rename_plan, *, on_log, on_progress)` 只返回 `Tuple[int, int]`，无回调式完成通知。`apply <plan-file>` 不在本轮范围（第 12 节第 5 项）。
3. **`--json` 的位置在阶段 2 前一次定死**。阶段 1 全是根层命令，现有 `default=argparse.SUPPRESS` 机制已正确；引入两层子命令前须先定死继承规则并补测试（第 6.2 节）。

## 8. 依赖与运行能力矩阵

| 依赖 | 使用功能 | Qt 影响 | 运行能力声明 | 处理要求 |
| --- | --- | --- | --- | --- |
| Pillow / pypdf / FPDF / NumPy | 图像、PDF、文本处理中的相应操作 | 自身不导入 Qt | Python 依赖 | **FPDF 需 `--include-package-data=fpdf`**；当前 CLI 构建缺此项，见 3.1 |
| `assets/`、`config/` 数据目录 | 去水印资源、配置读取 | 自身不导入 Qt | 运行时数据文件 | **CLI 构建当前缺 `--include-data-dir`**，须与主构建对齐（3.1） |
| **PyQt6（经 external_tools）** | 所有需构造 `ExternalToolManager()` 的命令 | **强制加载 Qt**，命令降为 Q1 | 库依赖，非可选 | 唯一可消除途径是提供无 Qt 的发现门面（第 5.4 节），本方案默认不做 |
| **PyQt6（经引擎基类）** | PDF 压缩、Office 转换 | **强制加载 Qt**（`QObject` + `pyqtSignal`） | 库依赖，非可选 | 拆分处理循环与信号发布 |
| vtracer | PNG 转 SVG | 自身不导入 Qt | Python 原生扩展 | **主构建有 `--include-package=vtracer`，CLI 构建没有**；需一并补齐并在产物中实测 |
| Pandoc | Word/Markdown、Markdown/PDF、HTML 高级路径 | 不引入 Qt，但获取路径经 `ExternalToolManager` | 外部程序，缺失时对应命令失败 | 使用既有工具发现能力；失败提示依赖名称和安装/启用方式 |
| Ghostscript | PDF 压缩及可选渲染 | 不引入 Qt，但 `GhostscriptTool` 继承 `ExternalTool` | 外部程序 | 检查可执行文件和资源目录；测试成功、缺失和取消路径 |
| PyMuPDF | PDF 页面渲染 | 自身不导入 Qt | 本机扩展依赖 | **CLI 构建当前未收集 PyMuPDF**；须照主构建把 `pymupdf.mupdf` 降级为字节码并显式补 `--include-module=pymupdf.mupdf` 与 `--include-module=pymupdf._mupdf`，否则 OOM 或漏收 C 扩展 |
| LibreOffice | headless Office 格式转换及部分 PDF 转换 | 不引入 Qt，但获取路径经 `ExternalToolManager` | 外部程序；具备 headless 命令路径，仍需实际验证目标格式 | 传参用 argv；设置超时、捕获 stderr、验证产物存在 |
| Microsoft Office COM | PPT/Word/Excel 转 PDF、Doc 转 Docx、PPT 转图片 | 仅 PPT/Word/Excel 转 PDF 经引擎基类引入 Qt；Doc 转 Docx 与 PPT 转图片为 Q0 | 系统安装与 COM 自动化；CLI 调用不等于无桌面保证 | 仅在明确支持的 Windows 会话实测；保留宏禁用、文档关闭和 COM 清理 |
| 当前系统剪贴板 | 剪贴板助手 | — | 需要当前桌面会话 | 保持 GUI 专属，除非另有交互式 CLI 需求 |

实施前核查 `ExternalToolManager` 的具体发现/安装行为。CLI 不应因为用户调用一次转换就隐式发起网络下载或长时间安装；默认建议只发现可用工具并报告缺失，在线安装若要提供，应是独立、明确的用户命令。

另需注意 `ExternalToolManager` 会读取 `config/` 与 `libs/`（经 `get_data_root()`）。CLI 打包漏收 `config/` 时，工具发现可能静默降级为“未安装”，表现为命令报缺少 Pandoc/Ghostscript 而实际已装——这类失败比直接崩溃更难诊断，必须靠真实产物冒烟而非源码测试发现。

## 9. 分阶段实施路线

阶段划分按“依赖复杂度递增”，而不是按菜单分类。阶段 0 是唯一允许阻塞后续阶段的关卡。

### 阶段 0：冻结清单与契约（阻塞项）

- 对照 `ui/main_window.py:353-386` 的 `category_mapping` 与各页面入口，逐项确认 24 项的完整子操作及参数。
- **确认 Qt 级别与桌面依赖两项标注**。21 个模块的导入断言已完成，#2/#4 另有类级补测（见第 4 节）；阶段 0 仍需补这两项的**实际桌面行为**验证——它们不加载 Qt，但需要 PowerPoint/Word 与桌面会话。
- ~~确认 `PDF 拆分/提取` 页面子操作~~：已定案，该页面只有 `start_split` 一条路径，无其他提取模式（第 12 节「已定案」项）。
- ~~冻结 `data` 字段是否启用~~：已定案为启用（第 12 节第 2 项），实现见 `core/operation_result.py`。
- 冻结 `--json` 的层级规则与参数错误输出方案（第 6.2 节）。
- 按第 6.3 节的三类取消能力，为每一项标注实际取消粒度（可直接传入 / 适配 `stop()` / 需改核心代码）。
- 输出物：一份含 Qt 级别、依赖、阶段归属、取消粒度的定稿矩阵。

阶段 0 的决策项已全部定案（第 12 节）。`--json` 层级规则按以下方式解除阻塞：

- **阶段 1 只加根层命令**（`image-colors`、`image-vectorize`、`image-to-pdf`、`text-extract-code`、`text-txt-to-pdf`、`files-rename-preview`），不引入两层子命令。现有 `_add_json_option()` 的 `default=argparse.SUPPRESS` 机制在单层下已正确，无需改动。
- **两层分组命令推迟到阶段 2**，届时必须先定死 `--json` 的继承规则（根层 / 第一层 / 最终子命令层）并补测试，再写第一个分组命令。
- **参数错误输出 JSON** 属独立增强，不阻塞任何阶段；实现前不得在 README 或帮助文本中声称支持。

这样阶段 1 可以立即开工，而不会把 parser 重构风险提前引入。

### 阶段 1：Q0 纯文件操作

**已完成**（2026-11-13）：

- 补齐 `--include-package=vtracer`、`--include-package-data=fpdf` 两项（本阶段唯一需要的新依赖）。未预装 `pymupdf`（52.9MB，且会重新引入 cc1 OOM 风险）、`comtypes`、`pypinyin`、`pptx`、`docx`、`assets`——它们只服务于后续阶段的命令，按阶段增量补齐。
- 6 条根层命令已实现：`image-colors`、`image-vectorize`、`image-to-pdf`、`text-extract-code`、`text-txt-to-pdf`、`files-rename-preview`。
- 真实 `OfficeToolkit_CLI.exe`（174.5 MB）构建并冒烟：10 条命令全部可用，6 条新命令成功路径 + `image-colors` 缺输入失败路径（退出码 1）全部符合预期，JSON 均为纯 ASCII。冷启动 1122 ms。
- 运行期未加载任何 `Qt6*.dll`（采样验证），但产物内含 `QtCore.pyd`/`QtGui.pyd`（PIL 的 `ImageQt` 被 Nuitka 推断带入）。这是产物冗余而非运行期依赖。
- `tests/test_cli.py` 16 条、`tests/test_operation_result.py` 6 条通过；全量 268 passed + 3 skipped。

范围（均为第 4 节标注 Q0 的项）：图片取色 #13、图片转 PDF #16、PNG 转 SVG #14、代码提取 #22、TXT 转 PDF #21、批量重命名预览 #23，以及已接入项的巩固：#8 合并、#10 拆分、#11 提图、#15 格式转换。

#17 去水印虽为 Q0，但要先抽出批处理核心入口（第 4 节记为「需新建核心入口」），因此归阶段 4，不在本阶段。

不包含 Markdown/HTML #19——它虽只用标准库与 Pandoc，但 `markdown_converter.py:6` 在模块顶层导入 `ExternalToolManager`，属 Q1，归入阶段 2。

每项的工作量按第 6.3 节的三类取消能力区分：已有 `should_cancel` 的只做参数映射；只有 `stop()` 的做适配层桥接；**两者都没有的**（#13 `ColorExtractor`、#14 `ImageVectorizer`、#16 `ImageToPdfConverter`、#22 `CodeExtractor`、#23 `BatchRenamer`）须改核心代码新增检查点，各自立小项与回归。#17 的取消随其批处理入口在阶段 4 一并实现。

不重写算法。CLI 结果由文件/数据真值验证，GUI 原页面信号与提示按原行为回归。

`files rename apply` 的 plan 文件机制、以及目录展开规则，属新增设计（第 7 节），独立于本阶段推进。

### 阶段 2：Q1 前半 —— PDF 与外部工具命令

范围：#9 Ghostscript 压缩、#12 PDF 页面渲染、#20 Markdown 批量转 PDF（`PandocMarkdownToPdf`）、#7 LibreOffice 格式转换（`LibreOfficeFormatConverter`）、#6 Word ↔ Markdown（`WordConverter`）、#19 Markdown ↔ HTML（`MarkdownConverter`）。

前置条件（须先决策，不可跳过）：

- **Qt 分级决策**：接受这些命令为 Q1，还是先做第 5.4 节的 `external_tools` 无 Qt 门面。这个决定直接决定阶段 2 的形状。
- **`BasePdfCompressor` 拆分方案**：压缩命令不是“加参数适配”，而是拆处理循环与信号发布。

不含 #1/#3/#5 的 Office 部分与 #2/#4——它们归阶段 3，因为需要 Office 或桌面会话，与 Qt 级别无关。

执行要求：统一进程超时、stderr 传递、取消后的子进程清理和产物核验。先实测 PyMuPDF 路径，再实测 Ghostscript 路径；工具缺失时给失败结果，不报成功计数。本阶段 6 项都只有 `stop()`（第 6.3 节第二类），CLI 适配层需把取消事件接到 `stop()`，并验证取消后子进程确实被回收。

**完成记录（阶段 2）**

Qt 分级按第 5.4 节默认方案维持 Q1：接受加载 Qt，但不建 `QApplication`、不建主窗口。实测确认 `pyqtSignal.emit` 在无事件循环时同步调用槽，`GhostscriptCompressor` 因此可直接把 `log`/`finished` 接到 CLI 输出。

已落地 6 条命令（`pdf-compress`、`pdf-render`、`text-markdown-batch-pdf`、`office-libreoffice-convert`、`office-word-markdown`、`text-markdown-html`），全部走 `OperationResult` + `--json`。

实测中修掉的三个真实缺陷：

1. **输出目录不存在即失败**：`MarkdownConverter`、`WordConverter`、`LibreOfficeFormatConverter` 的 `-o/--output-dir` 不自建目录，直接写文件报 `FileNotFoundError`。CLI 侧改为在分派前 `os.makedirs(..., exist_ok=True)`——目录创建属 CLI 的参数契约，不该改核心转换器。
2. **`--json` 丢失失败原因**：原先 `--json` 模式下 `on_log` 为 `None`，用户只看到「成功 0 个，失败 1 个」。改为 `_LogCapture` 始终收集日志（非 JSON 模式同时回显到 stderr），失败时取最后一条含错误标记的行追加到 `message`。实测 `text-markdown-batch-pdf` 现在会明确报「找不到 PDF 引擎 'xelatex'」。
3. **`import fitz` 的 deprecation 警告污染 stdout**：PyMuPDF 1.28.2 在 `import fitz` 时向 **stdout** 打印警告，使 `--json` 输出无法解析。改为优先 `import pymupdf as fitz`，回退 `import fitz`。

另修一处核心缺陷（`PDFPageRenderer`）：`render_all` 原先无条件 `fitz.open(pdf_path)`，因此即使指定 `--engine ghostscript` 也依赖 PyMuPDF；且 PyMuPDF 缺失时 `doc` 为 `None` 后仍调用 `doc[page_num]`，报 `AttributeError: 'NoneType' object has no attribute 'open'`。现补 `_count_pages_with_ghostscript()`（用 `pdfpagecount`），纯 GS 路径可独立工作。该方法须把 Windows 路径的反斜杠加倍——PostScript 字符串里反斜杠是转义符，不加倍时 GS 只返回 `ioerror`。

`pdf-render` 的 `--engine` 默认改为 `auto`：优先 PyMuPDF，不可用时回退 Ghostscript，两者都不可用才失败——因为打包产物中的 PyMuPDF 当前不可导入（见第 3.1 节的参数冲突缺陷）。

验证：`tests/test_cli.py` 新增 15 条测试（含 GS-only 渲染、页码范围、目录自建、失败原因透出、引擎回退），全量 `283 passed + 3 skipped`。真实 `OfficeToolkit_CLI.exe`（262 MB）实跑 9 条命令全部 `success`，JSON 全 ASCII 且 StrictUTF-8 可解析。

未完成：`pymupdf` 打包参数冲突未修（主构建同病，需单独立项）；`plugins/manifest.json`、`assets`、`pypinyin`/`pptx`/`docx` 三项依赖收集留待对应阶段。

### 阶段 3：Office COM 命令

范围：#1 PPT 转 PDF、#3 Word 转 PDF、#5 Excel 转 PDF（均 Q1）；#2 PPT 转图片、#4 Doc 转 Docx（Q0，但为桌面依赖）。这五项全部依赖 Office 或桌面会话，与 Qt 级别无关。

- 先定后端策略：是否保留 `core/engines/office/base.py:36-47` 的 Office→LibreOffice 自动回退，以及结果中如何表述实际后端（建议 `data.backend`）。
- LibreOffice 路径先作为可自动化路径验证；Office COM 路径仅在 Windows 且 Office 可用的环境验证。
- `PPT 转图片` 与 `Doc 转 Docx` 实测为 Q0（不加载 Qt），但分别设 `Visible=1`、`Visible=False`；Qt 级别与桌面依赖是两件事，验收时分别记录。
- 全部 Office 命令继续执行宏禁用、文档关闭与 COM 清理约束。
- 5 项都有 `stop()`（`BaseOfficeConverter` 与两个 Q0 转换器），取消在文件边界生效；COM 转换中途不可安全打断，`stop()` 只保证后续文件不再开始，须在帮助与文档中如实说明这一粒度。

### 阶段 4：新建入口、剪贴板决策与发行验收

- **两个需新建核心入口的项在此收口**：
  - **#18 Markdown 转 PDF**：逻辑现内联在 `ui/interfaces/text/markdown_interface.py:364-401`，依赖插件与 `has_pdf_engine`。抽核心函数后才能接 CLI；抽出后须复测 Qt 级别（当前为推定 Q1）。
  - **#17 图片去水印**：`GeminiWatermarkRemover` 只有单文件 `process_image`，需新增批处理入口（供 GUI 页面与 CLI 共用），并确保 `assets/watermark/` 已进 CLI 产物。
- 剪贴板助手默认保持 GUI 专属；如需 CLI，只承诺活动桌面会话中的显式命令。
- 发行验收：`--help` 命令集合检查、代表性纯文件 smoke、系统依赖的可用/缺失双环境验证、README 补齐退出码与 JSON 说明。

阶段可按依赖拆分提交；每阶段只有在核心结果、GUI 回归、CLI 子进程行为及必要发行检查通过后才算完成。

## 10. 验证与验收标准

### 10.1 单项功能

- 有真实输入/输出的成功测试，输出文件可重新打开或由格式解析器验证。
- 缺文件、坏格式、无效参数、无写权限和目标已存在等失败路径有确定结果。
- 批量操作验证成功项、失败项、实际输出路径和部分失败退出码。
- 支持取消的操作验证处理中取消、末项完成后的迟到取消、已完成产物保留以及无孤儿子进程。
- 纯数据操作（取色、重命名预览等）验证 JSON `data` 内容，而非只检查 message 字符串。
- 每个模块按 3.2 的 `on_finished` 签名表写断言：`(ok, msg)` 与 `(success, fail)` 两种形状不能混用同一套校验。

### 10.2 GUI 兼容（按页面清单核对）

| 页面 | 菜单项 | CLI 对应 | 需回归的行为 |
| --- | --- | --- | --- |
| `pdf/pdf_merge_interface.py` | PDF 合并 | `merge` | 完成横幅、失败提示、原子输出 |
| `pdf/pdf_split_interface.py` | PDF 拆分/提取 | `split` | 拆分文件计数、部分失败提示 |
| `pdf/pdf_image_extract_interface.py` | PDF 图片提取 | `extract-images` | 图片计数、子目录结构 |
| `image/image_convert_interface.py` | 图片格式转换 | `image-convert` | 取消计数（`None` 保留）、重试 |
| `pdf/pdf_compress_interface.py` | PDF 压缩 | 待接入 | 信号拆分后横幅仍只发一次 |
| `pdf/pdf_render_interface.py` | PDF 页面渲染 | 待接入 | 引擎切换、取消状态与按钮恢复 |
| `office/office_convert_interface.py` | PPT/Word/Excel 转 PDF | 待接入 | 后端回退提示、宏禁用生效、COM 清理 |
| `office/ppt_image_interface.py` | PPT 转图片 | 待接入 | 双发 `finished` 回归（历史缺陷） |
| `office/doc_to_docx_interface.py` | Doc 转 Docx | 待接入 | 双发 `finished` 回归、输出目录规则 |
| `office/word_markdown_interface.py` | Word ↔ Markdown | 待接入 | Pandoc 缺失提示、双向转换 |
| `office/libreoffice_batch_interface.py` | LibreOffice 格式转换 | 待接入 | 格式支持校验、目标格式映射 |
| `image/color_interface.py` | 图片取色 | 待接入 | 色卡渲染与数量参数 |
| `image/image_vector_interface.py` | PNG 转 SVG | 待接入 | vtracer 参数、池化并发 |
| `image/watermark_remove_interface.py` | 图片去水印 | 需新建入口 | 批处理入口抽出后按钮/计数不变；资源文件缺失提示 |
| `image/image_pdf_interface.py` | 图片转 PDF | 待接入 | 合并/单文件两种模式 |
| `text/markdown_interface.py` | Markdown 转 PDF | 需新建入口 | 插件缺失提示、`has_pdf_engine` 判定 |
| `text/markdown_html_interface.py` | Markdown ↔ HTML | 待接入 | Pandoc 与基础库双路径 |
| `text/markdown_pdf_batch_interface.py` | Markdown 批量转 PDF | 待接入 | 公式/高亮/Template 参数 |
| `text/txt_pdf_interface.py` | TXT 转 PDF | 待接入 | 字体回退与中文乱码提示 |
| `text/code_extract_interface.py` | 代码提取 | 待接入 | 同文件拒绝提示 |
| `utils/batch_rename_interface.py` | 批量重命名 | 待接入 | 预览与应用分离、冲突提示 |

通用要求：原有 Qt 信号或回调按界面现有槽的参数数量与含义触发；成功/部分失败/失败/取消四种终态下进度条、按钮、提示恢复正确；`TaskRegistry` 与关窗等待不受影响。

页面与菜单的对应关系不是 1:1：`office/office_convert_interface.py` 一个页面承载 PPT/Word/Excel 转 PDF 三项；`utils/clipboard_interface.py` 对应 #24，因不接入而不在本表。共 22 个页面覆盖 24 项菜单。

### 10.3 Qt 与运行环境

- 所有声明 **Q0** 的命令由真实子进程执行，断言 `PyQt6` 不在 `sys.modules`。
- 所有声明 **Q1** 的命令由真实子进程执行，断言未创建 `QApplication`/主窗口，且返回码与结果正确。
- 新增或改动的功能模块必须补做导入断言后再更新矩阵，不得沿用旧结论。
- Qt 级别与桌面能力分别记录：Q0/Q1 只描述是否加载 Qt，不描述是否需要桌面。`PPT 转图片`、`Doc 转 Docx` 是 Q0 但桌面依赖的典型例子。
- 能力矩阵目前只有「Qt 级别」一列；桌面依赖写在「状态与运行边界」文字中。实施时若需要机器可读的能力清单，应把桌面依赖提升为独立列，而不是继续塞进自由文本。
- Office COM、剪贴板等桌面能力只在声明的运行环境实测；未实测的场景不标为受支持。
- 外部依赖测试分别覆盖可用和缺失状态；普通 CI 不因无许可证或未安装商业 Office 而假装通过。

### 10.4 发行与文档

- 发布产物中的 `OfficeToolkit_CLI.exe --help` 成功、命令名断言齐全，且 9 条代表性命令在产物中真实执行返回 success（已实现于 `release.yml`）。
- 对每个命令的选项和运行前提更新 README 或用户指南；`BUILD_GUIDE.md` 说明源码与发行版入口。
- README 当前只有 5 行示例（`README.md:71-77`），缺少退出码表与 JSON 结构说明，属必修项。
- 单文件中 Python 依赖和包数据按需显式包含；系统级依赖列为运行前提，不虚称已捆绑。每个新命令合入前，必须核对 3.1 对照表并补对应收集项——`build_nuitka.bat` 的 CLI target 不会自动跟随源码导入。
- 发行验证记录准确的 VERSION、构建产物路径和实际 smoke 结果。

### 10.5 全局完成条件

同时满足以下五条才算本轮完成：

1. 24 项菜单在能力矩阵中均有定稿状态：已接入、待接入（含阶段）、需新建核心入口或不接入；无“待评估”残留。
2. 每一项非“不接入”的命令均有命令帮助、真实核心调用、结果协议和失败路径证据。
3. 每一项都标注并验证了 Qt 级别与桌面依赖两个维度；不存在把 Q1 描述成 Q0 的条目。
4. `OfficeToolkit_CLI.exe` 的发布产物通过全部已接入命令的真实执行（非仅 `--help`）。
5. 第 12 节的 6 项决策已书面定案并回写本文档（已完成）。

口径说明：第 1 条与第 2 条的验收对象不同。第 1 条验收**文档定稿**（矩阵无未决项），第 2 条验收**已实施部分的落地**。当阶段 1–4 尚未全部执行时，允许存在“待接入（阶段 N）”的条目——此时第 2 条只对“已接入”条目生效。全部阶段执行完毕后，第 2 条扩展到全部非“不接入”条目。

这样定义是为了避免两种极端：既不允许“只写结论就算完成”，也不要求文档评审当天就完成全部实现。

## 11. 主要风险及约束

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| Qt 依赖被低估（`external_tools` 模块级导入） | 10 项命令无法满足 Q0，若按 Q0 承诺则验收失败 | 采用 Q0/Q1 分级；已用导入断言固化归属，新增命令需补测 |
| 打包参数自我冲突（`--nofollow-import-to` 与 `--include-module` 同名） | 源码正常而产物缺模块；PyMuPDF 已中招，主构建同样受影响 | 每个新模块合入后用真实产物跑一次该命令，不只跑 `--help` |
| 过早统一回调/信号 | GUI 接收参数变化或重复完成事件 | 保留兼容适配，逐个页面验证，不做一次性全局替换 |
| `--json` 在参数错误时失效 | 脚本无法统一解析，自动化流程中断 | 覆写 `ArgumentParser.error()`；实现前不宣称该能力 |
| 多层子命令破坏 `--json` 继承 | 写了 `--json` 却无 JSON 输出的静默失败 | parser 设计中一次定死层级规则（第 7 节） |
| 结果数据只有 message | 脚本需要解析本地化文字，接口脆弱 | 用可序列化 `data` 返回机器可读值 |
| Office→LibreOffice 回退语义未定 | 计数来源不一致、后端不可见 | 阶段 3 前决定回退策略并加 `data.backend` |
| 外部工具自动发现副作用 | CLI 调用可能卡顿、解压或触网 | 明确发现与安装边界，默认不隐式下载 |
| COM 环境差异 | 命令可启动但转换挂起、弹窗或失败 | 按后端和 Office 类型定义支持环境，不承诺未经验证的无人值守模式 |
| PDF/图片输出覆盖 | 失败或取消损坏旧文件 | 复用原子输出；同路径覆盖明确拒绝或先安全暂存 |
| 批量重命名错误 | 用户文件名发生不可逆变化 | 预览计划、冲突检测、显式 apply 和回归测试 |
| **CLI 构建漏收依赖** | #14 导入失败、#21 字体缺失、#12 渲染不可用、工具发现静默降级为“未安装”、COM 路径导入失败 | 阶段 1 已补 `vtracer`+`fpdf` 并真产物冒烟；其余 8 类按 3.1 对照表随所属阶段补齐，每项必须真产物验证 |
| **18 项缺 `should_cancel`** | 新增命令无法 Ctrl+C 中断，长任务体验差 | 按 6.3 三类矩阵分层派工（12 项桥接 `stop()`、6 项改核心），6 项单独立项。阶段 1 的 6 条命令均属第三类，暂不支持取消 |
| Nuitka 包数据遗漏（其他包） | 源码运行成功而发行命令崩溃 | 对发行二进制做真实命令 smoke 和产物存在性检查 |
| 发行冒烟不校验命令集合 | 命令打包成功但入口缺失 | 已在 `release.yml` 增加命令名断言 + 6 条命令实跑 |

## 12. 已定案事项（阶段 0 已解除阻塞）

以下 6 项已由项目方决定，实施时直接按此执行，不再讨论。阶段 0 已全部解除阻塞：CLI 构建依赖收集与 6 条根层命令均已落地并通过真实产物冒烟（第 9 节阶段 1 完成记录）。

| # | 事项 | 决定 | 依据与影响 |
| ---: | --- | --- | --- |
| 1 | **Qt 分级策略** | **接受 10 项为 Q1**，不为 Qt 纯度推迟功能交付 | 改造成 Q0 需先做 `external_tools` 无 Qt 门面 + 拆两个引擎基类（第 5.4 节），属独立工程。阶段 2 按 Q1 形状推进 |
| 2 | **`OperationResult.data`** | **加**，可选、JSON-safe，空则从 JSON 省略；保留 `data.backend` 位置 | 阶段 1 的 #13 取色、#23 预览必须靠它返回非文件数据。已实现于 `core/operation_result.py` |
| 3 | **Office 回退** | **保留** `core/engines/office/base.py:36-47` 的自动 LibreOffice 回退，并新增 `--backend` 显式覆盖 | 与 GUI 行为一致；结果用 `data.backend` 暴露实际后端，计数在适配层归一（第 5.4 节末段） |
| 4 | **Office 支持边界** | 承诺「**当前登录 Windows 桌面可调用**」；仅对 LibreOffice headless 承诺无桌面 | 不宣称 Office COM 可无人值守。验收按第 10.3 节分别记录 Qt 级别与桌面依赖 |
| 5 | **批量重命名 plan 文件** | **首版不做**。只提供 `files-rename-preview --json` 一条无状态命令 | 目录展开与排序规则随 `preview` 一并定义（第 7 节第 2 条）；`apply` 与 plan 文件机制作为后续独立设计 |
| 6 | **`PDF 拆分/提取` 子操作** | 页面只有 `start_split`（`pdf_split_interface.py:121`）调用 `split(file_path, ranges, output_dir)`（`:138`），无其他提取模式 | #10 按「已接入」处理，无待办 |

**能力矩阵是否增加「桌面依赖」独立列**：决定为**暂不增加**。当前 24 项中只有 #1/#2/#3/#4/#5 与 #24 涉及桌面，#2/#4 的桌面依赖已写进「状态与运行边界」列，可读性足够。若后续需要机器可读清单（如自动生成文档或发布校验），再提升为独立列——届时须同步更新第 10.3 节。

附：PDF 加密/解密与元数据能力（`core/features/pdf/pdf_security.py`、`pdf_metadata.py`）默认不计入本轮 24 项范围，作为独立候选项排期。

## 13. 源码与文档参考

- GUI 菜单与 24 项功能：`ui/main_window.py` 的 `_init_feature_descriptions()`、`createCategoryInterface()`。
- 当前 CLI 和 JSON/退出码：`app/cli.py`、`cli_main.py`、`core/operation_result.py`。
- CLI 构建/打包：`build/build_nuitka.bat`、`build/build_release.bat`、`build/installer.iss`、`.github/workflows/release.yml`。
- 当前命令用法：`README.md`、`docs/BUILD_GUIDE.md`。
- 任务关窗规则：`core/task_registry.py`、`ui/threads.py`。
- 文件输出保护：`core/utils/atomic_output.py`。
- Office 宏安全：`core/utils/office_security.py`。
- 外部工具供给与发现：`core/external_tools/`、`core/tools/package_store.py`、`docs/PLUGIN_GUIDE.md`。

以上路径是方案事实来源。实施阶段若源码结构或调用点与本方案不符，应先更正功能矩阵和方案，再按更新后的事实实施。
