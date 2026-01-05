# Office Tool

这是一个基于 PyQt6 和 Fluent Widgets 的多功能办公工具箱，集成了多种文档处理和图像处理功能。

## 功能特性

1.  **PPT 转 PDF**: 批量将 PowerPoint 演示文稿转换为 PDF。
2.  **Word 转 PDF**: 批量将 Word 文档转换为 PDF。
3.  **Excel 转 PDF**: 批量将 Excel 工作簿转换为 PDF。
4.  **Doc 转 Docx**: 批量将旧版 Word 文档 (.doc) 转换为新版格式 (.docx)，支持自定义输出目录。
5.  **PDF 合并**: 将多个 PDF 文件合并为一个，支持拖拽排序。
6.  **PDF 压缩**: 使用 Ghostscript 压缩 PDF 文件体积。
7.  **PDF 拆分/提取页面**: 按页面范围（如 "1-5, 8, 10-end"）将 PDF 拆分为新文件。
8.  **PDF 图片提取**: 批量提取 PDF 文档中嵌入的所有图片。
9.  **图片取色**: 提取图片中的主色调并生成配色方案 (Hex/RGB)。
10. **Markdown 转 PDF**: 实时预览 Markdown 并导出为 PDF。**[新功能]** 支持切换内置转换引擎或 **Pandoc** 引擎，支持数学公式、代码高亮，以及深色模式下的白色背景导出优化。
11. **PNG 转 SVG**: 将位图转换为 SVG 矢量图，适合 Logo 和图标。
12. **TXT 转 PDF**: 将文本文件批量转换为 PDF，支持自动换行和中文。
13. **代码提取**: 遍历项目目录，提取指定扩展名的代码文件到一个文本文件中，便于分析。
14. **图片格式转换**: 支持 JPG, PNG, WEBP, BMP, ICO 格式的互转，支持批量处理、质量调节以及图片旋转/翻转功能。
15. **PPT转图片**: 将PPT演示文稿的每一页导出为图片（支持PNG/JPG/BMP）。
16. **图片转PDF**: 将图片合并转换为PDF文件。
17. **设置**: 支持切换应用主题（跟随系统、浅色模式、深色模式）。

## 架构设计

本项目采用分层架构设计，以提高可维护性和扩展性。

*   **配置管理 (Config)**: `config/` 模块提供统一的配置管理，支持默认配置 (`default.json`) 和用户配置 (`config.json`) 的递归合并与分层访问。
*   **依赖注入 (DI)**: `app/container.py` 提供单例应用容器，负责管理全局依赖（如配置加载器、服务实例、插件管理器）的生命周期，实现 UI 与业务逻辑的解耦。
*   **插件系统 (Plugin)**: `core/plugins/` 模块实现了轻量级插件架构，支持动态加载外部工具（如 Pandoc, MathJax, Pygments），实现功能的解耦与按需启用。
*   **引擎抽象 (Engine)**: `core/engines/` 模块定义了业务核心的抽象接口（如 `BasePdfCompressor`），并提供具体的实现（如 `GhostscriptCompressor`）。

## 环境要求

*   Windows 10/11 (推荐)
*   Python 3.8+
*   Microsoft Office (Word, Excel 和 PowerPoint 功能需要)
*   Ghostscript (PDF 压缩功能需要)
*   Pandoc (Markdown 转 PDF 高级功能需要)

## 安装

```bash
pip install -r requirements.txt
```

## 插件使用指南 (Plugin Guide)

### 什么是插件？

本软件采用**插件化架构**，将体积较大的第三方工具（如 Ghostscript、Pandoc）封装为独立的 `.mcy` 插件包。这种设计带来以下优势：

*   **按需下载**: 用户可根据实际需求选择性安装插件，无需下载完整的大体积安装包。
*   **绿色便携**: 插件无需系统安装，只需放入 `plugins` 目录即可使用。
*   **体积优化**: 分发包体积大幅减小，下载和部署更快捷。

### 支持的插件

*   **ghostscript.mcy** - PDF 压缩和处理引擎（用于 PDF 压缩功能，约 40MB）
*   **pandoc.mcy** - 文档格式转换工具（用于 Markdown 高级转换，约 80MB）

### 如何使用插件？

#### 1. 获取插件文件

插件文件将通过以下方式提供（请查看项目主页获取最新下载链接）：
*   GitHub Releases
*   项目文档页面
*   其他官方渠道

**重要**: 仅从官方渠道下载插件，以确保安全性。

#### 2. 安装插件

将下载的 `.mcy` 文件放入程序所在目录的 `plugins` 文件夹：

**安装版**:
```
C:\Program Files\Office Toolkit\
├── OfficeToolkit.exe
├── plugins\
│   ├── ghostscript.mcy  ← 放在这里
│   └── pandoc.mcy       ← 放在这里
└── ...
```

**绿化版**:
```
OfficeToolkit\
├── OfficeToolkit.exe
├── plugins\
│   ├── ghostscript.mcy  ← 放在这里
│   └── pandoc.mcy       ← 放在这里
└── ...
```

#### 3. 启动程序

程序启动时会自动检测 `plugins` 目录下的 `.mcy` 文件，并按需解压使用。

#### 4. 查看插件状态

在软件的 **设置 → 外部工具** 界面可以：
*   查看已安装插件的状态和版本
*   切换插件解压模式（临时/持久）
*   启用/禁用/卸载插件

### 插件模式说明

*   **临时模式（默认推荐）**: 插件在使用时解压到临时目录，程序退出后自动清理，节省磁盘空间。
*   **持久模式**: 插件解压后保留在 `libs` 目录，下次启动无需重复解压，启动速度更快但占用更多空间。

可在"设置"界面切换插件模式。

### 插件加载优先级

当检测到多种安装方式时，程序将按以下优先级加载：

1.  **plugins 目录 (.mcy 插件)** - 最高优先级
2.  **libs 目录 (已解压的插件)**
3.  **环境变量 (PATH)**
4.  **系统安装路径** (如 `C:\Program Files\gs\`)

## 私有加密插件系统 (.mcy) (New)

本软件引入了私有的 **.mcy** 加密插件格式，旨在提供更安全、轻量的组件分发方案。

### 特性
*   **高压缩比**: 采用 LZMA 算法 (Preset 9)，大幅减小组件体积（Ghostscript 可压缩至原大小的 40%）。
*   **安全加密**: 使用 AES-256-CBC 加密标准，保护插件内容的完整性。
*   **智能加载**: 支持 **惰性加载 (Lazy Loading)**，仅在功能被调用时才解压，降低内存占用。
*   **灵活模式**:
    *   **临时模式 (Temporary)**: 用完即焚，软件关闭后自动清理解压文件（默认，节省空间）。
    *   **持久模式 (Persistent)**: 解压后保留在 `libs/` 目录，下次启动直接使用（高性能）。

### 开发者工具
使用 `tools/pack_plugin.py` 可制作 `.mcy` 插件包：
```bash
python tools/pack_plugin.py libs/ghostscript output/ghostscript.mcy --tool-id ghostscript
```

## 运行

```bash
python main.py
```

## 构建与发布 (Building and Distribution)

本项目提供了完整的构建脚本，支持生成高性能的单文件可执行程序和标准的 Windows 安装包。

### 1. 构建环境准备
*   **Python**: 3.8+
*   **Nuitka**: 用于将 Python 代码编译为机器码 (EXE)。
*   **GCC (MinGW64)**: C 编译器，用于 Nuitka 的编译后端。
*   **Inno Setup 6**: 用于制作 Windows 安装程序。

### 2. 执行构建
项目根目录下提供了自动化构建脚本，位于 `build/` 目录：

1.  **编译核心程序**:
    运行 `build/build_nuitka.bat`
    *   使用 Nuitka 进行编译。
    *   自动处理 PyQt6 和 FluentWidgets 的依赖。
    *   生成单文件可执行程序 `dist/OfficeToolkit.exe`。

2.  **开发版快速编译 (Development Build)**:
    运行 `build/build_dev.bat`
    *   使用 `--standalone` 目录模式编译，跳过 Onefile 压缩。
    *   **速度极快**：编译时间缩短 70% 以上，适合开发调试。
    *   **控制台调试**：保留控制台窗口，方便查看实时日志。
    *   输出位置：`dist/dev/main.dist/OfficeToolkit.exe`。

3.  **生成发布包**:
    运行 `build/build_release.bat`
    *   自动调用 Inno Setup 生成安装包 (`.exe`)。
    *   自动打包生成绿化版 (`.zip`)。
    *   输出目录：`release/`。

### 3. 发布版本说明
构建完成后，`release/` 目录下将生成两种格式的分发包：
*   **安装版 (Setup)**: `OfficeToolkit_Setup_v1.0.0.exe`
    *   提供标准的安装向导。
    *   支持创建桌面快捷方式。
    *   包含完整的卸载程序。
*   **绿化版 (Portable)**: `OfficeToolkit_Portable_v1.0.0.zip`
    *   解压即用，无注册表残留。
    *   方便携带到 U 盘或其他电脑使用。

## 注意事项

*   **外部组件 (Ghostscript/Pandoc)**: 推荐使用 **libs 目录便携模式** 部署，避免复杂的环境变量配置。详情见上方说明。
*   **Office 转换**: 需要系统安装有 Microsoft Office，因为工具通过 COM 接口调用本地 Office 组件。
*   **Markdown 转 PDF**: 推荐配置 Pandoc 以获得最佳的渲染效果（包括数学公式支持）和更好的 PDF 输出质量。
*   **TXT 转 PDF**: 默认使用微软雅黑字体 (`msyh.ttc`) 以支持中文。

## 目录结构

*   `main.py`: 应用程序入口。
*   `tools/`: 开发者工具。
    *   `pack_plugin.py`: .mcy 插件打包工具。
*   `app/`: 应用容器与依赖注入。
    *   `container.py`: AppContainer 类。
*   `config/`: 配置管理模块。
    *   `default.json`: 默认配置文件。
    *   `loader.py`: 配置加载器。
*   `core/`: 核心功能模块。
    *   `engines/`: 引擎抽象层。
        *   `pdf/`: PDF 处理引擎。
            *   `base.py`: 抽象基类。
            *   `ghostscript.py`: Ghostscript 实现。
        *   `office/`: Office 处理引擎。
            *   `base.py`: 抽象基类。
            *   `word.py`: Word 转换引擎。
            *   `excel.py`: Excel 转换引擎。
            *   `powerpoint.py`: PPT 转换引擎。
    *   `plugins/`: 插件系统。
        *   `base.py`: 插件基类。
        *   `manager.py`: 插件管理器。
        *   `pandoc_plugin.py`: Pandoc 插件。
        *   `mathjax_plugin.py`: MathJax 插件。
        *   `highlight_plugin.py`: 代码高亮插件。
    *   `utils/`: 通用工具。
        *   `md_normalizer.py`: Markdown 格式规范化工具。
    *   `ppt_converter.py`: PPT 转 PDF 逻辑。
    *   `word_converter.py`: Word 转 PDF 逻辑。
    *   `excel_converter.py`: Excel 转 PDF 逻辑。
    *   `pdf_merger.py`: PDF 合并逻辑。
    *   `pdf_splitter.py`: PDF 拆分逻辑。
    *   `pdf_image_extractor.py`: PDF 图片提取逻辑。
    *   `environment_checker.py`: 运行环境检测工具。
    *   `font_finder.py`: 系统字体查找工具。
    *   `plugin_loader.py`: **[New]** .mcy 插件加载器（解密/解压/管理）。
*   `ui/`: 用户界面模块。
    *   `main_window.py`: 主窗口布局与导航。
    *   `threads.py`: 后台任务线程。
    *   `interfaces/`: 各功能页面界面。
    *   `widgets/`: 自定义可复用控件。
*   `tests/`: 测试文件。

## 未来计划 (Roadmap)

我们将持续迭代更新，计划添加以下实用功能：

### 文档转换与处理
*   **PDF转WORD**: 将PDF文档转换为可编辑的Word文档。
*   **PDF转EXCEL**: 将PDF表格转换为Excel电子表格。
*   **PDF转PPT**: 将PDF转换为PowerPoint演示文稿。
*   **HTML转PDF**: 将HTML网页转换为PDF文档。
*   **WORD转EXCEL**: 将Word文档内容转换为Excel。
*   **EXCEL转WORD**: 将Excel表格转换为Word文档。
*   **WORD转EPUB**: 将Word文档转换为电子书格式。
*   **EPUB转WORD**: 将电子书转换为Word文档。
*   **EPUB转PDF**: 将电子书转换为PDF文档。

### 文档编辑与工具
*   **合并WORD功能**: 将多个Word文档合并为一个。
*   **拆分WORD**: 将一个Word文档拆分为多个文件。
*   **WORD内容批量替换**: 批量替换Word文档中的指定内容。
*   **EXCEL内容批量替换**: 批量替换Excel表格中的指定内容。
*   **添加PDF水印**: 为PDF文件添加水印。
*   **移除PDF水印**: 移除PDF文件中的水印。

### 图片与其他
*   **文档转图片功能**: 将各类文档页面转换为图片。
*   **压缩图片**: 压缩图片体积。
*   **图片批量缩放**: 按固定尺寸或百分比调整图片大小。
*   **图片加水印**: 为图片添加文字或图片水印。
*   **Twain设备调试**: 用于扫描仪等Twain设备的调试工具。

## 更新日志

### 2026-01-04 启动性能与架构优化
*   **启动提速 (Startup Boost)**:
    *   **真·懒加载 (Lazy Loading)**: 重构了核心容器 (`AppContainer`) 和 UI 导航系统，实现了 Office 引擎和功能界面的**完全按需加载**。
    *   **内存优化**: 程序启动时仅加载最小核心框架，不再预加载 `python-docx`、`python-pptx` 等重型依赖，显著降低了内存占用和启动耗时。
    *   **UI 代理机制**: 引入 `UILazyLoader` 组件，所有功能界面均为“点击即加载”，彻底解决了界面初始化卡顿的问题。
    *   **分发优化**: 优化了代码结构，消除了模块间的隐式强耦合，更适合打包为独立可执行文件 (EXE)。

### 2026-01-05 构建系统完善与路径优化
*   **核心路径工具 (`resource_path.py`)**:
    *   新增智能路径解析模块，自动区分开发环境、Onefile 和 Standalone 模式。
    *   `get_app_root()`: 返回 EXE 真实目录（用于配置、外部插件）。
    *   `get_resource_path()`: 返回内部资源路径（用于图标、模板）。
    *   彻底解决了打包后配置无法保存、插件无法加载的问题。
*   **双模式构建系统**:
    *   **发布版 (`build_nuitka.bat`)**: Onefile 模式，生成单文件 EXE（64MB），适合最终分发。
    *   **开发版 (`build_dev.bat`)**: Standalone 目录模式，编译速度快（相比 Onefile 提速 70%+），附带控制台便于调试。
*   **Inno Setup 集成优化**:
    *   `installer.iss` 新增对 `plugins/` 和 `libs/` 的智能打包。
    *   支持安装版、绿化版和便携版三种分发形式的自动生成。
*   **依赖深度清理**:
    *   移除了 `numpy`, `scipy`, `pandas` 等非核心的超大体积数据科学库，显著减小了打包体积。
    *   移除了 `fastapi`, `uvicorn` 等未使用的 Web 框架依赖。
*   **高性能构建系统**:
    *   **Nuitka 编译**: 引入 Nuitka 将 Python 代码编译为本机机器码，大幅提升启动速度和运行效率。
    *   **Inno Setup 集成**: 实现了标准的 Windows 安装包制作流程。
    *   **多格式分发**: 自动化脚本一键生成**安装版 (Installer)** 和 **绿化版 (Portable)**。

### 2026-01-04 Doc 转 Docx
*   **新功能**:
    *   新增 **Doc 转 Docx** 功能，支持批量将旧版 .doc 文件转换为 .docx 格式。
    *   支持自定义输出目录。
    *   **覆盖保护**: 转换前自动检测同名文件，提供弹窗询问覆盖/取消。

### 2026-01-04 组件管理与 UI 优化
*   **组件管理升级**:
    *   支持在 UI 中直接 **启用/禁用** 外部组件（Ghostscript, Pandoc）。
    *   支持 **卸载** 便携版组件（物理删除文件）。
    *   优化了组件状态检测逻辑，禁用状态下不再尝试调用。
*   **UI 体验优化**:
    *   **PDF 压缩界面**：移除复杂的路径配置输入框，改为直观的状态卡片和管理按钮。
    *   **设置界面**：重构外部工具管理卡片，集成启用/禁用/卸载操作按钮。
*   **Bug 修复**:
    *   修复了 `pdf_compress_interface.py` 中缺失 `IconWidget` 导入的问题。
    *   修复了 `manager.py` 中 `ConfigLoader` 调用接口不匹配的问题。

### 2026-01-04 私有加密插件系统 (.mcy)
*   **架构升级**:
    *   **私有格式 (.mcy)**: 设计并实现基于 AES-256-CBC 加密和 LZMA 压缩的私有插件格式，支持完整性校验和版本控制。
    *   **插件加载器 (PluginLoader)**: 实现智能加载器，支持"惰性解压"和"自动清理"，并集成单例模式确保资源高效管理。
    *   **配置化模式**: 支持在设置中切换"临时模式"（退出即焚）和"持久模式"（解压后保留），满足不同用户对空间和性能的需求。
*   **开发者工具**:
    *   新增 `tools/pack_plugin.py`: 提供命令行工具，用于将普通目录打包为加密的 `.mcy` 插件文件。
*   **Bug 修复**:
    *   修复了打包工具在输出目录不存在时的崩溃问题。
    *   修复了 `Ghostscript` 和 `Pandoc` 工具类中配置加载接口调用的兼容性错误。
    *   修复了部分环境下的 `sys` 模块引用错误。

### 2026-01-03 用户体验 (UX) 升级
*   **交互引导优化**:
    *   **拖拽空状态提示**: 全局优化拖拽列表，为空时显示清晰的引导文字，提升易用性。
    *   **参数详解工具提示**: 为 PNG 转 SVG 等复杂功能的关键参数（如采样模式、颜色模式）添加了详细的悬停说明 (Tooltip)，降低学习门槛。
*   **效率工具**:
    *   **快捷键支持**: 引入常用快捷键（`Ctrl+O` 添加, `Ctrl+Enter` 运行, `Delete` 删除, `Ctrl+S` 导出等），大幅提升操作效率。
    *   **结果快速跳转**: 任务完成后提供「打开文件」和「打开所在文件夹」的快捷操作按钮，优化工作流闭环。

### 2026-01-04 插件系统深度重构
*   **能力注册机制 (Capability Registry)**: 
    *   引入基于"能力"的插件注册机制（如 `markdown_to_pdf`），替代基于名称的硬编码调用。
    *   实现 **UI 层解耦**，`MarkdownInterface` 不再直接依赖 `PandocPlugin`，而是请求具备相应能力的任意插件。
    *   **首选插件策略**: 支持通过配置 (`preferred_plugins`) 指定特定能力的首选实现插件。

### 2026-01-04 便携化支持与体验优化
*   **外部组件便携化 (Portable Support)**:
    *   新增 `libs/` 目录支持，实现 Ghostscript 和 Pandoc 的“绿色版”外挂。
    *   **优先加载机制**: 优先扫描 `libs/` 目录下的组件，实现与系统环境的隔离，解决版本冲突问题。
    *   **设置界面升级**: 外部工具管理卡片新增“安装来源”标识（便携版/系统安装）和“打开组件目录”快捷按钮，大幅降低配置门槛。
*   **深度瘦身**:
    *   移除 `PyMuPDF` (约 40MB)，完全迁移至轻量级 `pypdf`。
    *   移除 `pywin32` (约 15MB)，Office 自动化完全通过纯 Python 的 `comtypes` 实现。
    *   修复 `requirements.txt` 中缺失 `pypdf` 依赖的问题。

### 2026-01-03 依赖瘦身与性能优化
*   **依赖瘦身**:
    *   移除冗余依赖 `PyQt6-WebEngine`，大幅减小应用体积（约 100MB+）。
    *   软化 `Pygments` 依赖，不再强制要求安装，缺失时不影响核心功能。
*   **插件系统升级**:
    *   **延迟加载 (Lazy Loading)**: 重构插件加载机制，改为按需加载（Lazy Load），显著提升应用启动速度并降低内存占用。仅在进入相关功能界面（如 Markdown）时才加载对应插件。

### 2026-01-03 Markdown 增强与架构优化
*   **Markdown 转 PDF 升级**:
    *   引入 **Pandoc** 集成，大幅提升 PDF 导出质量，支持数学公式（MathJax）和复杂排版。
    *   实现**深色模式下的智能导出**：预览跟随主题，导出 PDF 自动切换为白底黑字。
    *   添加 **Markdown 格式自动规范化** (`md_normalizer`)，智能修复标题格式，提高解析容错率。
*   **架构优化**:
    *   引入 **插件化架构** (`core/plugins/`)，实现 Pandoc、MathJax 等外部工具的解耦管理。
    *   实现 **WorkerThread 通用线程模型**，解决耗时任务（如 Pandoc 转换）导致的主线程 UI 卡死问题。
    *   优化 **依赖注入**，将 `PluginManager` 纳入 `AppContainer` 统一管理，消除冗余实例化。
*   **UI 体验**: 优化 Markdown 编辑器样式，添加导出进度提示和操作反馈。

### 2026-01-03 架构重构更新
*   **UI 重构**: 完成 `PDFCompressInterface` 的重构，完全接入 `AppContainer` 和 `GhostscriptCompressor`，移除对旧版逻辑的直接依赖。
*   **代码清理**: 移除不再使用的 `core/pdf_compressor.py`，业务逻辑已完整迁移至 `core/engines/pdf/ghostscript.py`。
*   **引擎抽象**: 引入 `core/engines` 模块，实现 PDF 压缩功能的抽象化（Strategy Pattern），方便未来扩展 OCR 和其他 PDF 引擎。
*   **配置管理**: 引入 `ConfigLoader`，支持分层配置和 JSON 配置存储。
*   **依赖注入**: 引入 `AppContainer`，实现全局依赖管理。
*   **性能优化**: 优化 `EnvironmentChecker`，增加缓存机制，避免重复扫描系统路径。
*   **Office 引擎重构**: 将 Word/PPT/Excel 转换逻辑重构为基于模板方法模式的 `BaseOfficeConverter` 及其子类，消除了大量重复代码并统一了接口。
*   **Bug 修复**: 修复了 `core/engines/pdf/base.py` 中 QObject 和 ABC 的元类冲突，增强了稳定性。
