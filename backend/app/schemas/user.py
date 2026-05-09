"""
用户 Schema 定义
版本: v1.0
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.access_control import ROLE_INTERNAL_EMPLOYEE, validate_role_value


class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")


class UserCreate(UserBase):
    """创建用户请求"""

    password: str = Field(..., min_length=8, description="密码")
    role: str = Field(default=ROLE_INTERNAL_EMPLOYEE, description="角色")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return validate_role_value(v)


class UserUpdate(BaseModel):
    """更新用户请求"""

    password: Optional[str] = Field(None, min_length=8, description="新密码")
    role: Optional[str] = Field(None, description="角色")
    is_active: Optional[bool] = Field(None, description="是否激活")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        return validate_role_value(v) if v is not None else v


class UserResponse(UserBase):
    """用户响应"""

    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class Token(BaseModel):
    """令牌响应"""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class TokenPayload(BaseModel):
    """令牌载荷"""

    sub: str  # 用户 ID
    username: str
    role: str
    exp: datetime
    iat: datetime


class PasswordChange(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, description="新密码")
