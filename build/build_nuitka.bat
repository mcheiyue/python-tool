@echo off
chcp 65001 >nul
echo ==========================================
echo Nuitka 双重构建脚本
echo ==========================================

REM 版本号配置 (统一管理)
REM 版本号来自仓库根 VERSION 文件（唯一来源，勿在此写死）
set /p APP_VERSION=<"%~dp0..\VERSION"

REM 定义公共参数 (避免重复)
REM comtypes.gen 不纳入：应用全程 CreateObject(dynamic=True)，不生成/不读 typelib；该目录在干净机器上不存在，纳入会让构建 FATAL
set COMMON_FLAGS=^
    --mingw64 ^
    --assume-yes-for-downloads ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=assets/processed_icons/icon_transparent.ico ^
    --company-name="OfficeToolkit Team" ^
    --product-name="Office Toolkit" ^
    --file-version=%APP_VERSION% ^
    --product-version=%APP_VERSION% ^
    --file-description="多功能办公工具箱" ^
    --enable-plugin=pyqt6 ^
    --include-qt-plugins=sensible,styles ^
    --nofollow-import-to=tkinter ^
    --include-package=PyQt6 ^
    --include-package=qfluentwidgets ^
    --include-package=comtypes ^
    --include-package=core ^
    --include-package=ui ^
    --include-package=config ^
    --include-package=core.external_tools.ghostscript_tool ^
    --include-package=core.external_tools.pandoc_tool ^
    --include-package=vtracer ^
    --include-data-dir=assets=assets ^
    --include-data-dir=config=config ^
    --include-data-file=VERSION=VERSION ^
    --show-progress ^
    --show-memory ^
    --jobs=10

echo [INFO] 应用版本: %APP_VERSION%
echo [INFO] 编译器: Nuitka with MinGW64
echo.

echo ==========================================
echo [Task 1/2] 构建目录版 (Standalone)
echo ==========================================
echo 用途: 安装包和绿化版
echo 输出: dist\standalone\main.dist\OfficeToolkit.exe
echo.

REM 只删除产物目录，保留编译缓存以加速后续构建
if exist dist\standalone\main.dist (
    echo [INFO] 清理旧的构建产物（保留编译缓存）...
    rmdir /s /q dist\standalone\main.dist
) else (
    echo [INFO] 首次构建，正在创建输出目录...
)

if exist dist\standalone\main.build (
    echo [INFO] 检测到编译缓存，将加速构建过程
)

echo [INFO] 开始编译 (首次: 15-30分钟 / 增量: 5-10分钟)...
call nuitka %COMMON_FLAGS% ^
    --standalone ^
    --output-dir=dist\standalone ^
    --output-filename=OfficeToolkit.exe ^
    main.py || goto ERROR

echo [OK] 目录版编译完成

REM 添加插件目录说明文件
echo [INFO] 添加插件目录结构...
if not exist dist\standalone\main.dist\plugins mkdir dist\standalone\main.dist\plugins
if exist plugins\README.txt copy /Y plugins\README.txt dist\standalone\main.dist\plugins\ >nul

echo.
echo ==========================================
echo [Task 2/2] 构建单文件版 (Onefile)
echo ==========================================
echo 用途: 便携式单文件分发
echo 输出: dist\onefile\OfficeToolkit_Single.exe
echo.

REM 只删除最终的 exe 文件，保留编译缓存
if exist dist\onefile\OfficeToolkit_Single.exe (
    echo [INFO] 清理旧的单文件产物（保留编译缓存）...
    del /f /q dist\onefile\OfficeToolkit_Single.exe
) else (
    echo [INFO] 首次构建单文件版...
    if not exist dist\onefile mkdir dist\onefile
)

if exist dist\onefile\main.build (
    echo [INFO] 检测到编译缓存，将加速构建过程
)

echo [INFO] 开始编译 (首次: 15-30分钟 / 增量: 5-10分钟)...
echo [INFO] onefile 模式会先生成 standalone 再打包成单文件
call nuitka %COMMON_FLAGS% ^
    --onefile ^
    --include-data-dir=plugins=plugins ^
    --output-dir=dist\onefile ^
    --output-filename=OfficeToolkit_Single.exe ^
    main.py || goto ERROR

echo [OK] 单文件版编译完成

echo.
echo ==========================================
echo [SUCCESS] 所有构建完成！
echo ==========================================
echo 版本: %APP_VERSION%
echo 构建时间: %date% %time%
echo.
echo 1. 目录版 (Standalone): dist\standalone\main.dist\OfficeToolkit.exe
echo    - 用于制作安装包和绿化版
echo    - 结构清晰，启动速度快
echo    - 大小: ~150MB (含所有依赖)
echo.
echo 2. 单文件版 (Onefile): dist\onefile\OfficeToolkit_Single.exe
echo    - 内置所有插件，真正的单文件分发
echo    - 适合快速分享和便携使用
echo    - 大小: ~80MB (压缩后)
echo ==========================================
echo.
echo [提示] 验证构建产物是否存在...
if exist dist\standalone\main.dist\OfficeToolkit.exe (
    echo [✓] 目录版: 存在
) else (
    echo [✗] 目录版: 缺失！
)
if exist dist\onefile\OfficeToolkit_Single.exe (
    echo [✓] 单文件版: 存在
) else (
    echo [✗] 单文件版: 缺失！
)
echo.
echo 下一步：运行 build_release.bat 制作完整发布包
echo.
pause
exit /b 0

:ERROR
echo.
echo ==========================================
echo [ERROR] 编译失败！
echo ==========================================
echo 错误代码: %errorlevel%
echo.
echo 常见问题排查:
echo 1. 检查是否安装了 MinGW64 (Nuitka 需要)
echo 2. 检查磁盘空间是否充足 (至少需要 2GB)
echo 3. 检查是否有杀毒软件拦截
echo 4. 查看上方详细错误信息
echo ==========================================
pause
exit /b 1
