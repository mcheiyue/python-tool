@echo off
chcp 65001 >nul
echo ==========================================
echo Nuitka 双重构建脚本
echo ==========================================

REM 定义公共参数 (避免重复)
set COMMON_FLAGS=^
    --mingw64 ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=assets/processed_icons/icon_transparent.ico ^
    --company-name="OfficeToolkit Team" ^
    --product-name="Office Toolkit" ^
    --file-version=1.0.0 ^
    --product-version=1.0.0 ^
    --file-description="多功能办公工具箱" ^
    --enable-plugin=pyqt6 ^
    --include-qt-plugins=sensible,styles ^
    --nofollow-import-to=tkinter ^
    --include-package=PyQt6 ^
    --include-package=qfluentwidgets ^
    --include-package=comtypes ^
    --include-package=comtypes.gen ^
    --include-package=core ^
    --include-package=ui ^
    --include-package=config ^
    --include-package=core.external_tools.ghostscript_tool ^
    --include-package=core.external_tools.pandoc_tool ^
    --include-package=vtracer ^
    --include-data-dir=assets=assets ^
    --include-data-dir=config=config ^
    --show-progress ^
    --show-memory ^
    --jobs=10

echo.
echo [Task 1/2] 构建目录版 (Standalone) - 用于安装包和绿化版...
if exist dist\standalone rmdir /s /q dist\standalone

nuitka %COMMON_FLAGS% ^
    --standalone ^
    --output-dir=dist\standalone ^
    --output-filename=OfficeToolkit.exe ^
    main.py

if %errorlevel% neq 0 goto ERROR

REM 添加插件目录说明文件
if not exist dist\standalone\main.dist\plugins mkdir dist\standalone\main.dist\plugins
if exist plugins\README.txt copy /Y plugins\README.txt dist\standalone\main.dist\plugins\ >nul

echo.
echo [Task 2/2] 构建单文件版 (Onefile) - 用于单文件发布...
if exist dist\onefile rmdir /s /q dist\onefile

nuitka %COMMON_FLAGS% ^
    --standalone ^
    --onefile ^
    --include-data-dir=plugins=plugins ^
    --output-dir=dist\onefile ^
    --output-filename=OfficeToolkit_Single.exe ^
    main.py

if %errorlevel% neq 0 goto ERROR

echo.
echo ==========================================
echo [SUCCESS] 所有构建完成！
echo ==========================================
echo 1. 目录版 (Standalone): dist\standalone\main.dist\OfficeToolkit.exe
echo    - 用于制作安装包和绿化版
echo    - 结构清晰，启动速度快
echo.
echo 2. 单文件版 (Onefile): dist\onefile\OfficeToolkit_Single.exe
echo    - 内置所有插件，真正的单文件分发
echo    - 适合快速分享和便携使用
echo ==========================================
echo.
echo 下一步：运行 build_release.bat 制作完整发布包
echo.
pause
exit /b 0

:ERROR
echo.
echo [ERROR] 编译失败！请检查上方错误信息。
pause
exit /b 1
