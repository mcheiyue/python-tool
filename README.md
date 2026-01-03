# Office Tool

这是一个基于 PyQt6 和 Fluent Widgets 的多功能办公工具箱，集成了多种文档处理和图像处理功能。

## 功能特性

1.  **PPT 转 PDF**: 批量将 PowerPoint 演示文稿转换为 PDF。
2.  **Word 转 PDF**: 批量将 Word 文档转换为 PDF。
3.  **Excel 转 PDF**: 批量将 Excel 工作簿转换为 PDF。
4.  **PDF 合并**: 将多个 PDF 文件合并为一个，支持拖拽排序。
5.  **PDF 压缩**: 使用 Ghostscript 压缩 PDF 文件体积。
6.  **PDF 拆分/提取页面**: 按页面范围（如 "1-5, 8, 10-end"）将 PDF 拆分为新文件。
7.  **PDF 图片提取**: 批量提取 PDF 文档中嵌入的所有图片。
8.  **图片取色**: 提取图片中的主色调并生成配色方案 (Hex/RGB)。
9.  **Markdown 转 PDF**: 实时预览 Markdown 并导出为 PDF。
10. **PNG 转 SVG**: 将位图转换为 SVG 矢量图，适合 Logo 和图标。
11. **TXT 转 PDF**: 将文本文件批量转换为 PDF，支持自动换行和中文。
12. **代码提取**: 遍历项目目录，提取指定扩展名的代码文件到一个文本文件中，便于分析。
13. **图片格式转换**: 支持 JPG, PNG, WEBP, BMP, ICO 格式的互转，支持批量处理、质量调节以及图片旋转/翻转功能。
14. **PPT转图片**: 将PPT演示文稿的每一页导出为图片（支持PNG/JPG/BMP）。
15. **图片转PDF**: 将图片合并转换为PDF文件。
16. **设置**: 支持切换应用主题（跟随系统、浅色模式、深色模式）。

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

## 环境要求

*   Windows 10/11 (推荐)
*   Python 3.8+
*   Microsoft Office (Word, Excel 和 PowerPoint 功能需要)
*   Ghostscript (PDF 压缩功能需要)

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 注意事项

*   **PDF 压缩**: 需要安装 Ghostscript (gswin64c.exe)，并在软件界面中指定其路径。
*   **Office 转换**: 需要系统安装有 Microsoft Office，因为工具通过 COM 接口调用本地 Office 组件。
*   **TXT 转 PDF**: 默认使用微软雅黑字体 (`msyh.ttc`) 以支持中文。

## 目录结构

*   `main.py`: 主程序入口。
*   `core/`: 核心功能模块。
    *   `ppt_converter.py`: PPT 转 PDF 逻辑。
    *   `word_converter.py`: Word 转 PDF 逻辑。
    *   `excel_converter.py`: Excel 转 PDF 逻辑。
    *   `pdf_merger.py`: PDF 合并逻辑。
    *   `pdf_compressor.py`: PDF 压缩逻辑 (调用 Ghostscript)。
    *   `pdf_splitter.py`: PDF 拆分逻辑。
    *   `pdf_image_extractor.py`: PDF 图片提取逻辑。
    *   `color_extractor.py`: 颜色提取逻辑 (KMeans)。
    *   `image_converter.py`: 图片格式转换逻辑。
    *   `image_vectorizer.py`: 位图转矢量图逻辑 (vtracer)。
    *   `txt_converter.py`: 文本转 PDF 逻辑。
    *   `code_extractor.py`: 代码提取逻辑。
    *   `environment_checker.py`: 运行环境检测工具。
    *   `font_finder.py`: 系统字体查找工具。
*   `ui/`: 用户界面模块。
    *   `main_window.py`: 主窗口布局与导航。
    *   `threads.py`: 后台任务线程。
    *   `interfaces/`: 各功能页面界面。
    *   `widgets/`: 自定义可复用控件。
*   `tests/`: 测试文件。
