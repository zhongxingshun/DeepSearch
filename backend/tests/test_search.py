"""
搜索 API 测试
版本: v1.0
"""

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_search_without_auth(async_client: AsyncClient):
    """测试未认证搜索"""
    response = await async_client.get("/api/v1/search?q=test")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query(async_client: AsyncClient):
    """测试空搜索词（无法测试，因为需要认证）"""
    # 此测试需要先登录获取 token
    pass


@pytest.mark.asyncio
async def test_history_without_auth(async_client: AsyncClient):
    """测试未认证访问历史"""
    response = await async_client.get("/api/v1/history/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_history_without_auth(async_client: AsyncClient):
    """测试未认证删除历史"""
    response = await async_client.delete("/api/v1/history/1")
    assert response.status_code == 401


class TestMeilisearchClient:
    """Meilisearch 客户端测试"""

    def test_index_name(self):
        """测试索引名称"""
        from app.services.meilisearch_client import MeilisearchClient
        
        client = MeilisearchClient()
        assert client.INDEX_NAME == "documents"

    def test_searchable_attributes(self):
        """测试可搜索字段"""
        from app.services.meilisearch_client import MeilisearchClient
        
        assert "content" in MeilisearchClient.SEARCHABLE_ATTRIBUTES
        assert "filename" in MeilisearchClient.SEARCHABLE_ATTRIBUTES

    def test_filterable_attributes(self):
        """测试可过滤字段"""
        from app.services.meilisearch_client import MeilisearchClient
        
        assert "file_type" in MeilisearchClient.FILTERABLE_ATTRIBUTES
        assert "file_id" in MeilisearchClient.FILTERABLE_ATTRIBUTES
        assert "visibility_scope" in MeilisearchClient.FILTERABLE_ATTRIBUTES


class FakeMeiliClient:
    def __init__(self):
        self.filters = None

    async def search(self, **kwargs):
        self.filters = kwargs.get("filters")
        return {"hits": [], "total": 0}


@pytest.mark.asyncio
async def test_search_filters_visibility_for_external_customer():
    """测试外部客户搜索只带全员可见过滤。"""
    fake_meili = FakeMeiliClient()
    service = SearchService(db=None, meili=fake_meili)
    user = User(username="external", email="external@example.com", password_hash="hash", role="external_customer")

    await service.search("test", user_id=1, current_user=user, record_history=False)

    assert fake_meili.filters == "visibility_scope IN ['public']"


@pytest.mark.asyncio
async def test_search_filters_visibility_for_internal_employee():
    """测试内部员工搜索可见全员和内部范围。"""
    fake_meili = FakeMeiliClient()
    service = SearchService(db=None, meili=fake_meili)
    user = User(username="internal", email="internal@example.com", password_hash="hash", role="internal_employee")

    await service.search("test", user_id=1, current_user=user, file_type="pdf", record_history=False)

    assert fake_meili.filters == "file_type = 'pdf' AND visibility_scope IN ['public', 'internal']"
