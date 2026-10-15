"""PackageStore 测试：fake transport 注入，零真实网络。

覆盖：预置 zip 命中、manifest 缺条目、下载+解压成功、hash 不符降级、
网络错误降级、staged zip 清理。
"""
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
