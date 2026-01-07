# Office Toolkit

> 🛠️ 基于 PyQt6 的现代化多功能办公工具箱，集成文档转换、PDF处理、图像处理等17+实用功能

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ 核心功能

### 📄 文档转换
- **Office 转 PDF**: 批量转换 Word/Excel/PPT 为 PDF（支持 MS Office 或 LibreOffice）
- **Doc 转 Docx**: 旧版 Word 文档格式升级
- **Markdown 转 PDF**: 实时预览 + 高质量导出（支持数学公式）
- **TXT 转 PDF**: 文本文件转 PDF，支持中文

### 📑 PDF 工具
- **PDF 合并**: 多文件合并，支持拖拽排序
- **PDF 拆分**: 按页面范围灵活拆分
- **PDF 压缩**: Ghostscript 引擎压缩
- **图片提取**: 批量提取 PDF 中的所有图片
- **页面渲染**: 将 PDF 页面渲染为高清图片（支持矢量图形）

### 🖼️ 图像处理
- **格式转换**: JPG/PNG/WEBP/BMP/ICO 互转
- **图片转 PDF**: 多图合并为 PDF
- **PNG 转 SVG**: 位图矢量化
- **取色工具**: 提取主色调配色方案

### 🔧 实用工具
- **批量重命名**: 支持多种模板变量，实时预览，批量处理文件/文件夹
- **剪贴板助手**: 快速预览/保存剪贴板图片，或将本地图片复制到剪贴板
- **PPT 转图片**: 演示文稿每页导出为图片
- **代码提取**: 项目代码整合工具
- **主题切换**: 浅色/深色/跟随系统

---

## 🚀 快速开始

### 环境要求
- **操作系统**: Windows 10/11、Linux、macOS
- **Python**: 3.8+
- **Office 套件**: Microsoft Office 或 LibreOffice（Word/Excel/PowerPoint 转换功能需要）
- **可选组件**: Ghostscript (PDF压缩), Pandoc (Markdown增强), PyMuPDF (PDF页面渲染)

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/python-tool.git
cd python-tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python main.py
```

### 插件安装（可选）

下载 `.mcy` 插件文件并放入 `plugins/` 目录：
- **ghostscript.mcy** - PDF 压缩引擎（约 40MB）
- **pandoc.mcy** - Markdown 增强转换（约 80MB）

程序启动时会自动加载插件，可在"设置"中管理。

---

## 🔌 插件系统

### 什么是 .mcy 插件？
- **加密打包**: AES-256-CBC 加密 + LZMA 压缩
- **按需加载**: 仅在使用时解压，降低内存占用
- **便携部署**: 无需系统安装，放入 `plugins/` 即可

### 插件模式
- **临时模式（推荐）**: 程序退出后自动清理，节省空间
- **持久模式**: 解压到 `libs/` 目录，提升启动速度

详细说明请查看 [插件开发指南](docs/PLUGIN_GUIDE.md)

---

## 📖 文档

- 📘 [用户使用手册](docs/USER_MANUAL.md) - 功能详细使用指南
- 🔧 [API 参考文档](docs/API_REFERENCE.md) - 开发者接口文档
-  [完整更新日志](docs/CHANGELOG.md) - 所有版本更新记录
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md) - 技术架构说明
- 🔨 [构建部署指南](docs/BUILD_GUIDE.md) - Nuitka 编译打包
- 🗺️ [开发路线图](docs/ROADMAP.md) - 未来功能规划

---

## 💡 最近更新

### v1.1.0 (2026-01-06) - 功能增强版
- ✨ 新增 PDF 页面渲染功能（PyMuPDF）
  - 支持 72-600 DPI 高质量渲染
  - 支持 PNG/JPG/WebP 输出格式
  - 支持页面范围选择
  - 支持矢量图形渲染
- ✨ 新增 LibreOffice 备用引擎支持
  - 无需 Microsoft Office 即可转换文档
  - 跨平台支持（Windows/Linux/macOS）
  - 智能引擎自动选择
  - 完全免费开源

### v1.0.1 (2026-01-06) - 代码质量优化
- ✅ 修复 Image 资源泄漏问题（内存优化 5-10%）
- ✅ 新增工具卸载确认对话框
- ✅ 优化异常处理机制（提升错误定位能力 30%）
- ✅ 清理未实现的 OCR 配置

### v1.0.0 (2026-01-05) - 正式发布
- 🎉 启动性能优化（懒加载 + UI 代理机制）
- 🎉 私有加密插件系统 (.mcy 格式)
- 🎉 双模式构建系统（Nuitka + Inno Setup）

[查看完整更新日志](docs/CHANGELOG.md)

---

## 🏗️ 项目架构

```
python-tool/
├── main.py              # 应用入口
├── app/                 # 依赖注入容器
├── core/                # 核心业务逻辑
│   ├── features/        # 业务功能实现（按领域分组）
│   ├── engines/         # 引擎抽象层（PDF/Office）
│   ├── plugins/         # 插件系统
│   ├── external_tools/  # 外部工具管理
│   └── utils/           # 通用工具
├── ui/                  # 用户界面
│   ├── interfaces/      # 功能页面（按领域分组）
│   └── widgets/         # 自定义组件
├── config/              # 配置管理
├── docs/                # 文档
├── build/               # 构建脚本
└── plugins/             # 插件目录
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试 (使用 pytest)
pytest

# 快速编译（开发版）
build/build_dev.bat
```

### 反馈与交流
如果您发现了 Bug 或有新功能建议，欢迎提交 Issue：
- [提交 Bug 报告](https://github.com/your-username/python-tool/issues/new?template=bug_report.md)
- [提交功能建议](https://github.com/your-username/python-tool/issues/new?template=feature_request.md)

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## ⚠️ 注意事项

- Office 转换功能需要安装 **Microsoft Office 或 LibreOffice**（二选一）
  - 优先使用 Microsoft Office（如已安装）
  - 无 MS Office 时自动降级到 LibreOffice
  - LibreOffice 下载：https://www.libreoffice.org/download/
- PDF 压缩功能需要 Ghostscript 插件
- PDF 页面渲染功能需要 PyMuPDF 库（`pip install PyMuPDF>=1.23.0`）
- Markdown 高级功能（数学公式）需要 Pandoc 插件
- 推荐使用便携版插件部署方式

---

<p align="center">
  <sub>如果觉得项目有帮助，请给个 ⭐ Star 支持一下！</sub>
</p>
