# Tool Bundle 开发指南（.mcy v2）

本文档描述 `.mcy` Tool Bundle 的**真实格式与工具链**（v2，见 `docs/adr/0003-tool-bundle-v2-signature-trust-model.md`）。

## 什么是 Tool Bundle

`.mcy` 是 Office Toolkit 的外部工具便携分发包（术语见 `GLOSSARY.md`），仅装载外部二进制工具（Ghostscript、Pandoc 等），**不装载 Python 代码**。

v2 特性：

- **Ed25519 签名**：完整性与来源校验；不再加密（打包对象是开源二进制，保密无意义）
- **LZMA 高压缩**：preset 9
- **v1 不再读取**：旧 AES 加密包一律拒绝，需用下方工具重新打包
- **惰性加载**：使用时解压，支持临时/持久两种模式

## 文件格式（v2）

```
偏移    长度      字段
0        4        Magic: "MCY\x00"
4        1        Version: 2
5        1        Tool ID（0=Ghostscript, 1=Pandoc）
6        8        REST_SIZE（uint64 小端）= 64 + len(压缩数据)
14       64       Ed25519 签名（对压缩数据）
78       ...      LZMA 压缩的 TAR（TAR 内为工具目录）
```

读取（`core/bundles/format.py::read_bundle`）：

1. 校验 Magic 与 Version（非 v2 直接拒绝）
2. 按 REST_SIZE 读满「签名 + 载荷」，字节数不符即文件损坏
3. 内嵌公钥验签，失败抛 `BundleFormatError`
4. LZMA 解压得到 TAR 字节

解压（`core/bundles/loader.py::BundleLoader.extract_bundle`）：

1. 上述读取 + 验签
2. TAR 安全解包：**拒绝符号链接/硬链接**，**拒绝路径穿越**
3. 结果按 .mcy 路径缓存；临时模式解压到 `libs/.temp/session_*`（退出清理），持久模式解压到 `libs/`

## 打包（维护者）

验证公钥内嵌 `core/bundles/format.py`（`BUNDLE_PUBLIC_KEY`）；**签名私钥由维护者离线保管，绝不入库、绝不进 CI 日志**。更换公钥 = 旧 .mcy 全部作废并重打包。

```powershell
# 私钥：32 字节 hex（64 个字符），经环境变量传入，不写入任何文件
$env:MCY_SIGNING_KEY = "<private key hex>"
python tools\pack_plugin.py <源目录> <输出.mcy> [tool_id]
# tool_id: 0=Ghostscript, 1=Pandoc, 2=LibreOffice（默认 0）
#          该字段仅为元数据记录，加载器不据此定位解压位置
```

示例：

```powershell
python tools\pack_plugin.py libs\ghostscript plugins\ghostscript.mcy 0
```

**源目录必须命名为工具名**（`pandoc/`、`ghostscript/`、`libreoffice/`）。
打包用 `arcname=os.path.basename(source_dir)`，消费方按解压后的顶层目录名
定位可执行文件；名字不对的后果是运行时静默回退到 PATH 并报"未安装"。

### 三个维护者子命令

```powershell
# 1) 生成新密钥对（打印私钥 + 需替换进源码的公钥）
python tools\pack_plugin.py --gen-key

# 2) 校验已有 .mcy：验签并打印 tool_id、体积、解压顶层目录名
python tools\pack_plugin.py --verify plugins\pandoc.mcy

# 3) 打包（会自动比对「私钥推导公钥」与「源内嵌公钥」，不一致会告警）
python tools\pack_plugin.py <源目录> <输出.mcy> [tool_id]
```

打包时的公钥比对是硬防线：私钥与内嵌公钥不匹配时签出的包必然被内置校验拒绝，
历史上曾因内嵌公钥抄错导致产出全部不可用。

## 加载（运行时）

```python
from core.bundles.loader import loader

path = loader.extract_bundle("plugins/ghostscript.mcy", persistent=False)
```

- 文件不存在 → 抛 `FileNotFoundError`；验签失败/格式错误/解压失败 → 记录日志并返回 `None`
- `public_key` 参数（默认内嵌官方公钥）是第三方签名的可插拔留位（b2），未实现多公钥注册

## 第三方签名（b2 留位）

当前**只接受官方公钥签名的包**。b2（多贡献者公钥注册）按 ADR-0003 仅留可插拔接口，出现真实需求前不实现。

第三方贡献方式：提交工具二进制源与目录结构说明的 PR，由维护者用私钥打包分发；或自建包仅限自用（需自行改公钥，不受支持）。

## 加载优先级

1. `plugins/*.mcy`（内置资源或用户放置）
2. `libs/`（已解压的持久化工具）
3. 环境变量 PATH
4. 系统安装路径（如 `C:\Program Files`）

## 新增工具接入

1. 在 `core/external_tools/` 新建工具类（继承 `ExternalTool`，定义 `get_search_paths` 等）
2. 在 `core/external_tools/manager.py` 的 `tools` 字典注册
3. 用上方脚本打包为 `.mcy`，放入 `plugins/`

## 运行模式

- **temporary（默认）**：解压到 `libs/.temp/`，退出清理
- **persistent**：解压到 `libs/` 常驻，下次启动免解压

用户可在「设置 → 外部工具」中切换。

## FAQ

- **打包失败**：检查源目录存在、`MCY_SIGNING_KEY` 为 64 字符 hex、输出目录可写
- **加载失败（验签）**：文件被篡改、非官方私钥签名、或 v1 旧包（需重打包）
- **更新版本**：重打包 → 替换 `plugins/*.mcy` → 重启；持久模式需先卸载旧版
