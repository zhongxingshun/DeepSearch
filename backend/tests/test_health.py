"""
健康检查 API 测试
版本: v1.0
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_check(async_client: AsyncClient):
    """测试存活检查"""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """测试根路径"""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
