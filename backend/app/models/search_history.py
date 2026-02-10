"""
搜索历史数据模型
版本: v1.0
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SearchHistory(Base):
    """搜索历史表"""

    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )

    # 关系
    user = relationship("User", back_populates="search_histories")

    def __repr__(self) -> str:
        return f"<SearchHistory(id={self.id}, keyword='{self.keyword[:20]}...', results={self.result_count})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "keyword": self.keyword,
            "result_count": self.result_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
