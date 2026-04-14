"""
文件数据模型
版本: v1.0
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class File(Base):
    """文件表"""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    folder_path: Mapped[str] = mapped_column(
        String(1000), default="/", nullable=False, index=True
    )  # 虚拟文件夹路径，如 "/素材/封面"
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    md5_hash: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, index=True
    )
    index_status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, processing, completed, failed
    meilisearch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    uploader = relationship("User", back_populates="files")
    tasks = relationship("Task", back_populates="file", lazy="dynamic")
    share_links = relationship(
        "FileShareLink",
        back_populates="file",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename='{self.filename}', status='{self.index_status}')>"

    @property
    def extension(self) -> str:
        """获取文件扩展名"""
        if "." in self.filename:
            return self.filename.rsplit(".", 1)[1].lower()
        return ""

    @property
    def storage_bucket(self) -> str:
        """获取存储桶名称（MD5 前两位）"""
        if self.md5_hash:
            return self.md5_hash[:2]
        return "00"

    @property
    def file_size_human(self) -> str:
        """获取人类可读的文件大小"""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def display_name(self) -> str:
        """获取不含路径的纯文件名"""
        if "/" in self.filename:
            return self.filename.rsplit("/", 1)[1]
        return self.filename

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_path": self.file_path,
            "folder_path": self.folder_path,
            "uploaded_by": self.uploaded_by,
            "file_size": self.file_size,
            "file_size_human": self.file_size_human,
            "file_type": self.file_type,
            "source_url": self.source_url,
            "md5_hash": self.md5_hash,
            "index_status": self.index_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
