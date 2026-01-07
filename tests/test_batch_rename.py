import os
import pytest
from datetime import datetime
from core.features.utils.batch_rename import BatchRenamer

class TestBatchRenamer:
    @pytest.fixture
    def renamer(self):
        return BatchRenamer()

    def test_template_parsing(self, renamer):
        """测试模板解析逻辑"""
        path = "test_file.txt"
        
        # 测试基本变量
        assert renamer._apply_template(path, "{name}_backup", 1) == "test_file_backup.txt"
        assert renamer._apply_template(path, "{name}.{ext}", 1) == "test_file.txt"
        
        # 测试序号
        assert renamer._apply_template(path, "{name}_{index}", 5) == "test_file_05.txt"
        
        # 测试日期时间 (仅验证格式长度)
        result = renamer._apply_template(path, "{date}_{time}", 1)
        # YYYYMMDD_HHMMSS (15) + .txt (4) = 19
        assert len(result) == 8 + 1 + 6 + 4
        
    def test_preview_generation(self, renamer):
        """测试预览生成"""
        files = ["/tmp/a.txt", "/tmp/b.jpg"]
        template = "file_{index}"
        
        results = renamer.preview(files, template, start_index=1)
        
        assert len(results) == 2
        assert results[0]['new_name'] == "file_01.txt"
        assert results[1]['new_name'] == "file_02.jpg"
        assert results[0]['original'] == "/tmp/a.txt"