"""
文件分享短链服务
版本: v1.0
"""

from datetime import datetime, timedelta
import secrets
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.file_share_link import FileShareLink


class ShareLinkService:
    """文件分享短链服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_share_link(
        self,
        file_id: int,
        created_by: Optional[int] = None,
    ) -> Optional[FileShareLink]:
        """获取当前可用的短链。"""
        query = select(FileShareLink).where(
            FileShareLink.file_id == file_id,
            FileShareLink.is_active.is_(True),
            or_(FileShareLink.expires_at.is_(None), FileShareLink.expires_at > datetime.utcnow()),
        )
        if created_by is not None:
            query = query.where(FileShareLink.created_by == created_by)

        query = query.order_by(FileShareLink.created_at.desc()).limit(1)
        result = await self.db.execute(query)
        link = result.scalar_one_or_none()
        if link and link.is_download_limit_reached:
            link.is_active = False
            await self.db.flush()
            return None
        return link

    async def create_or_get_share_link(
        self,
        file_id: int,
        created_by: Optional[int],
        expires_in_hours: Optional[int] = None,
        max_downloads: Optional[int] = None,
        force_new: bool = False,
    ) -> FileShareLink:
        """获取可用短链，不存在时自动创建。"""
        if not force_new:
            existing = await self.get_active_share_link(file_id=file_id, created_by=created_by)
            if existing and existing.max_downloads == max_downloads:
                return existing

        expires_at = datetime.utcnow() + timedelta(
            hours=expires_in_hours or settings.file_share_link_expire_hours
        )

        if force_new:
            await self.deactivate_active_links(file_id=file_id, created_by=created_by)

        link = FileShareLink(
            file_id=file_id,
            created_by=created_by,
            code=await self._generate_unique_code(),
            expires_at=expires_at,
            max_downloads=max_downloads,
        )
        self.db.add(link)
        await self.db.flush()
        return link

    async def deactivate_active_links(
        self,
        file_id: int,
        created_by: Optional[int],
    ) -> None:
        """停用某个文件当前用户的有效短链。"""
        query = select(FileShareLink).where(
            FileShareLink.file_id == file_id,
            FileShareLink.is_active.is_(True),
        )
        if created_by is not None:
            query = query.where(FileShareLink.created_by == created_by)

        result = await self.db.execute(query)
        for link in result.scalars().all():
            link.is_active = False

        await self.db.flush()

    async def revoke_share_link(
        self,
        share_id: int,
        file_id: int,
        created_by: Optional[int],
    ) -> Optional[FileShareLink]:
        """手动失效一个短链。"""
        query = select(FileShareLink).where(
            FileShareLink.id == share_id,
            FileShareLink.file_id == file_id,
        )
        if created_by is not None:
            query = query.where(FileShareLink.created_by == created_by)

        result = await self.db.execute(query)
        link = result.scalar_one_or_none()
        if link is None:
            return None

        link.is_active = False
        await self.db.flush()
        return link

    async def get_share_link_by_code(self, code: str) -> Optional[FileShareLink]:
        """按短码获取短链。"""
        result = await self.db.execute(
            select(FileShareLink).where(FileShareLink.code == code).limit(1)
        )
        link = result.scalar_one_or_none()
        if link is None:
            return None

        if not link.is_active or link.is_expired or link.is_download_limit_reached:
            link.is_active = False
            await self.db.flush()
            return None

        return link

    async def record_download(self, link: FileShareLink) -> FileShareLink:
        """记录短链下载。"""
        link.download_count += 1
        link.last_accessed_at = datetime.utcnow()
        if link.max_downloads is not None and link.download_count >= link.max_downloads:
            link.is_active = False
        await self.db.flush()
        return link

    async def _generate_unique_code(self) -> str:
        """生成唯一短码。"""
        for _ in range(10):
            code = secrets.token_urlsafe(8)[: settings.file_share_link_code_length]
            result = await self.db.execute(
                select(FileShareLink.id).where(FileShareLink.code == code).limit(1)
            )
            if result.scalar_one_or_none() is None:
                return code

        raise ValueError("短链接生成失败，请重试")
