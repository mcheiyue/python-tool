@echo off
chcp 65001 >nul
echo ==========================================
echo Office Toolkit 全渠道发布打包脚本
echo ==========================================

REM 版本号配置 (与 build_nuitka.bat 保持一致)
set APP_VERSION=1.0.0

echo [INFO] 应用版本: %APP_VERSION%
echo [INFO] 开始打包发布文件...
echo.

REM 检查编译产物
echo [Step 0] 验证构建产物...
set BUILD_OK=1

if not exist "dist\standalone\main.dist\OfficeToolkit.exe" (
    echo [✗] 目录版构建产物: dist\standalone\main.dist\OfficeToolkit.exe - 缺失！
    set BUILD_OK=0
) else (
    echo [✓] 目录版构建产物: 存在
)

if not exist "dist\onefile\OfficeToolkit_Single.exe" (
    echo [✗] 单文件版构建产物: dist\onefile\OfficeToolkit_Single.exe - 缺失！
    set BUILD_OK=0
) else (
    echo [✓] 单文件版构建产物: 存在
)

if %BUILD_OK%==0 goto ERROR
echo [OK] 所有构建产物验证通过
echo.

REM 清理重建 release 目录
echo [INFO] 清理旧的发布文件...
if exist release rmdir /s /q release
mkdir release
echo [OK] release 目录已就绪
echo.

echo ==========================================
echo [Step 1/3] 制作安装包 (Installer)
echo ==========================================
echo 输入源: dist\standalone\main.dist
echo 输出: release\OfficeToolkit_Setup_v%APP_VERSION%.exe
echo.
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo [INFO] 正在编译安装包...
    %ISCC% build\installer.iss
    if %errorlevel% neq 0 (
        echo [ERROR] Inno Setup 编译失败！错误代码: %errorlevel%
        pause
        exit /b 1
    )
    echo [OK] 安装包已生成
) else (
    echo [WARNING] 未找到 Inno Setup，跳过安装包制作
    echo [WARNING] 默认路径: %ISCC%
    echo [提示] 如需制作安装包，请安装 Inno Setup 6
)

echo.
echo ==========================================
echo [Step 2/3] 制作绿化版 (Portable ZIP)
echo ==========================================
echo 输入源: dist\standalone\main.dist
echo 输出: release\OfficeToolkit_Portable_v%APP_VERSION%.zip
echo.

echo [INFO] 准备绿化版文件结构...
mkdir release\temp_portable

REM 复制 standalone 构建的所有内容 (包含 EXE, _internal, 和已经打包进去的 config/assets)
echo [INFO] 复制主程序文件...
xcopy dist\standalone\main.dist release\temp_portable\OfficeToolkit\ /E /I /Y >nul

REM 确保空的插件目录供用户使用
echo [INFO] 添加插件目录结构...
if not exist release\temp_portable\OfficeToolkit\plugins mkdir release\temp_portable\OfficeToolkit\plugins
if exist plugins\README.txt copy /Y plugins\README.txt release\temp_portable\OfficeToolkit\plugins\ >nul

REM 如果需要外部 libs，这里复制
if exist libs (
    echo [INFO] 复制外部库...
    xcopy libs release\temp_portable\OfficeToolkit\libs\ /E /I /Y >nul
)

echo [INFO] 正在压缩为 ZIP (使用最大压缩率)...
powershell Compress-Archive -Path release\temp_portable\OfficeToolkit -DestinationPath release\OfficeToolkit_Portable_v%APP_VERSION%.zip -Force -CompressionLevel Optimal
rmdir /s /q release\temp_portable
echo [OK] 绿化版已生成

echo.
echo ==========================================
echo [Step 3/3] 复制单文件版
echo ==========================================
echo 输入源: dist\onefile\OfficeToolkit_Single.exe
echo 输出: release\OfficeToolkit_Single_v%APP_VERSION%.exe
echo.
echo [INFO] 复制单文件版...
copy dist\onefile\OfficeToolkit_Single.exe release\OfficeToolkit_Single_v%APP_VERSION%.exe >nul
echo [OK] 单文件版已就绪

echo.
echo ==========================================
echo 全部打包完成！
echo ==========================================
echo 版本: %APP_VERSION%
echo 打包时间: %date% %time%
echo 输出目录: %CD%\release
echo.
echo 文件清单:
if exist release\OfficeToolkit_Setup_v%APP_VERSION%.exe (
    echo   [✓] OfficeToolkit_Setup_v%APP_VERSION%.exe ^(安装包^)
    for %%A in (release\OfficeToolkit_Setup_v%APP_VERSION%.exe) do echo       大小: %%~zA 字节
) else (
    echo   [✗] OfficeToolkit_Setup_v%APP_VERSION%.exe ^(未生成^)
)

if exist release\OfficeToolkit_Portable_v%APP_VERSION%.zip (
    echo   [✓] OfficeToolkit_Portable_v%APP_VERSION%.zip ^(绿化版^)
    for %%A in (release\OfficeToolkit_Portable_v%APP_VERSION%.zip) do echo       大小: %%~zA 字节
) else (
    echo   [✗] OfficeToolkit_Portable_v%APP_VERSION%.zip ^(失败^)
)

if exist release\OfficeToolkit_Single_v%APP_VERSION%.exe (
    echo   [✓] OfficeToolkit_Single_v%APP_VERSION%.exe ^(单文件版^)
    for %%A in (release\OfficeToolkit_Single_v%APP_VERSION%.exe) do echo       大小: %%~zA 字节
) else (
    echo   [✗] OfficeToolkit_Single_v%APP_VERSION%.exe ^(失败^)
)
echo ==========================================
echo.
echo [提示] 发布前检查清单:
echo   1. 测试安装包是否正常安装和卸载
echo   2. 测试绿化版解压后能否正常运行
echo   3. 测试单文件版能否正常启动
echo   4. 检查所有版本的功能是否完整
echo.
pause
exit /b 0

:ERROR
echo.
echo ==========================================
echo [ERROR] 打包失败！
echo ==========================================
echo.
echo 原因: 缺少必要的构建产物
echo.
echo 解决方法:
echo 1. 运行 build_nuitka.bat 完成双重编译
echo 2. 确保编译过程没有错误
echo 3. 验证以下文件存在:
echo    - dist\standalone\main.dist\OfficeToolkit.exe
echo    - dist\onefile\OfficeToolkit_Single.exe
echo ==========================================
pause
exit /b 1
