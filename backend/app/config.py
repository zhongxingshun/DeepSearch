"""
DeepSearch 配置管理模块
版本: v1.0
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================
    # 应用配置
    # ============================================
    app_env: str = Field(default="development", description="运行环境")
    app_debug: bool = Field(default=False, description="调试模式")
    app_secret_key: str = Field(
        default="your-super-secret-key-change-this",
        description="应用密钥"
    )
    app_name: str = Field(default="DeepSearch", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")

    # ============================================
    # 数据库配置
    # ============================================
    db_host: str = Field(default="localhost", description="数据库主机")
    db_port: int = Field(default=5432, description="数据库端口")
    db_name: str = Field(default="deepsearch", description="数据库名称")
    db_user: str = Field(default="deepsearch", description="数据库用户")
    db_password: str = Field(default="deepsearch123", description="数据库密码")
    db_pool_size: int = Field(default=10, description="连接池大小")
    db_max_overflow: int = Field(default=20, description="最大溢出连接数")

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL"""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """获取同步数据库连接 URL (用于 Alembic)"""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ============================================
    # Redis 配置
    # ============================================
    redis_host: str = Field(default="localhost", description="Redis 主机")
    redis_port: int = Field(default=6379, description="Redis 端口")
    redis_db: int = Field(default=0, description="Redis 数据库")
    redis_password: Optional[str] = Field(default=None, description="Redis 密码")

    @property
    def redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ============================================
    # Meilisearch 配置
    # ============================================
    meili_host: str = Field(default="localhost", description="Meilisearch 主机")
    meili_port: int = Field(default=7700, description="Meilisearch 端口")
    meili_master_key: str = Field(
        default="deepsearch_meili_key",
        description="Meilisearch 主密钥"
    )

    @property
    def meili_url(self) -> str:
        """获取 Meilisearch URL"""
        return f"http://{self.meili_host}:{self.meili_port}"

    # ============================================
    # JWT 配置
    # ============================================
    jwt_secret_key: str = Field(
        default="your-jwt-secret-key-change-this",
        description="JWT 密钥"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    jwt_expire_hours: int = Field(default=24, description="JWT 过期时间(小时)")
    jwt_refresh_expire_days: int = Field(default=7, description="刷新令牌过期时间(天)")

    # ============================================
    # 文件存储配置
    # ============================================
    file_storage_path: str = Field(
        default="/data/files",
        description="文件存储路径"
    )
    backup_storage_path: str = Field(
        default="/data/backups",
        description="备份存储路径"
    )
    max_upload_size: int = Field(
        default=524288000,  # 500MB
        description="最大上传大小(字节)"
    )
    allowed_extensions: list[str] = Field(
        default=[
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "txt", "md", "csv", "rtf",
            "jpg", "jpeg", "png", "gif", "bmp", "tiff",
            "zip", "rar"
        ],
        description="允许的文件扩展名"
    )

    # ============================================
    # Celery 配置
    # ============================================
    celery_broker_url: Optional[str] = Field(default=None, description="Celery Broker URL")
    celery_result_backend: Optional[str] = Field(default=None, description="Celery 结果后端")

    @property
    def celery_broker(self) -> str:
        """获取 Celery Broker URL"""
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        """获取 Celery 结果后端 URL"""
        return self.celery_result_backend or self.redis_url

    # ============================================
    # 安全配置
    # ============================================
    password_min_length: int = Field(default=8, description="密码最小长度")
    max_login_attempts: int = Field(default=5, description="最大登录失败次数")
    lockout_duration_minutes: int = Field(default=30, description="锁定时长(分钟)")

    # ============================================
    # 限流配置
    # ============================================
    rate_limit_requests: int = Field(default=100, description="限流请求数")
    rate_limit_window: int = Field(default=60, description="限流时间窗口(秒)")

    # ============================================
    # 日志配置
    # ============================================
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式")

    # ============================================
    # 备份配置
    # ============================================
    backup_retention_days: int = Field(default=7, description="备份保留天数")
    meili_backup_retention_days: int = Field(default=3, description="Meilisearch 备份保留天数")
    audit_log_retention_days: int = Field(default=180, description="审计日志保留天数")
    search_history_retention_days: int = Field(default=90, description="搜索历史保留天数")
    file_share_link_expire_hours: int = Field(default=24, description="文件分享短链默认有效期（小时）")
    file_share_link_code_length: int = Field(default=10, description="文件分享短码长度")
    public_base_url: Optional[str] = Field(default=None, description="公开访问基地址，用于生成可分享链接")


@lru_cache
def get_settings() -> Settings:
    """获取配置实例（缓存）"""
    return Settings()


# 全局配置实例
settings = get_settings()
