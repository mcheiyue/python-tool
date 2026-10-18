import re
from pathlib import Path

from core.utils.version import get_app_version

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"


def test_version_file_exists_and_is_semver():
    assert VERSION_FILE.is_file(), "仓库根缺少 VERSION 文件"
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION_FILE.read_text(encoding="utf-8").strip())


def test_app_version_matches_version_file():
    assert get_app_version() == VERSION_FILE.read_text(encoding="utf-8").strip()


def test_build_scripts_read_version_file_and_hardcode_nowhere():
    for name in ("build_nuitka.bat", "build_release.bat", "build_dev.bat", "installer.iss"):
        text = (ROOT / "build" / name).read_text(encoding="utf-8", errors="replace")
        assert "VERSION" in text, f"{name} 未引用 VERSION 文件"
        assert not re.search(r"APP_VERSION=\d+\.\d+\.\d+", text), f"{name} 写死了版本号"
        assert not re.search(r"--(?:file|product)-version=\d", text), f"{name} 写死了版本号"
        assert not re.search(r'MyAppVersion\s+"\d+\.\d+\.\d+"', text), f"{name} 写死了版本号"
