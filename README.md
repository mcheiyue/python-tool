# Office Tool

这是一个基于 PyQt6 和 Fluent Widgets 的多功能办公工具箱，集成了多种文档处理和图像处理功能。

## 功能特性

1.  **PPT 转 PDF**: 批量将 PowerPoint 演示文稿转换为 PDF。
2.  **Word 转 PDF**: 批量将 Word 文档转换为 PDF。
3.  **PDF 合并**: 将多个 PDF 文件合并为一个，支持拖拽排序。
4.  **PDF 压缩**: 使用 Ghostscript 压缩 PDF 文件体积。
5.  **图片取色**: 提取图片中的主色调并生成配色方案 (Hex/RGB)。
6.  **Markdown 转 PDF**: 实时预览 Markdown 并导出为 PDF。
7.  **PNG 转 SVG**: 将位图转换为 SVG 矢量图，适合 Logo 和图标。
8.  **TXT 转 PDF**: 将文本文件批量转换为 PDF，支持自动换行和中文。
9.  **代码提取**: 遍历项目目录，提取指定扩展名的代码文件到一个文本文件中，便于分析。

## 环境要求

*   Windows 10/11 (推荐)
*   Python 3.8+
*   Microsoft Office (Word 和 PowerPoint 功能需要)
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

*   `main.py`: 主程序入口和 UI 实现。
*   `core/`: 核心功能模块。
    *   `ppt_converter.py`: PPT 转 PDF 逻辑。
    *   `word_converter.py`: Word 转 PDF 逻辑。
    *   `pdf_merger.py`: PDF 合并逻辑。
    *   `pdf_compressor.py`: PDF 压缩逻辑 (调用 Ghostscript)。
    *   `color_extractor.py`: 颜色提取逻辑 (KMeans)。
    *   `image_vectorizer.py`: 位图转矢量图逻辑 (vtracer)。
    *   `txt_converter.py`: 文本转 PDF 逻辑。
    *   `code_extractor.py`: 代码提取逻辑。
