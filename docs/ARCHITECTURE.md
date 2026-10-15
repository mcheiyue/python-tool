# 架构设计文档 (Architecture)

本文档详细说明 Office Toolkit 的技术架构设计。

---

## 📐 总体架构

Office Toolkit 采用**分层架构设计**，遵循**关注点分离原则**，确保代码的可维护性和可扩展性。

```
┌─────────────────────────────────────────┐
│          UI Layer (用户界面层)            │
│   ├─ main_window.py                     │
│   ├─ interfaces/ (按领域分组的功能界面)    │
│   └─ widgets/ (自定义组件)                │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│      Application Layer (应用层)          │
│   └─ app/container.py (DI容器)          │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│       Business Layer (业务逻辑层)         │
│   ├─ core/engines/ (引擎抽象)            │
│   ├─ core/plugins/ (插件系统)            │
│   └─ core/features/ (功能领域模块)       │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│    Infrastructure Layer (基础设施层)      │
│   ├─ config/ (配置管理)                  │
│   ├─ core/external_tools/ (外部工具)     │
│   └─ core/utils/ (通用工具)              │
└─────────────────────────────────────────┘
```

---

## 🏗️ 核心设计模式

### 1. 依赖注入 (Dependency Injection)

**文件**: `app/container.py`

**设计思想**: 使用单例容器管理全局依赖，实现UI与业务逻辑的解耦。

```python
class AppContainer:
    _instance = None  # 单例模式
    
    def __init__(self):
        self.config_loader = ConfigLoader()  # 配置加载器
        self.plugin_manager = PluginManager()  # 插件管理器
        # 其他服务...
```

**优势**:
- ✅ 统一管理全局依赖的生命周期
- ✅ 便于单元测试（可mock依赖）
- ✅ 避免循环依赖问题

---

### 2. 策略模式 + 抽象工厂

**文件**: `core/engines/`

**设计思想**: 为不同的业务引擎（PDF/Office）定义抽象基类，提供多种实现。

```python
# 抽象基类
class BasePdfCompressor(QObject, ABC):
    @abstractmethod
    def compress(self, input_path, output_path, quality):
        pass

# 具体实现
class GhostscriptCompressor(BasePdfCompressor):
    def compress(self, input_path, output_path, quality):
        # 使用 Ghostscript 实现压缩
        ...
```

**优势**:
- ✅ 支持多种引擎实现（Ghostscript、OCR等）
- ✅ 易于扩展新的引擎
- ✅ 符合开闭原则

---

### 3. 插件系统

**文件**: `core/plugins/`

**设计思想**: 基于能力注册机制（Capability Registry）的插件架构。

```python
class PluginManager:
    def register_plugin(self, plugin_instance):
        for capability in plugin_instance.provides():
            self._capabilities[capability].append(plugin_instance)
    
    def get_plugin(self, capability):
        # 根据能力获取首选插件
        return self._capabilities.get(capability, [])[0]
```

**支持的插件**:
- **PandocPlugin**: Markdown高级转换
- **MathJaxPlugin**: 数学公式渲染
- **HighlightPlugin**: 代码高亮

**优势**:
- ✅ UI层与插件解耦
- ✅ 支持动态加载/卸载
- ✅ 可配置首选插件

---

### 4. 懒加载 (Lazy Loading)

**文件**: `core/utils/lazy_loader.py` + `ui/interfaces/__init__.py`

**设计思想**: 延迟加载重型依赖，加速启动。

```python
class UILazyLoader:
    def load_interface(self, interface_name):
        if interface_name not in self._cache:
            module = importlib.import_module(f'ui.interfaces.{interface_name}')
            self._cache[interface_name] = getattr(module, class_name)()
        return self._cache[interface_name]
```

**优化效果**:
- ⚡ 启动速度提升 **60%+**
- 💾 初始内存占用减少 **40%+**
- 🛡️ 增加超时重试机制，提升系统稳定性

---

### 5. 并发任务管理 (Concurrency)

**文件**: `ui/interfaces/image/image_convert_interface.py` (示例)

**设计思想**: 摒弃为每个任务创建独立 `QThread` 的模式，转为使用 `QThreadPool` 管理轻量级 `QRunnable` 任务。

```python
class ConvertTask(QRunnable):
    def run(self):
        # 执行具体任务
        pass

# 在界面类中
self.thread_pool = QThreadPool()
self.thread_pool.setMaxThreadCount(4)  # 限制并发数
self.thread_pool.start(ConvertTask(...))
```

**优势**:
- ✅ 避免大量小文件处理时线程数爆炸
- ✅ 降低系统上下文切换开销
- ✅ 更可控的资源占用

---

## 🗂️ 模块说明

### UI Layer (ui/)

| 模块 | 职责 |
|------|------|
| `main_window.py` | 主窗口布局与导航 |
| `interfaces/` | 各功能页面（PDF合并、图片转换等） |
| `widgets/` | 可复用UI组件（拖拽列表、颜色卡片等） |
| `threads.py` | 后台任务线程（避免UI阻塞） |

### Business Layer (core/)

| 模块 | 职责 |
|------|------|
| `features/` | 按领域组织的业务逻辑 (pdf, image, office, text) |
| `engines/` | 业务引擎抽象（PDF/Office/OCR） |
| `plugins/` | 插件系统实现 |

### Infrastructure Layer

| 模块 | 职责 |
|------|------|
| `config/` | 配置加载与管理 |
| `core/external_tools/` | 外部工具管理（Ghostscript/Pandoc） |
| `core/utils/` | 通用工具（路径处理、图标加载等） |

---

## 📦 外部工具供给链（Manifest + 预置包）

**设计思想**: 外部便携依赖以「官方 URL + SHA256」的 manifest 描述获取方式，
预置 zip 随安装包分发，按需下载/解压（spec: ADR-0003 修订版）。
旧 `.mcy` 签名载体保留读取兼容，去留待 B5 裁决。

**发现链**（收拢于 `core/external_tools/base.py::_resolve_executable`）:

```
libs/<tool>/exe            →  已安装（便携或持久化解压产物）
  → plugins/<tool>.zip     →  预置包：SHA256 校验后安全解压
  → manifest 下载          →  plugins/manifest.json 的 url 下载 + 校验 + 解压
  → plugins/<tool>.mcy     →  遗留：内嵌公钥验签 + LZMA 流式解压
  → PATH / 系统路径        →  环境安装
```

**Manifest 项**（`plugins/manifest.json`，入库可评审）:

```json
"pandoc": { "version": "3.12.1", "url": "https://github.com/jgm/pandoc/…",
            "sha256": "6ef431cb…" }
```

**关键实现**:

| 组件 | 职责 |
| --- | --- |
| `core/tools/downloader.py` | `urllib` 分块下载、hash 校验、重试、取消 |
| `core/tools/package_store.py` | 读 manifest、下载/定位 zip、委托 `BundleLoader.extract_zip` |
| `core/bundles/loader.py` | 成员路径审查 + tar/zip 安全解压（顶层目录归一化） |
| `base.ExternalTool` | 四步发现链、异步状态解析、版本指纹缓存 |

**优势**:
- 🔗 二进制位级对齐上游（hash 钉住官方产物，而非维护者 repack）
- 📝 维护动作是编辑 JSON；新增贡献者可对清单提 PR
- 🧊 离线场景：预置 zip 随包分发，命中后不触网
- 🚀 惰性安装，按需解压；「按需解压/调用」语义与 `.mcy` 时代一致

---

## 🔄 数据流示例

以 **PDF 压缩** 为例：

```
用户点击"开始压缩"
    ▼
UI Layer (PDFCompressInterface)
    ▼
调用 WorkerThread 后台线程
    ▼
获取 GhostscriptCompressor（从 AppContainer）
    ▼
检查 Ghostscript 可用性（ExternalToolManager）
    ▼
执行压缩逻辑（subprocess调用gs.exe）
    ▼
通过信号返回结果
    ▼
UI Layer 更新界面（进度条/成功提示）
```

---

## 🎯 设计原则

1. **单一职责原则 (SRP)**: 每个类只负责一个功能
2. **开闭原则 (OCP)**: 对扩展开放，对修改封闭
3. **依赖倒置原则 (DIP)**: 依赖抽象而非具体实现
4. **接口隔离原则 (ISP)**: 使用小而专一的接口

---

## 📚 参考资料

- [PyQt6 官方文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [设计模式: 可复用面向对象软件的基础](https://refactoring.guru/design-patterns)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

*最后更新时间：2026-01-06*
