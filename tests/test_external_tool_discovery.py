"""外部工具发现链集成测试（消费者侧）。

CodeGraph 标注 extract_bundle 的消费者无测试覆盖。本文件锁定
GhostscriptTool._find() 的便携包发现路径：
    查 plugins/*.mcy → extract_bundle → 定位 exe → 设 GS_LIB → source="portable"
extract_bundle 本身的行为由 test_bundle_extract_e2e.py 覆盖；
此处替身化它，专测「发现/装配」逻辑，零网络、零真二进制。
"""
import os
import time

import pytest

from core.external_tools.base import ExternalTool
from core.external_tools.ghostscript_tool import GhostscriptTool
from core.external_tools.libreoffice_tool import LibreOfficeTool


@pytest.fixture
def tool_env(tmp_path, monkeypatch):
    """app_root/resource 定向 tmp；重置工具缓存与 GS_LIB。

    需同时 patch 两处：ghostscript_tool 的模块级绑定，以及
    base.get_libs_path() 在调用时的晚导入（from core.utils.resource_path import ...）。
    """
    for target in (
        "core.utils.resource_path.get_app_root",
        "core.external_tools.ghostscript_tool.get_app_root",
    ):
        monkeypatch.setattr(target, lambda: str(tmp_path))
    monkeypatch.setattr(
        "core.external_tools.ghostscript_tool.get_resource_path",
        lambda rel: str(tmp_path / "_no_internal" / rel),
    )
    monkeypatch.delenv("GS_LIB", raising=False)
    tool = GhostscriptTool()
    tool.clear_cache()
    yield tool, tmp_path
    tool.clear_cache()


def _make_extracted_gs(root):
    """构造一个模拟已解压的便携 ghostscript 目录"""
    gs_dir = root / "libs" / "ghostscript"
    (gs_dir / "lib").mkdir(parents=True)
    (gs_dir / "gswin64c.exe").write_bytes(b"fake")
    (gs_dir / "lib" / "gs_init.ps").write_text("% init", encoding="utf-8")
    return gs_dir


def test_discovers_bundle_from_plugins_dir(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "ghostscript.mcy").write_bytes(b"signed bundle placeholder")

    extracted = _make_extracted_gs(tmp_path)
    monkeypatch.setattr(
        "core.external_tools.ghostscript_tool.bundle_loader.extract_bundle",
        lambda path, persistent=False: str(extracted),
    )

    assert tool.check_installed() is True
    assert os.path.basename(tool.get_path()) == "gswin64c.exe"
    assert tool.get_source() == "portable"
    assert os.environ.get("GS_LIB") == str(extracted / "lib")


def test_bundle_absent_reports_not_found(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    # 无 plugins/*.mcy、无 PATH、无 Program Files 安装
    monkeypatch.setattr(
        "core.external_tools.ghostscript_tool.shutil.which", lambda name: None
    )
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "no_such_pf"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "no_such_pf86"))

    assert tool.check_installed() is False
    assert tool.get_path() is None
    assert tool.get_source() is None


def test_uses_cached_libs_dir_without_bundle(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    # libs/ghostscript 已存在 → 不应触碰 plugins/extract
    _make_extracted_gs(tmp_path)

    def _fail(*a, **k):
        raise AssertionError("已解压的 libs 目录存在时不应再解压 .mcy")

    monkeypatch.setattr(
        "core.external_tools.ghostscript_tool.bundle_loader.extract_bundle", _fail
    )

    assert tool.check_installed() is True
    assert tool.get_source() == "portable"


class TestLibreOfficeDiscovery:
    """LibreOffice 便携/Tool Bundle 发现链（① 新增分支）"""

    @pytest.fixture
    def lo_env(self, tmp_path, monkeypatch):
        for target in (
            "core.utils.resource_path.get_app_root",
            "core.external_tools.libreoffice_tool.get_app_root",
        ):
            monkeypatch.setattr(target, lambda: str(tmp_path))
        monkeypatch.setattr(
            "core.external_tools.libreoffice_tool.get_resource_path",
            lambda rel: str(tmp_path / "_no_internal" / rel),
        )
        monkeypatch.setattr(
            "core.external_tools.libreoffice_tool.shutil.which", lambda name: None
        )
        monkeypatch.setenv("ProgramFiles", str(tmp_path / "no_such_pf"))
        monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "no_such_pf86"))
        tool = LibreOfficeTool()
        tool.clear_cache()
        yield tool, tmp_path
        tool.clear_cache()

    def test_discovers_bundle_from_plugins_dir(self, lo_env, monkeypatch):
        tool, tmp_path = lo_env
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        (plugins / "libreoffice.mcy").write_bytes(b"signed bundle placeholder")

        extracted = tmp_path / "libs" / "libreoffice"
        (extracted / "program").mkdir(parents=True)
        (extracted / "program" / "soffice.exe").write_bytes(b"fake")

        monkeypatch.setattr(
            "core.external_tools.libreoffice_tool.bundle_loader.extract_bundle",
            lambda path, persistent=False: str(extracted),
        )

        assert tool.check_installed() is True
        assert os.path.basename(tool.get_path()) == "soffice.exe"
        assert tool.get_source() == "portable"

    def test_uses_existing_libs_dir_without_bundle(self, lo_env, monkeypatch):
        tool, tmp_path = lo_env
        extracted = tmp_path / "libs" / "libreoffice"
        (extracted / "program").mkdir(parents=True)
        (extracted / "program" / "soffice.exe").write_bytes(b"fake")

        def _fail(*a, **k):
            raise AssertionError("libs 目录已存在时不应再解压 .mcy")

        monkeypatch.setattr(
            "core.external_tools.libreoffice_tool.bundle_loader.extract_bundle", _fail
        )

        assert tool.check_installed() is True
        assert tool.get_source() == "portable"

    def test_absent_reports_not_found(self, lo_env):
        tool, _ = lo_env
        assert tool.check_installed() is False
        assert tool.get_source() is None


class TestRefreshStatusAsync:
    """refresh_status_async 的线程生命周期回归。

    历史 bug：每次调用新建 QThread，界面重复触发（构造 + showEvent）时前一个
    仍在运行的线程被替换、引用归零 → 运行中的 QThread 被析构 → 进程硬崩
    （Qt Fatal: Destroyed while thread is still running）。故 resolver 必须常驻复用。
    """

    def _pump(self, deadline_ms=4000):
        """驱动主线程事件循环，直到 deadline（QThread 的回调经队列信号投递）。"""
        from PyQt6.QtCore import QElapsedTimer
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        timer = QElapsedTimer()
        timer.start()
        while timer.elapsed() < deadline_ms:
            app.processEvents()
            time.sleep(0.01)

    def test_reuses_single_resolver(self, qapp, tool_env):
        tool, _ = tool_env
        first = tool.refresh_status_async(lambda s: None)
        second = tool.refresh_status_async(lambda s: None)
        assert first is second

    def test_repeated_calls_all_callbacks_fire(self, qapp, tool_env):
        """飞行中/已完成的重复调用都不能丢回调，且不得重建线程"""
        tool, _ = tool_env
        got = []
        tool.refresh_status_async(got.append)
        tool.refresh_status_async(got.append)   # 飞行中追加
        resolver = tool._resolver
        self._pump(3000)
        tool.refresh_status_async(got.append)   # 已结束后再调用
        self._pump(3000)
        assert tool._resolver is resolver
        assert len(got) == 3
        assert all(isinstance(s, dict) and "installed" in s for s in got)

    def test_callback_runs_on_main_thread(self, qapp, tool_env):
        import threading
        tool, _ = tool_env
        box = {}
        def cb(status):
            box["thread"] = threading.current_thread()
        tool.refresh_status_async(cb)
        self._pump(3000)
        assert box["thread"] is threading.main_thread()


class _FakeConfig:
    """内存版配置替身，隔离用户配置文件。"""

    def __init__(self):
        self._data = {}
        self.saved = 0

    def get(self, key_path, default=None):
        node = self._data
        for k in key_path.split('.'):
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def set(self, key_path, value):
        keys = key_path.split('.')
        node = self._data
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value

    def save(self):
        self.saved += 1


class _ProbeTool(ExternalTool):
    """探针计数用的最小 ExternalTool 子类。"""

    name = "probe_tool"

    def __init__(self):
        self.probe_calls = 0

    def check_installed(self):
        return True

    def get_version(self):
        return "1.0"

    def get_path(self):
        return "/nonexistent/exe"

    def _get_version_from_exe(self, path):
        self.probe_calls += 1
        return f"v{self.probe_calls}"


class TestVersionProbeCache:
    """probe_version 的持久缓存：命中跳过子进程，文件变更即失效。"""

    def _make(self, monkeypatch, tmp_path):
        exe = tmp_path / "tool.exe"
        exe.write_bytes(b"binary-content")
        tool = _ProbeTool()
        fake = _FakeConfig()
        monkeypatch.setattr(ExternalTool, "_version_cache_config", staticmethod(lambda: fake))
        return tool, exe, fake

    def test_second_call_hits_cache(self, monkeypatch, tmp_path):
        tool, exe, fake = self._make(monkeypatch, tmp_path)
        assert tool.probe_version(str(exe)) == "v1"
        assert tool.probe_version(str(exe)) == "v1"
        assert tool.probe_calls == 1

    def test_new_instance_reuses_cache(self, monkeypatch, tmp_path):
        """跨实例（模拟重启）命中同一份缓存，不再 spawn 子进程。"""
        tool, exe, fake = self._make(monkeypatch, tmp_path)
        tool.probe_version(str(exe))
        fresh = _ProbeTool()
        assert fresh.probe_version(str(exe)) == "v1"
        assert fresh.probe_calls == 0

    def test_mtime_change_invalidates(self, monkeypatch, tmp_path):
        tool, exe, fake = self._make(monkeypatch, tmp_path)
        tool.probe_version(str(exe))
        os.utime(exe, (0, 0))
        assert tool.probe_version(str(exe)) == "v2"
        assert tool.probe_calls == 2

    def test_size_change_invalidates(self, monkeypatch, tmp_path):
        tool, exe, fake = self._make(monkeypatch, tmp_path)
        tool.probe_version(str(exe))
        exe.write_bytes(b"binary-content-changed")
        assert tool.probe_version(str(exe)) == "v2"

    def test_probe_failure_not_cached(self, monkeypatch, tmp_path):
        tool, exe, fake = self._make(monkeypatch, tmp_path)

        def _boom(path):
            raise OSError("spawn failed")

        monkeypatch.setattr(tool, "_get_version_from_exe", _boom)
        assert tool.probe_version(str(exe)) is None
        assert fake.saved == 0
