# Office Toolkit

面向 Windows 的桌面办公工具箱：把文档转换、PDF、图像与文件批处理能力集成在一个应用中，并通过外部引擎与可扩展包按需增强能力。

## Language

### 扩展与集成

**Plugin（插件）**:
用 Python 编写、为应用增添新处理逻辑的扩展单元。
_Avoid_: 扩展、addon、.mcy 插件

**Tool Bundle（工具包）**:
装载外部二进制工具、以加密单文件形式分发的便携包。
_Avoid_: 插件（旧称，专指 Plugin）、组件包

**External Tool（外部工具）**:
应用在运行时发现、检测状态并管理启停的外部可执行工具实例；一个实例可来自 Tool Bundle、系统安装或环境变量。
_Avoid_: 依赖、二进制

**Engine（引擎）**:
为某一转换能力提供的可替换实现，同一能力可由不同引擎（如 MS Office 与 LibreOffice）承担。
_Avoid_: 转换器、后端

**临时模式 / 持久模式**:
Tool Bundle 解压产物的驻留策略：使用后清理，或解压后常驻。
_Avoid_: 便携模式

### 能力与任务

**Feature（功能）**:
用户可独立调用的一项工具能力，构成产品功能清单的单位。
_Avoid_: 工具（与 External Tool 撞名）、模块

**Batch Task（批任务）**:
对一组文件执行同一操作的可取消任务，逐项汇报进度与结果。
_Avoid_: 作业、循环
