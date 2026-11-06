"""配置分层合并特征测试（蓝图 §4：临时目录双 JSON）。

锁定 ConfigLoader 的合并语义：默认配置打底、用户配置递归覆盖、
新增默认键不丢失、点号路径取值、缺失键回落默认值。
"""
import json

import pytest

import config.loader as loader_module
from config.loader import ConfigLoader


def _write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    """默认配置在 config_dir，用户配置在 get_data_root()（monkeypatch 到 tmp）"""
    config_dir = tmp_path / "defaults"
    config_dir.mkdir()
    user_root = tmp_path / "user"
    user_root.mkdir()

    monkeypatch.setattr(loader_module, "get_data_root", lambda: user_root)
    monkeypatch.setattr(
        loader_module, "get_resource_path", lambda rel: str(config_dir / rel.split("/")[-1])
    )
    return config_dir, user_root


def test_default_only(config_env):
    config_dir, _ = config_env
    _write(config_dir / "default.json", {"pdf": {"compress": {"quality": "/printer"}}})

    cfg = ConfigLoader(config_dir=str(config_dir))
    assert cfg.get("pdf.compress.quality") == "/printer"


def test_user_overrides_and_deep_merge(config_env):
    config_dir, user_root = config_env
    _write(config_dir / "default.json", {
        "pdf": {"compress": {"quality": "/printer", "default_output_dir": "Compressed"}},
        "app": {"theme_mode": "Auto"},
    })
    _write(user_root / "config.json", {
        "pdf": {"compress": {"quality": "/ebook"}},
        "app": {"theme_mode": "Dark"},
    })

    cfg = ConfigLoader(config_dir=str(config_dir))
    assert cfg.get("pdf.compress.quality") == "/ebook"          # 用户覆盖
    assert cfg.get("pdf.compress.default_output_dir") == "Compressed"  # 深层兄弟键保留
    assert cfg.get("app.theme_mode") == "Dark"


def test_new_default_key_not_lost(config_env):
    config_dir, user_root = config_env
    _write(config_dir / "default.json", {"a": {"x": 1, "y": 2}})
    _write(user_root / "config.json", {"a": {"x": 99}})

    cfg = ConfigLoader(config_dir=str(config_dir))
    assert cfg.get("a.y") == 2


def test_get_missing_returns_default(config_env):
    config_dir, _ = config_env
    _write(config_dir / "default.json", {"a": 1})

    cfg = ConfigLoader(config_dir=str(config_dir))
    assert cfg.get("nope.missing", "fallback") == "fallback"
    assert cfg.get("a.b.c", None) is None


def test_set_persists_to_user_config(config_env):
    config_dir, user_root = config_env
    _write(config_dir / "default.json", {"dependencies": {"disabled_tools": []}})

    cfg = ConfigLoader(config_dir=str(config_dir))
    cfg.set("dependencies.disabled_tools", ["pandoc"])

    saved = json.loads((user_root / "config.json").read_text(encoding="utf-8"))
    assert saved["dependencies"]["disabled_tools"] == ["pandoc"]


def test_independent_instances_merge_only_their_changes(config_env):
    config_dir, _ = config_env
    _write(config_dir / "default.json", {"app": {"theme": "Auto", "mode": "persistent"}})
    first = ConfigLoader(str(config_dir))
    second = ConfigLoader(str(config_dir))

    first.set("app.theme", "Dark")
    second.set("app.mode", "temporary")

    saved = ConfigLoader(str(config_dir))
    assert saved.get("app") == {"theme": "Dark", "mode": "temporary"}


def test_failed_replace_preserves_previous_config_and_reports_error(config_env, monkeypatch):
    config_dir, user_root = config_env
    _write(config_dir / "default.json", {"app": {"theme": "Auto"}})
    _write(user_root / "config.json", {"app": {"theme": "Dark"}})
    config = ConfigLoader(str(config_dir))

    def denied(source, target):
        raise PermissionError("cannot replace configuration")

    monkeypatch.setattr(loader_module.os, "replace", denied)

    with pytest.raises(PermissionError):
        config.set("app.theme", "Light")
    assert json.loads((user_root / "config.json").read_text(encoding="utf-8")) == {"app": {"theme": "Dark"}}


def test_concurrent_instances_preserve_all_updated_keys(config_env):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    config_dir, _ = config_env
    _write(config_dir / "default.json", {"tools": {}})
    configs = [ConfigLoader(str(config_dir)) for _ in range(8)]
    barrier = Barrier(8)

    def update(index):
        barrier.wait(timeout=10)
        configs[index].set(f"tools.tool{index}", index)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(update, range(8)))

    assert ConfigLoader(str(config_dir)).get("tools") == {f"tool{index}": index for index in range(8)}
