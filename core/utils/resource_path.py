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


def get_log_dir():
    """日志目录：优先当前目录下的 logs（便携形态）；只读环境回退到用户数据目录。

    装到 Program Files 后从安装目录启动时，当前目录不可写，
    原先直接 mkdir 会抛 PermissionError —— 异常发生在日志/崩溃处理器自身初始化阶段，
    控制台又被禁用，表现为「双击后无任何反应」。
    """
    fallback_root = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    for candidate in (Path("logs"), Path(fallback_root) / "OfficeToolkit" / "logs"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    return Path(tempfile.gettempdir())
