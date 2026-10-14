# 术语分家：Plugin 与 Tool Bundle 各归其位

代码里 "plugin" 一词同时指两套互不相干的系统：`core/plugins` 的 Python 能力框架，与 `core/plugin_loader` 的 .mcy 加密二进制包加载器，且 Ghostscript/Pandoc 横跨「外部工具」两侧。我们决定（GLOSSARY.md 为真源）：**Plugin** 只指 Python 能力扩展；**Tool Bundle** 指 .mcy 加密便携分发包（仅装载外部二进制工具，不装 Python 代码）；**External Tool** 保留「运行时发现的工具实例」；**Engine** 指转换能力的可替换实现。

**Status**: accepted

## Considered Options

- **保留双义**：拒绝——审查确认这正是重构时改错地方的高发区（同一词两种 import 目标）。
- **两套都改名**（谁都不叫 plugin）：拒绝——Python 框架叫 Plugin 是行业标准语义，改名成本大于收益。

## Consequences

- `core/plugin_loader.py` 在阶段 1 第 8 步随 Tool Bundle v2 改名为 `core/bundles/`。
- 新代码命名前先查 `GLOSSARY.md`；`.mcy` 装 Python 代码的需求被显式排除（Q16=a），若未来出现须先开新 ADR。
