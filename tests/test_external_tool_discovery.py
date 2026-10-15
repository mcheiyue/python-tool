"""外部工具发现链集成测试（消费者侧）。

CodeGraph 标注 extract_bundle 的消费者无测试覆盖。本文件锁定
GhostscriptTool._find() 的便携包发现路径：
    查 plugins/*.mcy → extract_bundle → 定位 exe → 设 GS_LIB → source="portable"
extract_bundle 本身的行为由 test_bundle_extract_e2e.py 覆盖；
此处替身化它，专测「发现/装配」逻辑，零网络、零真二进制。
"""
import os

import pytest

from core.external_tools.ghostscript_tool import GhostscriptTool


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
