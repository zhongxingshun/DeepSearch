"""
健康检查 API
版本: v1.0
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.config import settings
from app.core.database import get_db

router = APIRouter()


async def check_database(db: AsyncSession) -> dict[str, Any]:
    """检查数据库连接"""
    try:
        start = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> dict[str, Any]:
    """检查 Redis 连接"""
    try:
        start = datetime.utcnow()
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_meilisearch() -> dict[str, Any]:
    """检查 Meilisearch 连接"""
    try:
        import httpx
        
        start = datetime.utcnow()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.meili_url}/health",
                timeout=5.0
            )
            response.raise_for_status()
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("")
@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    系统健康状态检查
    
    返回所有组件的健康状态
    """
    database_status = await check_database(db)
    redis_status = await check_redis()
    meilisearch_status = await check_meilisearch()
    
    components = {
        "database": database_status,
        "redis": redis_status,
        "meilisearch": meilisearch_status,
    }
    
    # 判断整体状态
    all_healthy = all(
        c["status"] == "healthy" for c in components.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.app_version,
        "components": components,
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    服务就绪状态检查
    
    用于 Kubernetes 就绪探针
    """
    database_status = await check_database(db)
    
    if database_status["status"] != "healthy":
        return {"status": "not_ready", "reason": "database unavailable"}
    
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    服务存活状态检查
    
    用于 Kubernetes 存活探针
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}
