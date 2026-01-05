@echo off
chcp 65001 >nul
echo ==========================================
echo Nuitka 编译脚本 - 生成独立 EXE
echo ==========================================

echo.
echo [Step 1] 清理旧的 EXE 文件...
if exist dist\OfficeToolkit.exe del /f /q dist\OfficeToolkit.exe

echo.
echo [Step 2] 开始 Nuitka 编译 (增量模式)...
echo 注意：首次编译可能需要较长时间 (下载依赖/编译缓存)，请耐心等待。

nuitka ^
    --mingw64 ^
    --standalone ^
    --onefile ^
    --windows-disable-console ^
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
    --output-dir=dist ^
    --output-filename=OfficeToolkit.exe ^
    --show-progress ^
    --show-memory ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 编译失败！请检查上方错误信息。
    pause
    exit /b %errorlevel%
)

echo.
echo [Step 3] 编译完成！
echo 输出位置: dist\OfficeToolkit.exe
echo.
pause
