import os
import tempfile
from pathlib import Path
from uuid import uuid4

def get_app_root():
    """
    获取应用程序根目录（用户可访问的外部数据目录）
    - 开发环境：项目根目录
    - Nuitka Onefile：真实 EXE 所在目录（非临时解压目录）
    - Nuitka Standalone：EXE 所在目录
    """
    compiled = globals().get('__compiled__')
    if compiled is not None:
        return os.path.abspath(compiled.containing_dir)
    return str(Path(__file__).resolve().parents[2])

def get_resource_path(relative_path):
    """
    获取内部资源的绝对路径 (如图标、UI文件)
    - 开发环境：项目根目录/relative_path
    - Nuitka Onefile：临时解压目录/relative_path
    """
    return str(Path(__file__).resolve().parents[2] / relative_path)


def get_user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "OfficeToolkit"


def _is_writable(directory: Path) -> bool:
    """真实写一个探针文件判断可写。

    不能用 mkdir 判断：目录已存在时 mkdir(exist_ok=True) 是空操作，
    在只读目录里也会“成功”，随后写日志才抛 PermissionError。
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / f".write_probe_{uuid4().hex}"
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def get_data_root() -> Path:
    """可写数据根目录（config.json / libs 等放这里）。

    程序目录可写则用它（源码运行、Portable、单文件版：数据跟着程序走）；
    装到 Program Files 时程序目录只读，回退到 %LOCALAPPDATA%\\OfficeToolkit。
    """
    for base in (Path(get_app_root()), get_user_data_dir()):
        if _is_writable(base):
            return base
    return Path(tempfile.gettempdir())


def get_log_dir() -> Path:
    """日志目录：候选按「程序目录 → 用户数据目录 → 系统临时目录」逐个真实试写。

    日志目录拿不到可写位置时绝不能抛异常——日志/崩溃处理器的初始化一旦失败，
    控制台又是禁用的，用户看到的就是「双击后毫无反应」。
    """
    for base in (Path(get_app_root()), get_user_data_dir()):
        logs = base / "logs"
        if _is_writable(logs):
            return logs
    return Path(tempfile.gettempdir())
