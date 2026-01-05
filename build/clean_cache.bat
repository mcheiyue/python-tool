@echo off
chcp 65001 >nul
echo ==========================================
echo Nuitka 缓存清理工具
echo ==========================================
echo.
echo 此脚本将删除所有编译缓存和构建产物
echo 下次编译将从零开始（耗时更长，但确保干净）
echo.
echo 缓存目录大小通常: 500MB - 1GB
echo.

REM 检查是否存在缓存
set HAS_CACHE=0
if exist dist\standalone\main.build set HAS_CACHE=1
if exist dist\onefile\main.build set HAS_CACHE=1

if %HAS_CACHE%==0 (
    echo [INFO] 未发现编译缓存
    goto END
)

echo 将要删除的内容:
if exist dist\standalone\main.build echo   - dist\standalone\main.build\ (目录版缓存)
if exist dist\onefile\main.build echo   - dist\onefile\main.build\ (单文件版缓存)
if exist dist\standalone\main.dist echo   - dist\standalone\main.dist\ (目录版产物)
if exist dist\onefile\OfficeToolkit_Single.exe echo   - dist\onefile\OfficeToolkit_Single.exe (单文件版产物)
echo.

choice /C YN /M "确认删除所有缓存和产物吗"
if errorlevel 2 goto CANCEL
if errorlevel 1 goto CLEAN

:CLEAN
echo.
echo [INFO] 正在清理...

if exist dist\standalone\main.build (
    echo [INFO] 删除目录版编译缓存...
    rmdir /s /q dist\standalone\main.build
)

if exist dist\onefile\main.build (
    echo [INFO] 删除单文件版编译缓存...
    rmdir /s /q dist\onefile\main.build
)

if exist dist\standalone\main.dist (
    echo [INFO] 删除目录版构建产物...
    rmdir /s /q dist\standalone\main.dist
)

if exist dist\onefile\OfficeToolkit_Single.exe (
    echo [INFO] 删除单文件版构建产物...
    del /f /q dist\onefile\OfficeToolkit_Single.exe
)

REM 清理 Nuitka 全局缓存（可选）
echo.
choice /C YN /M "是否同时清理 Nuitka 全局缓存（位于用户目录）"
if errorlevel 2 goto DONE
if errorlevel 1 goto CLEAN_GLOBAL

:CLEAN_GLOBAL
if exist "%LOCALAPPDATA%\Nuitka\Nuitka\Cache" (
    echo [INFO] 清理 Nuitka 全局缓存...
    rmdir /s /q "%LOCALAPPDATA%\Nuitka\Nuitka\Cache"
)

:DONE
echo.
echo ==========================================
echo [SUCCESS] 清理完成！
echo ==========================================
echo.
echo 下次运行 build_nuitka.bat 将进行完全重新编译
echo 预计耗时: 30-60 分钟（取决于硬件配置）
echo.
goto END

:CANCEL
echo.
echo [INFO] 已取消清理操作
echo.

:END
pause
exit /b 0
