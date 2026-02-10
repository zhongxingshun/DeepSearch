"""
Celery 任务共享的同步数据库引擎
使用 NullPool 避免连接池泄漏（每次连接用完即关闭）
"""
from sqlalchemy import create_engine
from app.config import settings

# 使用 NullPool 确保连接用完即释放，不会因连接池持有导致 too many clients
sync_engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    pool_size=0,          # NullPool equivalent via StaticPool workaround
    max_overflow=5,       # 最多只允许5个并发连接
    pool_recycle=300,     # 5分钟回收
    pool_timeout=10,      # 10秒超时
)
