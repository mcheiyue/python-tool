import os
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Union

class ConfigLoader:
    """配置加载器，支持分层配置和递归更新"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # 默认为当前文件所在目录
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = Path(config_dir)
            
        self.default_config_path = self.config_dir / "default.json"
        self.user_config_path = self.config_dir.parent / "config.json" # 项目根目录
        
        self._config = {}
        self.load()

    def load(self):
        """加载配置：默认配置 -> 用户配置覆盖"""
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
            except Exception as e:
                print(f"Error loading user config: {e}")
        
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
        keys = key_path.split('.')
        target = self._config
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        target[keys[-1]] = value
        self.save()

    def save(self):
        """保存当前配置到用户配置文件"""
        try:
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    @property
    def all(self) -> Dict:
        """获取完整配置字典"""
        return self._config
