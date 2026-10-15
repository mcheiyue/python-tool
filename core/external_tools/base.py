from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, List
import os
import shutil
import sys
import threading

from PyQt6.QtCore import QThread, pyqtSignal

# 解析串行化：惰性解压是重 IO 操作，并发解压会叠加内存/磁盘峰值，
# 故所有工具共用一把锁。_find() 不会回调其他工具，因此不存在死锁面。
_RESOLVE_LOCK = threading.Lock()


class _StatusResolver(QThread):
    """工具的常驻状态解析线程：run() 一次解析，结果扇出给所有等待中的回调。

    线程由工具持有（不随调用结束回收），因此不存在"运行中被析构"的致命错误；
    调用方只需传回调，无需持有线程引用。
    """

    resolved = pyqtSignal(object)

    def __init__(self, tool: "ExternalTool"):
        super().__init__()
        self._tool = tool
        self._waiters: List[Callable[[Optional[Dict[str, Any]]], None]] = []
        self._waiters_lock = threading.Lock()

    def add_callback(self, callback: Callable[[Optional[Dict[str, Any]]], None]):
        with self._waiters_lock:
            self._waiters.append(callback)

    def run(self):
        try:
            with _RESOLVE_LOCK:
                result = self._tool.get_status_info()
        except Exception:
            result = None
        self.resolved.emit(result)

    def _fan_out(self, result):
        with self._waiters_lock:
            waiters, self._waiters = self._waiters, []
        for callback in waiters:
            try:
                callback(result)
            except Exception:
                pass


class ExternalTool(ABC):
    """外部工具抽象基类"""
    
    # 唯一标识符 (例如: 'pandoc', 'ghostscript')
    name: str = ""
    
    # 显示名称 (例如: 'Pandoc')
    display_name: str = ""
    
    # 功能描述
    description: str = ""
    
    # 功能用途说明（用于界面提示）
    features: str = ""
    
    # 官方下载地址
    download_url: str = ""
    
    # 是否是应用程序的核心依赖
    is_required: bool = False
    
    # 引用管理器实例
    _manager = None

    def clear_cache(self):
        """清除缓存，强制重新检测"""
        if hasattr(self, '_cache'):
            self._cache = None

    def probe_version(self, exe_path: str) -> Optional[str]:
        """带缓存的版本探测：按 (mtime, size) 指纹命中则跳过子进程。

        每次 spawn 子进程取版本是可观开销（LibreOffice 达秒级），而进程内
        _find() 已缓存一次，真正的浪费发生在「每次应用启动都重新探测」。
        缓存写用户配置的 dependencies.tool_version_cache，文件一变即失效；
        不含路径——temporary 模式每次解压到新的 session 目录，按路径匹配
        将使缓存永不命中。配置不可用（缺 default.json 等）时退回无缓存探测。
        """
        try:
            st = os.stat(exe_path)
            fingerprint = [int(st.st_mtime), int(st.st_size)]
        except OSError:
            fingerprint = None

        cache = {}
        config = None
        try:
            config = self._version_cache_config()
            cache = config.get("dependencies.tool_version_cache", {}) or {}
        except Exception:
            config = None

        entry = cache.get(self.name) if isinstance(cache, dict) else None
        # 只按指纹（mtime+size）匹配：temporary 模式每次启动都解压到新的
        # session_xxxx 目录，按路径匹配会让缓存永远不命中（实测跨启动零命中）。
        if fingerprint and isinstance(entry, dict) and entry.get("fp") == fingerprint:
            return entry.get("version")

        try:
            version = self._get_version_from_exe(exe_path)
        except Exception:
            return None

        if config is not None and fingerprint is not None and version is not None:
            cache[self.name] = {"path": exe_path, "fp": fingerprint, "version": version}
            config.set("dependencies.tool_version_cache", cache)
            config.save()
        return version

    @staticmethod
    def _version_cache_config():
        from config.loader import ConfigLoader
        return ConfigLoader()

    def _get_version_from_exe(self, path: str) -> Optional[str]:
        """子类实现：spawn 一次子进程取版本号。基类返回 None。"""
        return None

    def _locate_bundle(self, filename: str) -> Optional[str]:
        """载体(.mcy)路径：内部资源优先，外部 plugins 目录兜底；不存在返回 None。"""
        from core.utils.resource_path import get_app_root, get_resource_path
        internal = get_resource_path(f"plugins/{filename}")
        if os.path.exists(internal):
            return internal
        external = os.path.join(get_app_root(), "plugins", filename)
        return external if os.path.exists(external) else None

    @staticmethod
    def _exe_in_dirs(base_dir: str, exe_names, subdirs=("",)) -> Optional[str]:
        """在 base_dir 的若干子目录中按序查找可执行文件，返回首个存在的完整路径。"""
        for sub in subdirs:
            directory = os.path.join(base_dir, sub) if sub else base_dir
            for exe_name in exe_names:
                candidate = os.path.join(directory, exe_name)
                if os.path.exists(candidate):
                    return candidate
        return None

    def _resolve_executable(self, exe_names, which_names=None,
                            portable_subdirs=("",), on_portable=None):
        """发现链步骤 1-3：便携目录 → 载体(.mcy)惰性解压 → PATH。

        返回 (路径, source)，source 取值为 "portable"/"env"/None。
        步骤 4（平台系统路径）各工具差异大（gs 版本目录扫描 / LO 固定路径 /
        pandoc 无），由调用方自行追加。
        on_portable(exe_path) 在便携命中时回调（gs 借它注入 GS_LIB）。
        """
        tool_dir = os.path.join(self.get_libs_path(), self.name)
        found = self._exe_in_dirs(tool_dir, exe_names, portable_subdirs)
        if not found:
            plugin_path = self._locate_bundle(f"{self.name}.mcy")
            if plugin_path:
                from config.loader import ConfigLoader
                from core.bundles.loader import loader as bundle_loader
                persistent = ConfigLoader().get(
                    "app.plugin_mode", "temporary") == "persistent"
                extracted = bundle_loader.extract_bundle(
                    plugin_path, persistent=persistent)
                if extracted:
                    found = self._exe_in_dirs(extracted, exe_names, portable_subdirs)
        if found:
            if on_portable:
                on_portable(found)
            return found, "portable"

        for exe_name in (which_names or exe_names):
            path = shutil.which(exe_name)
            if path:
                return path, "env"
        return None, None

    @property
    def is_disabled(self) -> bool:
        """检查工具是否被禁用"""
        if self._manager:
            return self._manager.is_tool_disabled(self.name)
        return False

    @abstractmethod
    def check_installed(self) -> bool:
        """检查工具是否已安装"""
        pass
    
    def uninstall(self) -> bool:
        """卸载工具（删除相关文件）"""
        return False

    @abstractmethod
    def get_version(self) -> Optional[str]:
        """获取已安装版本"""
        pass
    
    @abstractmethod
    def get_path(self) -> Optional[str]:
        """获取可执行文件路径"""
        pass
    
    def get_source(self) -> Optional[str]:
        """获取安装来源 (portable/system/env)"""
        # 默认返回 None，子类可以在 _find 结果中包含此信息
        return None

    # 别名，为了更好的语义兼容性
    def is_available(self) -> bool:
        return self.check_installed() and not self.is_disabled
        
    def get_executable_path(self) -> Optional[str]:
        if self.is_disabled:
            return None
        return self.get_path()

    def refresh_status_async(self, callback: Callable[[Optional[Dict[str, Any]]], None]):
        """后台刷新工具状态，完成后 callback(status) 在主线程被调用。

        状态解析可能触发 .mcy 惰性解压（秒级），因此不能在 UI 线程同步调用
        check_installed()/get_path()；本方法是唯一入口。status 形如 get_status_info()。
        解析进行中再次调用会复用同一次结果（回调排队扇出），线程由工具持有，
        调用方无需（也不应）保存线程引用。
        """
        resolver = getattr(self, "_resolver", None)
        if resolver is None:
            resolver = _StatusResolver(self)
            resolver.resolved.connect(resolver._fan_out)
            self._resolver = resolver

        resolver.add_callback(callback)
        if not resolver.isRunning():
            resolver.start()
        return resolver
        
    def get_status_info(self) -> Dict[str, Any]:
        """获取工具状态信息"""
        installed = self.check_installed()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "features": self.features,
            "installed": installed,
            "disabled": self.is_disabled,
            "version": self.get_version() if installed else None,
            "path": self.get_path() if installed else None,
            "source": self.get_source() if installed else None,
            "download_url": self.download_url,
            "is_required": self.is_required
        }

    @staticmethod
    def get_libs_path() -> str:
        """获取便携 libs 目录路径"""
        from core.utils.resource_path import get_app_root
        return os.path.join(get_app_root(), "libs")
