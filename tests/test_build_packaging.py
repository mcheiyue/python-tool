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
    assert re.search(r'--include-data-files=%PYMUPDF_DIR%\\mupdf\.py=mupdf\.py', text)
    assert re.search(r'--include-data-files=%PYMUPDF_DIR%\\_mupdf\.pyd=_mupdf\.pyd', text)

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
