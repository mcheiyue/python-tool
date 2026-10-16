# Tool Bundle v2：以签名取代共享密钥加密

`.mcy` v1 的 AES 密钥硬编码在公开仓库中（`pack_plugin.py:13` / `plugin_loader.py:16`），打包器与加载器共享该密钥，因此加密只能防误改、防不住伪造——而打包工具与文档（PLUGIN_GUIDE.md 欢迎第三方贡献）表明该格式的初衷是**可扩展的生产流水线**，不是保密容器。我们决定（意识形态=b，实施=b1）：v2 格式放弃 AES 加密（打包对象是开源二进制，保密无意义），改为 **LZMA 压缩 + SHA256 清单 + Ed25519 签名**：签名私钥由维护者离线持有、绝不入库，验证公钥内嵌程序；格式头 `VERSION=2`，v1 不再读取（仅需重打包两个官方包）；第三方签名支持以可插拔验证接口留位（b2），出现真实需求前不实现。

**Status**: superseded — 核心决定（以签名为信任锚）已被 ADR-0004 取代；下方修订记录保留完整的五步演进链。

**动机**：修复审查报告 P0 第 1 条（名不副实的安全宣称），同时兑现 Q15' 的 b1 生产线需求（你自己新增 ffmpeg.mcy 等包时，有真实的完整性与来源校验）。

## Considered Options

- **轻档（仅 SHA256 清单）**：拒绝——防损坏不防伪造，P0 的「密钥公开=人人可打包」问题原样保留。
- **保留 AES + 附加签名**：拒绝——密钥既已公开，加密只剩混淆价值；对 GPL 开源二进制混淆无收益，徒增密钥管理面。
- **重档（多贡献者公钥注册表）**：拒绝——目前不存在非维护者的制作者，YAGNI；b2 留了可插拔接口。
- **沿用 v1 兼容**：拒绝——v1 头部无校验字段，无法承载签名，兼容等于放弃修复。

## Consequences

- `docs/PLUGIN_GUIDE.md` 必须随 v2 重写为与实现一致的真实规格（当前文档描述的格式在 v1 中并不存在）。
- 符号链接/硬链接拒绝（P0 第 2 条）不依赖本 ADR，已在阶段 0 先行加固。
- 实施时需在 `tests/test_plugin_loader.py` 补：v2 打包/解包往返、篡改签名拒绝、v1 样本拒绝。

## 实施记录（2026-09-24）

- 测试随模块改名落在 `tests/test_bundle_loader.py`（另含验签密钥不匹配、_safe_extract 链接安全），并覆盖上述三条验收项。
- 「SHA256 清单」未单独实现：Ed25519 签名直接覆盖 LZMA 压缩载荷，完整性由签名承载，独立清单为冗余（YAGNI）。
- 打包器经 `MCY_SIGNING_KEY` 环境变量接收私钥（32 字节 hex），仓库内无任何密钥；验证公钥内嵌 `core/bundles/format.py`。

## 修订记录（2026-10-15）：签名对象改为 TAR 摘要

原实现签的是 LZMA 压缩载荷。`Ed25519PublicKey.verify()` 是一次性 API，必须把
**整个压缩包装进内存**才能验签；加上解压产物，加载 LibreOffice 量级的包（tar 约 1.5GB）
峰值内存远超可接受范围。实测同一 224.6MB tar 的包：签载荷路径峰值 595MB，签摘要路径 106MB。

因此签名对象改为 **TAR 的 SHA256 摘要**（Authenticode/minisign/PEP 427 RECORD 的标准做法）。
磁盘布局不变（`SIGNATURE(64) | COMPRESSED`），仅签名语义改变；加载侧改为
`core.bundles.format.stream_bundle()` 流式解压、边解压边哈希，内存与包体积解耦。

这也意味着当初判为冗余的「SHA256 清单」以更轻的形式回归了——但只需一个摘要而非逐文件清单。
已分发的 v2 实物包（若有）需重新签名；截至本次修订仓库内无入库的 .mcy 实物，
仅本地 `plugins/pandoc.mcy`（gitignored）已重新打包验证：`pandoc 3.12.1` 可执行、
Markdown→HTML 转换正确。

## 修订记录（2026-10-15）：分发模型转向 Manifest + 预置包

**触发**：重新审视「为什么需要这套签名」时确认——单密钥 + 内嵌公钥 + 只能靠发新版
轮换，在威胁模型上等价于一条硬编码 SHA256，却额外带来密钥 ceremony（私钥丢失=永久
停产、泄露=轮换重打）与 `cryptography` 依赖。业界对「应用要带第三方二进制」的标准做法
（winget/scoop）不是维护签名工件，而是维护一份清单：官方 URL + hash，二进制从上游
位级获取。winget 维护者拒绝以 Authenticode 替代 manifest SHA256 的理由可作为判据：
*签名并不证明装的是审过的那个产物，manifest hash 才钉住它*。

**决定**：`.mcy` 从分发载体降级为遗留选项；新增 `plugins/manifest.json`
（tool_id → version/url/sha256）与 `core/tools/downloader.py`（`urllib` 分块下载 +
hash 校验 + 重试 + 取消），发现链扩展为：

```
libs/<tool>/exe → 预置 zip（plugins/<tool>.zip）→ manifest 下载解压 → plugins/<tool>.mcy（遗留）→ PATH → 系统路径
```

- **信任锚**从「私钥签名」变为「manifest 中的 hash + 上游 URL」，溯源强度反而提高
  （二进制位级对齐官方，而非维护者 repack）。
- **维护动作**从「打包+签名 350MB 工件」变为「编辑几十行 JSON」，第三方也可对清单提 PR。
- **`_find()` 的四步发现链**已随 B0 收拢进 `base.ExternalTool`，新步骤只改一处。
- 「按需解压/调用」语义不变：触发时机、双驻留模式、版本指纹缓存、引擎 spawn 全部保留。
- **代价**：新增下载路径的失败面（网络超时/403/URL 腐化），以重试+静默降级到 PATH 应对；
  离线场景随安装包预置 zip 即可。

**待裁决（B5）**：`.mcy` 最终去留——全删 / 留作预置载体（zip+hash 弃签名）/ 双支持。
裁决前 loader 保持读取兼容；本修订生效后新工具一律走 manifest。

## 修订记录（2026-10-15）：B5 执行——`.mcy` 全删

**裁决**：全删。理由：双支持是纯技术债（两套信任模型、两条解压路径、两套测试基线，
却没有任何真实场景需要签名——仓库内从无入库 `.mcy` 实物，唯一本地包已由预置 zip 取代）。

**删除清单**：

- `core/bundles/format.py`（MAGIC/VERSION 头、Ed25519 签名与验签、`pack_bundle`/`read_bundle`/`stream_bundle`）
- `tools/pack_plugin.py`（打包器，含 `--gen-key`/`--verify` 与 `MCY_SIGNING_KEY` 流程）
- `core/bundles/loader.py` 的 tar/`.mcy` 读取路径（`_safe_extract`、`extract_bundle`、`_stage_and_verify`、`_remove_staged`、`_extracted_cache`）；只保留 zip 供给链
- `core/bundles/__init__.py` 的格式层导出
- `tests/test_bundle_loader.py`、`tests/test_bundle_extract_e2e.py`；zip 安全测试中的 tar 遗留用例
- `requirements.txt` 与 `build/check_dependencies.py` 中的 `cryptography`（及其传递依赖 `cffi`/`pycparser` 白名单）

**执行结果**：签名密钥 ceremony 随之终结——私钥此后再无用途。`.mcy` 发现分支从
`_resolve_executable` 移除，发现链回到三步（便携目录 → 上游包装配 → PATH）。
全量测试 133 → 116 passed（少的 17 个即随模块退役的签名/解包用例）。

