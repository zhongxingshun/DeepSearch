"""
文件分享短链 API 路由
版本: v1.0
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_client_ip
from app.services.audit_service import AuditService
from app.services.file_service import FileService
from app.services.share_link_service import ShareLinkService

router = APIRouter()


@router.get("/s/{code}", name="download_shared_file")
async def download_shared_file(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """通过短链直接下载文件。"""
    share_service = ShareLinkService(db)
    file_service = FileService(db)
    audit_service = AuditService(db)
    ip_address = get_client_ip(request)

    share_link = await share_service.get_share_link_by_code(code)
    if share_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享链接不存在或已失效",
        )

    file = await file_service.get_file_by_id(share_link.file_id)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )

    file_path = await file_service.get_file_path(share_link.file_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件存储不存在",
        )

    await share_service.record_download(share_link)
    await audit_service.log_file_download(
        user_id=None,
        file_id=file.id,
        filename=file.filename,
        ip_address=ip_address,
        details={
            "via_share_link": True,
            "share_code": share_link.code,
            "share_link_id": share_link.id,
        },
    )
    await db.commit()

    return FileResponse(
        path=file_path,
        filename=file.filename,
        media_type="application/octet-stream",
    )
