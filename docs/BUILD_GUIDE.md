# Office Toolkit 构建指南

## 概述

本项目采用**双重构建方案**，生成三种发布格式：
1. **安装版**：传统 Windows 安装程序（基于 Standalone 模式）
2. **绿化版**：免安装的 ZIP 压缩包（基于 Standalone 模式）
3. **单文件版**：包含所有插件的独立 EXE（基于 Onefile 模式）

---

## 构建流程

### 第一步：运行 Nuitka 双重编译

```bash
cd build
build_nuitka.bat
```

**输出产物：**
- `dist\standalone\main.dist\` - 目录版（用于安装包和绿化版）
- `dist\onefile\OfficeToolkit_Single.exe` - 单文件版

**编译时间：** 首次约 10-15 分钟，后续增量编译约 2-5 分钟

---

### 第二步：打包发布版本

```bash
build_release.bat
```

**输出产物（位于 `release\` 目录）：**
1. `OfficeToolkit_Setup_v1.0.0.exe` - 安装包（需要安装 Inno Setup）
2. `OfficeToolkit_Portable_v1.0.0.zip` - 绿化版
3. `OfficeToolkit_Single_v1.0.0.exe` - 单文件版

---

## 三种发布模式详解

### 1. 安装版 (Installer)

**特点：**
- 使用 Inno Setup 打包
- 支持开始菜单、桌面快捷方式
- 自动注册卸载程序
- 基于 Standalone 编译，启动速度快

**用户使用场景：**
- 企业环境，需要规范安装
- 需要多用户使用
- 希望系统集成（右键菜单等未来功能）

**安装后目录结构：**
```
C:\Program Files\Office Toolkit\
├── OfficeToolkit.exe          # 主程序
├── _internal\                 # 依赖库（由 Nuitka 生成）
│   ├── PyQt6\
│   ├── qfluentwidgets\
│   └── ...
├── assets\                    # 内置资源（图标等）
├── config\                    # 配置文件
├── plugins\                   # 插件目录（空，用户可放置 .mcy 文件）
└── libs\                      # 运行时生成（插件解压位置）
```

---

### 2. 绿化版 (Portable)

**特点：**
- 解压即用，无需安装
- 所有数据在程序目录内（配置、缓存、插件）
- 基于 Standalone 编译，启动速度快
- 可放置在 U 盘等移动存储设备

**用户使用场景：**
- 个人用户，不想安装
- 需要便携使用（不同电脑间迁移）
- 测试环境

**目录结构：**（与安装版相同）
```
OfficeToolkit\
├── OfficeToolkit.exe
├── _internal\
├── assets\
├── config\
├── plugins\
└── libs\（运行时生成）
```

---

### 3. 单文件版 (Onefile)

**特点：**
- 只有一个 EXE 文件
- **内置所有插件**（ghostscript.mcy、pandoc.mcy）
- 首次启动会自解压到临时目录（稍慢）
- 适合快速分享和演示

**用户使用场景：**
- 快速分享给他人试用
- 不想解压一堆文件
- 演示、临时使用

**工作原理：**
```
OfficeToolkit_Single.exe
  ↓（首次运行）
%TEMP%\onefile_xxx\（临时解压）
├── OfficeToolkit.exe（真实运行程序）
├── _internal\
├── assets\
├── config\
└── plugins\（内置的 .mcy 文件）
    ├── ghostscript.mcy
    └── pandoc.mcy
```

**重要说明：**
- 用户仍可在 EXE 所在目录创建 `plugins` 文件夹，放置额外插件
- 代码会优先加载内置插件，兜底加载外部插件

---

## 技术实现细节

### 插件查找逻辑（内外兼查）

**修改文件：**
- `core/external_tools/ghostscript_tool.py`
- `core/external_tools/pandoc_tool.py`

**逻辑：**
```python
# 优先查找内部资源（单文件版打包进去的）
internal_plugin = get_resource_path("plugins/ghostscript.mcy")

# 兜底查找外部目录（用户手动放置的）
external_plugin = os.path.join(get_app_root(), "plugins", "ghostscript.mcy")

# 选择存在的插件路径
plugin_path = internal_plugin if os.path.exists(internal_plugin) else external_plugin
```

**关键函数：**
- `get_resource_path()` - 返回内部资源路径（临时解压目录或项目根目录）
- `get_app_root()` - 返回 EXE 所在的真实目录

---

### 双重构建参数差异

| 参数 | Standalone | Onefile |
|------|-----------|---------|
| `--standalone` | ✅ | ✅ |
| `--onefile` | ❌ | ✅ |
| `--include-data-dir=plugins=plugins` | ❌ | ✅ |

**关键点：**
- Standalone：不打包 plugins，让用户自行添加
- Onefile：打包 plugins，实现真正的"单文件"

---

## 常见问题

### Q1: 为什么需要两次编译？

**A:** 因为 Standalone 和 Onefile 模式的目录结构不同：
- **Standalone**：适合安装版和绿化版（启动快，结构清晰）
- **Onefile**：适合单文件分发（方便分享，但启动稍慢）

### Q2: 单文件版为什么启动慢？

**A:** Onefile 模式下，首次启动需要：
1. 解压整个程序到 `%TEMP%`
2. 运行解压后的程序
3. 退出时清理临时文件

**优化建议：** 如果用户需要长期使用，推荐安装版或绿化版。

### Q3: 插件会重复解压吗？

**A:** 不会。插件加载器使用了缓存机制（`_extracted_cache`），同一 `.mcy` 文件只解压一次。

### Q4: 如何回滚到旧版本构建方案？

**A:** 使用 Git 恢复：
```bash
git log --oneline  # 查看提交历史
git checkout <旧版本的 commit hash>
```

建议在修改前的提交：`19fb1e1`

---

## 构建环境要求

### 必需工具
- **Python 3.11+**
- **Nuitka** (`pip install nuitka`)
- **MinGW64** (Nuitka 自动下载)
- **Inno Setup 6**（仅安装包需要）

### 可选工具
- **UPX**（压缩 EXE，可减小 30% 体积）

---

## 更新版本号

修改以下文件：
1. `build/build_nuitka.bat` - `--file-version` 和 `--product-version`
2. `build/installer.iss` - `#define MyAppVersion`
3. `build/build_release.bat` - 输出文件名中的版本号

---

## 许可协议

本项目采用 MIT 许可证，详见 LICENSE 文件。
