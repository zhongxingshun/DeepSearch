"""
DeepSearch FastAPI 应用入口
版本: v1.0
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import close_db, ensure_schema_compatibility, init_db
from app.api import auth, search, files, history, admin, health
from app.services.meilisearch_client import meili_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"Starting {settings.app_name} v{settings.app_version}")
    await ensure_schema_compatibility()
    await meili_client.init_index()
    # 初始化数据库连接
    # await init_db()  # 使用 Alembic 管理迁移
    yield
    # 关闭时
    print(f"Shutting down {settings.app_name}")
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title="DeepSearch API",
    description="企业级全格式深度搜索系统 API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api/v1/health", tags=["健康检查"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(search.router, prefix="/api/v1/search", tags=["搜索"])
app.include_router(files.router, prefix="/api/v1/files", tags=["文件"])
app.include_router(history.router, prefix="/api/v1/history", tags=["搜索历史"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理"])


@app.get("/", include_in_schema=False)
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug,
    )
