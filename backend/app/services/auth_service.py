"""
认证服务模块
版本: v1.0
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    validate_password_strength,
)
from app.models.user import User
from app.models.audit_log import AuditLog, AuditActionType


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> tuple[Optional[User], str]:
        """
        验证用户凭证
        
        Returns:
            (用户对象, 错误信息) - 成功时错误信息为空
        """
        user = await self.get_user_by_username(username)
        
        if not user:
            return None, "用户名或密码错误"
        
        # 检查账号是否激活
        if not user.is_active:
            await self._log_audit(
                user.id, AuditActionType.LOGIN_FAILED, ip_address,
                {"reason": "account_disabled"}
            )
            return None, "账号已被禁用"
        
        # 检查账号是否锁定
        if user.is_locked:
            remaining = user.get_lock_remaining_seconds()
            await self._log_audit(
                user.id, AuditActionType.LOGIN_FAILED, ip_address,
                {"reason": "account_locked", "remaining_seconds": remaining}
            )
            return None, f"账号已被锁定，请 {int(remaining / 60)} 分钟后重试"
        
        # 验证密码
        if not verify_password(password, user.password_hash):
            await self._handle_failed_login(user, ip_address)
            return None, "用户名或密码错误"
        
        # 登录成功，重置失败次数
        await self._handle_successful_login(user, ip_address)
        
        return user, ""

    async def _handle_failed_login(
        self,
        user: User,
        ip_address: Optional[str] = None
    ) -> None:
        """处理登录失败"""
        user.failed_attempts += 1
        
        # 达到最大失败次数，锁定账号
        if user.failed_attempts >= settings.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.lockout_duration_minutes
            )
            await self._log_audit(
                user.id, AuditActionType.LOGIN_FAILED, ip_address,
                {
                    "reason": "max_attempts_reached",
                    "attempts": user.failed_attempts,
                    "locked_until": user.locked_until.isoformat()
                }
            )
        else:
            await self._log_audit(
                user.id, AuditActionType.LOGIN_FAILED, ip_address,
                {
                    "reason": "invalid_password",
                    "attempts": user.failed_attempts
                }
            )
        
        await self.db.commit()

    async def _handle_successful_login(
        self,
        user: User,
        ip_address: Optional[str] = None
    ) -> None:
        """处理登录成功"""
        user.failed_attempts = 0
        user.locked_until = None
        
        await self._log_audit(
            user.id, AuditActionType.LOGIN, ip_address,
            {"username": user.username}
        )
        
        await self.db.commit()

    def create_tokens(self, user: User) -> dict:
        """为用户创建令牌"""
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expire_hours * 3600,
        }

    async def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        修改密码
        
        Returns:
            (是否成功, 错误信息)
        """
        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            return False, "原密码错误"
        
        # 验证新密码强度
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg
        
        # 更新密码
        user.password_hash = get_password_hash(new_password)
        
        await self._log_audit(
            user.id, AuditActionType.PASSWORD_CHANGE, ip_address,
            {"username": user.username}
        )
        
        await self.db.commit()
        
        return True, ""

    async def logout(
        self,
        user: User,
        ip_address: Optional[str] = None
    ) -> None:
        """用户登出"""
        await self._log_audit(
            user.id, AuditActionType.LOGOUT, ip_address,
            {"username": user.username}
        )
        await self.db.commit()

    async def _log_audit(
        self,
        user_id: int,
        action_type: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ) -> None:
        """记录审计日志"""
        audit_log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            target_type="user",
            target_id=str(user_id),
            ip_address=ip_address,
            details=details,
        )
        self.db.add(audit_log)
