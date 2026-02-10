"""
认证 API 路由
版本: v1.0
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, get_client_ip
from app.models.user import User
from app.schemas.user import (
    UserLogin,
    UserResponse,
    Token,
    PasswordChange,
)
from app.schemas.common import ResponseBase
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录
    
    - 验证用户名和密码
    - 返回访问令牌和刷新令牌
    - 登录失败 5 次后锁定账号 30 分钟
    """
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    
    user, error_msg = await auth_service.authenticate_user(
        username=login_data.username,
        password=login_data.password,
        ip_address=ip_address,
    )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = auth_service.create_tokens(user)
    
    return tokens


@router.post("/logout", response_model=ResponseBase)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    用户登出
    
    - 记录登出审计日志
    - 客户端应清除本地存储的令牌
    """
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    
    await auth_service.logout(current_user, ip_address)
    
    return ResponseBase(message="登出成功")


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    刷新访问令牌
    
    - 使用有效的访问令牌获取新令牌
    """
    auth_service = AuthService(db)
    tokens = auth_service.create_tokens(current_user)
    
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户信息
    
    - 返回当前登录用户的详细信息
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.put("/password", response_model=ResponseBase)
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    修改密码
    
    - 验证原密码
    - 新密码需符合复杂度要求:
      - 至少 8 位
      - 包含大小写字母、数字和特殊字符
    """
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    
    success, error_msg = await auth_service.change_password(
        user=current_user,
        old_password=password_data.old_password,
        new_password=password_data.new_password,
        ip_address=ip_address,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    
    return ResponseBase(message="密码修改成功")
