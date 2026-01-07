# Office Toolkit 技术架构深度审查与规划方案

> 文档版本：v1.0  
> 审查日期：2026-01-06  
> 审查范围：插件系统架构、现有插件集成、功能扩展规划

---

## 📋 目录

1. [执行摘要](#执行摘要)
2. [插件架构深度审计](#一插件架构深度审计)
3. [现有插件赋能分析](#二现有插件赋能分析)
4. [原生轻量级功能扩展规划](#三原生轻量级功能扩展规划)
5. [实施路线图](#四实施路线图)
6. [附录：架构图](#附录架构图)

---

## 执行摘要

本次技术审查对 Office Toolkit 项目进行了全面的架构分析。项目采用**分层架构设计**，具备良好的模块化和可扩展性。核心发现如下：

### 架构健康度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 插件生命周期管理 | ⭐⭐⭐⭐ | 完整的加载/卸载/缓存机制 |
| 接口解耦程度 | ⭐⭐⭐⭐⭐ | 依赖注入 + 策略模式，高度解耦 |
| 异常处理机制 | ⭐⭐⭐ | 基础异常处理，缺乏沙箱隔离 |
| 性能优化 | ⭐⭐⭐⭐ | 懒加载机制成熟，启动速度优化良好 |

### 关键建议

1. **增强插件隔离**：引入进程级沙箱机制
2. **统一事件总线**：建立跨模块通信标准
3. **深化插件集成**：三个现有插件可与 8 个核心业务流程集成
4. **扩展 5 项原生功能**：无需引入大型库即可实现

---

## 一、插件架构深度审计

### 1.1 当前架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    UI Layer (PyQt6)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ MainWindow  │  │ Interfaces  │  │  Widgets    │         │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘         │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                Application Layer                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              AppContainer (DI 容器)                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ConfigLoader │  │PluginMgr   │  │ExternalToolMgr│  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Plugin System                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  PluginLoader   │  │ ExternalTools   │                  │
│  │  (.mcy 解密)     │  │  (GS/Pandoc/LO) │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                            │
│           ▼                    ▼                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              libs/.temp/ (临时解压目录)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 插件生命周期管理分析

#### 1.2.1 加载机制

**当前实现** ([`core/plugin_loader.py`](core/plugin_loader.py:73))：

```python
def extract_plugin(self, mcy_path, persistent=False):
    # 1. 缓存检查 - 避免重复解压
    if mcy_path in self._extracted_cache:
        return self._extracted_cache[mcy_path]
    
    # 2. 解密流程: AES-256-CBC -> LZMA 解压 -> TAR 解包
    # 3. 根据模式选择目标目录 (临时/持久)
    # 4. 缓存结果并返回
```

**评估**：
- ✅ **优点**：
  - 缓存机制避免重复解压，性能友好
  - 支持临时/持久两种部署模式
  - AES-256 加密保护插件完整性
  
- ⚠️ **风险点**：
  - 解密密钥硬编码在源码中 ([`core/plugin_loader.py:15`](core/plugin_loader.py:15))
  - 缺乏插件签名验证机制
  - TAR 解包时未做路径穿越检查 (`tar.extractall` 存在安全隐患)

**改进建议**：

```python
# 建议增加路径安全检查
def _safe_extract(self, tar, target_base):
    for member in tar.getmembers():
        # 防止路径穿越攻击
        abs_path = os.path.abspath(os.path.join(target_base, member.name))
        if not abs_path.startswith(os.path.abspath(target_base)):
            raise SecurityError(f"Path traversal detected: {member.name}")
    tar.extractall(path=target_base)
```

#### 1.2.2 卸载机制

**当前实现** ([`core/external_tools/manager.py:96`](core/external_tools/manager.py:96))：

```python
def uninstall_tool(self, name: str) -> bool:
    tool = self.get_tool(name)
    if tool and hasattr(tool, 'uninstall'):
        success = tool.uninstall()
        if success:
            self.disable_tool(name)  # 卸载后自动禁用
        return success
```

**评估**：
- ✅ 卸载后自动禁用，防止自动重新解压
- ✅ 安全检查：仅允许卸载便携版（[`ghostscript_tool.py:173`](core/external_tools/ghostscript_tool.py:173)）
- ⚠️ 缺少卸载前的依赖检查（可能影响正在使用该插件的功能）

#### 1.2.3 初始化机制

**当前实现** ([`core/plugin_loader.py:30`](core/plugin_loader.py:30))：

```python
def _init(self):
    atexit.register(self.cleanup)  # 注册退出清理
    self._clean_stale_temps()       # 清理残留临时目录
```

**评估**：
- ✅ 使用 `atexit` 确保程序退出时清理临时文件
- ✅ 启动时清理上次异常退出遗留的临时目录
- ⚠️ 多实例运行时可能相互影响（虽有 Windows 文件锁保护）

### 1.3 宿主与插件通信接口分析

#### 1.3.1 当前通信模式

项目采用**直接调用模式**，通过 [`ExternalToolManager`](core/external_tools/manager.py:20) 作为中介：

```
┌───────────────┐     get_tool()      ┌──────────────────┐
│   Feature     │ ──────────────────► │ ExternalToolMgr  │
│   Module      │                     │                  │
└───────────────┘                     └────────┬─────────┘
                                               │
                                               ▼
                                      ┌──────────────────┐
                                      │   ExternalTool   │
                                      │   (GS/Pandoc)    │
                                      └──────────────────┘
```

**代码示例** ([`markdown_converter.py:22`](core/features/text/markdown_converter.py:22))：

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.pandoc_tool = ExternalToolManager().get_tool("pandoc")
```

**评估**：
- ✅ **解耦程度高**：功能模块不直接依赖具体工具实现
- ✅ **单例模式**：全局唯一的工具管理器
- ⚠️ **缺乏事件通知**：工具状态变化时，依赖方无法主动感知

#### 1.3.2 信号机制

项目使用 PyQt6 信号进行状态通知 ([`manager.py:7`](core/external_tools/manager.py:7))：

```python
class ToolSignals(QObject):
    tool_status_changed = pyqtSignal(str)  # tool_name
```

**评估**：
- ✅ 使用 Qt 信号槽机制，符合框架设计
- ⚠️ 信号粒度较粗，仅传递工具名称

**改进建议**：扩展信号携带更多上下文

```python
class ToolSignals(QObject):
    tool_status_changed = pyqtSignal(str, str, dict)  # name, event_type, details
    # event_type: 'installed', 'uninstalled', 'enabled', 'disabled', 'error'
```

### 1.4 异常处理与沙箱隔离分析

#### 1.4.1 当前异常处理

**外部工具调用** ([`ghostscript.py:87`](core/engines/pdf/ghostscript.py:87))：

```python
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, ...)
stdout, stderr = process.communicate()

if process.returncode == 0:
    success += 1
else:
    err_msg = stderr.decode('gbk', errors='ignore')
    self.log.emit(f"❌ 失败: {err_msg}")
```

**评估**：
- ✅ 捕获子进程输出，记录错误信息
- ✅ 使用 `errors='ignore'` 处理编码问题
- ⚠️ **无超时机制**：外部工具挂起会阻塞主程序
- ⚠️ **无资源限制**：无法防止外部工具耗尽系统资源

#### 1.4.2 沙箱隔离现状

**当前状态**：❌ 无沙箱隔离

外部工具以当前用户权限运行，可访问：
- 所有用户文件
- 网络资源
- 系统注册表（Windows）

**改进建议**：

```python
# 方案 A：超时控制 (轻量级)
import signal

def run_with_timeout(cmd, timeout=60):
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True)
        return result
    except subprocess.TimeoutExpired:
        raise PluginTimeoutError(f"Plugin execution exceeded {timeout}s")

# 方案 B：进程隔离 (中等复杂度)
# 使用 Windows Job Objects 或 Linux cgroups 限制资源
```

### 1.5 循环依赖风险分析

#### 1.5.1 模块依赖图

```
main.py
    └── AppContainer
            ├── ConfigLoader
            ├── PluginManager (未实际使用)
            └── ExternalToolManager
                    ├── GhostscriptTool
                    │       └── PluginLoader (惰性加载)
                    ├── PandocTool
                    │       └── PluginLoader (惰性加载)
                    └── LibreOfficeTool (系统检测)
```

**评估**：
- ✅ **无循环依赖**：依赖方向单一，从上到下
- ✅ **惰性加载**：避免启动时加载所有模块
- ⚠️ [`GhostscriptCompressor`](core/engines/pdf/ghostscript.py:11) 直接导入 `AppContainer`，形成隐式依赖

### 1.6 性能瓶颈分析

#### 1.6.1 启动性能

**优化措施**：
- ✅ UI 懒加载 ([`lazy_loader.py`](core/utils/lazy_loader.py:6))
- ✅ 插件按需解压（首次使用时解压）
- ✅ 配置分层加载（默认配置 + 用户覆盖）

**实测数据**（来自架构文档）：
- 启动速度提升 **60%+**
- 初始内存占用减少 **40%+**

#### 1.6.2 运行时性能

**潜在瓶颈**：
1. **LZMA 解压**：首次加载大型插件（如 Ghostscript ~50MB）可能需要数秒
2. **COM 初始化**：Office 引擎每次启动需初始化 COM 环境

**优化建议**：
- 预解压模式：在空闲时后台解压常用插件
- COM 连接池：复用 Office 应用实例

---

## 二、现有插件赋能分析

### 2.1 插件概览

| 插件名 | 类型 | 当前用途 | 集成深度 |
|--------|------|----------|----------|
| Ghostscript | PDF 处理引擎 | PDF 压缩 | 单一功能 |
| Pandoc | 文档转换器 | Markdown ↔ HTML | 部分集成 |
| LibreOffice | 办公套件 | Office 降级备选 | 降级方案 |

### 2.2 Ghostscript 赋能策略

#### 2.2.1 当前使用场景

- **PDF 压缩** ([`pdf_compress_interface.py`](ui/interfaces/pdf/pdf_compress_interface.py))

#### 2.2.2 可扩展集成点

```
┌─────────────────────────────────────────────────────────────┐
│                  Ghostscript 能力矩阵                        │
├─────────────────────────────────────────────────────────────┤
│  当前集成 ●                                                  │
│  ├── PDF 压缩 (已实现)                                       │
│                                                             │
│  建议集成 ○                                                  │
│  ├── PDF → 图片渲染 (取代/增强现有 pdf_page_renderer)        │
│  ├── PDF 灰度化 (文档打印优化)                               │
│  ├── PDF 页面旋转/裁剪                                       │
│  └── PostScript/EPS 处理                                    │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.3 集成方案：PDF 高清渲染

**业务价值**：当前 [`pdf_page_renderer.py`](core/features/pdf/pdf_page_renderer.py) 使用 PyMuPDF，Ghostscript 可提供更高 DPI 输出

**技术实现**：

```python
# core/features/pdf/pdf_gs_renderer.py
class GhostscriptRenderer:
    def render_page(self, pdf_path, page_num, dpi=300, output_format='png'):
        gs_path = ExternalToolManager().get_tool("ghostscript").get_path()
        cmd = [
            gs_path,
            "-dNOPAUSE", "-dBATCH",
            "-sDEVICE=png16m",  # 或 pngalpha 支持透明
            f"-r{dpi}",
            f"-dFirstPage={page_num}",
            f"-dLastPage={page_num}",
            f"-sOutputFile={output_path}",
            pdf_path
        ]
        subprocess.run(cmd, check=True)
```

**挂载点**：[`ui/interfaces/pdf/pdf_render_interface.py`](ui/interfaces/pdf/pdf_render_interface.py) - 添加"使用 Ghostscript 高清渲染"选项

### 2.3 Pandoc 赋能策略

#### 2.3.1 当前使用场景

- **Markdown → HTML** ([`markdown_converter.py:212`](core/features/text/markdown_converter.py:212))
- **HTML → Markdown** ([`markdown_converter.py:238`](core/features/text/markdown_converter.py:238))

#### 2.3.2 可扩展集成点

```
┌─────────────────────────────────────────────────────────────┐
│                    Pandoc 能力矩阵                           │
├─────────────────────────────────────────────────────────────┤
│  当前集成 ●                                                  │
│  ├── Markdown → HTML                                        │
│  └── HTML → Markdown                                        │
│                                                             │
│  建议集成 ○                                                  │
│  ├── Markdown → PDF (带数学公式、代码高亮)                   │
│  ├── Markdown → DOCX                                        │
│  ├── DOCX → Markdown (增强现有 Word ↔ MD 功能)              │
│  ├── LaTeX → PDF                                            │
│  └── reStructuredText 支持                                  │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3.3 集成方案：Markdown → PDF（数学公式支持）

**业务价值**：当前 [`markdown_interface.py`](ui/interfaces/text/markdown_interface.py) 的 PDF 导出缺乏数学公式渲染能力

**技术实现**：

```python
# core/features/text/markdown_pdf_pandoc.py
class PandocMarkdownToPdf:
    def convert(self, md_path, pdf_path, options=None):
        pandoc_path = ExternalToolManager().get_tool("pandoc").get_path()
        
        cmd = [
            pandoc_path,
            md_path,
            "-o", pdf_path,
            "--pdf-engine=xelatex",  # 或 wkhtmltopdf
            "--highlight-style=tango",
            "-V", "geometry:margin=1in",
            "-V", "mainfont=Microsoft YaHei",  # 中文支持
        ]
        
        # 数学公式支持
        if options.get('math', True):
            cmd.extend(["--mathjax"])
        
        subprocess.run(cmd, check=True)
```

**挂载点**：[`markdown_interface.py`](ui/interfaces/text/markdown_interface.py) - 增加"使用 Pandoc 导出 PDF"选项

#### 2.3.4 集成方案：增强 Word ↔ Markdown

**业务价值**：当前 [`word_markdown_interface.py`](ui/interfaces/office/word_markdown_interface.py) 使用基础库，格式保真度有限

**技术实现**：

```python
# core/features/office/word_markdown_pandoc.py
class PandocWordMarkdownConverter:
    def docx_to_markdown(self, docx_path, md_path):
        cmd = [
            pandoc_path,
            docx_path,
            "-f", "docx",
            "-t", "gfm",  # GitHub Flavored Markdown
            "-o", md_path,
            "--extract-media=./media",  # 提取图片
            "--wrap=none"
        ]
        subprocess.run(cmd, check=True)
    
    def markdown_to_docx(self, md_path, docx_path, template=None):
        cmd = [
            pandoc_path,
            md_path,
            "-o", docx_path,
        ]
        if template:
            cmd.extend(["--reference-doc", template])
        subprocess.run(cmd, check=True)
```

### 2.4 LibreOffice 赋能策略

#### 2.4.1 当前使用场景

- **Office 引擎降级备选** ([`container.py:73`](app/container.py:73))

#### 2.4.2 可扩展集成点

```
┌─────────────────────────────────────────────────────────────┐
│                  LibreOffice 能力矩阵                        │
├─────────────────────────────────────────────────────────────┤
│  当前集成 ●                                                  │
│  └── Word/Excel/PPT → PDF (作为 MS Office 降级方案)          │
│                                                             │
│  建议集成 ○                                                  │
│  ├── 批量格式转换 (ODT↔DOCX, ODS↔XLSX)                      │
│  ├── PDF → 可编辑文档 (PDF → ODT → DOCX)                     │
│  ├── 文档模板渲染 (邮件合并)                                 │
│  └── 无头模式批处理 (--headless)                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4.3 集成方案：批量格式转换

**业务价值**：支持开源格式与 MS Office 格式互转，满足兼容性需求

**技术实现**：

```python
# core/features/office/libreoffice_converter.py
class LibreOfficeConverter:
    def convert(self, input_path, output_format, output_dir=None):
        """
        通用格式转换
        :param output_format: 'pdf', 'docx', 'odt', 'xlsx', 'ods', 'pptx', 'odp'
        """
        lo_tool = ExternalToolManager().get_tool("libreoffice")
        soffice_path = lo_tool.get_path()
        
        output_dir = output_dir or os.path.dirname(input_path)
        
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to", output_format,
            "--outdir", output_dir,
            input_path
        ]
        subprocess.run(cmd, check=True)
```

### 2.5 插件集成总结

```
┌─────────────────────────────────────────────────────────────────────┐
│                      插件 × 业务流程 集成矩阵                         │
├─────────────────────┬─────────────┬─────────────┬───────────────────┤
│ 业务流程            │ Ghostscript │   Pandoc    │   LibreOffice     │
├─────────────────────┼─────────────┼─────────────┼───────────────────┤
│ PDF 压缩            │     ●       │             │                   │
│ PDF 渲染            │     ○       │             │                   │
│ Markdown → PDF      │             │     ○       │                   │
│ Markdown → HTML     │             │     ●       │                   │
│ Word ↔ Markdown     │             │     ○       │                   │
│ Office → PDF        │             │             │     ●(降级)        │
│ 格式互转            │             │             │     ○             │
│ 文档模板渲染        │             │     ○       │     ○             │
├─────────────────────┴─────────────┴─────────────┴───────────────────┤
│ ● = 已集成   ○ = 建议集成                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、原生轻量级功能扩展规划

### 3.1 设计原则

- ❌ **禁止**引入大型第三方库（如 TensorFlow、OpenCV 完整版）
- ✅ **允许**使用 Python 标准库
- ✅ **允许**使用已有轻量依赖（PIL/Pillow、pypdf、markdown）
- ✅ **优先**使用原生算法实现

### 3.2 功能扩展方案

#### 3.2.1 📊 PDF 元数据编辑器

**痛点**：无法查看/编辑 PDF 的标题、作者、关键词等元数据

**技术方案**：

```python
# core/features/pdf/pdf_metadata.py
from pypdf import PdfReader, PdfWriter

class PDFMetadataEditor:
    def read_metadata(self, pdf_path) -> dict:
        reader = PdfReader(pdf_path)
        return dict(reader.metadata) if reader.metadata else {}
    
    def write_metadata(self, pdf_path, output_path, metadata: dict):
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        writer.add_metadata({
            '/Title': metadata.get('title', ''),
            '/Author': metadata.get('author', ''),
            '/Subject': metadata.get('subject', ''),
            '/Keywords': metadata.get('keywords', ''),
            '/Creator': 'Office Toolkit',
        })
        
        with open(output_path, 'wb') as f:
            writer.write(f)
```

**依赖**：`pypdf`（已有）

**可行性**：⭐⭐⭐⭐⭐ 完全可行，无需新增依赖

---

#### 3.2.2 🔐 PDF 加密/解密

**痛点**：无法为 PDF 添加密码保护或解除密码

**技术方案**：

```python
# core/features/pdf/pdf_security.py
from pypdf import PdfReader, PdfWriter

class PDFSecurity:
    def encrypt(self, pdf_path, output_path, user_password, owner_password=None):
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        writer.encrypt(
            user_password=user_password,
            owner_password=owner_password or user_password,
            permissions_flag=0b1111111111000000  # 禁止打印/复制
        )
        
        with open(output_path, 'wb') as f:
            writer.write(f)
    
    def decrypt(self, pdf_path, output_path, password):
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            reader.decrypt(password)
        
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        with open(output_path, 'wb') as f:
            writer.write(f)
```

**依赖**：`pypdf`（已有）

**可行性**：⭐⭐⭐⭐⭐ 完全可行

---

#### 3.2.3 📝 批量文件重命名引擎

**痛点**：用户经常需要批量重命名导出的文件

**技术方案**：

```python
# core/features/utils/batch_rename.py
import os
import re
from datetime import datetime

class BatchRenamer:
    """
    支持模板变量:
    - {name}: 原文件名（不含扩展名）
    - {ext}: 扩展名
    - {index}: 序号 (01, 02, ...)
    - {date}: 日期 (YYYYMMDD)
    - {time}: 时间 (HHMMSS)
    """
    
    def preview(self, files: list, template: str, start_index=1) -> list:
        """预览重命名结果"""
        results = []
        for i, path in enumerate(files):
            new_name = self._apply_template(path, template, start_index<think>
用户要求我从截断处继续输出。我需要继续编写技术方案文档，从批量文件重命名引擎的代码处继续。

让我继续完成这个文档的剩余部分。
</think>
<write_to_file>
<path>plans/technical_architecture_review.md</path>
<content>
# Office Toolkit 技术架构深度审查与规划方案

> 文档版本：v1.0  
> 审查日期：2026-01-06  
> 审查范围：插件系统架构、现有插件集成、功能扩展规划

---

## 📋 目录

1. [执行摘要](#执行摘要)
2. [插件架构深度审计](#一插件架构深度审计)
3. [现有插件赋能分析](#二现有插件赋能分析)
4. [原生轻量级功能扩展规划](#三原生轻量级功能扩展规划)
5. [实施路线图](#四实施路线图)
6. [附录：架构图](#附录架构图)

---

## 执行摘要

本次技术审查对 Office Toolkit 项目进行了全面的架构分析。项目采用**分层架构设计**，具备良好的模块化和可扩展性。核心发现如下：

### 架构健康度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 插件生命周期管理 | ⭐⭐⭐⭐ | 完整的加载/卸载/缓存机制 |
| 接口解耦程度 | ⭐⭐⭐⭐⭐ | 依赖注入 + 策略模式，高度解耦 |
| 异常处理机制 | ⭐⭐⭐ | 基础异常处理，缺乏沙箱隔离 |
| 性能优化 | ⭐⭐⭐⭐ | 懒加载机制成熟，启动速度优化良好 |

### 关键建议

1. **增强插件隔离**：引入进程级沙箱机制
2. **统一事件总线**：建立跨模块通信标准
3. **深化插件集成**：三个现有插件可与 8 个核心业务流程集成
4. **扩展 5 项原生功能**：无需引入大型库即可实现

---

## 一、插件架构深度审计

### 1.1 当前架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    UI Layer - PyQt6                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ MainWindow  │  │ Interfaces  │  │  Widgets    │         │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘         │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                Application Layer                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              AppContainer - DI 容器                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ConfigLoader │  │PluginMgr   │  │ExternalToolMgr│  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Plugin System                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  PluginLoader   │  │ ExternalTools   │                  │
│  │  - .mcy 解密    │  │  GS/Pandoc/LO   │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                            │
│           ▼                    ▼                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              libs/.temp/ - 临时解压目录              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 插件生命周期管理分析

#### 1.2.1 加载机制

**当前实现** - [`core/plugin_loader.py`](core/plugin_loader.py:73)：

```python
def extract_plugin(self, mcy_path, persistent=False):
    # 1. 缓存检查 - 避免重复解压
    if mcy_path in self._extracted_cache:
        return self._extracted_cache[mcy_path]
    
    # 2. 解密流程: AES-256-CBC -> LZMA 解压 -> TAR 解包
    # 3. 根据模式选择目标目录 - 临时/持久
    # 4. 缓存结果并返回
```

**评估**：
- ✅ **优点**：
  - 缓存机制避免重复解压，性能友好
  - 支持临时/持久两种部署模式
  - AES-256 加密保护插件完整性
  
- ⚠️ **风险点**：
  - 解密密钥硬编码在源码中 - [`core/plugin_loader.py:15`](core/plugin_loader.py:15)
  - 缺乏插件签名验证机制
  - TAR 解包时未做路径穿越检查 - tar.extractall 存在安全隐患

**改进建议**：

```python
# 建议增加路径安全检查
def _safe_extract(self, tar, target_base):
    for member in tar.getmembers():
        # 防止路径穿越攻击
        abs_path = os.path.abspath(os.path.join(target_base, member.name))
        if not abs_path.startswith(os.path.abspath(target_base)):
            raise SecurityError(f"Path traversal detected: {member.name}")
    tar.extractall(path=target_base)
```

#### 1.2.2 卸载机制

**当前实现** - [`core/external_tools/manager.py:96`](core/external_tools/manager.py:96)：

```python
def uninstall_tool(self, name: str) -> bool:
    tool = self.get_tool(name)
    if tool and hasattr(tool, 'uninstall'):
        success = tool.uninstall()
        if success:
            self.disable_tool(name)  # 卸载后自动禁用
        return success
```

**评估**：
- ✅ 卸载后自动禁用，防止自动重新解压
- ✅ 安全检查：仅允许卸载便携版 - [`ghostscript_tool.py:173`](core/external_tools/ghostscript_tool.py:173)
- ⚠️ 缺少卸载前的依赖检查（可能影响正在使用该插件的功能）

#### 1.2.3 初始化机制

**当前实现** - [`core/plugin_loader.py:30`](core/plugin_loader.py:30)：

```python
def _init(self):
    atexit.register(self.cleanup)  # 注册退出清理
    self._clean_stale_temps()       # 清理残留临时目录
```

**评估**：
- ✅ 使用 atexit 确保程序退出时清理临时文件
- ✅ 启动时清理上次异常退出遗留的临时目录
- ⚠️ 多实例运行时可能相互影响（虽有 Windows 文件锁保护）

### 1.3 宿主与插件通信接口分析

#### 1.3.1 当前通信模式

项目采用**直接调用模式**，通过 [`ExternalToolManager`](core/external_tools/manager.py:20) 作为中介：

```
┌───────────────┐     get_tool      ┌──────────────────┐
│   Feature     │ ───────────────►  │ ExternalToolMgr  │
│   Module      │                   │                  │
└───────────────┘                   └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │   ExternalTool   │
                                    │   GS/Pandoc      │
                                    └──────────────────┘
```

**代码示例** - [`markdown_converter.py:22`](core/features/text/markdown_converter.py:22)：

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.pandoc_tool = ExternalToolManager().get_tool("pandoc")
```

**评估**：
- ✅ **解耦程度高**：功能模块不直接依赖具体工具实现
- ✅ **单例模式**：全局唯一的工具管理器
- ⚠️ **缺乏事件通知**：工具状态变化时，依赖方无法主动感知

#### 1.3.2 信号机制

项目使用 PyQt6 信号进行状态通知 - [`manager.py:7`](core/external_tools/manager.py:7)：

```python
class ToolSignals(QObject):
    tool_status_changed = pyqtSignal(str)  # tool_name
```

**评估**：
- ✅ 使用 Qt 信号槽机制，符合框架设计
- ⚠️ 信号粒度较粗，仅传递工具名称

**改进建议**：扩展信号携带更多上下文

```python
class ToolSignals(QObject):
    tool_status_changed = pyqtSignal(str, str, dict)  # name, event_type, details
    # event_type: installed, uninstalled, enabled, disabled, error
```

### 1.4 异常处理与沙箱隔离分析

#### 1.4.1 当前异常处理

**外部工具调用** - [`ghostscript.py:87`](core/engines/pdf/ghostscript.py:87)：

```python
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, ...)
stdout, stderr = process.communicate()

if process.returncode == 0:
    success += 1
else:
    err_msg = stderr.decode('gbk', errors='ignore')
    self.log.emit(f"❌ 失败: {err_msg}")
```

**评估**：
- ✅ 捕获子进程输出，记录错误信息
- ✅ 使用 errors=ignore 处理编码问题
- ⚠️ **无超时机制**：外部工具挂起会阻塞主程序
- ⚠️ **无资源限制**：无法防止外部工具耗尽系统资源

#### 1.4.2 沙箱隔离现状

**当前状态**：❌ 无沙箱隔离

外部工具以当前用户权限运行，可访问：
- 所有用户文件
- 网络资源
- 系统注册表（Windows）

**改进建议**：

```python
# 方案 A：超时控制 - 轻量级
import signal

def run_with_timeout(cmd, timeout=60):
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True)
        return result
    except subprocess.TimeoutExpired:
        raise PluginTimeoutError(f"Plugin execution exceeded {timeout}s")

# 方案 B：进程隔离 - 中等复杂度
# 使用 Windows Job Objects 或 Linux cgroups 限制资源
```

### 1.5 循环依赖风险分析

#### 1.5.1 模块依赖图

```
main.py
    └── AppContainer
            ├── ConfigLoader
            ├── PluginManager - 未实际使用
            └── ExternalToolManager
                    ├── GhostscriptTool
                    │       └── PluginLoader - 惰性加载
                    ├── PandocTool
                    │       └── PluginLoader - 惰性加载
                    └── LibreOfficeTool - 系统检测
```

**评估**：
- ✅ **无循环依赖**：依赖方向单一，从上到下
- ✅ **惰性加载**：避免启动时加载所有模块
- ⚠️ [`GhostscriptCompressor`](core/engines/pdf/ghostscript.py:11) 直接导入 AppContainer，形成隐式依赖

### 1.6 性能瓶颈分析

#### 1.6.1 启动性能

**优化措施**：
- ✅ UI 懒加载 - [`lazy_loader.py`](core/utils/lazy_loader.py:6)
- ✅ 插件按需解压（首次使用时解压）
- ✅ 配置分层加载（默认配置 + 用户覆盖）

**实测数据**（来自架构文档）：
- 启动速度提升 **60%+**
- 初始内存占用减少 **40%+**

#### 1.6.2 运行时性能

**潜在瓶颈**：
1. **LZMA 解压**：首次加载大型插件（如 Ghostscript ~50MB）可能需要数秒
2. **COM 初始化**：Office 引擎每次启动需初始化 COM 环境

**优化建议**：
- 预解压模式：在空闲时后台解压常用插件
- COM 连接池：复用 Office 应用实例

---

## 二、现有插件赋能分析

### 2.1 插件概览

| 插件名 | 类型 | 当前用途 | 集成深度 |
|--------|------|----------|----------|
| Ghostscript | PDF 处理引擎 | PDF 压缩 | 单一功能 |
| Pandoc | 文档转换器 | Markdown ↔ HTML | 部分集成 |
| LibreOffice | 办公套件 | Office 降级备选 | 降级方案 |

### 2.2 Ghostscript 赋能策略

#### 2.2.1 当前使用场景

- **PDF 压缩** - [`pdf_compress_interface.py`](ui/interfaces/pdf/pdf_compress_interface.py)

#### 2.2.2 可扩展集成点

```
┌─────────────────────────────────────────────────────────────┐
│                  Ghostscript 能力矩阵                        │
├─────────────────────────────────────────────────────────────┤
│  当前集成 ●                                                  │
│  ├── PDF 压缩 - 已实现                                       │
│                                                             │
│  建议集成 ○                                                  │
│  ├── PDF → 图片渲染 - 取代/增强现有 pdf_page_renderer        │
│  ├── PDF 灰度化 - 文档打印优化                               │
│  ├── PDF 页面旋转/裁剪                                       │
│  └── PostScript/EPS 处理                                    │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.3 集成方案：PDF 高清渲染

**业务价值**：当前 [`pdf_page_renderer.py`](core/features/pdf/pdf_page_renderer.py) 使用 PyMuPDF，Ghostscript 可提供更高 DPI 输出

**技术实现**：

```python
# core/features/pdf/pdf_gs_renderer.py
class GhostscriptRenderer:
    def render_page(self, pdf_path, page_num, dpi=300, output_format='png'):
        gs_path = ExternalToolManager().get_tool("ghostscript").get_path()
        cmd = [
            gs_path,
            "-dNOPAUSE", "-dBATCH",
            "-sDEVICE=png16m",  # 或 pngalpha 支持透明
            f"-r{dpi}",
            f"-dFirstPage={page_num}",
            f"-dLastPage={page_num}",
            f"-sOutputFile={output_path}",
            pdf_path
        ]
        subprocess.run(cmd, check=True)
```

**挂载点**：[`ui/interfaces/pdf/pdf_render_interface.py`](ui/interfaces/pdf/pdf_render_interface.py) - 添加"使用 Ghostscript 高清渲染"选项

### 2.3 Pandoc 赋能策略

#### 2.3.1 当前使用场景

- **Markdown → HTML** - [`markdown_converter.py:212`](core/features/text/markdown_converter.py:212)
- **HTML → Markdown** - [`markdown_converter.py:238`](core/features/text/markdown_converter.py:238)

#### 2.3.2 可扩展集成点

```
┌─────────────────────────────────────────────────────────────┐
│                    Pandoc 能力矩阵                           │
├─────────────────────────────────────────────────────────────┤
│  当前集成 ●                                                  │
│  ├── Markdown → HTML                                        │
│  └── HTML → Markdown                                        │
│                                                             │
│  建议集成 ○                                                  │
│  ├── Markdown → PDF - 带数学公式、代码高亮                   │
│  ├── Markdown → DOCX                                        │
│  ├── DOCX → Markdown - 增强现有 Word ↔ MD 功能              │
│  ├── LaTeX → PDF                                            │
│  └── reStructuredText 支持                                  │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3.3 集成方案：Markdown → PDF（数学公式支持）

**业务价值**：当前 [`markdown_interface.py`](ui/interfaces/text/markdown_interface.py) 的 PDF 导出缺乏数学公式渲染能力

**技术实现**：

```python
# core/features/text/markdown_pdf_pandoc.py
class PandocMarkdownToPdf:
    def convert(self, md_path, pdf_path, options=None):
        pandoc_path = ExternalToolManager().get_tool("pandoc").get_path()
        
        cmd = [
            pandoc_path,
            md_path,
            "-o", pdf_path,
            "--pdf-engine=xelatex",  # 或 wkhtmltopdf
            "--highlight-style=tango",
            "-V", "geometry:margin=1in",
            "-V", "mainfont=Microsoft YaHei",  # 中文支持
        ]
        
        # 数学公式支持
        if options.get('math', True):
            cmd.extend(["--mathjax"])
        
        subprocess.run(cmd, check=True)
```

**挂载点**：[`markdown_interface.py`](ui/interfaces/text/markdown_interface.py) - 增加"使用 Pandoc 导出 PDF"选项

#### 2.3.4 集成方案：增强 Word ↔ Markdown

**业务价值**：当前 [`word_markdown_interface.py`](ui/interfaces/office/word_markdown_interface.py) 使用基础库，格式保真度有限

**技术实现**：

```python
# core/features/office/word_markdown_pandoc.py
class PandocWordMarkdownConverter:
    def docx_to_markdown(self, docx_path, md_path):
        cmd = [
            pandoc_path,
            docx_path,
            "-f", "docx",
            "-t", "gfm",  # GitHub Flavored Markdown
            "-o", md_path,
            "--extract-media=./media",  # 提取图片
            "--wrap=none"
        ]
        subprocess.run(cmd, check=True)
    
    def markdown_to_docx(self, md_path, docx_path, template=None):
        cmd = [
            pandoc_path,
            md_path,
            "-o", docx_path,
        ]
        if template:
            cmd.extend(["--reference-doc", template])
        subprocess.run(cmd, check=True)
```

### 2.4 LibreOffice 赋能策略

#### 2.4.1 当前使用场景

- **Office 引擎降级备选** - [`container.py:73`](app/container.py:73)

#### 2.4.2 可扩展集成点

```
┌─────────────────────────────────────────────────────────────┐
│                  LibreOffice 能力矩阵                        │
├─────────────────────────────────────────────────────────────┤
│  当前集成 ●                                                  │
│  └── Word/Excel/PPT → PDF - 作为 MS Office 降级方案          │
│                                                             │
│  建议集成 ○                                                  │
│  ├── 批量格式转换 - ODT↔DOCX, ODS↔XLSX                      │
│  ├── PDF → 可编辑文档 - PDF → ODT → DOCX                     │
│  ├── 文档模板渲染 - 邮件合并                                 │
│  └── 无头模式批处理 - --headless                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4.3 集成方案：批量格式转换

**业务价值**：支持开源格式与 MS Office 格式互转，满足兼容性需求

**技术实现**：

```python
# core/features/office/libreoffice_converter.py
class LibreOfficeConverter:
    def convert(self, input_path, output_format, output_dir=None):
        """
        通用格式转换
        :param output_format: pdf, docx, odt, xlsx, ods, pptx, odp
        """
        lo_tool = ExternalToolManager().get_tool("libreoffice")
        soffice_path = lo_tool.get_path()
        
        output_dir = output_dir or os.path.dirname(input_path)
        
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to", output_format,
            "--outdir", output_dir,
            input_path
        ]
        subprocess.run(cmd, check=True)
```

### 2.5 插件集成总结

```
┌─────────────────────────────────────────────────────────────────────┐
│                      插件 × 业务流程 集成矩阵                         │
├─────────────────────┬─────────────┬─────────────┬───────────────────┤
│ 业务流程            │ Ghostscript │   Pandoc    │   LibreOffice     │
├─────────────────────┼─────────────┼─────────────┼───────────────────┤
│ PDF 压缩            │     ●       │             │                   │
│ PDF 渲染            │     ○       │             │                   │
│ Markdown → PDF      │             │     ○       │                   │
│ Markdown → HTML     │             │     ●       │                   │
│ Word ↔ Markdown     │             │     ○       │                   │
│ Office → PDF        │             │             │     ● 降级        │
│ 格式互转            │             │             │     ○             │
│ 文档模板渲染        │             │     ○       │     ○             │
├─────────────────────┴─────────────┴─────────────┴───────────────────┤
│ ● = 已集成   ○ = 建议集成                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、原生轻量级功能扩展规划

### 3.1 设计原则

- ❌ **禁止**引入大型第三方库（如 TensorFlow、OpenCV 完整版）
- ✅ **允许**使用 Python 标准库
- ✅ **允许**使用已有轻量依赖（PIL/Pillow、pypdf、markdown）
- ✅ **优先**使用原生算法实现

### 3.2 功能扩展方案

#### 3.2.1 📊 PDF 元数据编辑器

**痛点**：无法查看/编辑 PDF 的标题、作者、关键词等元数据

**技术方案**：

```python
# core/features/pdf/pdf_metadata.py
from pypdf import PdfReader, PdfWriter

class PDFMetadataEditor:
    def read_metadata(self, pdf_path) -> dict:
        reader = PdfReader(pdf_path)
        return dict(reader.metadata) if reader.metadata else {}
    
    def write_metadata(self, pdf_path, output_path, metadata: dict):
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        writer.add_metadata({
            '/Title': metadata.get('title', ''),
            '/Author': metadata.get('author', ''),
            '/Subject': metadata.get('subject', ''),
            '/Keywords': metadata.get('keywords', ''),
            '/Creator': 'Office Toolkit',
        })
        
        with open(output_path, 'wb') as f:
            writer.write(f)
```

**依赖**：pypdf（已有）

**可行性**：⭐⭐⭐⭐⭐ 完全可行，无需新增依赖

---

#### 3.2.2 🔐 PDF 加密/解密

**痛点**：无法为 PDF 添加密码保护或解除密码

**技术方案**：

```python
# core/features/pdf/pdf_security.py
from pypdf import PdfReader, PdfWriter

class PDFSecurity:
    def encrypt(self, pdf_path, output_path, user_password, owner_password=None):
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        writer.encrypt(
            user_password=user_password,
            owner_password=owner_password or user_password,
            permissions_flag=0b1111111111000000  # 禁止打印/复制
        )
        
        with open(output_path, 'wb') as f:
            writer.write(f)
    
    def decrypt(self, pdf_path, output_path, password):
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            reader.decrypt(password)
        
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        with open(output_path, 'wb') as f:
            writer.write(f)
```

**依赖**：pypdf（已有）

**可行性**：⭐⭐⭐⭐⭐ 完全可行

---

#### 3.2.3 📝 批量文件重命名引擎

**痛点**：用户经常需要批量重命名导出的文件

**技术方案**：

```python
# core/features/utils/batch_rename.py
import os
import re
from datetime import datetime

class BatchRenamer:
    """
    支持模板变量:
    - {name}: 原文件名（不含扩展名）
    - {ext}: 扩展名
    - {index}: 序号 01, 02, ...
    - {date}: 日期 YYYYMMDD
    - {time}: 时间 HHMMSS
    """
    
    def preview(self, files: list, template: str, start_index=1) -> list:
        """预览重命名结果"""
        results = []
        for i, path in enumerate(files):
            new_name = self._apply_template(path, template, start_index + i)
            results.append({
                'original': path,
                'new_name': new_name,
                'new_path': os.path.join(os.path.dirname(path), new_name)
            })
        return results
    
    def execute(self, rename_plan: list) -> tuple:
        """执行重命名"""
        success, fail = 0, 0
        for item in rename_plan:
            try:
                os.<think>
用户要求我继续从截断处输出。上一个输出结束于：

```python
    def execute(self, rename_plan: list) -> tuple:
        """执行重命名"""
        success, fail = 0, 0
        for item in rename_plan:
            try:
                os.
```

我需要继续完成这个文件的写入，从 `os.` 开始继续。
</think>
rename(item['original'], item['new_path'])
                success += 1
            except Exception:
                fail += 1
        return success, fail
    
    def _apply_template(self, path: str, template: str, index: int) -> str:
        name, ext = os.path.splitext(os.path.basename(path))
        now = datetime.now()
        
        replacements = {
            '{name}': name,
            '{ext}': ext.lstrip('.'),
            '{index}': f"{index:02d}",
            '{date}': now.strftime('%Y%m%d'),
            '{time}': now.strftime('%H%M%S'),
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result + ext if '{ext}' not in template else result
```

**依赖**：Python 标准库

**可行性**：⭐⭐⭐⭐⭐ 完全可行

---

#### 3.2.4 📋 剪贴板图片快速处理

**痛点**：用户需要将剪贴板中的截图快速保存或转换格式

**技术方案**：

```python
# core/features/image/clipboard_handler.py
from PIL import Image, ImageGrab
import io

class ClipboardImageHandler:
    def get_image_from_clipboard(self) -> Image.Image:
        """从剪贴板获取图片"""
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            return img
        return None
    
    def save_clipboard_image(self, output_path: str, format: str = 'PNG', quality: int = 95):
        """保存剪贴板图片到文件"""
        img = self.get_image_from_clipboard()
        if img is None:
            raise ValueError("剪贴板中没有图片")
        
        save_kwargs = {}
        if format.upper() in ['JPEG', 'JPG']:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            save_kwargs['quality'] = quality
        
        img.save(output_path, format=format, **save_kwargs)
        return output_path
    
    def copy_image_to_clipboard(self, image_path: str):
        """复制图片到剪贴板"""
        img = Image.open(image_path)
        output = io.BytesIO()
        img.convert('RGB').save(output, 'BMP')
        data = output.getvalue()[14:]  # 去除 BMP 文件头
        
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
```

**依赖**：Pillow（已有）、pywin32（Windows 剪贴板操作，可选）

**可行性**：⭐⭐⭐⭐ 基础功能可行，高级剪贴板操作需 pywin32

---

#### 3.2.5 📈 简易日志系统与性能监控

**痛点**：缺乏统一的日志收集和任务耗时统计

**技术方案**：

```python
# core/utils/logger.py
import logging
import time
from functools import wraps
from pathlib import Path
from datetime import datetime

class AppLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        self.logger = logging.getLogger("OfficeToolkit")
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # 格式
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
    
    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)
    def warning(self, msg): self.logger.warning(msg)


def timed_operation(operation_name: str):
    """装饰器：记录操作耗时"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = AppLogger()
            start = time.perf_counter()
            logger.info(f"[START] {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[DONE] {operation_name} - {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"[FAIL] {operation_name} - {elapsed:.2f}s - {str(e)}")
                raise
        return wrapper
    return decorator
```

**依赖**：Python 标准库 logging

**可行性**：⭐⭐⭐⭐⭐ 完全可行

---

### 3.3 功能扩展总结

| 功能 | 依赖 | 复杂度 | 优先级 | 可行性 |
|------|------|--------|--------|--------|
| PDF 元数据编辑 | pypdf | 低 | P1 | ⭐⭐⭐⭐⭐ |
| PDF 加密/解密 | pypdf | 低 | P1 | ⭐⭐⭐⭐⭐ |
| 批量重命名 | 标准库 | 低 | P2 | ⭐⭐⭐⭐⭐ |
| 剪贴板图片处理 | Pillow | 中 | P2 | ⭐⭐⭐⭐ |
| 日志与性能监控 | 标准库 | 低 | P1 | ⭐⭐⭐⭐⭐ |

---

## 四、实施路线图

### 4.1 阶段划分

```
Phase 1: 基础加固                   Phase 2: 插件深化
─────────────────────────────────────────────────────────────►
    2-3 周                              3-4 周

┌─────────────────────┐          ┌─────────────────────┐
│ ▸ 插件安全增强       │          │ ▸ GS PDF渲染集成    │
│   - 路径穿越防护     │          │ ▸ Pandoc MD→PDF    │
│   - 超时控制         │          │ ▸ LO 格式互转       │
│ ▸ 日志系统上线       │          │ ▸ 增强信号机制      │
│ ▸ PDF元数据/加密     │          │                     │
└─────────────────────┘          └─────────────────────┘

Phase 3: 体验优化                   Phase 4: 持续改进
─────────────────────────────────────────────────────────────►
    2-3 周                              持续

┌─────────────────────┐          ┌─────────────────────┐
│ ▸ 批量重命名         │          │ ▸ 用户反馈收集      │
│ ▸ 剪贴板快捷处理     │          │ ▸ 性能基准测试      │
│ ▸ UI 集成与测试      │          │ ▸ 文档完善          │
└─────────────────────┘          └─────────────────────┘
```

### 4.2 优先级矩阵

```
                        业务价值
                    高 ─────────────────► 低
            ┌───────────────────────────────────┐
        高  │  P1: PDF加密     P2: 批量重命名   │
            │      日志系统        剪贴板处理   │
  实现      │      元数据编辑                   │
  难度      ├───────────────────────────────────┤
            │  P1: GS渲染      P3: 沙箱隔离     │
        低  │      Pandoc PDF      COM连接池   │
            │      LO格式转换                   │
            └───────────────────────────────────┘
```

### 4.3 验收标准

| 阶段 | 验收条件 |
|------|----------|
| Phase 1 | 插件加载无安全漏洞；日志文件正常生成；PDF 加密/解密功能可用 |
| Phase 2 | Ghostscript 高清渲染 DPI ≥ 300；Pandoc PDF 支持数学公式 |
| Phase 3 | 批量重命名支持 5+ 模板变量；剪贴板处理响应 < 500ms |
| Phase 4 | 性能监控覆盖核心流程；文档覆盖率 > 80% |

---

## 附录：架构图

### A. 插件系统时序图

```
┌──────┐      ┌────────────┐      ┌────────────┐      ┌──────────┐
│ User │      │ Interface  │      │ToolManager │      │PluginLdr │
└──┬───┘      └─────┬──────┘      └─────┬──────┘      └────┬─────┘
   │                │                   │                  │
   │ 点击PDF压缩    │                   │                  │
   │───────────────►│                   │                  │
   │                │  get_tool("gs")   │                  │
   │                │──────────────────►│                  │
   │                │                   │                  │
   │                │                   │ _load_tool()     │
   │                │                   │─────────────────►│
   │                │                   │                  │
   │                │                   │   extract_plugin │
   │                │                   │◄─────────────────│
   │                │                   │                  │
   │                │    GS实例         │                  │
   │                │◄──────────────────│                  │
   │                │                   │                  │
   │                │ gs.compress()     │                  │
   │                │──────────────────►│                  │
   │                │                   │                  │
   │  完成通知      │                   │                  │
   │◄───────────────│                   │                  │
   │                │                   │                  │
```

### B. 建议的事件总线架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Event Bus                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   QObject Signals                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │   │
│  │  │tool_ready│ │tool_error│ │task_done │            │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘            │   │
│  └───────┼────────────┼────────────┼────────────────────┘   │
│          │            │            │                        │
└──────────┼────────────┼────────────┼────────────────────────┘
           │            │            │
     ┌─────▼────┐ ┌─────▼────┐ ┌─────▼────┐
     │ToolMgr   │ │ Logger   │ │ UI Layer │
     └──────────┘ └──────────┘ └──────────┘
```

---

## 结语

本技术方案基于对 Office Toolkit 项目的深度代码审查，提出了系统性的改进建议。核心要点：

1. **插件系统架构健康**，但需加强安全性（路径检查、超时控制）
2. **三个现有插件**可与更多业务流程深度集成，释放更大价值
3. **五项原生功能扩展**无需引入大型依赖，即可显著提升用户体验
4. **分阶段实施**确保风险可控，价值逐步交付

建议优先实施 Phase 1 的安全加固和基础功能，为后续扩展奠定坚实基础。

---

*文档作者：AI 架构师*  
*审核状态：待评审*