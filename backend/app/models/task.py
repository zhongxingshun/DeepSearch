"""
任务数据模型
版本: v1.0
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Task(Base):
    """任务表"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("files.id"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # parse, index, scan, backup, cleanup
    priority: Mapped[str] = mapped_column(
        String(10), default="low", index=True
    )  # high, low
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, running, completed, failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    file = relationship("File", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type='{self.task_type}', status='{self.status}')>"

    @property
    def duration(self) -> Optional[float]:
        """获取任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_retriable(self) -> bool:
        """是否可以重试"""
        return self.status == "failed" and self.retry_count < 3

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "file_id": self.file_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "status": self.status,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "celery_task_id": self.celery_task_id,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
