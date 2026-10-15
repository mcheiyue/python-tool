"""上游官方包安装：预置 zip 优先，manifest 驱动的下载兜底。

读取 plugins/manifest.json（version/url/sha256）→ 下载到 libs/.temp
→ sha256 校验 → 委托 BundleLoader.extract_zip 安全解压。所有失败静默降级
（返回 None 并记日志）：网络不可用/URL 失效都不阻塞界面，由发现链继续回退
到 PATH 与系统路径。
"""
import json
import os

from core.utils.logger import AppLogger
from core.tools.downloader import Downloader


def _default_loader():
    from core.bundles.loader import loader
    return loader


class PackageStore:
    """单个工具的 zip 装载（预置或下载）。失败一律返回 None，不抛给 UI 层。"""

    def __init__(self, loader=None, downloader=None):
        self._loader = loader if loader is not None else _default_loader()
        self._downloader = downloader if downloader is not None else Downloader()
        self._logger = AppLogger()

    def install(self, tool_name, persistent=False,
                on_progress=None, should_cancel=None):
        """安装工具包，返回解压出的目录；任何失败返回 None。"""
        zip_path = self.locate_zip(tool_name)
        if zip_path:
            return self._extract(zip_path, persistent, tool_name)

        entry = self.read_manifest_entry(tool_name)
        if not entry:
            return None

        from core.utils.resource_path import get_app_root
        stage = os.path.join(get_app_root(), "libs", ".temp", f"stage_{tool_name}.zip")
        os.makedirs(os.path.dirname(stage), exist_ok=True)

        try:
            self._downloader.download(
                entry["url"], stage,
                expected_sha256=entry.get("sha256"),
                on_progress=on_progress,
                should_cancel=should_cancel,
            )
        except Exception as e:
            self._logger.error(f"下载 {tool_name} 失败: {e}")
            return None

        try:
            return self._extract(stage, persistent, tool_name)
        finally:
            # zip 只是解压源：持久化解压后不再需要，临时模式退出即清
            try:
                os.remove(stage)
            except OSError:
                pass

    def locate_zip(self, tool_name):
        """预置 zip（随安装包分发）：内部资源优先，外部 plugins 目录兜底。"""
        from core.utils.resource_path import get_app_root, get_resource_path
        internal = get_resource_path(f"plugins/{tool_name}.zip")
        if os.path.exists(internal):
            return internal
        external = os.path.join(get_app_root(), "plugins", f"{tool_name}.zip")
        return external if os.path.exists(external) else None

    def read_manifest_entry(self, tool_name):
        """读 plugins/manifest.json 中该工具的条目；缺文件/缺条目返回 None。"""
        from core.utils.resource_path import get_app_root, get_resource_path
        for candidate in (
            get_resource_path("plugins/manifest.json"),
            os.path.join(get_app_root(), "plugins", "manifest.json"),
        ):
            try:
                with open(candidate, encoding="utf-8") as f:
                    manifest = json.load(f)
            except (OSError, ValueError):
                continue
            entry = manifest.get(tool_name)
            if isinstance(entry, dict) and entry.get("url"):
                return entry
            return None
        return None

    def _extract(self, zip_path, persistent, tool_name):
        try:
            return self._loader.extract_zip(
                zip_path, persistent=persistent, subdir=tool_name
            )
        except Exception as e:
            self._logger.error(f"解压 {os.path.basename(zip_path)} 失败: {e}")
            return None
