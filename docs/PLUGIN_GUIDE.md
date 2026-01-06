# 插件开发指南 (Plugin Development Guide)

本文档面向插件开发者，详细说明如何创建和打包 `.mcy` 插件。

---

## 📦 什么是 .mcy 插件？

`.mcy` 是 Office Toolkit 的私有加密插件格式，具有以下特性：

- 🔒 **AES-256-CBC 加密**：保护插件完整性和安全性
- 📦 **LZMA 高压缩**：体积缩小 60%+ (Preset 9)
- 🚀 **惰性加载**：按需解压，降低内存占用
- ✅ **完整性校验**：SHA256 哈希验证

---

## 🛠️ 创建插件

### 1. 准备插件目录

将要打包的工具放入独立目录，例如：

```
ghostscript/
├── bin/
│   └── gswin64c.exe
├── lib/
│   └── (依赖文件)
└── README.txt
```

### 2. 使用打包工具

运行 `tools/pack_plugin.py` 脚本：

```bash
python tools/pack_plugin.py <源目录> <输出文件> --tool-id <工具ID>
```

**示例**：

```bash
python tools/pack_plugin.py libs/ghostscript plugins/ghostscript.mcy --tool-id ghostscript
```

**参数说明**：
- `<源目录>`: 要打包的工具目录（如 `libs/ghostscript`）
- `<输出文件>`: 输出的 `.mcy` 文件路径（如 `plugins/ghostscript.mcy`）
- `--tool-id`: 工具标识符（如 `ghostscript`、`pandoc`）

### 3. 验证插件

打包完成后，将 `.mcy` 文件放入 `plugins/` 目录，启动程序测试：

```bash
# 放置插件
cp ghostscript.mcy plugins/

# 启动程序
python main.py
```

在"设置 → 外部工具"中查看插件是否正常加载。

---

## 🔐 .mcy 文件结构

```
.mcy 文件格式
├─ Header (16 bytes)
│  └─ Magic Number: "MCY_PLUGIN_PKG\x00"
│
├─ Metadata Block (JSON)
│  ├─ tool_id: "ghostscript"
│  ├─ version: "10.02.0"
│  ├─ checksum: "sha256..."
│  └─ compressed_size: 41943040
│
└─ Encrypted Payload
   ├─ AES-256-CBC 加密
   ├─ Key: 从密码派生 (PBKDF2)
   └─ 内容: LZMA 压缩的 tar 包
```

---

## 🔧 配置插件加载

### 在代码中注册插件

如果要添加新的工具支持，需要：

#### 1. 创建工具类

在 `core/external_tools/` 中创建工具类：

```python
# core/external_tools/your_tool.py
from .base import BaseExternalTool

class YourTool(BaseExternalTool):
    def __init__(self, config_loader):
        super().__init__("your_tool", config_loader)
        self.executable = "your_tool.exe"  # 可执行文件名
    
    def get_search_paths(self):
        # 定义搜索路径
        return [
            os.path.join(self.libs_dir, "your_tool", "bin"),
            "C:/Program Files/YourTool/bin",
        ]
```

#### 2. 注册到管理器

在 `core/external_tools/manager.py` 中注册：

```python
from .your_tool import YourTool

class ExternalToolManager:
    def __init__(self, config_loader):
        self.tools = {
            "ghostscript": GhostscriptTool(config_loader),
            "pandoc": PandocTool(config_loader),
            "your_tool": YourTool(config_loader),  # 新增
        }
```

---

## 📋 插件模式说明

### 临时模式 (Temporary Mode)

- **特点**: 插件使用时解压到临时目录，程序退出后自动清理
- **优势**: 节省磁盘空间
- **适用**: 默认推荐模式

### 持久模式 (Persistent Mode)

- **特点**: 插件解压到 `libs/` 目录并永久保留
- **优势**: 下次启动无需重复解压，速度更快
- **适用**: 频繁使用的工具

用户可在"设置 → 外部工具"中切换模式。

---

## 🔍 插件加载优先级

程序按以下优先级搜索工具：

1. **plugins/ 目录 (.mcy 插件)** - 最高优先级
2. **libs/ 目录 (已解压的插件)**
3. **环境变量 (PATH)**
4. **系统安装路径** (如 `C:\Program Files\...`)

---

## 💡 最佳实践

### 1. 目录结构规范

建议插件目录结构：

```
your_tool/
├── bin/          # 可执行文件
├── lib/          # 依赖库
├── share/        # 共享资源
└── README.txt    # 说明文档
```

### 2. 版本管理

在工具目录中添加 `VERSION` 文件：

```
10.02.0
```

### 3. 最小化体积

- 移除不必要的文件（文档、示例等）
- 压缩可执行文件（UPX等工具）
- 仅包含必要的依赖

### 4. 测试清单

- ✅ 插件能否正常解密和解压
- ✅ 工具可执行文件能否正常运行
- ✅ 临时模式和持久模式都能工作
- ✅ 卸载功能正常

---

## 🐛 常见问题

### Q: 插件打包失败？

**A**: 检查以下几点：
1. 源目录是否存在
2. 输出目录是否有写入权限
3. 源目录中是否包含无效字符

### Q: 插件加载失败？

**A**: 可能原因：
1. `.mcy` 文件已损坏
2. 解密密钥不匹配
3. 目标目录权限不足

查看程序日志获取详细错误信息。

### Q: 如何更新插件版本？

**A**: 
1. 重新打包新版本插件
2. 在"设置"中卸载旧版本
3. 放入新的 `.mcy` 文件
4. 重启程序

---

## 📚 参考示例

### 示例：打包 Pandoc 插件

```bash
# 1. 下载 Pandoc 便携版
wget https://github.com/jgm/pandoc/releases/download/3.1.8/pandoc-3.1.8-windows-x86_64.zip

# 2. 解压到 libs 目录
unzip pandoc-3.1.8-windows-x86_64.zip -d libs/pandoc

# 3. 打包为 .mcy 插件
python tools/pack_plugin.py libs/pandoc plugins/pandoc.mcy --tool-id pandoc

# 4. 验证
python main.py
```

---

## 🤝 贡献插件

欢迎为项目贡献新的插件！

### 贡献流程

1. Fork 本项目
2. 创建插件分支：`git checkout -b feature/new-plugin`
3. 添加工具类和打包脚本
4. 测试插件功能
5. 提交 Pull Request

### 插件要求

- ✅ 开源或允许再分发的工具
- ✅ 提供完整的使用文档
- ✅ 经过充分测试
- ✅ 体积合理（建议 < 200MB）

---

*最后更新时间：2026-01-06*
