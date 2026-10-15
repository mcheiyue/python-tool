"""zip 安全解压回归测试（B1：成员审查 tar/zip 共用）。

锁定 _safe_extract_zip/_validate_member_paths 的三类拒绝：
路径穿越（../）、符号链接成员（external_attr S_IFLNK），以及正常 zip 的解压。
tar 侧审查由 test_bundle_extract_e2e.py 覆盖。
"""
import io
import os
import stat
import tarfile
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
    assert os.path.basename(result) == "pandoc"
    assert os.path.isfile(os.path.join(result, "pandoc.exe"))
    # temporary 模式的会话目录登记了清理
    assert result.startswith(str(tmp_path / "libs" / ".temp"))
    session_dir = os.path.dirname(result)
    assert session_dir in loader._temp_dirs


def test_tar_symlink_still_rejected(tmp_path, monkeypatch):
    """共用审查不得削弱 tar 侧的链接拒绝（回归护栏）。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        data = b"payload"
        info = tarfile.TarInfo("evil.txt")
        info.size = len(data)
        info.type = tarfile.SYMTYPE
        tar.addfile(info, io.BytesIO(data))
    src = tmp_path / "m.tar"
    src.write_bytes(buf.getvalue())

    tar_obj = tarfile.open(src)
    target = tmp_path / "out"
    target.mkdir()
    with pytest.raises(SecurityError, match="符号链接/硬链接"):
        loader._safe_extract(tar_obj, str(target))
