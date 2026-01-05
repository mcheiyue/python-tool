@echo off
chcp 65001 >nul
echo ==========================================
echo Office Toolkit 发布打包脚本
echo ==========================================

REM 检查 dist 目录
if not exist "dist\release\main.dist\OfficeToolkit.exe" (
    echo [ERROR] 未找到 dist\release\main.dist\OfficeToolkit.exe
    echo 请先运行 build_nuitka.bat 进行编译！
    pause
    exit /b 1
)

REM 创建 release 目录
if not exist release mkdir release

echo.
echo [Step 1] 制作安装包 (Installer)...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% build\installer.iss
    if %errorlevel% neq 0 (
        echo [ERROR] Inno Setup 编译失败！
        pause
        exit /b 1
    )
    echo 安装包已生成: release\OfficeToolkit_Setup_v1.0.0.exe
) else (
    echo [WARNING] 未找到 Inno Setup编译器，跳过安装包制作。
    echo 请确保安装在默认路径: %ISCC%
)

echo.
echo [Step 2] 制作绿化版 (Portable ZIP)...

REM 清理临时目录
if exist release\temp_portable rmdir /s /q release\temp_portable
mkdir release\temp_portable

REM 复制整个 standalone 目录
echo 正在复制 standalone 目录...
xcopy dist\release\main.dist release\temp_portable\OfficeToolkit /E /I /Y >nul

REM 确保 plugins 目录存在并包含说明文件
if not exist release\temp_portable\OfficeToolkit\plugins mkdir release\temp_portable\OfficeToolkit\plugins
if exist plugins\README.txt copy /Y plugins\README.txt release\temp_portable\OfficeToolkit\plugins\ >nul

REM 压缩打包
echo 正在压缩 ZIP...
powershell Compress-Archive -Path release\temp_portable\OfficeToolkit -DestinationPath release\OfficeToolkit_Portable_v1.0.0.zip -Force

REM 清理临时目录
rmdir /s /q release\temp_portable

echo 绿化版已生成: release\OfficeToolkit_Portable_v1.0.0.zip

echo.
echo ==========================================
echo 全部打包完成！
echo ==========================================
echo 输出目录: %CD%\release
pause
