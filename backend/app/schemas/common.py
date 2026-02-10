"""
通用 Schema 定义
版本: v1.0
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel):
    """基础响应模型"""

    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应模型"""

    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class PaginationMeta(BaseModel):
    """分页元数据"""

    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    total_pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    success: bool = True
    message: str = "操作成功"
    data: list[T]
    pagination: PaginationMeta


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str
    timestamp: str
    version: Optional[str] = None
    components: Optional[dict[str, Any]] = None
