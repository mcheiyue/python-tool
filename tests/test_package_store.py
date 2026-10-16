"""PackageStore 测试：fake transport 注入，零真实网络。

覆盖：预置 zip 命中、manifest 缺条目、下载+解压成功、hash 不符降级、
网络错误降级、staged zip 清理、来源指纹护栏（source_identity / is_current / 标记写入）。
"""
import hashlib
import io
import json
import os
import zipfile

import pytest

from core.tools.package_store import PackageStore


def _make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return str(path)


class _StubLoader:
    """记录 extract_zip 调用，直接返回指定目录。"""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def extract_zip(self, zip_path, persistent=False, subdir=None):
        self.calls.append((zip_path, persistent, subdir))
        return self.result


class _FakeResponse:
    def __init__(self, data):
        self._buf = io.BytesIO(data)
        self.status = 200
        self.headers = {"Content-Length": str(len(data))}

    def read(self, size):
        return self._buf.read(size)

    def close(self):
        pass


def _store(tmp_path, loader, response=None, manifest=None):
    if manifest is not None:
        (tmp_path / "plugins").mkdir(exist_ok=True)
        (tmp_path / "plugins" / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    from core.tools.downloader import Downloader
    fetch = (lambda url, timeout: _FakeResponse(response)) if response is not None else None
    return PackageStore(
        loader=loader,
        downloader=Downloader(fetch=fetch) if fetch else Downloader(),
    )


@pytest.fixture
def app_root(tmp_path, monkeypatch):
    monkeypatch.setattr("core.utils.resource_path.get_app_root", lambda: str(tmp_path))
    monkeypatch.setattr(
        "core.utils.resource_path.get_resource_path",
        lambda rel: str(tmp_path / "_internal" / rel),
    )
    return tmp_path


def test_preplaced_zip_used_without_manifest(app_root):
    extracted = app_root / "libs" / "pandoc"
    extracted.mkdir(parents=True)
    z = _make_zip(app_root / "plugins" / "pandoc.zip", {"a": b"x"}) \
        if (app_root / "plugins").mkdir() is None else None
    loader = _StubLoader(str(extracted))
    store = _store(app_root, loader)
    result = store.install("pandoc")
    assert result == str(extracted)
    assert loader.calls  # 走了预置 zip，没读 manifest


def test_manifest_download_and_extract(app_root):
    payload = b"official-binary" * 1000
    import hashlib
    manifest = {
        "pandoc": {
            "version": "3.12.1",
            "url": "https://example.invalid/pandoc.zip",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    }
    extracted = app_root / "libs" / "pandoc"
    extracted.mkdir(parents=True)
    loader = _StubLoader(str(extracted))
    store = _store(app_root, loader, response=payload, manifest=manifest)

    progress = []
    result = store.install("pandoc", persistent=False,
                           on_progress=lambda d, t: progress.append(d))

    assert result == str(extracted)
    assert loader.calls
    assert loader.calls[0][1] is False
    assert loader.calls[0][2] == "pandoc"
    assert progress[-1] == len(payload)
    # staged zip 已清理
    assert not (app_root / "libs" / ".temp" / "stage_pandoc.zip").exists()


def test_manifest_missing_entry_returns_none(app_root):
    loader = _StubLoader("/should/not/be/used")
    store = _store(app_root, loader, manifest={})
    assert store.install("ghostscript") is None
    assert not loader.calls


def test_hash_mismatch_silently_degrades(app_root):
    manifest = {
        "pandoc": {
            "version": "3.12.1",
            "url": "https://example.invalid/pandoc.zip",
            "sha256": "0" * 64,
        }
    }
    loader = _StubLoader("/should/not/be/used")
    store = _store(app_root, loader, response=b"tampered", manifest=manifest)
    assert store.install("pandoc") is None
    assert not loader.calls
    assert not (app_root / "libs" / ".temp" / "stage_pandoc.zip").exists()


def test_network_error_silently_degrades(app_root):
    def boom(url, timeout):
        raise OSError("offline")

    from core.tools.downloader import Downloader
    manifest = {
        "pandoc": {
            "version": "3.12.1",
            "url": "https://example.invalid/pandoc.zip",
            "sha256": "a" * 64,
        }
    }
    loader = _StubLoader("/should/not/be/used")
    store = PackageStore(loader=loader, downloader=Downloader(fetch=boom))
    assert store.install("pandoc") is None


def _write_manifest(app_root, entry):
    (app_root / "plugins").mkdir(exist_ok=True)
    (app_root / "plugins" / "manifest.json").write_text(
        json.dumps({"pandoc": entry}), encoding="utf-8"
    )


def test_source_identity_prefers_manifest_sha256(app_root):
    _write_manifest(app_root, {"url": "https://x/p.zip", "sha256": "AB" * 32})
    _make_zip(app_root / "plugins" / "pandoc.zip", {"pandoc/pandoc.exe": b"x"})
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.source_identity("pandoc") == "sha256:" + "ab" * 32


def test_source_identity_falls_back_to_zip_fingerprint(app_root):
    (app_root / "plugins").mkdir(exist_ok=True)
    z = app_root / "plugins" / "pandoc.zip"
    _make_zip(z, {"pandoc/pandoc.exe": b"x"})
    st = z.stat()
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.source_identity("pandoc") == f"zip:{int(st.st_mtime)}:{st.st_size}"


def test_source_identity_none_without_source(app_root):
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.source_identity("pandoc") is None


def test_persistent_install_writes_source_marker(app_root):
    (app_root / "plugins").mkdir(exist_ok=True)
    z = app_root / "plugins" / "pandoc.zip"
    _make_zip(z, {"pandoc/pandoc.exe": b"x"})
    sha = hashlib.sha256(z.read_bytes()).hexdigest()
    _write_manifest(app_root, {"url": "https://x/p.zip", "sha256": sha})
    extracted = app_root / "libs" / "pandoc"
    extracted.mkdir(parents=True)
    store = PackageStore(loader=_StubLoader(str(extracted)))

    assert store.install("pandoc", persistent=True) == str(extracted)
    marker = extracted / ".source-id"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "sha256:" + sha


def test_temporary_install_writes_no_marker(app_root):
    (app_root / "plugins").mkdir(exist_ok=True)
    _make_zip(app_root / "plugins" / "pandoc.zip", {"pandoc/pandoc.exe": b"x"})
    extracted = app_root / "libs" / ".temp" / "session_x"
    extracted.mkdir(parents=True)
    store = PackageStore(loader=_StubLoader(str(extracted)))

    assert store.install("pandoc", persistent=False) == str(extracted)
    assert not (extracted / ".source-id").exists()


def test_is_current_false_when_marker_mismatches(app_root):
    _write_manifest(app_root, {"url": "https://x/p.zip", "sha256": "ab" * 32})
    tool_dir = app_root / "libs" / "pandoc"
    tool_dir.mkdir(parents=True)
    (tool_dir / ".source-id").write_text("sha256:" + "cd" * 32, encoding="utf-8")
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.is_current(str(tool_dir), "pandoc") is False


def test_is_current_true_when_marker_matches(app_root):
    _write_manifest(app_root, {"url": "https://x/p.zip", "sha256": "ab" * 32})
    tool_dir = app_root / "libs" / "pandoc"
    tool_dir.mkdir(parents=True)
    (tool_dir / ".source-id").write_text("sha256:" + "ab" * 32, encoding="utf-8")
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.is_current(str(tool_dir), "pandoc") is True


def test_is_current_true_without_marker(app_root):
    _write_manifest(app_root, {"url": "https://x/p.zip", "sha256": "ab" * 32})
    tool_dir = app_root / "libs" / "pandoc"
    tool_dir.mkdir(parents=True)
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.is_current(str(tool_dir), "pandoc") is True


def test_is_current_true_when_source_unknown(app_root):
    tool_dir = app_root / "libs" / "pandoc"
    tool_dir.mkdir(parents=True)
    (tool_dir / ".source-id").write_text("sha256:" + "ab" * 32, encoding="utf-8")
    store = PackageStore(loader=_StubLoader("unused"))
    assert store.is_current(str(tool_dir), "pandoc") is True


def test_sha256_file_returns_lowercase_digest(app_root):
    from core.tools.downloader import sha256_file

    payload = b"streamed-content" * 64
    target = app_root / "blob.bin"
    target.write_bytes(payload)
    assert sha256_file(str(target)) == hashlib.sha256(payload).hexdigest()


def test_preplaced_zip_used_when_hash_matches(app_root):
    (app_root / "plugins").mkdir(exist_ok=True)
    zip_path = app_root / "plugins" / "pandoc.zip"
    _make_zip(zip_path, {"pandoc/pandoc.exe": b"x"})
    _write_manifest(app_root, {
        "url": "https://example.invalid/p.zip",
        "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    })

    from core.tools.downloader import Downloader

    def _boom(url, timeout):
        raise AssertionError(f"hash 一致时不该触发下载: {url}")

    extracted = app_root / "libs" / "pandoc"
    extracted.mkdir(parents=True)
    loader = _StubLoader(str(extracted))
    store = PackageStore(loader=loader, downloader=Downloader(fetch=_boom))

    assert store.install("pandoc") == str(extracted)
    assert loader.calls
    assert loader.calls[0][0] == str(zip_path)


def test_preplaced_zip_skipped_when_hash_mismatches(app_root):
    payload = b"official-bytes" * 100
    (app_root / "plugins").mkdir(exist_ok=True)
    _make_zip(app_root / "plugins" / "pandoc.zip", {"pandoc/pandoc.exe": b"stale"})
    manifest = {
        "pandoc": {
            "version": "3.12.1",
            "url": "https://example.invalid/pandoc.zip",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    }
    extracted = app_root / "libs" / "pandoc"
    extracted.mkdir(parents=True)
    loader = _StubLoader(str(extracted))
    store = _store(app_root, loader, response=payload, manifest=manifest)

    assert store.install("pandoc") == str(extracted)
    assert loader.calls
    assert loader.calls[0][0].endswith("stage_pandoc.zip")


def test_preplaced_zip_mismatch_degrades_when_download_fails(app_root):
    (app_root / "plugins").mkdir(exist_ok=True)
    _make_zip(app_root / "plugins" / "pandoc.zip", {"pandoc/pandoc.exe": b"stale"})
    manifest = {
        "pandoc": {
            "version": "3.12.1",
            "url": "https://example.invalid/pandoc.zip",
            "sha256": "0" * 64,
        }
    }
    loader = _StubLoader("/should/not/be/used")
    store = _store(app_root, loader, response=b"tampered", manifest=manifest)

    assert store.install("pandoc") is None
    assert not loader.calls
    assert not (app_root / "libs" / ".temp" / "stage_pandoc.zip").exists()
