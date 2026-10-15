"""Tool Bundle v2 格式与加载器测试。

覆盖 ADR-0003 验收项：v2 打包/解包往返、篡改签名拒绝、v1 样本拒绝；
外加签名密钥不匹配拒绝与 _safe_extract 路径/链接安全契约。
"""
import io
import tarfile
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.bundles.format import BundleFormatError, pack_bundle, read_bundle
from core.bundles.loader import BundleLoader, SecurityError


def _make_signed_bundle(tmp_path, key, tool_id=0):
    src = tmp_path / "ghostscript"
    src.mkdir()
    (src / "gswin64c.exe").write_bytes(b"fake binary")
    out = tmp_path / "gs.mcy"
    pack_bundle(str(src), str(out), tool_id, key)
    return out


class TestBundleFormat:

    def test_v2_roundtrip(self, tmp_path):
        key = Ed25519PrivateKey.generate()
        out = _make_signed_bundle(tmp_path, key, tool_id=1)

        tool_id, tar_data = read_bundle(str(out), key.public_key())

        assert tool_id == 1
        with tarfile.open(fileobj=io.BytesIO(tar_data)) as tar:
            names = tar.getnames()
        assert any("gswin64c.exe" in n for n in names)

    def test_tampered_signature_rejected(self, tmp_path):
        key = Ed25519PrivateKey.generate()
        out = _make_signed_bundle(tmp_path, key)

        data = bytearray(out.read_bytes())
        data[-1] ^= 0xFF  # 篡改压缩载荷末字节
        out.write_bytes(bytes(data))

        # 篡改压缩载荷会被 LZMA 层发现（"解压失败"）；
        # 若篡改恰好落在可解压区域，则由签名兜底（"签名"）。
        # 二者都必须是 BundleFormatError，不允许静默通过。
        with pytest.raises(BundleFormatError, match="(解压失败|签名)"):
            read_bundle(str(out), key.public_key())

    def test_v1_sample_rejected(self, tmp_path):
        key = Ed25519PrivateKey.generate()
        v1 = tmp_path / "legacy.mcy"
        # v1 布局：MAGIC(4) + VERSION(1)=1 + 其余
        v1.write_bytes(b"MCY\x00\x01\x00" + b"\x00" * 100)

        with pytest.raises(BundleFormatError, match="版本"):
            read_bundle(str(v1), key.public_key())

    def test_wrong_public_key_rejected(self, tmp_path):
        packer_key = Ed25519PrivateKey.generate()
        other_key = Ed25519PrivateKey.generate()
        out = _make_signed_bundle(tmp_path, packer_key)

        with pytest.raises(BundleFormatError, match="签名"):
            read_bundle(str(out), other_key.public_key())


class TestBundleLoader:

    @pytest.fixture
    def loader(self):
        return BundleLoader()

    def test_safe_extract_path_traversal(self, loader, tmp_path):
        target_dir = tmp_path / "bundles"
        target_dir.mkdir()

        malicious_member = tarfile.TarInfo(name="../../evil.exe")
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [malicious_member]

        with pytest.raises(SecurityError) as excinfo:
            loader._safe_extract(mock_tar, str(target_dir))
        assert "路径穿越攻击检测" in str(excinfo.value)

    def test_safe_extract_absolute_path(self, loader, tmp_path):
        target_dir = tmp_path / "bundles"
        target_dir.mkdir()

        external_path = str(tmp_path.parent / "evil.exe")
        malicious_member = tarfile.TarInfo(name=external_path)
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [malicious_member]

        with pytest.raises(SecurityError) as excinfo:
            loader._safe_extract(mock_tar, str(target_dir))
        assert "路径穿越攻击检测" in str(excinfo.value)

    def test_safe_extract_valid(self, loader, tmp_path):
        target_dir = tmp_path / "bundles"
        target_dir.mkdir()

        valid_member = tarfile.TarInfo(name="bundle/data.txt")
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [valid_member]

        loader._safe_extract(mock_tar, str(target_dir))
        mock_tar.extractall.assert_called_once_with(path=str(target_dir))

    def test_safe_extract_rejects_symlink(self, loader, tmp_path):
        target_dir = tmp_path / "bundles"
        target_dir.mkdir()

        member = tarfile.TarInfo(name="evil_link")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../outside"
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [member]

        with pytest.raises(SecurityError) as excinfo:
            loader._safe_extract(mock_tar, str(target_dir))
        assert "被拒绝" in str(excinfo.value)

    def test_safe_extract_rejects_hardlink(self, loader, tmp_path):
        target_dir = tmp_path / "bundles"
        target_dir.mkdir()

        member = tarfile.TarInfo(name="evil_hard")
        member.type = tarfile.LNKTYPE
        member.linkname = "../../outside"
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [member]

        with pytest.raises(SecurityError) as excinfo:
            loader._safe_extract(mock_tar, str(target_dir))
        assert "被拒绝" in str(excinfo.value)
