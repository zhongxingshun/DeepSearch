"""
DeepSearch 数据库连接模块
版本: v1.0
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from app.config import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明式基类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话依赖

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema_compatibility() -> None:
    """补齐运行所需的兼容字段，避免旧初始化脚本造成运行失败。"""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                ALTER TABLE tasks
                ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE tasks
                SET retry_count = 0
                WHERE retry_count IS NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE tasks
                ALTER COLUMN retry_count SET DEFAULT 0
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE files
                ADD COLUMN IF NOT EXISTS source_url VARCHAR(2000)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS file_share_links (
                    id SERIAL PRIMARY KEY,
                    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    created_by INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
                    code VARCHAR(32) NOT NULL UNIQUE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    max_downloads INTEGER NULL,
                    download_count INTEGER NOT NULL DEFAULT 0,
                    expires_at TIMESTAMP NULL,
                    last_accessed_at TIMESTAMP NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_file_share_links_file
                ON file_share_links (file_id, created_by, is_active)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_file_share_links_code
                ON file_share_links (code)
                """
            )
        )


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
