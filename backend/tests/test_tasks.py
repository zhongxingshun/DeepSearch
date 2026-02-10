"""
Celery 任务测试
版本: v1.0
"""

import pytest
from pathlib import Path
import tempfile


class TestParseTask:
    """解析任务测试"""

    def test_extract_text_from_txt(self):
        """测试纯文本提取"""
        from app.tasks.parse_task import fallback_extract
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            suffix=".txt",
            mode="w",
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write("Hello, World! 你好世界！")
            temp_path = Path(f.name)
        
        try:
            content = fallback_extract(temp_path, "text")
            assert "Hello" in content
            assert "你好" in content
        finally:
            temp_path.unlink()

    def test_file_type_mapping(self):
        """测试文件类型映射"""
        from app.tasks.scan_task import get_file_type
        
        assert get_file_type("pdf") == "pdf"
        assert get_file_type("docx") == "word"
        assert get_file_type("xlsx") == "excel"
        assert get_file_type("pptx") == "powerpoint"
        assert get_file_type("png") == "image"
        assert get_file_type("unknown") == "other"


class TestScanTask:
    """扫描任务测试"""

    def test_is_allowed_extension(self):
        """测试扩展名检查"""
        from app.tasks.scan_task import is_allowed_extension
        
        assert is_allowed_extension(Path("doc.pdf"))
        assert is_allowed_extension(Path("doc.docx"))
        assert not is_allowed_extension(Path("doc.exe"))

    def test_calculate_md5(self):
        """测试 MD5 计算"""
        from app.tasks.scan_task import calculate_md5
        
        with tempfile.NamedTemporaryFile(
            suffix=".txt",
            mode="w",
            delete=False,
        ) as f:
            f.write("Hello, World!")
            temp_path = Path(f.name)
        
        try:
            md5 = calculate_md5(temp_path)
            assert len(md5) == 32
            assert md5 == "65a8e27d8879283831b664bd8b7f0ad4"
        finally:
            temp_path.unlink()


class TestCleanupTask:
    """清理任务测试"""

    def test_format_size(self):
        """测试大小格式化"""
        from app.tasks.cleanup_task import format_size
        
        assert format_size(500) == "500.0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"


class TestCeleryConfig:
    """Celery 配置测试"""

    def test_queue_config(self):
        """测试队列配置"""
        from app.tasks import celery_app
        
        # 检查队列配置
        queue_names = [q.name for q in celery_app.conf.task_queues]
        assert "high" in queue_names
        assert "low" in queue_names
        assert "maintenance" in queue_names

    def test_beat_schedule(self):
        """测试定时任务配置"""
        from app.tasks import celery_app
        
        schedule = celery_app.conf.beat_schedule
        assert "daily-backup" in schedule
        assert "daily-cleanup" in schedule
        assert "hourly-scan" in schedule
