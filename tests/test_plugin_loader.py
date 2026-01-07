import os
import pytest
import tarfile
from unittest.mock import MagicMock, patch
from core.plugin_loader import PluginLoader, SecurityError

class TestPluginLoader:
    
    @pytest.fixture
    def loader(self):
        return PluginLoader()
    
    def test_safe_extract_path_traversal(self, loader, tmp_path):
        """测试路径穿越保护"""
        target_dir = tmp_path / "plugins"
        target_dir.mkdir()
        
        # 模拟恶意的 TarInfo 对象
        # 尝试跳出目标目录
        malicious_member = tarfile.TarInfo(name="../../evil.exe")
        
        # 创建一个模拟的 tar 对象
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [malicious_member]
        
        # 预期抛出 SecurityError
        with pytest.raises(SecurityError) as excinfo:
            loader._safe_extract(mock_tar, str(target_dir))
            
        assert "路径穿越攻击检测" in str(excinfo.value)

    def test_safe_extract_absolute_path(self, loader, tmp_path):
        """测试绝对路径攻击"""
        target_dir = tmp_path / "plugins"
        target_dir.mkdir()
        
        # 尝试写入系统关键目录（这里用 tmp_path 的父目录模拟外部目录）
        external_path = str(tmp_path.parent / "evil.exe")
        # 在 Windows 上，tarfile 可能会保留驱动器号，例如 C:/Windows/System32/...
        # 这里我们模拟一个绝对路径
        
        malicious_member = tarfile.TarInfo(name=external_path)
        
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [malicious_member]
        
        with pytest.raises(SecurityError) as excinfo:
            loader._safe_extract(mock_tar, str(target_dir))
            
        assert "路径穿越攻击检测" in str(excinfo.value)
        
    def test_safe_extract_valid(self, loader, tmp_path):
        """测试正常解压"""
        target_dir = tmp_path / "plugins"
        target_dir.mkdir()
        
        valid_member = tarfile.TarInfo(name="plugin/data.txt")
        
        mock_tar = MagicMock(spec=tarfile.TarFile)
        mock_tar.getmembers.return_value = [valid_member]
        
        # 正常解压不应报错
        loader._safe_extract(mock_tar, str(target_dir))
        
        # 验证 extractall 被调用
        mock_tar.extractall.assert_called_once_with(path=str(target_dir))