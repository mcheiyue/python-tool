"""上游官方包下载器（B 链路）：流式下载 + sha256 校验 + 取消/重试。

零第三方依赖（urllib.request）。全部失败路径通过注入 fetch 替身在测试中覆盖，
不打真实网络。
"""
import hashlib
import os
import urllib.error
import urllib.request

_USER_AGENT = "OfficeToolkit/1.0 (external tool downloader)"
_CHUNK_SIZE = 1 << 18


class DownloadError(Exception):
    """下载或校验失败。

    message 面向最终用户可直接展示；retryable 标记网络类临时失败（可重试），
    HTTP 4xx/4xx 与 hash 不符属确定性失败，重试无益。
    """

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def default_fetch(url: str, timeout: float):
    """默认传输：urllib 直连。测试注入替身。"""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


class Downloader:
    """单文件流式下载器。下载中先写 <dest>.part，成功后原子替换。"""

    def __init__(self, fetch=default_fetch, chunk_size=_CHUNK_SIZE):
        self._fetch = fetch
        self._chunk_size = chunk_size

    def download(self, url, dest_path, expected_sha256=None,
                 on_progress=None, should_cancel=None, timeout=30, retries=1):
        """下载 url 到 dest_path 并校验 sha256，返回 dest_path。

        :param on_progress: (downloaded_bytes, total_bytes_or_None) 回调，在下载线程调用
        :param should_cancel: 返回真值时中止下载并抛 DownloadError("下载已取消")
        :raises DownloadError: 网络错误（重试耗尽）/HTTP 错误/hash 不符/被取消
        """
        part_path = dest_path + ".part"
        attempts = retries + 1

        for attempt in range(1, attempts + 1):
            try:
                self._download_once(
                    url, part_path, expected_sha256,
                    on_progress, should_cancel, timeout,
                )
                os.replace(part_path, dest_path)
                return dest_path
            except DownloadError as e:
                self._remove(part_path)
                if e.retryable and attempt < attempts:
                    continue
                raise
        raise DownloadError("下载失败：重试次数耗尽", retryable=False)

    def _download_once(self, url, part_path, expected_sha256,
                       on_progress, should_cancel, timeout):
        digest = hashlib.sha256()
        downloaded = 0

        try:
            response = self._fetch(url, timeout)
        except urllib.error.HTTPError as e:
            raise DownloadError(
                f"服务器返回 HTTP {e.code}（URL 可能失效，需更新 manifest）",
                retryable=False,
            ) from e
        except Exception as e:
            raise DownloadError(f"无法连接：{e}", retryable=True) from e

        with open(part_path, "wb") as f:
            try:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                if status is not None and int(status) >= 400:
                    raise DownloadError(f"服务器返回 HTTP {status}", retryable=False)

                total = self._content_length(response)
                while True:
                    if should_cancel is not None and should_cancel():
                        raise DownloadError("下载已取消")
                    chunk = response.read(self._chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if on_progress is not None:
                        on_progress(downloaded, total)
            finally:
                close = getattr(response, "close", None)
                if close is not None:
                    close()

        if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
            raise DownloadError(
                "sha256 校验失败（文件损坏或 manifest 需更新）", retryable=False
            )

    @staticmethod
    def _content_length(response):
        headers = getattr(response, "headers", None)
        if headers is None:
            return None
        try:
            return int(headers.get("Content-Length") or 0) or None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _remove(path):
        try:
            os.remove(path)
        except OSError:
            pass
