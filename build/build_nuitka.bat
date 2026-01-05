@echo off
chcp 65001 >nul
echo ==========================================
echo Nuitka 编译脚本 - 生成 Standalone 发布版
echo ==========================================

echo.
echo [Step 1] 清理旧的输出目录...
if exist dist\release rmdir /s /q dist\release

echo.
echo [Step 2] 开始 Nuitka 编译 (增量模式)...
echo 注意：首次编译可能需要较长时间 (下载依赖/编译缓存)，请耐心等待。

nuitka ^
    --mingw64 ^
    --standalone ^
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
    --output-dir=dist/release ^
    --output-filename=OfficeToolkit.exe ^
    --show-progress ^
    --show-memory ^
    --jobs=10 ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 编译失败！请检查上方错误信息。
    pause
    exit /b %errorlevel%
)

echo.
echo [Step 3] 复制插件目录说明文件...
if not exist dist\release\main.dist\plugins mkdir dist\release\main.dist\plugins
if exist plugins\README.txt copy /Y plugins\README.txt dist\release\main.dist\plugins\ >nul

echo.
echo [Step 4] 编译完成！
echo ==========================================
echo 输出位置: dist\release\main.dist\
echo 可执行文件: dist\release\main.dist\OfficeToolkit.exe
echo ==========================================
echo 说明: 
echo - 用户可以将 .mcy 插件文件放到 plugins\ 目录下
echo - 请运行 build_release.bat 制作安装包和绿化版
echo.
pause
