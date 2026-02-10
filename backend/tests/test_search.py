"""
搜索 API 测试
版本: v1.0
"""

import pytest
from httpx import AsyncClient


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
