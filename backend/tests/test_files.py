"""
文件管理 API 测试
版本: v1.0
"""

import io
import pytest
from httpx import AsyncClient

from app.services.file_storage_service import FileStorageService


class TestFileStorage:
    """文件存储服务测试"""

    def test_calculate_md5(self):
        """测试 MD5 计算"""
        content = b"Hello, World!"
        file = io.BytesIO(content)
        
        md5 = FileStorageService.calculate_md5(file)
        
        # Hello, World! 的 MD5
        assert md5 == "65a8e27d8879283831b664bd8b7f0ad4"

    def test_get_bucket(self):
        """测试存储桶名称"""
        storage = FileStorageService("/tmp/test_storage")
        
        md5 = "65a8e27d8879283831b664bd8b7f0ad4"
        bucket = storage.get_bucket(md5)
        
        assert bucket == "65"

    def test_get_file_type(self):
        """测试文件类型识别"""
        assert FileStorageService.get_file_type("doc.pdf") == "pdf"
        assert FileStorageService.get_file_type("doc.docx") == "word"
        assert FileStorageService.get_file_type("data.xlsx") == "excel"
        assert FileStorageService.get_file_type("pres.pptx") == "powerpoint"
        assert FileStorageService.get_file_type("image.png") == "image"
        assert FileStorageService.get_file_type("unknown.xyz") == "other"

    def test_validate_extension(self):
        """测试扩展名验证"""
        storage = FileStorageService("/tmp/test_storage")
        
        assert storage.validate_extension("doc.pdf") is True
        assert storage.validate_extension("doc.docx") is True
        assert storage.validate_extension("doc.exe") is False
        assert storage.validate_extension("doc.sh") is False


@pytest.mark.asyncio
async def test_upload_without_auth(async_client: AsyncClient):
    """测试未认证上传"""
    response = await async_client.post(
        "/api/v1/files/upload",
        files={"file": ("test.txt", b"content", "text/plain")}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_without_auth(async_client: AsyncClient):
    """测试未认证获取列表"""
    response = await async_client.get("/api/v1/files/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_without_auth(async_client: AsyncClient):
    """测试未认证下载"""
    response = await async_client.get("/api/v1/files/1/download")
    assert response.status_code == 401
