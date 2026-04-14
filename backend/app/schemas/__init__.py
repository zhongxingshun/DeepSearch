"""
DeepSearch Pydantic Schemas
版本: v1.0
"""

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    TokenPayload,
)
from app.schemas.file import (
    FileCreate,
    FileResponse,
    FileListResponse,
    FileStatusResponse,
    FileShareLinkCreateRequest,
    FileShareLinkResponse,
    FileShareLinkEnvelope,
)
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.schemas.common import (
    ResponseBase,
    PaginatedResponse,
    ErrorResponse,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenPayload",
    # File schemas
    "FileCreate",
    "FileResponse",
    "FileListResponse",
    "FileStatusResponse",
    "FileShareLinkCreateRequest",
    "FileShareLinkResponse",
    "FileShareLinkEnvelope",
    # Search schemas
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    # Common schemas
    "ResponseBase",
    "PaginatedResponse",
    "ErrorResponse",
]
