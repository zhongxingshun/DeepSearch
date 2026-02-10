"""
审计日志服务模块
版本: v1.0
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog, AuditActionType


class AuditService:
    """审计日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        user_id: Optional[int],
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """
        记录审计日志
        
        Args:
            user_id: 用户 ID
            action_type: 动作类型
            target_type: 目标类型 (user, file, task, config)
            target_id: 目标 ID
            ip_address: 客户端 IP
            details: 详细信息
            
        Returns:
            创建的审计日志
        """
        audit_log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            details=details,
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log

    async def log_login(
        self,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
        success: bool = True,
        reason: Optional[str] = None,
    ) -> AuditLog:
        """记录登录日志"""
        action_type = AuditActionType.LOGIN if success else AuditActionType.LOGIN_FAILED
        details = {"username": username}
        if reason:
            details["reason"] = reason
        
        return await self.log(
            user_id=user_id,
            action_type=action_type,
            target_type="user",
            target_id=str(user_id),
            ip_address=ip_address,
            details=details,
        )

    async def log_logout(
        self,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """记录登出日志"""
        return await self.log(
            user_id=user_id,
            action_type=AuditActionType.LOGOUT,
            target_type="user",
            target_id=str(user_id),
            ip_address=ip_address,
            details={"username": username},
        )

    async def log_file_download(
        self,
        user_id: int,
        file_id: int,
        filename: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """记录文件下载日志"""
        return await self.log(
            user_id=user_id,
            action_type=AuditActionType.FILE_DOWNLOAD,
            target_type="file",
            target_id=str(file_id),
            ip_address=ip_address,
            details={"filename": filename},
        )

    async def log_file_upload(
        self,
        user_id: int,
        file_id: int,
        filename: str,
        file_size: int,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """记录文件上传日志"""
        return await self.log(
            user_id=user_id,
            action_type=AuditActionType.FILE_UPLOAD,
            target_type="file",
            target_id=str(file_id),
            ip_address=ip_address,
            details={"filename": filename, "file_size": file_size},
        )

    async def log_search(
        self,
        user_id: int,
        keyword: str,
        result_count: int,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """记录搜索日志"""
        return await self.log(
            user_id=user_id,
            action_type=AuditActionType.SEARCH,
            ip_address=ip_address,
            details={"keyword": keyword, "result_count": result_count},
        )

    async def log_admin_action(
        self,
        user_id: int,
        action: str,
        target_type: str,
        target_id: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """记录管理操作日志"""
        action_mapping = {
            "create_user": AuditActionType.USER_CREATE,
            "update_user": AuditActionType.USER_UPDATE,
            "delete_user": AuditActionType.USER_DELETE,
            "update_config": AuditActionType.CONFIG_UPDATE,
            "retry_task": AuditActionType.TASK_RETRY,
        }
        
        action_type = action_mapping.get(action, action)
        
        return await self.log(
            user_id=user_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            details=details,
        )

    async def get_logs(
        self,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """获取审计日志列表"""
        query = select(AuditLog)
        
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        
        if action_type is not None:
            query = query.where(AuditLog.action_type == action_type)
        
        query = query.order_by(desc(AuditLog.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
