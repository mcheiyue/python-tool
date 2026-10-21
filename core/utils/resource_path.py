import os
import sys
import tempfile
from pathlib import Path

def get_app_root():
    """
    获取应用程序根目录（用户可访问的外部数据目录）
    - 开发环境：项目根目录
    - Nuitka Onefile：真实 EXE 所在目录（非临时解压目录）
    - Nuitka Standalone：EXE 所在目录
    """
    if getattr(sys, 'frozen', False):
        # Nuitka 打包环境
        # 使用 sys.executable 获取真实的 EXE 路径（Onefile 和 Standalone 都适用）
        # sys.argv[0] 在某些情况下可能不可靠
        exe_path = sys.executable
        return os.path.dirname(os.path.abspath(exe_path))
    else:
        # 开发环境
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # core/utils/resource_path.py -> core/utils -> core -> root
            return os.path.dirname(os.path.dirname(current_dir))
        except Exception:
            # __file__ 不可用时，使用当前工作目录作为后备方案
            return os.getcwd()

def get_resource_path(relative_path):
    """
    获取内部资源的绝对路径 (如图标、UI文件)
    - 开发环境：项目根目录/relative_path
    - Nuitka Onefile：临时解压目录/relative_path
    """
    if getattr(sys, 'frozen', False):
        # Nuitka 内部资源位于临时解压目录
        # __file__ 指向 dist/core/utils/resource_path.pyd
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 回退到根目录 (dist)
        base_path = os.path.dirname(os.path.dirname(current_dir))
        return os.path.join(base_path, relative_path)
    else:
        # 开发环境：直接使用项目根目录
        return os.path.join(get_app_root(), relative_path)


def get_data_root() -> Path:
    """可写数据根目录（logs / config.json / libs 都放这里）。

    程序目录可写则用它（源码运行、Portable、单文件版：数据跟着程序走）；
    装到 Program Files 时程序目录只读，回退到 %LOCALAPPDATA%\\OfficeToolkit，
    否则日志初始化会抛 PermissionError（控制台已禁用 → 表现为双击无反应），
    配置保存与外部工具下载也会失败。
    """
    root = Path(get_app_root())
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / "logs"
        probe.mkdir(parents=True, exist_ok=True)
        return root
    except OSError:
        pass
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    fallback = Path(base) / "OfficeToolkit"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_log_dir() -> Path:
    """日志目录：始终位于可写数据根目录下。

    注意不能依赖当前工作目录——快捷方式启动的 CWD 可能是任何位置
    （装到 Program Files 时就是只读的安装目录）。
    """
    log_dir = get_data_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
