# 外部工具供给指南（Manifest + 预置包）

本文档描述 Office Toolkit 外部便携依赖的**真实获取机制**：`plugins/manifest.json`
（官方 URL + SHA256）与预置 zip 分发；`.mcy` 签名载体已降级为遗留选项
（ADR-0003 修订版），去留待 B5 裁决。

## 供给方式

- **Manifest 项**：`plugins/manifest.json` 中按工具名登记 `version/url/sha256`。
  入库可评审——任何人可为清单提 PR 修正版本。
- **预置包**：随安装包分发的 `plugins/<tool>.zip`（上游官方 zip 原样拷贝），
  命中后完全离线可用，不触网。
- **下载兜底**：本地无 zip 时按 manifest URL 下载并校验 hash 后解压。

发现顺序（收拢于 `core/external_tools/base.py`）：

```
libs/<tool>/exe  →  plugins/<tool>.zip  →  manifest 下载解压  →  plugins/<tool>.mcy（遗留）  →  PATH  →  系统路径
```

## 维护 Manifest（维护者/贡献者）

新增或更新一个外部工具只需三步：

```powershell
# 1. 从官方 URL 下载 zip（初装/「一键安装」会自动下载到 plugins/<tool>.zip）
# 2. 用下载器自带的能力算 hash 并校对，编辑 plugins/manifest.json：
python -c "from core.tools.downloader import sha256_file; print(sha256_file('plugins/pandoc.zip'))"
```

```json
"pandoc": {
  "version": "3.12.1",
  "url": "https://github.com/jgm/pandoc/releases/download/3.12.1/pandoc-3.12.1-windows-x86_64.zip",
  "sha256": "6ef431cb20b2c24a0371fc19200dc49d452be54b1b5c9239f3462841ef53e587"
}
```

```powershell
# 3. 入库提交；用户下次启动/「一键安装」即生效
```

**hash 是信任锚**：二进制必须来自 URL 指向的官方产物，hash 由下载方计算并记录。
替换二进制 = 同时改 hash；只有 hash 匹配才会被解压。

## 运行时行为

- **按需安装**：页面显示或点击开始时发现工具不在本地 → 临时模式下载解压到
  `libs/.temp/session_*`（退出清理）或持久模式解压到 `libs/`（下次直连缓存）。
- **静默降级**：网络失败/URL 腐化/校验不符 → 记录日志，回退到 PATH/系统路径；
  界面不弹错，按钮按未安装呈现，不阻塞其他功能。
- **一键安装**：设置页未安装卡片显示「一键安装」（manifest 有条目时），
  下载进度在 InfoBar 上实时更新，完成后自动重新探测版本。
- **版本缓存**：`dependencies.tool_version_cache` 按 (mtime, size) 指纹命中，
  换进程不重复 spawn `--version`。

## 新增工具接入

1. 在 `core/external_tools/` 新建工具类（继承 `ExternalTool`，`_find()` 实现平台特有
   的第 4 步系统路径探测；发现链前 3 步在基类已收拢）
2. 在 `core/external_tools/manager.py` 的 `tools` 字典注册
3. 在 `plugins/manifest.json` 登记该工具的 url/sha256
4. 需要离线分发包时，把官方 zip 拷到 `plugins/<tool>.zip`（gitignored）

## 遗留：.mcy（待裁决）

ADR-0003 修订版记录了 `.mcy` 降级为遗留的原因与演变。当前实现仍可读取：

```python
from core.bundles.loader import loader
path = loader.extract_bundle("plugins/pandoc.mcy", persistent=False)
```

维护性说明（不再演进）：

- `tools/pack_plugin.py` 的 `MCY_SIGNING_KEY` 私钥流程与 `--gen-key/--verify` 仅用于
  历史遗留包的再签名与校验；新工具不使用。
- `plugins/*.mcy` 仍可在发现链中作为回退源，但优先级低于预置 zip。
- **B5 待裁决**：全删 / 转为预置载体（zip+hash 弃签名）/ 双支持。裁决前代码与本文
  「遗留」章节保持现状。

## 运行模式

- **temporary（默认）**：解压到 `libs/.temp/`，退出清理
- **persistent**：解压到 `libs/` 常驻，下次启动免解压

用户可在「设置 → 外部工具」中切换。

## FAQ

- **一键安装失败**：网络不通、URL 失效、或 hash 与 manifest 不符——改用「下载」按钮
  去官网手动获取，放入 `plugins/` 后重启
- **加载失败（hash）**：zip 被替换/损坏，重新下载官方产物并核对 hash
- **更新版本**：改 manifest 的 version/url/sha256 → 用户点「一键安装」或删掉旧
  `libs/<tool>/` 后重启；持久模式需先卸载旧版
