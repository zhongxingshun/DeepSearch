"""
搜索 Schema 定义
版本: v1.0
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """搜索请求"""

    keyword: str = Field(..., min_length=1, max_length=500, description="搜索关键词")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    file_type: Optional[str] = Field(None, description="文件类型过滤")


class SearchHighlight(BaseModel):
    """搜索高亮"""

    field: str = Field(..., description="字段名")
    snippet: str = Field(..., description="高亮片段")


class SearchResult(BaseModel):
    """单个搜索结果"""

    id: str = Field(..., description="文档 ID")
    file_id: int = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小")
    file_path: str = Field(..., description="文件路径")
    content_snippet: str = Field(..., description="内容片段（带高亮）")
    score: float = Field(default=0, description="相关性得分")
    highlights: list[SearchHighlight] = Field(default=[], description="高亮信息")
    created_at: Optional[str] = Field(None, description="创建时间")


class SearchResponse(BaseModel):
    """搜索响应"""

    success: bool = True
    keyword: str = Field(..., description="搜索关键词")
    results: list[SearchResult] = Field(..., description="搜索结果")
    total: int = Field(..., description="总结果数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    query_time_ms: float = Field(..., description="查询耗时（毫秒）")


class SearchHistoryItem(BaseModel):
    """搜索历史项"""

    id: int
    keyword: str
    result_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SearchHistoryResponse(BaseModel):
    """搜索历史响应"""

    success: bool = True
    data: list[SearchHistoryItem]
    total: int
