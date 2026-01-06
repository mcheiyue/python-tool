# 功能升级实施计划

> 创建时间：2026-01-06
> 版本：v1.1
> 更新：明确集成方式

---

## 📋 升级概览

| 阶段 | 功能 | 优先级 | 复杂度 | 集成方式 |
|------|------|--------|--------|----------|
| **第一阶段** | PyMuPDF - PDF 页面渲染 | ⭐⭐⭐⭐⭐ | 低 | 📦 直接集成（pip 依赖） |
| **第二阶段** | LibreOffice 备用引擎 | ⭐⭐⭐⭐ | 中 | 🔌 外部工具（系统检测） |

### 集成方式说明

| 组件 | 类型 | 方式 | 用户操作 |
|------|------|------|----------|
| **PyMuPDF** | Python 包 | 添加到 requirements.txt | 无需额外安装 |
| **LibreOffice** | 独立程序 | 检测系统安装 | 需用户自行安装 |

> 💡 **注意**：LibreOffice 便携版支持将在后续版本中研究实现

---

## 🚀 第一阶段：PyMuPDF 集成

### 目标
实现"PDF 页面 → 图片"功能，解决当前 pypdf 只能提取嵌入图片的局限。

### 新增能力
- ✅ 将 PDF 任意页面渲染为高清图片
- ✅ 支持自定义 DPI（分辨率）
- ✅ 支持多种输出格式（PNG/JPG/WebP）
- ✅ 批量处理多个 PDF

### 涉及文件

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `requirements.txt` | 添加 PyMuPDF 依赖 |
| 新建 | `core/pdf_page_renderer.py` | 核心渲染模块 |
| 新建 | `ui/interfaces/pdf_render_interface.py` | 用户界面 |
| 修改 | `ui/interfaces/__init__.py` | 注册新界面 |
| 修改 | `app/container.py` | 注册到依赖容器（如需要） |

### 实施步骤

#### 步骤 1：添加依赖
- 在 `requirements.txt` 添加 `PyMuPDF>=1.23.0`

#### 步骤 2：创建核心模块
- 创建 `core/pdf_page_renderer.py`
- 实现 `PDFPageRenderer` 类
- 关键方法：
  - `render_page()` - 渲染单页
  - `render_all()` - 批量渲染
  - `get_page_count()` - 获取页数
- 继承 `QObject`，发出进度信号

#### 步骤 3：创建用户界面
- 创建 `ui/interfaces/pdf_render_interface.py`
- 参考现有 `pdf_image_extract_interface.py` 的结构
- 界面元素：
  - PDF 文件选择区域
  - DPI 选择（72/150/300/600）
  - 输出格式选择（PNG/JPG）
  - 页面范围选择（全部/指定页）
  - 输出目录选择
  - 进度显示和日志

#### 步骤 4：集成到主界面
- 在 `ui/interfaces/__init__.py` 中导出新界面
- 在主窗口中添加导航入口
- 建议放在 "PDF 工具" 分类下

### 验收标准
- [ ] 可以将 PDF 页面渲染为图片
- [ ] 支持自定义 DPI
- [ ] 批量处理正常工作
- [ ] 进度显示正确
- [ ] 错误处理完善

---

## 🔧 第二阶段：LibreOffice 备用引擎

### 目标
为无 Microsoft Office 的用户提供文档转换能力。

### 新增能力
- ✅ 使用 LibreOffice 转换 Office 文档
- ✅ 支持 DOCX/XLSX/PPTX → PDF
- ✅ 自动检测可用引擎并选择最佳方案
- ✅ 跨平台支持（Windows/Linux/Mac）

### 涉及文件

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新建 | `core/external_tools/libreoffice_tool.py` | LibreOffice 检测工具 |
| 新建 | `core/engines/office/libreoffice.py` | LibreOffice 转换引擎 |
| 修改 | `core/external_tools/manager.py` | 注册新工具 |
| 修改 | `core/engines/office/__init__.py` | 导出新引擎 |
| 修改 | `ui/interfaces/word_interface.py` | 添加引擎选择逻辑 |
| 修改 | `ui/interfaces/settings_interface.py` | 显示 LibreOffice 状态 |

### 实施步骤

#### 步骤 1：创建外部工具检测
- 创建 `core/external_tools/libreoffice_tool.py`
- 继承 `ExternalTool` 基类
- 实现检测逻辑：
  - Windows: 检查常见安装路径 + 注册表
  - Linux/Mac: 检查 `soffice` 命令
- 参考现有 `pandoc_tool.py` 的结构

#### 步骤 2：创建转换引擎
- 创建 `core/engines/office/libreoffice.py`
- 继承 `BaseOfficeConverter`（或创建新基类）
- 使用 CLI 方式调用：
  ```
  soffice --headless --convert-to pdf --outdir <dir> <file>
  ```
- 处理转换结果和错误

#### 步骤 3：实现引擎自动选择
- 修改 `word_interface.py`（及其他 Office 界面）
- 检测顺序：MS Office → LibreOffice → 提示安装
- 可选：在设置中允许用户手动选择偏好引擎

#### 步骤 4：更新工具管理器
- 在 `manager.py` 的 `TOOL_REGISTRY` 中注册
- 在设置界面显示 LibreOffice 状态

#### 步骤 5：测试与优化
- 测试无 Office 环境下的转换
- 测试跨平台兼容性
- 优化错误提示信息

### 验收标准
- [ ] 正确检测 LibreOffice 安装
- [ ] 使用 LibreOffice 成功转换文档
- [ ] 引擎自动选择逻辑正常
- [ ] 设置界面显示工具状态
- [ ] 错误处理和用户提示完善

---

## 📊 架构图

### 第一阶段架构
```
用户界面层
└── pdf_render_interface.py  [新建]
        │
        ▼
核心业务层
└── pdf_page_renderer.py  [新建]
        │
        ▼
第三方库
└── PyMuPDF (fitz)  [新增依赖]
```

### 第二阶段架构
```
用户界面层
├── word_interface.py  [修改: 添加引擎选择]
├── excel_interface.py
└── ppt_interface.py
        │
        ▼
引擎层
├── engines/office/word.py      [现有: MS Office]
├── engines/office/libreoffice.py  [新建: LibreOffice]
└── engines/office/base.py      [可能需要调整]
        │
        ▼
外部工具层
├── external_tools/libreoffice_tool.py  [新建]
└── external_tools/manager.py  [修改: 注册工具]
```

---

## ⚠️ 注意事项

### PyMuPDF 相关
1. PyMuPDF 有 AGPL 许可证，商业使用需注意
2. 库体积约 15MB，会增加打包体积
3. 高 DPI 渲染时内存占用较大，建议添加提示

### LibreOffice 相关
1. 当前版本仅支持系统安装的 LibreOffice（便携版后续研究）
2. 需要用户自行安装 LibreOffice
3. CLI 模式下 LibreOffice 第一次启动较慢
4. 不同版本的 LibreOffice 行为可能有差异
5. 需要处理 LibreOffice 进程异常退出的情况
6. Windows 下检测路径：Program Files、注册表
7. Linux/Mac 下检测：soffice 命令

---

## 📝 实施检查清单

### 第一阶段
- [ ] 添加 PyMuPDF 依赖
- [ ] 创建 PDFPageRenderer 核心类
- [ ] 创建用户界面
- [ ] 集成到主窗口
- [ ] 测试各种 PDF 文件
- [ ] 更新文档

### 第二阶段
- [ ] 创建 LibreOfficeTool 检测类
- [ ] 创建 LibreOffice 转换引擎
- [ ] 实现引擎自动选择
- [ ] 更新工具管理器
- [ ] 更新设置界面
- [ ] 跨平台测试
- [ ] 更新文档

---

## 📚 参考资料

- PyMuPDF 官方文档: https://pymupdf.readthedocs.io/
- LibreOffice CLI 参考: https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html
- 项目架构文档: `docs/ARCHITECTURE.md`
- 插件开发指南: `docs/PLUGIN_GUIDE.md`