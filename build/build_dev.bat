@echo off
chcp 65001 >nul
echo ==========================================
echo Nuitka 极速开发编译 - 目录模式 (Standalone)
echo ==========================================
echo 说明: 此模式不生成单文件 EXE，而是生成包含所有依赖的文件夹。
echo 优势: 编译速度快，启动速度快，适合开发调试。
echo ==========================================

echo.
echo [Step 1] 清理旧的开发构建...
if exist dist\dev rmdir /s /q dist\dev

echo.
echo [Step 2] 开始 Nuitka 编译 (开发模式)...

nuitka ^
    --mingw64 ^
    --standalone ^
    --windows-console ^
    --windows-icon-from-ico=assets/processed_icons/icon_transparent.ico ^
    --product-name="Office Toolkit (Dev)" ^
    --file-description="多功能办公工具箱 (开发版)" ^
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
    --output-dir=dist/dev ^
    --output-filename=OfficeToolkit.exe ^
    --show-progress ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 编译失败！请检查上方错误信息。
    pause
    exit /b %errorlevel%
)

echo.
echo [Step 3] 编译完成！
echo.
echo ==========================================
echo 运行程序请执行: dist\dev\main.dist\OfficeToolkit.exe
echo ==========================================
echo.
pause
