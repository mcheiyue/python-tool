# 外部工具供给指南（Manifest + 预置包）

本文档描述 Office Toolkit 外部便携依赖的**真实获取机制**：`plugins/manifest.json`
（官方 URL + SHA256）与预置 zip 分发。第一代 `.mcy` 签名载体已整体退役
（ADR-0003 修订版 + B5 执行），本文「历史」节有删除清单。

## 供给方式

- **Manifest 项**：`plugins/manifest.json` 中按工具名登记 `version/url/sha256`。
  入库可评审——任何人可为清单提 PR 修正版本。
- **预置包**：随安装包分发的 `plugins/<tool>.zip`（上游官方 zip 原样拷贝），
  命中后完全离线可用，不触网。
- **下载兜底**：本地无 zip 时按 manifest URL 下载并校验 hash 后解压。

发现顺序（收拢于 `core/external_tools/base.py`）：

```
libs/<tool>/exe  →  plugins/<tool>.zip  →  manifest 下载解压  →  PATH  →  系统路径
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

## 历史：.mcy 已退役（B5 执行）

`.mcy` 单文件签名包是外部工具的第一代分发载体。ADR-0003 修订版决定转用
Manifest + 预置包后，B5 已整体删除：`core/bundles/format.py`（签名/格式）、
`tools/pack_plugin.py`（打包器）、`core/bundles/loader.py` 的 tar/`.mcy` 读取
路径、`cryptography` 依赖与相关测试。历史 Git 提交保留了全部代码与决策记录；
本目录现只服务 zip 供给链。

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
