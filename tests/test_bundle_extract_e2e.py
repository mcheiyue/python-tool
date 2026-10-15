"""extract_bundle 端到端测试（首次真执行整条链）。

现有测试只隔离验证 read_bundle（验签）与 _safe_extract（mock tar）；
本文件补上从未执行过的完整路径：
    读头 → 验签 → LZMA 解压 → 安全解包 → 顶层目录定位 → 缓存 → 返回路径
用本地生成密钥对经 public_key 注入（b2 可插拔槽），零网络、零真二进制。
"""
import tarfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.bundles.format import pack_bundle
from core.bundles.loader import BundleLoader


@pytest.fixture
def loader_env(tmp_path, monkeypatch):
    """将 get_app_root 定向到 tmp，并重置单例缓存"""
    import core.utils.resource_path as rp

    monkeypatch.setattr(rp, "get_app_root", lambda: str(tmp_path))
    ldr = BundleLoader()
    ldr._extracted_cache.clear()
    ldr._temp_dirs.clear()
    yield ldr, tmp_path
    ldr.cleanup()
    ldr._extracted_cache.clear()


def _pack_gs_bundle(tmp_path: Path, key, tool_id: int = 0) -> Path:
    """构造带真实目录层级的 ghostscript 源并打包"""
    src = tmp_path / "src" / "ghostscript"
    (src / "lib").mkdir(parents=True)
    (src / "gswin64c.exe").write_bytes(b"fake gs binary")
    (src / "lib" / "gs_init.ps").write_text("% gs init", encoding="utf-8")
    out = tmp_path / "ghostscript.mcy"
    pack_bundle(str(src), str(out), tool_id, key)
    return out


class TestExtractBundleE2E:

    def test_temp_mode_full_chain(self, loader_env):
        ldr, tmp_path = loader_env
        key = Ed25519PrivateKey.generate()
        bundle = _pack_gs_bundle(tmp_path, key)

        result = ldr.extract_bundle(str(bundle), persistent=False, public_key=key.public_key())

        assert result is not None
        assert Path(result).name == "ghostscript"
        assert (Path(result) / "gswin64c.exe").read_bytes() == b"fake gs binary"
        assert (Path(result) / "lib" / "gs_init.ps").read_text(encoding="utf-8") == "% gs init"
        # 临时模式落在 libs/.temp/session_* 下
        assert ".temp" in Path(result).parts

    def test_persistent_mode_extracts_to_libs(self, loader_env):
        ldr, tmp_path = loader_env
        key = Ed25519PrivateKey.generate()
        bundle = _pack_gs_bundle(tmp_path, key)

        result = ldr.extract_bundle(str(bundle), persistent=True, public_key=key.public_key())

        assert result is not None
        assert Path(result) == tmp_path / "libs" / "ghostscript"
        assert (Path(result) / "gswin64c.exe").exists()

    def test_cache_hit_returns_same_path(self, loader_env):
        ldr, tmp_path = loader_env
        key = Ed25519PrivateKey.generate()
        bundle = _pack_gs_bundle(tmp_path, key)

        first = ldr.extract_bundle(str(bundle), public_key=key.public_key())
        second = ldr.extract_bundle(str(bundle), public_key=key.public_key())

        assert first == second

    def test_missing_file_raises(self, loader_env):
        ldr, tmp_path = loader_env
        with pytest.raises(FileNotFoundError):
            ldr.extract_bundle(str(tmp_path / "nope.mcy"))

    def test_tampered_bundle_returns_none(self, loader_env):
        ldr, tmp_path = loader_env
        key = Ed25519PrivateKey.generate()
        bundle = _pack_gs_bundle(tmp_path, key)

        data = bytearray(bundle.read_bytes())
        data[-1] ^= 0xFF
        bundle.write_bytes(bytes(data))

        assert ldr.extract_bundle(str(bundle), public_key=key.public_key()) is None

    def test_nested_dirs_preserved(self, loader_env):
        ldr, tmp_path = loader_env
        key = Ed25519PrivateKey.generate()

        src = tmp_path / "src" / "pandoc"
        (src / "share" / "templates").mkdir(parents=True)
        (src / "pandoc.exe").write_bytes(b"fake pandoc")
        (src / "share" / "templates" / "default.tex").write_text("tpl", encoding="utf-8")
        bundle = tmp_path / "pandoc.mcy"
        pack_bundle(str(src), str(bundle), 1, key)

        result = ldr.extract_bundle(str(bundle), public_key=key.public_key())

        assert Path(result).name == "pandoc"
        assert (Path(result) / "share" / "templates" / "default.tex").read_text(encoding="utf-8") == "tpl"
