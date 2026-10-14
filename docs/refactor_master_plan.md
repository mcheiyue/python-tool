# 重构总蓝图 (Refactor Master Plan)

> 状态：已与全部决议对齐（14 项共识 + Q15'/Q16），待批准后执行
> 日期：2026-09-24
> 关联：`GLOSSARY.md`（术语真源）、ADR-0001 ~ ADR-0003（`docs/adr/`）

---

## 1. 目标与约束

| 项        | 决议                                                                |
| --------- | ------------------------------------------------------------------- |
| 第一目标  | 可维护性（其次：启动性能 > 作品集 > 可测试性 > 瘦身）                |
| 终点形态  | 整体重写：骨架先行，旧架构代码全部退场（ADR-0001）                  |
| 路径      | 增量小步，每步可运行                                                 |
| 硬约束    | 功能可用、Windows 优先、不换技术栈（PyQt6 留用）                    |
| 范围      | 仅 `core/ app/ ui/ config/` 源码 + 测试；不动 `build/ tools/ docs/` 既有内容 |
| 性能      | 启动速度：每次收尾跑 `--benchmark` 记录基线，不卡硬阈值             |
| 完成定义  | 特征测试绿 + 应用可启动 + 原子提交（骨架期走短分支）                |

## 2. 目标架构骨架

```
python-tool/
├── main.py                  # 入口（不变更职责）
├── app/
│   └── container.py         # 仅装配与生命周期，不含引擎选型策略
├── core/
│   ├── features/            # ★ 纯 Python 业务逻辑，零 PyQt6（分层规则，测试守护）
│   │   ├── image/ office/ pdf/ text/ utils/
│   ├── engines/             # Qt 信号适配层（QObject 允许）；含 EngineSelector
│   │   ├── office/          # MS Office (COM) + LibreOffice，共享一个批处理循环
│   │   └── pdf/
│   ├── batch.py             # BatchRunner：全项目唯一的批处理循环（纯 Python + 回调协议）
│   ├── external_tools/      # External Tool 发现与状态（不变）
│   ├── bundles/             # Tool Bundle (.mcy) 加载（原 plugin_loader 改名，v2 见 ADR-0003）
│   ├── plugins/             # Python 能力插件框架（独占 Plugin 一词，概念不变）
│   └── utils/
├── ui/                      # 仅 WorkerThread 一种线程原语；main_window 瘦身后
├── config/
├── tests/
├── GLOSSARY.md              # 术语真源
└── docs/adr/                # 架构决策记录
```

**依赖规则（三层，配守护测试）**

1. `core/features` 不得 import PyQt6 —— 业务逻辑纯函数/类，pytest 直测
2. `core/features` 不得 import `app/`、`ui/` —— 依赖只准向下（audit 发现的 `ghostscript.py → AppContainer` 反向依赖在此清零）
3. `ui/` 只经 `app/container` 取装配结果，不直接 new 服务

守护方式：`tests/test_layering.py` 用 AST 扫描上述 import 规则，违规即红。

## 3. 迁移顺序（滚雪球）

### 阶段 0：骨架（短分支 `refactor/skeleton`，合回 main 后删除）

1. 建目标目录骨架 + `test_layering.py` 分层守护测试
2. 实现 `core/batch.py` BatchRunner（纯 Python：遍历、停止旗标、逐项回调、成败统计）+ 单测
3. **垂直样例**：迁移批量重命名（`core/features/utils/batch_rename.py` + 现有 22 个测试符号）进新骨架，全绿
4. 修 `tests/test_imports.py` 假测试（补真 assert 或删除）
5. `_safe_extract` 补符号链接/硬链接拒绝（纯加固，不依赖格式变更，立即可做）
6. `--benchmark` 首测，记录基线数值
7. 合回 main：**首个原子提交**

### 阶段 1+：按模块滚雪球（每模块 = 特征测试绿 + 可启动 + 原子提交）

| 序 | 模块                               | 前置动作                                                | 裁决（源自审查）                |
| -- | ---------------------------------- | ------------------------------------------------------- | ------------------------------- |
| 1  | 批量重命名（样例，阶段 0 已带入）  | —                                                       | 搬运                            |
| 2  | 剪贴板、Gemini 去水印              | 现有测试兜底                                            | 原样搬运                        |
| 3  | PDF 合并/拆分/提图                 | 补特征测试（pypdf 密封夹具）                            | 渐进重写（并入 BatchRunner 形态） |
| 4  | PDF 压缩/渲染                      | 补依赖注入测试                                          | 重写（GhostscriptCompressor 依赖反转，去掉 AppContainer import） |
| 5  | Office 转换链（Word/Excel/PPT/LO） | 补特征测试（FakeEngine 驱动 + 可选真引擎冒烟）          | 引擎搬运修裸 except；LO 空子类删除；4 循环收敛 BatchRunner |
| 6  | Markdown 文本族                    | 补插件空值守卫测试                                      | 重写（9 处 get_preferred_plugin 判空治理） |
| 7  | 图像族（转换/矢量/取色）           | —                                                       | 搬运                            |
| 8  | Tool Bundle v2（b1）               | ADR-0003 批准后                                         | 重写（去硬编码密钥、签名校验、文档与实现一致） |
| 9  | UI 层收尾                          | 阶段 0 分层守护已生效                                   | threads.py 删 14 遗留类（调用点先换 WorkerThread）；word/excel/ppt 三合一；main_window 拆搜索/图标控制器 |
| 10 | 旧架构清退                         | `rg` 确认零引用                                         | 删除全部旧码（Q7=1 的兑现点）   |

**顺序依据**：测试成熟度与外部依赖从低到高（纯逻辑 → 密封夹具 → 需真引擎），每一步都让可验证性先于改动。

## 4. 特征测试清单（Q8「纯逻辑链路」的具体化）

| 链路                     | 夹具策略                                   | 现状           |
| ------------------------ | ------------------------------------------ | -------------- |
| 批量重命名               | 纯内存/临时目录                           | ✅ 已有 22 符号 |
| PDF 合并/拆分            | pypdf 空白页夹具（conftest 已有雏形）     | ⬜ 补          |
| 配置分层合并             | 临时目录双 JSON                            | ⬜ 补          |
| Tool Bundle 解密/解压    | 测试内现场打包 fixture .mcy + 穿越/symlink 用例 | ⬜ 补（部分已有） |
| Markdown → HTML/DOCX     | 纯文本输入，pandoc 缺席时走纯 Python 分支   | ⬜ 补          |
| Office 转换编排          | FakeEngine（记录信号序列），真引擎冒烟 skip-if-unavailable | ⬜ 补 |

不测：GUI 布局、像素级表现（手工冒烟清单代替：17 个功能页逐个开一次）。

## 5. P0 修复项归属

| P0 项                                | 归属                                       |
| ------------------------------------ | ------------------------------------------ |
| `.mcy` 硬编码密钥 + 无真实性校验     | ADR-0003 → 阶段 1 第 8 步（b1 实施）       |
| `_safe_extract` 符号链接缺口         | 阶段 0 第 5 步（立即，纯加固）             |
| `test_imports.py` 假测试             | 阶段 0 第 4 步（立即）                     |

## 6. 交付纪律（Q14）

- 骨架期：短分支 `refactor/skeleton` → 测试绿合回 main → 之后各模块原子提交直推 main
- 每次收尾：特征测试绿 → `python main.py --benchmark` 记录数值 → 原子提交（提交信息遵循仓库既有中文风格）
- 提交粒度：一个模块（或一个 P0 修复）= 一个提交，可独立回滚

## 7. ADR 索引

| ADR          | 决策                                     | 状态   |
| ------------ | ---------------------------------------- | ------ |
| ADR-0001     | 骨架先行 + 增量迁移 + 完成定义           | 已批准 |
| ADR-0002     | 术语分家：Plugin / Tool Bundle 两词各归其位 | 已批准 |
| ADR-0003     | Tool Bundle v2 信任模型（b1）            | 待批准（见 ADR 内分档推荐） |
