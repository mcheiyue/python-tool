@echo off
chcp 65001 >nul
echo ==========================================
echo Office Toolkit 全渠道发布打包脚本
echo ==========================================

REM 检查编译产物
if not exist "dist\standalone\main.dist\OfficeToolkit.exe" (
    echo [ERROR] 未找到目录版构建产物 (dist\standalone\main.dist)
    goto ERROR
)
if not exist "dist\onefile\OfficeToolkit_Single.exe" (
    echo [ERROR] 未找到单文件版构建产物 (dist\onefile)
    goto ERROR
)

REM 清理重建 release 目录
if exist release rmdir /s /q release
mkdir release

echo.
echo [Step 1] 制作安装包 (Installer)...
echo 输入源: dist\standalone (目录版)
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% build\installer.iss
    if %errorlevel% neq 0 (
        echo [ERROR] Inno Setup 编译失败！
        pause
        exit /b 1
    )
    echo [OK] 安装包已生成
) else (
    echo [WARNING] 未找到 Inno Setup，跳过安装包制作。
    echo 请确保安装在默认路径: %ISCC%
)

echo.
echo [Step 2] 制作绿化版 (Portable ZIP)...
echo 输入源: dist\standalone (目录版)

mkdir release\temp_portable
REM 复制 standalone 构建的所有内容 (包含 EXE, _internal, 和已经打包进去的 config/assets)
xcopy dist\standalone\main.dist release\temp_portable\OfficeToolkit\ /E /I /Y >nul

REM 确保空的插件目录供用户使用
if not exist release\temp_portable\OfficeToolkit\plugins mkdir release\temp_portable\OfficeToolkit\plugins
if exist plugins\README.txt copy /Y plugins\README.txt release\temp_portable\OfficeToolkit\plugins\ >nul

REM 如果需要外部 libs，这里复制
if exist libs xcopy libs release\temp_portable\OfficeToolkit\libs\ /E /I /Y >nul

echo 正在压缩 ZIP...
powershell Compress-Archive -Path release\temp_portable\OfficeToolkit -DestinationPath release\OfficeToolkit_Portable_v1.0.0.zip -Force
rmdir /s /q release\temp_portable
echo [OK] 绿化版已生成

echo.
echo [Step 3] 复制单文件版...
copy dist\onefile\OfficeToolkit_Single.exe release\OfficeToolkit_Single_v1.0.0.exe >nul
echo [OK] 单文件版已就绪

echo.
echo ==========================================
echo 全部打包完成！
echo ==========================================
echo 输出目录: %CD%\release
echo.
echo 文件清单:
if exist release\OfficeToolkit_Setup_v1.0.0.exe echo   [✓] OfficeToolkit_Setup_v1.0.0.exe (安装包)
echo   [✓] OfficeToolkit_Portable_v1.0.0.zip (绿化版)
echo   [✓] OfficeToolkit_Single_v1.0.0.exe (单文件版)
echo ==========================================
pause
exit /b 0

:ERROR
echo.
echo 请先运行 build_nuitka.bat 完成双重编译！
pause
exit /b 1
