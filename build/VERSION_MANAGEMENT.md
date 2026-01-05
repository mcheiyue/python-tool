# 版本管理指南

## 版本号统一管理

为了保持版本号的一致性，所有版本号定义都集中在以下三个文件中：

### 1. `build_nuitka.bat`
```batch
set APP_VERSION=1.0.0
```

### 2. `build_release.bat`
```batch
set APP_VERSION=1.0.0
```

### 3. `installer.iss`
```inno
#define MyAppVersion "1.0.0"
```

## 升级版本号流程

当需要发布新版本时，按以下步骤操作：

### 方法一：手动修改（推荐初学者）

1. 打开 `build/build_nuitka.bat`
   - 找到 `set APP_VERSION=1.0.0`
   - 修改为新版本号，例如 `set APP_VERSION=1.1.0`

2. 打开 `build/build_release.bat`
   - 找到 `set APP_VERSION=1.0.0`
   - 修改为相同的版本号 `set APP_VERSION=1.1.0`

3. 打开 `build/installer.iss`
   - 找到 `#define MyAppVersion "1.0.0"`
   - 修改为相同的版本号 `#define MyAppVersion "1.1.0"`

### 方法二：使用脚本批量替换（推荐高级用户）

创建一个 PowerShell 脚本来自动更新所有文件中的版本号。

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

升级版本号后，执行以下步骤：

- [ ] 更新 `README.md` 中的版本号和更新日志
- [ ] 确认三个文件中的版本号一致
- [ ] 运行 `build_nuitka.bat` 完成编译
- [ ] 运行 `build_release.bat` 生成发布包
- [ ] 测试所有三种分发版本（安装包、绿化版、单文件版）
- [ ] 创建 Git 标签：`git tag v1.x.x`
- [ ] 推送标签到远程仓库：`git push origin v1.x.x`

## 常见问题

**Q: 为什么版本号要在三个地方定义？**
A: 因为 Batch 脚本和 Inno Setup 脚本使用不同的语法，无法直接共享变量。未来可以考虑使用外部配置文件统一管理。

**Q: 忘记修改某个文件的版本号会怎样？**
A: 可能导致生成的文件名与实际版本不一致，或者安装包显示的版本号错误。建议每次升级都检查三个文件。

**Q: 可以使用 Beta 或 Alpha 版本号吗？**
A: 可以，例如 `1.0.0-beta.1` 或 `1.0.0-alpha.2`，但需要确保在所有三个文件中保持一致。
