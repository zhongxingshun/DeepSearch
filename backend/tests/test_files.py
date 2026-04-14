"""
文件管理 API 测试
版本: v1.0
"""

import io
from pathlib import Path
from urllib.parse import urlparse

import pytest
from httpx import AsyncClient

from app.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.file import File
from app.models.user import User
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


@pytest.fixture
async def share_test_context(db_session, tmp_path):
    """创建分享短链测试所需的用户、文件和依赖覆盖。"""
    original_storage_path = settings.file_storage_path
    settings.file_storage_path = str(tmp_path)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    user = User(
        username="share_user",
        email="share@example.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    relative_path = "ab/share-test.txt"
    full_path = Path(tmp_path) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    content = b"shared file content"
    full_path.write_bytes(content)

    file = File(
        filename="share-test.txt",
        file_path=relative_path,
        folder_path="/",
        uploaded_by=user.id,
        file_size=len(content),
        file_type="text",
        md5_hash="a" * 32,
        index_status="completed",
    )
    db_session.add(file)
    await db_session.commit()

    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "role": user.role}
    )

    yield {
        "token": token,
        "file_id": file.id,
        "content": content,
    }

    app.dependency_overrides.clear()
    settings.file_storage_path = original_storage_path


@pytest.mark.asyncio
async def test_get_share_link_with_auth(async_client: AsyncClient, share_test_context):
    """测试登录后可直接获取文件分享短链接。"""
    response = await async_client.get(
        f"/api/v1/files/{share_test_context['file_id']}/share-link",
        params={"ensure": True},
        headers={"Authorization": f"Bearer {share_test_context['token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["file_id"] == share_test_context["file_id"]
    assert body["data"]["short_url"].endswith(f"/s/{body['data']['code']}")


@pytest.mark.asyncio
async def test_shared_link_download_without_auth(
    async_client: AsyncClient,
    share_test_context,
):
    """测试匿名用户可通过分享短链接直接下载。"""
    create_response = await async_client.get(
        f"/api/v1/files/{share_test_context['file_id']}/share-link",
        params={"ensure": True},
        headers={"Authorization": f"Bearer {share_test_context['token']}"},
    )
    share_url = create_response.json()["data"]["short_url"]
    share_path = urlparse(share_url).path

    download_response = await async_client.get(share_path)

    assert download_response.status_code == 200
    assert download_response.content == share_test_context["content"]
