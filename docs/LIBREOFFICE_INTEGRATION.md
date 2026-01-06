# LibreOffice 备用引擎集成文档

## 概述

为了支持无 Microsoft Office 用户，项目已集成 LibreOffice 作为免费开源的备用引擎，实现跨平台的 Office 文档转 PDF 功能。

## 功能特性

### 1. 智能引擎选择
系统会按以下优先级自动选择转换引擎：
1. **Microsoft Office**（如已安装）- 优先使用
2. **LibreOffice**（如已安装）- 降级备选
3. **提示安装**（都未安装）- 显示错误信息

### 2. 跨平台支持
- ✅ **Windows**: 自动检测 Program Files 安装位置
- ✅ **Linux**: 检测 /usr/bin、/opt 等常见路径
- ✅ **macOS**: 检测 /Applications 应用程序目录

### 3. 无缝集成
- 用户无需手动配置，系统自动检测并选择可用引擎
- 界面提示已更新为"支持 MS Office 或 LibreOffice"
- 设置界面自动显示 LibreOffice 安装状态

## 技术实现

### 架构设计

```
引擎选择流程:
┌─────────────────┐
│ AppContainer    │
│ _create_office_ │
│ engine()        │
└────────┬────────┘
         │
         ├─> 尝试 MS Office (COM)
         │   └─> 成功 → 返回 WordEngine
         │
         ├─> 检查 LibreOffice
         │   └─> 可用 → 返回 LibreOfficeWordEngine
         │
         └─> 降级到 MS Office (错误提示)
```

### 新增文件

#### 1. `core/external_tools/libreoffice_tool.py`
LibreOffice 检测工具类，负责：
- 跨平台路径检测
- 版本号获取
- 可执行文件定位

**关键方法**:
```python
def _find(self) -> dict:
    """查找 LibreOffice 安装路径"""
    # 1. 检查环境变量 (PATH)
    # 2. 检查平台特定路径
    #    - Windows: Program Files
    #    - macOS: /Applications
    #    - Linux: /usr/bin, /opt
```

#### 2. `core/engines/office/libreoffice.py`
LibreOffice CLI 转换引擎，包含：
- `LibreOfficeEngine` - 基础引擎类
- `LibreOfficeWordEngine` - Word 专用引擎
- `LibreOfficeExcelEngine` - Excel 专用引擎
- `LibreOfficePowerPointEngine` - PowerPoint 专用引擎

**转换命令**:
```bash
soffice --headless --convert-to pdf --outdir <output_dir> <input_file>
```

### 修改文件

#### 1. `app/container.py`
添加 `_create_office_engine()` 工厂方法实现智能选择：

```python
def _create_office_engine(self, engine_type: str):
    # 1. 优先尝试 MS Office
    try:
        import comtypes.client
        return WordEngine()  # 成功
    except:
        pass
    
    # 2. 降级到 LibreOffice
    if libreoffice_available:
        return LibreOfficeWordEngine()
    
    # 3. 返回 MS Office (会报错)
    return WordEngine()
```

#### 2. `core/external_tools/manager.py`
注册 LibreOffice 工具：
```python
TOOL_REGISTRY = {
    "ghostscript": (...),
    "pandoc": (...),
    "libreoffice": ("core.external_tools.libreoffice_tool", "LibreOfficeTool"),
}
```

#### 3. 界面文件更新
- `ui/interfaces/word_interface.py`
- `ui/interfaces/excel_interface.py`
- `ui/interfaces/ppt_interface.py`

提示文本更新为：
```python
self.desc = BodyLabel("批量转换 Word 文件 (支持 MS Word 或 LibreOffice)", self)
```

## 使用指南

### 用户使用

#### 安装 LibreOffice
1. 访问 https://www.libreoffice.org/download/
2. 下载适合您操作系统的版本
3. 安装后重启应用程序
4. 在"设置"中查看 LibreOffice 状态

#### 验证安装
打开"设置" → "外部工具" → 查看 LibreOffice 状态：
- ✅ **已就绪 (系统安装)** - 可以使用
- ❌ **未安装 (功能受限)** - 需要安装

### 开发测试

#### 测试 LibreOffice 检测
```python
from core.external_tools.manager import ExternalToolManager

manager = ExternalToolManager()
tool = manager.get_tool("libreoffice")

print(f"已安装: {tool.is_available()}")
print(f"版本: {tool.get_version()}")
print(f"路径: {tool.get_path()}")
```

#### 测试转换功能
```python
from core.engines.office.libreoffice import LibreOfficeWordEngine

engine = LibreOfficeWordEngine()
if engine.is_available():
    engine.convert(["test.docx"])
```

## 兼容性

### 支持的文档格式
- **Word**: `.doc`, `.docx`
- **Excel**: `.xls`, `.xlsx`
- **PowerPoint**: `.ppt`, `.pptx`

### 系统要求
- **Windows**: LibreOffice 7.0+
- **Linux**: LibreOffice 6.0+
- **macOS**: LibreOffice 7.0+

### 已测试版本
- ✅ LibreOffice 7.6.x
- ✅ LibreOffice 24.2.x

## 故障排查

### 问题：LibreOffice 已安装但检测不到

**可能原因**:
1. LibreOffice 未添加到系统 PATH
2. 安装在非标准路径

**解决方案**:
1. 检查 `soffice` 命令是否可用：
   ```bash
   # Windows
   where soffice
   
   # Linux/Mac
   which soffice
   ```
2. 手动添加到 PATH 或重新安装

### 问题：转换失败或超时

**可能原因**:
1. 文档损坏或格式不支持
2. LibreOffice 进程冲突

**解决方案**:
1. 尝试用 LibreOffice GUI 打开文档确认
2. 关闭其他 LibreOffice 进程
3. 检查日志中的详细错误信息

### 问题：转换质量不佳

**说明**:
LibreOffice 的转换质量可能与 Microsoft Office 略有差异，这是正常现象。

**建议**:
- 对于高质量需求，推荐使用 Microsoft Office
- 对于日常使用，LibreOffice 转换质量足够

## 性能对比

| 引擎 | 启动速度 | 转换质量 | 资源占用 | 跨平台 |
|------|---------|---------|---------|--------|
| MS Office | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ❌ |
| LibreOffice | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | ✅ |

## 未来计划

- [ ] 添加 LibreOffice 转换选项配置（DPI、压缩等）
- [ ] 支持更多输出格式（HTML、ODT 等）
- [ ] 添加批量转换性能优化
- [ ] 支持云端 LibreOffice Online

## 参考资料

- [LibreOffice 官方文档](https://documentation.libreoffice.org/)
- [LibreOffice CLI 参数](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)
- [LibreOffice API](https://api.libreoffice.org/)

---

*最后更新: 2026-01-06*