@echo off
chcp 65001 >nul
echo ==========================================
echo 环境验证检查
echo ==========================================

echo.
echo [1] 检查 Python 版本...
python --version

echo.
echo [2] 检查 Nuitka...
nuitka --version

echo.
echo [3] 检查 C 编译器...
gcc --version >nul 2>&1
if %errorlevel% equ 0 (
    gcc --version
) else (
    cl >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found MSVC (cl.exe)
    ) else (
        echo [WARNING] 未找到 GCC 或 MSVC 编译器，Nuitka 可能会报错或回退到慢速模式。
        echo 请安装 MinGW64 或 Visual Studio Build Tools。
    )
)

echo.
echo [4] 检查 Inno Setup...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /? >nul
    echo Inno Setup 6 已安装。
) else (
    echo [WARNING] 未找到 Inno Setup 6 (默认路径)。
    echo 请确认是否安装，或路径是否不同。
)

echo.
echo [5] 检查依赖...
python build/check_dependencies.py

echo.
echo [6] 测试应用启动 (仅检查帮助信息)...
python main.py --help >nul 2>&1
if %errorlevel% equ 0 (
    echo 应用主程序可正常启动。
) else (
    echo [ERROR] 应用主程序启动失败，请检查环境。
)

echo.
echo ==========================================
echo 环境检查完成！
echo ==========================================
