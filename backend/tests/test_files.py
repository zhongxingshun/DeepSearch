"""
文件管理 API 测试
版本: v1.0
"""

import io
from pathlib import Path
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.dependencies import get_current_user
from app.main import app
from app.models.file import File
from app.models.user import User
from app.services.file_storage_service import FileStorageService
from app.core.access_control import (
    can_access_file_scope,
    visible_file_scopes_for_role,
)


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


def test_external_customer_only_has_public_visibility_scope():
    """测试外部客户只能检索/查看全员可见文件。"""
    assert visible_file_scopes_for_role("external_customer") == ["public"]


def test_internal_employee_visibility_scopes_exclude_marketing():
    """测试内部员工可见全员/内部文件，但不含仅营销文件。"""
    assert visible_file_scopes_for_role("internal_employee") == ["public", "internal"]


def test_admin_visibility_scopes_include_marketing():
    """测试管理员可见全部开放范围。"""
    assert visible_file_scopes_for_role("admin") == ["public", "internal", "marketing"]


def test_legacy_user_role_is_treated_as_internal_employee():
    """测试历史 user 角色按内部员工兼容。"""
    user = User(username="legacy", email="legacy@example.com", password_hash="hash", role="user")

    assert can_access_file_scope(user, "internal") is True
    assert can_access_file_scope(user, "marketing") is False


@pytest.mark.asyncio
async def test_upload_without_auth(async_client: AsyncClient):
    """测试未认证上传"""
    response = await async_client.post(
        "/api/v1/files/upload",
        files={"file": ("test.txt", b"content", "text/plain")}
    )
    assert response.status_code == 401


@pytest_asyncio.fixture
async def normal_user_auth_context():
    """创建普通用户登录上下文。"""

    user = User(
        username="normal_upload_user",
        email="normal-upload@example.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    token = create_access_token(
        {"sub": "1", "username": user.username, "role": user.role}
    )

    yield {"token": token}

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_normal_user_cannot_upload_file(
    async_client: AsyncClient,
    normal_user_auth_context,
):
    """测试普通用户不能上传单个文件。"""
    response = await async_client.post(
        "/api/v1/files/upload",
        files={"file": ("test.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {normal_user_auth_context['token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_normal_user_cannot_batch_upload_files(
    async_client: AsyncClient,
    normal_user_auth_context,
):
    """测试普通用户不能批量上传文件。"""
    response = await async_client.post(
        "/api/v1/files/upload/batch",
        files=[("files", ("test.txt", b"content", "text/plain"))],
        headers={"Authorization": f"Bearer {normal_user_auth_context['token']}"},
    )
    assert response.status_code == 403


@pytest_asyncio.fixture
async def admin_auth_context():
    """创建管理员登录上下文。"""

    user = User(
        username="upload_admin",
        email="upload-admin@example.com",
        password_hash="hash",
        role="admin",
        is_active=True,
    )

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    token = create_access_token(
        {"sub": "2", "username": user.username, "role": user.role}
    )

    yield {"token": token}

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_upload_requires_visibility_scope(
    async_client: AsyncClient,
    admin_auth_context,
):
    """测试管理员上传时必须选择文件开放范围。"""
    response = await async_client.post(
        "/api/v1/files/upload",
        files={"file": ("test.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {admin_auth_context['token']}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "文件开放范围为必选项"


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


@pytest_asyncio.fixture
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
