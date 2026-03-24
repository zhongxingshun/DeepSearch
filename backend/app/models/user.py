"""
用户数据模型
版本: v1.0
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, default=""
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user"
    )  # admin, user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    files = relationship("File", back_populates="uploader", lazy="dynamic")
    search_histories = relationship(
        "SearchHistory", back_populates="user", lazy="dynamic"
    )
    audit_logs = relationship("AuditLog", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role in {"admin", "super_admin"}

    @property
    def is_super_admin(self) -> bool:
        """是否为超级管理员"""
        return self.role == "super_admin"

    @property
    def is_locked(self) -> bool:
        """账号是否被锁定"""
        if self.locked_until is None:
            return False
        return self.get_lock_remaining_seconds() > 0

    def get_lock_remaining_seconds(self) -> float:
        """返回账号剩余锁定秒数，兼容有无时区信息的时间字段。"""
        if self.locked_until is None:
            return 0

        locked_until = self.locked_until
        if locked_until.tzinfo is not None:
            now = datetime.now(timezone.utc)
            locked_until = locked_until.astimezone(timezone.utc)
        else:
            now = datetime.utcnow()

        return max((locked_until - now).total_seconds(), 0)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
