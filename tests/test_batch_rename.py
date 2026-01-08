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
    
    def test_index3_format(self, renamer):
        """测试三位数序号格式"""
        path = "file.txt"
        result = renamer._apply_template(path, "doc_{index3}", 99)
        assert result == "doc_099.txt"
        
        result = renamer._apply_template(path, "doc_{index3}", 1)
        assert result == "doc_001.txt"
    
    def test_datetime_combined(self, renamer):
        """测试日期时间组合变量"""
        path = "file.txt"
        result = renamer._apply_template(path, "backup_{datetime}", 1)
        # 格式: backup_YYYYMMDD_HHMMSS.txt
        # backup_ = 7, YYYYMMDD_HHMMSS = 15, .txt = 4, total = 26
        assert len(result) == 26
        assert result.startswith("backup_")
        assert result.endswith(".txt")
        # 验证格式
        assert "_" in result[7:]  # datetime 部分包含下划线
    
    def test_extension_handling(self, renamer):
        """测试扩展名处理"""
        # 无扩展名的文件
        path = "README"
        result = renamer._apply_template(path, "{name}_copy", 1)
        assert result == "README_copy"
        
        # 多点文件名
        path = "archive.tar.gz"
        result = renamer._apply_template(path, "{name}_backup", 1)
        assert result == "archive.tar_backup.gz"
    
    def test_special_characters_sanitization(self, renamer):
        """测试特殊字符清理"""
        # 包含非法字符的模板
        template = "{name}_<new>|version?"
        path = "file.txt"
        result = renamer._apply_template(path, template, 1)
        # 非法字符应被替换为下划线
        assert "<" not in result
        assert "|" not in result
        assert "?" not in result
    
    def test_empty_template(self, renamer):
        """测试空模板"""
        path = "file.txt"
        result = renamer._apply_template(path, "", 1)
        # 空模板应返回原扩展名
        assert result == ".txt"
    
    def test_no_variables_template(self, renamer):
        """测试无变量的固定模板"""
        path = "file.txt"
        result = renamer._apply_template(path, "static_name", 1)
        assert result == "static_name.txt"
    
    def test_preview_with_conflicts(self, renamer):
        """测试预览时的名称冲突检测"""
        # 两个文件会生成相同的新名称
        files = ["/tmp/a.txt", "/tmp/b.txt"]
        template = "same_name"
        
        results = renamer.preview(files, template, start_index=1)
        
        # 两个文件会生成相同的名称
        assert results[0]['new_name'] == results[1]['new_name']
    
    def test_execute_success(self, renamer, tmp_path):
        """测试实际重命名成功"""
        # 创建测试文件
        file1 = tmp_path / "old1.txt"
        file2 = tmp_path / "old2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        # 生成重命名计划（使用 preview 方法生成完整的数据结构）
        files = [str(file1), str(file2)]
        template = "new{index}"
        rename_plan = renamer.preview(files, template, start_index=1)
        
        # 执行重命名
        success, fail = renamer.execute(rename_plan)
        
        assert success == 2
        assert fail == 0
        assert (tmp_path / "new01.txt").exists()
        assert (tmp_path / "new02.txt").exists()
        assert not file1.exists()
        assert not file2.exists()
    
    def test_execute_partial_failure(self, renamer, tmp_path):
        """测试部分失败的情况"""
        # 创建一个存在的文件和一个不存在的文件路径
        file1 = tmp_path / "file1.txt"
        file1.write_text("content")
        file2_nonexist = tmp_path / "nonexistent.txt"
        
        # 使用 preview 生成计划
        files = [str(file1), str(file2_nonexist)]
        template = "renamed{index}"
        rename_plan = renamer.preview(files, template, start_index=1)
        
        success, fail = renamer.execute(rename_plan)
        
        # 第一个成功，第二个因为文件不存在而失败
        assert success == 1
        assert fail == 1
        assert (tmp_path / "renamed01.txt").exists()
    
    def test_unicode_filename(self, renamer):
        """测试 Unicode 文件名"""
        path = "测试文件.txt"
        result = renamer._apply_template(path, "{name}_副本", 1)
        assert result == "测试文件_副本.txt"
    
    def test_long_filename(self, renamer):
        """测试长文件名"""
        long_name = "a" * 200 + ".txt"
        result = renamer._apply_template(long_name, "{name}_{index}", 1)
        # 结果应包含所有字符
        assert "a" * 200 in result
        assert result.endswith(".txt")
    
    def test_start_index_custom(self, renamer):
        """测试自定义起始序号"""
        files = ["/tmp/a.txt", "/tmp/b.txt", "/tmp/c.txt"]
        template = "file_{index}"
        
        # 从 10 开始
        results = renamer.preview(files, template, start_index=10)
        
        assert results[0]['new_name'] == "file_10.txt"
        assert results[1]['new_name'] == "file_11.txt"
        assert results[2]['new_name'] == "file_12.txt"
    
    def test_mixed_extensions(self, renamer):
        """测试混合扩展名的文件"""
        files = [
            "/tmp/doc.pdf",
            "/tmp/image.png",
            "/tmp/data.xlsx",
            "/tmp/README"  # 无扩展名
        ]
        template = "file_{index}"
        
        results = renamer.preview(files, template, start_index=1)
        
        assert results[0]['new_name'] == "file_01.pdf"
        assert results[1]['new_name'] == "file_02.png"
        assert results[2]['new_name'] == "file_03.xlsx"
        assert results[3]['new_name'] == "file_04"  # 保持无扩展名