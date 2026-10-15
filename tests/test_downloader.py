"""下载器测试：fake transport 注入，零真实网络。

覆盖 happy path（流式+进度+hash 通过）、四类失败（HTTP 4xx、网络错误重试、
hash 不符、取消）与部分文件清理。
"""
import hashlib
import io

import pytest

from core.tools.downloader import DownloadError, Downloader

DATA = b"fake-pandoc-binary-content" * 4096
GOOD_SHA = hashlib.sha256(DATA).hexdigest()


class _FakeResponse:
    def __init__(self, data, status=200, headers=None, fail_after=None):
        self._buf = io.BytesIO(data)
        self.status = status
        self.headers = headers if headers is not None else {
            "Content-Length": str(len(data))
        }
        self._fail_after = fail_after
        self.closed = False

    def read(self, size):
        if self._fail_after is not None:
            if self._fail_after <= 0:
                raise OSError("connection reset")
            self._fail_after -= size
        return self._buf.read(size)

    def close(self):
        self.closed = True


def _fetcher(response):
    def fetch(url, timeout):
        return response
    return fetch


def test_download_verifies_and_reports_progress(tmp_path):
    resp = _FakeResponse(DATA)
    dl = Downloader(fetch=_fetcher(resp))
    dest = tmp_path / "tool.zip"
    seen = []
    result = dl.download(
        "https://example.invalid/tool.zip", str(dest),
        expected_sha256=GOOD_SHA,
        on_progress=lambda d, t: seen.append((d, t)),
    )
    assert result == str(dest)
    assert dest.read_bytes() == DATA
    assert not (tmp_path / "tool.zip.part").exists()
    assert seen[-1][0] == len(DATA)
    assert seen[0][1] == len(DATA)
    assert resp.closed is True


def test_http_error_not_retried(tmp_path):
    resp = _FakeResponse(b"not found", status=404)
    dl = Downloader(fetch=_fetcher(resp))
    with pytest.raises(DownloadError, match="HTTP 404"):
        dl.download("https://example.invalid/x.zip", str(tmp_path / "x.zip"))
    assert not (tmp_path / "x.zip.part").exists()


def test_network_error_retries_then_fails(tmp_path):
    calls = []

    def flaky(url, timeout):
        calls.append(url)
        raise OSError("connection refused")

    dl = Downloader(fetch=flaky, chunk_size=1024)
    with pytest.raises(DownloadError, match="无法连接"):
        dl.download("https://example.invalid/x.zip", str(tmp_path / "x.zip"),
                    retries=1)
    assert len(calls) == 2  # 初次 + 1 次重试
    assert not (tmp_path / "x.zip.part").exists()


def test_hash_mismatch_rejected(tmp_path):
    resp = _FakeResponse(b"tampered-content")
    dl = Downloader(fetch=_fetcher(resp))
    with pytest.raises(DownloadError, match="sha256"):
        dl.download("https://example.invalid/x.zip", str(tmp_path / "x.zip"),
                    expected_sha256=GOOD_SHA)
    assert not (tmp_path / "x.zip.part").exists()


def test_cancel_midway_cleans_partial(tmp_path):
    resp = _FakeResponse(DATA)
    dl = Downloader(fetch=_fetcher(resp), chunk_size=1024)
    with pytest.raises(DownloadError, match="取消"):
        dl.download("https://example.invalid/x.zip", str(tmp_path / "x.zip"),
                    expected_sha256=GOOD_SHA,
                    should_cancel=lambda: True)
    assert not (tmp_path / "x.zip.part").exists()


def test_http_error_from_urlopen_raises_http_error(tmp_path):
    import urllib.error

    def raising(url, timeout):
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

    dl = Downloader(fetch=raising)
    with pytest.raises(DownloadError, match="HTTP 403"):
        dl.download("https://example.invalid/x.zip", str(tmp_path / "x.zip"))
