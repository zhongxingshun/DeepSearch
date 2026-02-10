"""
文件管理 API 路由
版本: v1.0
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user, get_client_ip, require_admin
from app.models.user import User
from app.schemas.file import (
    FileResponse as FileResponseSchema,
    FileListResponse,
    FileStatusResponse,
    FileUploadResponse,
    FileMoveRequest,
    FolderInfo,
    FolderListResponse,
)
from app.schemas.common import ResponseBase, PaginationMeta
from app.services.file_service import FileService
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_path: Optional[str] = Form(None, description="目标文件夹路径"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传单个文件
    
    - 支持格式: PDF, Word, Excel, PPT, TXT, 图片等
    - 最大文件大小: 500MB
    - 自动去重: 相同 MD5 的文件不会重复存储
    - folder_path: 可指定目标文件夹
    """
    file_service = FileService(db)
    audit_service = AuditService(db)
    ip_address = get_client_ip(request)
    
    try:
        db_file, is_duplicate, task_id = await file_service.upload_file(
            file=file,
            user_id=current_user.id,
            target_folder=folder_path,
        )
        
        # 记录上传审计日志
        await audit_service.log_file_upload(
            user_id=current_user.id,
            file_id=db_file.id,
            filename=db_file.filename,
            file_size=db_file.file_size,
            ip_address=ip_address,
        )
        await db.commit()
        
        return FileUploadResponse(
            success=True,
            message="文件上传成功" if not is_duplicate else "文件已存在",
            file_id=db_file.id,
            filename=db_file.filename,
            md5_hash=db_file.md5_hash or "",
            is_duplicate=is_duplicate,
            task_id=task_id,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/upload/batch")
async def upload_files_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    批量上传文件
    
    - 最多同时上传 10 个文件
    - 返回每个文件的上传结果
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次最多上传 10 个文件",
        )
    
    file_service = FileService(db)
    results = await file_service.upload_files(files, current_user.id)
    
    success_count = sum(1 for r in results if r.get("success"))
    
    return {
        "success": True,
        "message": f"上传完成: {success_count}/{len(files)} 个文件成功",
        "results": results,
    }


@router.post("/retry-all-failed", response_model=ResponseBase)
async def retry_all_failed(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    重试所有未完成的文件（仅管理员）
    
    - 批量重置所有 failed/parsed/pending 状态的文件
    - 重新派发解析任务
    """
    from sqlalchemy import select
    from app.models.file import File as FileModel
    
    result = await db.execute(
        select(FileModel).where(
            FileModel.index_status.in_(["failed", "parsed", "pending"])
        )
    )
    retry_files = result.scalars().all()
    
    if not retry_files:
        return ResponseBase(
            success=True,
            message="没有需要重试的文件",
        )
    
    retry_count = 0
    for f in retry_files:
        f.index_status = "pending"
        try:
            from app.tasks.parse_task import parse_document
            parse_document.delay(
                file_id=f.id,
                file_path=f.file_path,
                file_type=f.file_type,
            )
            retry_count += 1
        except Exception:
            pass
    
    await db.commit()
    
    return ResponseBase(
        success=True,
        message=f"已重新提交 {retry_count}/{len(retry_files)} 个文件的解析任务",
    )


@router.get("", response_model=FileListResponse)
@router.get("/", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    file_type: Optional[str] = Query(None, description="文件类型过滤"),
    status: Optional[str] = Query(None, description="索引状态过滤"),
    keyword: Optional[str] = Query(None, description="文件名关键词"),
    folder: Optional[str] = Query(None, description="文件夹路径过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取文件列表
    
    - 支持分页和过滤
    - file_type: pdf, word, excel, powerpoint, text, image, other
    - status: pending, processing, completed, failed
    """
    file_service = FileService(db)
    
    files, total = await file_service.get_files(
        page=page,
        page_size=page_size,
        file_type=file_type,
        status=status,
        keyword=keyword,
        folder_path=folder,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return FileListResponse(
        success=True,
        data=[
            FileResponseSchema(
                id=f.id,
                filename=f.filename,
                file_path=f.file_path,
                folder_path=f.folder_path,
                display_name=f.display_name,
                uploaded_by=f.uploaded_by,
                file_size=f.file_size,
                file_size_human=f.file_size_human,
                file_type=f.file_type,
                md5_hash=f.md5_hash,
                index_status=f.index_status,
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
            for f in files
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/folders/tree", response_model=FolderListResponse)
async def list_folders(
    parent: Optional[str] = Query(None, description="父文件夹路径"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取文件夹树
    
    - 指定 parent 参数时返回子文件夹
    - 不指定时返回所有文件夹
    """
    file_service = FileService(db)
    
    if parent:
        folders = await file_service.get_subfolders(parent)
    else:
        folders = await file_service.get_folders()
    
    return FolderListResponse(
        folders=[FolderInfo(**f) for f in folders],
        current_path=parent or "/",
    )


@router.get("/{file_id}", response_model=FileResponseSchema)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个文件详情"""
    file_service = FileService(db)
    file = await file_service.get_file_by_id(file_id)
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    
    return FileResponseSchema(
        id=file.id,
        filename=file.filename,
        file_path=file.file_path,
        uploaded_by=file.uploaded_by,
        file_size=file.file_size,
        file_size_human=file.file_size_human,
        file_type=file.file_type,
        md5_hash=file.md5_hash,
        index_status=file.index_status,
        created_at=file.created_at,
        updated_at=file.updated_at,
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    下载文件
    
    - 记录下载审计日志
    """
    file_service = FileService(db)
    audit_service = AuditService(db)
    ip_address = get_client_ip(request)
    
    # 获取文件信息
    file = await file_service.get_file_by_id(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    
    # 获取文件路径
    file_path = await file_service.get_file_path(file_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件存储不存在",
        )
    
    # 记录下载审计日志
    await audit_service.log_file_download(
        user_id=current_user.id,
        file_id=file_id,
        filename=file.filename,
        ip_address=ip_address,
    )
    await db.commit()
    
    return FileResponse(
        path=file_path,
        filename=file.filename,
        media_type="application/octet-stream",
    )


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    预览文件（内联显示）
    
    - 图片文件直接返回图片内容（浏览器内嵌显示）
    - PDF 文件以 inline 方式返回
    - 其他文件返回下载
    """
    import mimetypes
    
    file_service = FileService(db)
    
    file = await file_service.get_file_by_id(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    
    file_path = await file_service.get_file_path(file_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件存储不存在",
        )
    
    # 确定 MIME 类型
    mime_map = {
        'image': {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'bmp': 'image/bmp', 'webp': 'image/webp',
            'svg': 'image/svg+xml',
        },
        'pdf': {'pdf': 'application/pdf'},
    }
    
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    media_type = None
    
    # 图片
    if file.file_type == 'image' and ext in mime_map['image']:
        media_type = mime_map['image'][ext]
    # PDF
    elif file.file_type == 'pdf':
        media_type = 'application/pdf'
    else:
        media_type = mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
    
    from starlette.responses import Response
    from urllib.parse import quote
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # URL 编码文件名，支持中文
    encoded_filename = quote(file.filename)
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/{file_id}/status", response_model=FileStatusResponse)
async def get_file_status(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文件索引状态"""
    file_service = FileService(db)
    status_info = await file_service.get_file_status(file_id)
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    
    return FileStatusResponse(
        id=status_info["id"],
        filename=status_info["filename"],
        index_status=status_info["index_status"],
        error_message=status_info.get("task_error"),
        updated_at=status_info["updated_at"],
    )


@router.delete("/{file_id}", response_model=ResponseBase)
async def delete_file(
    file_id: int,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    删除文件（仅管理员）
    
    - 同时删除存储文件和数据库记录
    """
    file_service = FileService(db)
    
    success = await file_service.delete_file(file_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    
    return ResponseBase(message="文件删除成功")


@router.get("/stats/overview")
async def get_file_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文件统计概览"""
    file_service = FileService(db)
    stats = await file_service.get_stats()
    
    return {
        "success": True,
        "data": stats,
    }


@router.post("/{file_id}/retry", response_model=ResponseBase)
async def retry_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    重试解析失败的文件
    
    - 重置文件状态为 pending
    - 重新派发 Celery 解析任务
    """
    from sqlalchemy import text
    
    file_service = FileService(db)
    file = await file_service.get_file_by_id(file_id)
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    
    if file.index_status not in ("failed", "parsed", "completed", "pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态 '{file.index_status}' 不支持重试",
        )
    
    # 重置文件状态
    file.index_status = "pending"
    await db.commit()
    
    # 重新派发解析任务
    try:
        from app.tasks.parse_task import parse_document
        celery_result = parse_document.delay(
            file_id=file.id,
            file_path=file.file_path,
            file_type=file.file_type,
        )
        return ResponseBase(
            success=True,
            message=f"已重新提交解析任务: {celery_result.id}",
        )
    except Exception as e:
        return ResponseBase(
            success=False,
            message=f"任务提交失败: {str(e)}",
        )



@router.put("/{file_id}/move", response_model=ResponseBase)
async def move_file(
    file_id: int,
    body: FileMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    移动文件到指定文件夹
    
    - 仅修改数据库记录，不影响物理存储和搜索索引
    """
    file_service = FileService(db)
    
    try:
        file = await file_service.move_file(file_id, body.target_folder)
        return ResponseBase(
            success=True,
            message=f"文件已移动到 {body.target_folder}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
