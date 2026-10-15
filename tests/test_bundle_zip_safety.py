"""zip 安全解压回归测试（B1 建立；.mcy 退役后仅存 zip 侧）。

锁定 _safe_extract_zip/_validate_member_paths 的三类拒绝：
路径穿越（../）、符号链接成员（external_attr S_IFLNK），以及正常 zip 的解压
与持久模式的目录布局契约。
"""
import os
import stat
import zipfile

import pytest

from core.bundles.loader import SecurityError, loader


def _make_zip(path, entries):
    """entries: {name: (bytes, external_attr)}"""
    with zipfile.ZipFile(path, "w") as zf:
        for name, (data, attr) in entries.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = attr
            zf.writestr(info, data)
    return str(path)


def test_zip_path_traversal_rejected(tmp_path):
    z = _make_zip(tmp_path / "evil.zip", {"../escape.txt": (b"x", 0)})
    target = tmp_path / "out"
    target.mkdir()
    with pytest.raises(SecurityError, match="路径穿越"):
        loader.extract_zip(z, persistent=False)


def test_zip_symlink_member_rejected(tmp_path):
    attr = (stat.S_IFLNK | 0o777) << 16
    z = _make_zip(tmp_path / "link.zip", {"pandoc.exe": (b"x", attr)})
    with pytest.raises(SecurityError, match="符号链接"):
        loader.extract_zip(z, persistent=False)


def test_zip_happy_path_extracts(tmp_path, monkeypatch):
    z = _make_zip(
        tmp_path / "ok.zip",
        {
            "pandoc/pandoc.exe": (b"binary", 0),
            "pandoc/README.md": (b"# hi", 0),
        },
    )
    monkeypatch.setattr(
        "core.utils.resource_path.get_app_root", lambda: str(tmp_path)
    )
    result = loader.extract_zip(z, persistent=False)
    # 顶层目录被提升：exe 直接在会话根下（持久模式才能命中 libs/<工具名>/）
    assert os.path.isfile(os.path.join(result, "pandoc.exe"))
    assert result.startswith(str(tmp_path / "libs" / ".temp"))
    session_dir = result
    assert session_dir in loader._temp_dirs


def test_persistent_mode_lands_on_discovery_layout(tmp_path, monkeypatch):
    """持久模式解压后 exe 必须在 libs/<工具名>/ 下——发现链按此布局查找。"""
    z = _make_zip(
        tmp_path / "official.zip",
        {
            "pandoc-3.12.1/pandoc.exe": (b"binary", 0),
            "pandoc-3.12.1/README.md": (b"doc", 0),
        },
    )
    monkeypatch.setattr(
        "core.utils.resource_path.get_app_root", lambda: str(tmp_path)
    )
    result = loader.extract_zip(z, persistent=True, subdir="pandoc")
    assert result == str(tmp_path / "libs" / "pandoc")
    assert os.path.isfile(os.path.join(result, "pandoc.exe"))
