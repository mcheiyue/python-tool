import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUITKA_BAT = ROOT / "build" / "build_nuitka.bat"


def test_pymupdf_mupdf_is_shipped_as_top_level_data_not_include_module():
    """pymupdf.mupdf 必须当顶层数据文件带，不能用 --include-module。

    --nofollow-import-to 优先级高于同名 --include-module，两者并存时 include 被静默否决，
    pymupdf/__init__.py 的 "from . import mupdf" 永久失败，整个包不可导入。这条只在打包
    产物里现形（源码运行完全正常），历史上已因此发过多个坏 Release。
    """
    text = NUITKA_BAT.read_text(encoding="utf-8", errors="replace")

    assert "--nofollow-import-to=pymupdf.mupdf" in text
    assert "--include-module=pymupdf.mupdf" not in text, (
        "pymupdf.mupdf 不能用 --include-module 补：会被 --nofollow-import-to 否决"
    )
    # _mupdf 同理，且重复打包会让产物多背 13MB
    assert "--nofollow-import-to=pymupdf._mupdf" in text
    assert "--include-module=pymupdf._mupdf" not in text

    # 两个文件都要以顶层数据文件形式进入产物（mupdf.py 靠 __init__ 的 import mupdf 兜底）
    # 出现两次：COMMON_FLAGS（目录版 + 单文件版）和 CLI 目标各一份，少一处就有产物缺文件
    assert text.count("--include-data-files=%PYMUPDF_DIR%\\mupdf.py=mupdf.py") == 2
    assert text.count("--include-data-files=%PYMUPDF_DIR%\\_mupdf.pyd=_mupdf.pyd") == 2

    # 定位安装目录的探测必须存在，否则上面两条会展开成不存在的路径
    assert "PYMUPDF_DIR" in text


def test_release_smoke_pins_pymupdf_engine():
    """冒烟里的 pdf-render 必须显式 --engine pymupdf。

    默认 auto 在 PyMuPDF 不可用时会静默回退 Ghostscript，产物里 pymupdf 完全不可
    导入也照样返回 success，v0.0.13 就是这样把坏包发出去的。
    """
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if '@("pdf-render"' in l)
    assert '"--engine"' in line and '"pymupdf"' in line, line


def test_release_smoke_asserts_gui_pymupdf_data_files():
    """GUI 产物也要断言两个顶层 pymupdf 文件存在。

    --benchmark 只测启动，碰不到懒加载的 mupdf，所以 GUI 侧一直没被覆盖到：
    v0.0.6~v0.0.13 的安装版都把「PDF 页面渲染」显示成不可用。
    """
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert '"mupdf.py"' in text and '"_mupdf.pyd"' in text
    assert 'Join-Path $src $f' in text
