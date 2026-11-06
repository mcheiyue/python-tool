import os
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from collections.abc import Iterator
from typing import Any, Dict, Union
from core.utils.resource_path import get_data_root, get_resource_path
from core.utils.logger import AppLogger

class ConfigLoader:
    """配置加载器，支持分层配置和递归更新"""
    
    _lock = RLock()

    def __init__(self, config_dir: str = None):
        # 1. 确定默认配置文件路径 (只读，可能在EXE内部或源码目录)
        if config_dir is None:
            # 使用 get_resource_path 获取内部资源路径
            self.default_config_path = Path(get_resource_path("config/default.json"))
        else:
            self.default_config_path = Path(config_dir) / "default.json"
            
        # 2. 确定用户配置文件路径 (读写，必须在可写位置)
        self.user_config_path = get_data_root() / "config.json"
        
        self._config = {}
        self._pending = {}
        self.load()

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with self._lock, open(self.user_config_path.with_suffix(".lock"), "a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def load(self):
        """加载配置：默认配置 -> 用户配置覆盖"""
        with self._locked():
            self._load()

    def _load(self):
        # 1. 加载默认配置
        if not self.default_config_path.exists():
            raise FileNotFoundError(f"Default config not found at {self.default_config_path}")
            
        with open(self.default_config_path, 'r', encoding='utf-8') as f:
            default_config = json.load(f)
            
        # 2. 加载用户配置
        user_config = {}
        if self.user_config_path.exists():
            try:
                with open(self.user_config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                AppLogger().warning(f"读取用户配置失败: {e}")
        
        # 3. 合并配置
        self._config = default_config
        self._update_recursive(self._config, user_config)

    def _update_recursive(self, target: Dict, source: Dict):
        """递归合并配置字典，确保新增的默认配置项不会被覆盖丢失"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_recursive(target[key], value)
            else:
                target[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项，支持点号路径访问
        例如: config.get("pdf.compress.quality")
        """
        keys = key_path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """
        设置配置项，支持点号路径访问
        例如: config.set("pdf.compress.quality", "/ebook")
        """
        with self._lock:
            self._pending[key_path] = value
            self.save()

    def save(self):
        """在进程间锁内合并本实例修改的键，再原子替换配置。"""
        with self._locked():
            if not self._pending:
                return
            self._load()
            for key_path, value in self._pending.items():
                keys = key_path.split('.')
                target = self._config
                for key in keys[:-1]:
                    target = target.setdefault(key, {})
                target[keys[-1]] = value
            with tempfile.TemporaryDirectory(dir=self.user_config_path.parent) as staging:
                pending = Path(staging) / "config.json"
                with pending.open('w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=4, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(pending, self.user_config_path)
            self._pending.clear()

    @property
    def all(self) -> Dict:
        """获取完整配置字典"""
        return self._config
