# 版本管理指南

## 版本号唯一来源

版本号只在一个地方定义：

```
VERSION        # 仓库根目录，纯文本，内容形如 0.0.1
```

改版本号 = 改这一个文件。所有消费方都从这里读，**不要在别处再写死版本号**：

| 消费方                | 读取方式                                                          |
| --------------------- | ----------------------------------------------------------------- |
| `build/build_nuitka.bat`  | `set /p APP_VERSION=<"%~dp0..\VERSION"`                             |
| `build/build_release.bat` | 同上                                                              |
| `build/build_dev.bat`     | 同上，`--file-version=%APP_VERSION%`                                |
| `build/installer.iss`     | ISPP 预处理期 `FileRead("..\VERSION")`                              |
| 运行时（崩溃报告等）  | `core/utils/version.py` 的 `get_app_version()`（读打包进去的 VERSION） |
| CI/CD                 | `.github/workflows/release.yml` 校验 `git tag` == `VERSION`           |

`tests/test_version_consistency.py` 会守住这条约束：构建脚本里出现写死的版本号即测试失败。

## 升级版本号流程

1. 修改 `VERSION`（例如改成 `1.1.0`）
2. 在 `docs/CHANGELOG.md` 补一条对应版本的记录
3. （可选）本地验证：`build\build_dev.bat` 编一个开发版看文件属性
4. 提交、打 tag、推送：

```powershell
git tag v1.1.0
git push origin v1.1.0
```

`tag v1.1.0` 与 `VERSION` 内容不一致时，Release 工作流会在第一步直接报错退出——
所以打 tag 前先确认两者相同。

## 版本号命名规范

遵循语义化版本 (Semantic Versioning)：

```
主版本号.次版本号.修订号
MAJOR.MINOR.PATCH
```

- **主版本号 (MAJOR)**：不兼容的 API 修改
- **次版本号 (MINOR)**：向下兼容的功能性新增
- **修订号 (PATCH)**：向下兼容的问题修正

### 示例

- `1.0.0` → `1.0.1`：修复 bug
- `1.0.1` → `1.1.0`：新增功能
- `1.1.0` → `2.0.0`：重大重构或不兼容变更

## 发布检查清单

- [ ] 使用 Python 3.12.10 x64 和 Inno Setup 6.7.1
- [ ] 在独立虚拟环境按下方锁定命令安装依赖
- [ ] `VERSION` 已改为目标版本
- [ ] `docs/CHANGELOG.md` 已记录该版本
- [ ] 本地跑过测试：`python -m pytest`
- [ ] `git tag vX.Y.Z` 与 `VERSION` 一致
- [ ] 推送 tag 后，在 Actions 页面确认 Release 工作流通过
- [ ] 到 Releases 页确认三个产物（安装包 / 绿化 zip / 单文件）均已上传

## 发布依赖锁定

`requirements.txt` 保留直接依赖范围，`requirements.lock` 固定 Windows 发布所用的直接和传递依赖，以及 pip、Nuitka、setuptools、wheel、toml。普通安装同样通过约束文件使用这些固定版本。CI 和 Release 均执行下列安装命令；本地构建须在 Python 3.12.10 x64 的独立虚拟环境中执行：

```powershell
python -m pip install -r build/requirements-bootstrap.txt
python -m pip install --no-build-isolation --no-deps -r requirements.lock
python -m pip check
python -m pytest
build\build_nuitka.bat
build\build_release.bat
```

先安装锁定的构建基础包，再禁用隔离构建和隐式依赖安装，避免安装 Nuitka 时又引入未固定的构建依赖。安装器使用 Inno Setup 6.7.1；工作流的中文语言文件固定到上游提交。

升级依赖时，在干净环境解析并更新锁定文件的完整依赖集合，运行上述检查及可写/只读目录产物冒烟后再发布，不在 CI 中自动升级。初始锁定采用本机已验证的 PyMuPDF 1.28.2 / Qt 6.11 组合；v0.0.13 的未锁定构建曾自动升级为 PyMuPDF 2.1 / Qt 6.12。缓存随锁定文件、解释器版本和构建参数变化而失效；业务代码变化不使依赖缓存整体失效。

这是依赖版本可重复的构建流程，不承诺生成逐字节一致的 exe；GitHub 托管系统镜像仍会接收系统更新。

## 常见问题

**Q: 为什么不能让 bat 和 Inno Setup 直接共享一个变量？**
A: 两者语法不同、又不通过 shell 互相调用，所以它们各自读同一个 `VERSION` 文件；
`VERSION` 就是那个共享的外部来源。

**Q: 忘记同步某个文件的版本号会怎样？**
A: 不会了——除 `VERSION` 外没有任何地方写死版本号，`test_version_consistency.py`
会拦下回退到写死的改动。

**Q: 可以使用 Beta 或 Alpha 版本号吗？**
A: 可以，但 `VERSION` 与 tag 都要写全，例如 `VERSION` = `1.0.0-beta.1`、
tag = `v1.0.0-beta.1`。注意 Inno Setup 的 `AppVersion` 对非数字后缀的容忍度有限，
正式分发给用户前建议只发数字三段式版本。
