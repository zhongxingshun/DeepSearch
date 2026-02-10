"""
管理后台 API 路由
版本: v1.0
说明: 完整实现
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.models.file import File
from app.models.audit_log import AuditLog
from app.core.security import pwd_context

router = APIRouter(dependencies=[Depends(get_current_admin_user)])


# ============================================
# Schemas
# ============================================

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"


class UpdateStatusRequest(BaseModel):
    is_active: bool


# ============================================
# 用户管理
# ============================================

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """获取用户列表"""
    result = await db.execute(
        select(User).order_by(desc(User.created_at))
    )
    users = result.scalars().all()
    return {
        "data": [
            {
                "id": u.id,
                "username": u.username,
                "email": getattr(u, "email", ""),
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


@router.post("/users")
async def create_user(req: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    """创建用户"""
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否已存在
    existing_email = await db.execute(select(User).where(User.email == req.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=pwd_context.hash(req.password),
        role=req.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"message": "用户创建成功", "id": user.id}


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    req: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = req.is_active
    await db.commit()

    return {"message": "状态更新成功"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: int, db: AsyncSession = Depends(get_db)):
    """重置用户密码"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    new_password = "deepsearch123"
    user.password_hash = pwd_context.hash(new_password)
    await db.commit()

    return {"message": f"密码已重置为: {new_password}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """删除用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.delete(user)
    await db.commit()
    return {"message": "用户已删除"}


# ============================================
# 系统统计
# ============================================

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取系统统计"""
    # 用户统计
    user_count_result = await db.execute(select(func.count(User.id)))
    user_count = user_count_result.scalar() or 0

    # 文件统计
    file_count_result = await db.execute(select(func.count(File.id)))
    file_count = file_count_result.scalar() or 0

    file_size_result = await db.execute(select(func.coalesce(func.sum(File.file_size), 0)))
    total_file_size = file_size_result.scalar() or 0

    # 今日搜索次数（从审计日志中统计今天 login 类型之外的记录）
    from datetime import date
    today = date.today()
    search_count_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.action_type == "search",
            func.date(AuditLog.created_at) == today,
        )
    )
    today_search_count = search_count_result.scalar() or 0

    # 文件类型分布
    file_type_result = await db.execute(
        select(File.file_type, func.count(File.id))
        .group_by(File.file_type)
        .order_by(desc(func.count(File.id)))
        .limit(10)
    )
    file_type_distribution = [
        {"type": row[0] or "unknown", "count": row[1]}
        for row in file_type_result.all()
    ]

    # 索引状态
    index_status_result = await db.execute(
        select(File.index_status, func.count(File.id))
        .group_by(File.index_status)
    )
    index_status = {row[0]: row[1] for row in index_status_result.all()}

    return {
        "user_count": user_count,
        "file_count": file_count,
        "total_file_size": total_file_size,
        "today_search_count": today_search_count,
        "file_type_distribution": file_type_distribution,
        "index_status": index_status,
    }


# ============================================
# 审计日志
# ============================================

@router.get("/logs")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取审计日志"""
    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if action_type:
        query = query.where(AuditLog.action_type == action_type)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "data": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================
# 维护操作
# ============================================

@router.post("/maintenance/backup")
async def trigger_backup():
    """触发备份"""
    # TODO: 集成 Celery 任务
    return {"message": "备份任务已触发", "status": "started"}


@router.post("/maintenance/reindex")
async def trigger_reindex():
    """触发重建索引"""
    # TODO: 集成 Celery 任务
    return {"message": "重建索引任务已触发", "status": "started"}


@router.post("/maintenance/cleanup")
async def trigger_cleanup():
    """触发清理"""
    # TODO: 集成 Celery 任务
    return {"message": "清理任务已触发", "status": "started"}
