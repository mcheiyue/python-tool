"""外部工具发现链集成测试（消费者侧）。

锁定「便携目录 → plugins/<tool>.zip 预置包 → manifest 下载兜底 → PATH」这条
发现路径（B0 起步骤 1-3 收拢在 base.ExternalTool._resolve_executable）。
此处对 PackageStore 替身化，专测「发现/装配」逻辑，零网络、零真二进制；
zip 解压与安全审查本身由 test_bundle_zip_safety.py 覆盖。
"""
import os
import json
import shutil
import time
import zipfile

import pytest

from core.external_tools.base import ExternalTool
from core.external_tools.ghostscript_tool import GhostscriptTool
from core.external_tools.libreoffice_tool import LibreOfficeTool
from core.external_tools.pandoc_tool import PandocTool


@pytest.fixture
def tool_env(tmp_path, monkeypatch):
    """app_root/resource 定向 tmp；重置工具缓存与 GS_LIB。

    patch 源模块而非工具别名：发现链已收拢进 base，资源函数在 base 内
    以晚导入方式从 core.utils.resource_path 取。
    """
    monkeypatch.setattr("core.utils.resource_path.get_app_root", lambda: str(tmp_path))
    monkeypatch.setattr(
        "core.utils.resource_path.get_resource_path",
        lambda rel: str(tmp_path / "_no_internal" / rel),
    )
    monkeypatch.delenv("GS_LIB", raising=False)
    tool = GhostscriptTool()
    tool.clear_cache()
    yield tool, tmp_path
    tool.clear_cache()
    # _set_gs_lib 会直写 os.environ["GS_LIB"]（不走 monkeypatch），teardown 必须清掉，
    # 否则泄漏的 tmp 路径会让同一进程后续真实 GS 调用找不到资源而失败
    os.environ.pop("GS_LIB", None)


def _make_extracted_gs(root):
    """构造一个模拟已解压的便携 ghostscript 目录"""
    gs_dir = root / "libs" / "ghostscript"
    (gs_dir / "lib").mkdir(parents=True)
    (gs_dir / "gswin64c.exe").write_bytes(b"fake")
    (gs_dir / "lib" / "gs_init.ps").write_text("% init", encoding="utf-8")
    return gs_dir


def _make_preplaced_zip(path, entries):
    """构造预置包 plugins/<tool>.zip（条目=发现链第一个真实来源）"""
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_discovers_from_plugins_dir(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    _make_preplaced_zip(plugins / "ghostscript.zip", {
        "ghostscript/gswin64c.exe": b"binary",
        "ghostscript/lib/gs_init.ps": b"% init",
    })

    extracted = _make_extracted_gs(tmp_path)
    monkeypatch.setattr(
        "core.tools.package_store.PackageStore.install",
        lambda self, name, **kw: str(extracted),
    )

    assert tool.check_installed() is True
    assert os.path.basename(tool.get_path()) == "gswin64c.exe"
    assert tool.get_source() == "portable"
    assert os.environ.get("GS_LIB") == str(extracted / "lib")


def test_bundle_absent_reports_not_found(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    # 无 zip/manifest/PATH/Program Files 安装
    monkeypatch.setattr(
        "core.external_tools.base.shutil.which", lambda name: None
    )
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "no_such_pf"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "no_such_pf86"))

    assert tool.check_installed() is False
    assert tool.get_path() is None
    assert tool.get_source() is None


def test_uses_cached_libs_dir_without_install(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    # libs/ghostscript 已存在 → 不应触发安装
    _make_extracted_gs(tmp_path)

    def _fail(*a, **k):
        raise AssertionError("已解压的 libs 目录存在时不应再触发安装")

    monkeypatch.setattr(
        "core.tools.package_store.PackageStore.install", _fail
    )

    assert tool.check_installed() is True
    assert tool.get_source() == "portable"


def _write_manifest(tmp_path, tool_name, sha256):
    plugins = tmp_path / "plugins"
    plugins.mkdir(exist_ok=True)
    (plugins / "manifest.json").write_text(
        json.dumps({tool_name: {"url": "https://example.invalid/x.zip", "sha256": sha256}}),
        encoding="utf-8",
    )


def test_stale_portable_dir_triggers_reinstall(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    extracted = _make_extracted_gs(tmp_path)
    _write_manifest(tmp_path, "ghostscript", "ab" * 32)
    # 目录标记是旧版本，manifest 已是新 sha256 → 过期
    (extracted / ".source-id").write_text("sha256:" + "cd" * 32, encoding="utf-8")

    installs = []

    def _fake_install(self, name, **kw):
        installs.append(name)
        extracted.mkdir(parents=True, exist_ok=True)
        (extracted / "gswin64c.exe").write_bytes(b"fake")
        return str(extracted)

    monkeypatch.setattr("core.tools.package_store.PackageStore.install", _fake_install)

    assert tool.check_installed() is True
    assert installs == ["ghostscript"]


def test_current_portable_dir_skips_reinstall(tool_env, monkeypatch):
    tool, tmp_path = tool_env
    extracted = _make_extracted_gs(tmp_path)
    _write_manifest(tmp_path, "ghostscript", "ab" * 32)
    (extracted / ".source-id").write_text("sha256:" + "ab" * 32, encoding="utf-8")

    def _fail(*a, **k):
        raise AssertionError("未过期的持久目录不应触发重装")

    monkeypatch.setattr("core.tools.package_store.PackageStore.install", _fail)

    assert tool.check_installed() is True
    assert tool.get_source() == "portable"


class TestLibreOfficeDiscovery:
    """LibreOffice 发现链（便携目录 → 预置包/上游安装 → PATH → 系统路径）"""

    @pytest.fixture
    def lo_env(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.utils.resource_path.get_app_root", lambda: str(tmp_path))
        monkeypatch.setattr(
            "core.utils.resource_path.get_resource_path",
            lambda rel: str(tmp_path / "_no_internal" / rel),
        )
        monkeypatch.setattr(
            "core.external_tools.base.shutil.which", lambda name: None
        )
        monkeypatch.setenv("ProgramFiles", str(tmp_path / "no_such_pf"))
        monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "no_such_pf86"))
        tool = LibreOfficeTool()
        tool.clear_cache()
        yield tool, tmp_path
        tool.clear_cache()

    def test_discovers_from_plugins_dir(self, lo_env, monkeypatch):
        tool, tmp_path = lo_env
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        _make_preplaced_zip(plugins / "libreoffice.zip", {
            "libreoffice/program/soffice.exe": b"binary",
        })

        extracted = tmp_path / "libs" / "libreoffice"
        (extracted / "program").mkdir(parents=True)
        (extracted / "program" / "soffice.exe").write_bytes(b"fake")

        monkeypatch.setattr(
            "core.tools.package_store.PackageStore.install",
            lambda self, name, **kw: str(extracted),
        )

        assert tool.check_installed() is True
        assert os.path.basename(tool.get_path()) == "soffice.exe"
        assert tool.get_source() == "portable"

    def test_uses_existing_libs_dir_without_install(self, lo_env, monkeypatch):
        tool, tmp_path = lo_env
        extracted = tmp_path / "libs" / "libreoffice"
        (extracted / "program").mkdir(parents=True)
        (extracted / "program" / "soffice.exe").write_bytes(b"fake")

        def _fail(*a, **k):
            raise AssertionError("libs 目录已存在时不应再触发安装")

        monkeypatch.setattr(
            "core.tools.package_store.PackageStore.install", _fail
        )

        assert tool.check_installed() is True
        assert tool.get_source() == "portable"

    def test_absent_reports_not_found(self, lo_env):
        tool, _ = lo_env
        assert tool.check_installed() is False
        assert tool.get_source() is None

    def test_portable_branch_uses_version_cache(self, lo_env, monkeypatch):
        """回归：便携分支也必须走 probe_version（曾绕过缓存）。

        该分支的参数名是 portable_exe 而非 path，靠人工逐一比对 _find()
        的调用点时极易漏掉；此用例直接锁死行为。
        """
        tool, tmp_path = lo_env
        extracted = tmp_path / "libs" / "libreoffice"
        (extracted / "program").mkdir(parents=True)
        (extracted / "program" / "soffice.exe").write_bytes(b"fake")

        seen = []
        monkeypatch.setattr(tool, "probe_version",
                            lambda p: seen.append(p) or "24.2.0")
        monkeypatch.setattr(tool, "_get_version_from_exe",
                            lambda p: (_ for _ in ()).throw(
                                AssertionError("便携分支不得绕过 probe_version")))

        assert tool.get_version() == "24.2.0"
        assert seen and os.path.basename(seen[0]) == "soffice.exe"


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

    def test_same_content_at_new_path_hits(self, monkeypatch, tmp_path):
        """回归：缓存不得把路径计入命中条件。

        temporary 模式每次启动都解压到新的 session_xxxx 目录——路径每变一次，
        内容却完全相同。按路径匹配会让跨启动缓存永不命中（实测每次启动都重新
        探测），故命中条件只认 (mtime, size) 指纹。
        """
        tool, exe, fake = self._make(monkeypatch, tmp_path)
        other_dir = tmp_path / "session_other" / "pandoc"
        other_dir.mkdir(parents=True)
        other_exe = other_dir / "pandoc.exe"
        shutil.copy2(exe, other_exe)

        assert tool.probe_version(str(exe)) == "v1"
        assert tool.probe_version(str(other_exe)) == "v1"
        assert tool.probe_calls == 1

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


@pytest.fixture
def pandoc_env(tmp_path, monkeypatch):
    """pandoc 专用环境：资源定向 tmp、shutil.which 置空。"""
    monkeypatch.setattr("core.utils.resource_path.get_app_root", lambda: str(tmp_path))
    monkeypatch.setattr(
        "core.utils.resource_path.get_resource_path",
        lambda rel: str(tmp_path / "_no_internal" / rel),
    )
    monkeypatch.setattr(
        "core.external_tools.base.shutil.which", lambda name: None
    )
    tool = PandocTool()
    tool.clear_cache()
    yield tool, tmp_path
    tool.clear_cache()


def test_discovers_from_preplaced_zip(pandoc_env):
    """plugins/<tool>.zip（预置官方包）走真 extract_zip，命中 portable。"""
    tool, tmp_path = pandoc_env
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    with zipfile.ZipFile(plugins / "pandoc.zip", "w") as zf:
        zf.writestr("pandoc/pandoc.exe", b"official-binary")

    assert tool.check_installed() is True
    assert tool.get_source() == "portable"
    assert "pandoc.exe" in tool.get_path()


def test_manifest_absent_and_no_zip_falls_back(pandoc_env):
    """无 zip、无 manifest、无 PATH → 未安装（不触发任何下载）。"""
    tool, _ = pandoc_env
    assert tool.check_installed() is False
    assert tool.get_source() is None


class _StubTool(ExternalTool):
    name = "stubtool"
    display_name = "Stub"
    download_url = ""

    def _find(self):
        return {"found": False, "path": None, "version": None, "source": None}

    def check_installed(self):
        return False

    def get_path(self):
        return None

    def get_version(self):
        return None


class TestToolInstallWorker:
    """安装 worker：跨线程把 install 结果转成 (installed, version)。

    锁两个真实坑：run() 内引用 AppLogger 曾漏 import（NameError 让整个
    异步安装在生产路径必炸）；install 抛异常时必须降级为 finished(False)
    而不是崩线程。
    """

    def test_success_reports_version(self, qtbot, monkeypatch):
        from core.external_tools.base import _ToolInstallWorker

        tool = _StubTool()
        monkeypatch.setattr(
            "core.tools.package_store.PackageStore.install",
            lambda self, name, **kw: "/fake/extracted",
        )
        monkeypatch.setattr(
            _StubTool, "_find",
            lambda self: {"found": True, "version": "1.2.3"},
        )

        worker = _ToolInstallWorker(tool)
        got = []
        worker.signals.finished.connect(lambda ok, ver: got.append((ok, ver)))
        worker.run()
        assert got == [(True, "1.2.3")]

    def test_install_failure_degrades(self, qtbot, monkeypatch):
        from core.external_tools.base import _ToolInstallWorker

        tool = _StubTool()

        def _boom(self, name, **kw):
            raise OSError("network down")

        monkeypatch.setattr("core.tools.package_store.PackageStore.install", _boom)

        worker = _ToolInstallWorker(tool)
        got = []
        worker.signals.finished.connect(lambda ok, ver: got.append((ok, ver)))
        worker.run()
        assert got == [(False, None)]

    def test_cancel_flag_stops_download(self, qtbot, monkeypatch):
        from core.external_tools.base import _ToolInstallWorker

        tool = _StubTool()
        seen = {}

        def _install(self, name, on_progress=None, should_cancel=None, **kw):
            seen["cancel_fn"] = should_cancel
            return None

        monkeypatch.setattr("core.tools.package_store.PackageStore.install", _install)
        worker = _ToolInstallWorker(tool)
        worker.cancel()
        worker.run()
        assert seen["cancel_fn"]() is True
