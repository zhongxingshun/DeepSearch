"""
搜索 API 路由
版本: v1.0
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, get_client_ip
from app.models.user import User
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchHighlight,
)
from app.services.search_service import SearchService
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=SearchResponse)
@router.get("/", response_model=SearchResponse)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    file_type: Optional[str] = Query(None, description="文件类型过滤"),
    sort_by: Optional[str] = Query(None, description="排序字段 (created_at, file_size)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    全文搜索
    
    - 支持中文分词搜索
    - 支持按文件类型过滤
    - 返回带高亮的内容摘要
    """
    search_service = SearchService(db)
    audit_service = AuditService(db)
    ip_address = get_client_ip(request)
    
    # 执行搜索
    result = await search_service.search(
        keyword=q,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        file_type=file_type,
        sort_by=sort_by,
        sort_order=sort_order,
        record_history=True,
    )
    
    # 记录搜索审计日志
    await audit_service.log_search(
        user_id=current_user.id,
        keyword=q,
        result_count=result["total"],
        ip_address=ip_address,
    )
    await db.commit()
    
    # 转换为响应模型
    search_results = [
        SearchResult(
            id=hit["id"],
            file_id=hit["file_id"],
            filename=hit["filename"],
            file_type=hit["file_type"],
            file_size=hit["file_size"],
            file_path=hit["file_path"],
            content_snippet=hit["content_snippet"],
            score=hit.get("score", 0),
            highlights=[
                SearchHighlight(
                    field=h["field"],
                    snippet=f"位置: {h['start']}-{h['start']+h['length']}"
                )
                for h in hit.get("highlights", [])
            ],
            created_at=hit.get("created_at"),
        )
        for hit in result["results"]
    ]
    
    return SearchResponse(
        success=True,
        keyword=result["keyword"],
        results=search_results,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        query_time_ms=result["query_time_ms"],
    )


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情"""
    search_service = SearchService(db)
    document = await search_service.get_document(doc_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )
    
    return {
        "success": True,
        "data": document,
    }


@router.post("/suggest")
async def search_suggest(
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    limit: int = Query(5, ge=1, le=10, description="建议数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索建议
    
    根据输入的关键词返回搜索建议（基于历史搜索和热门关键词）
    """
    from app.services.search_service import SearchHistoryService
    
    history_service = SearchHistoryService(db)
    
    # 获取用户最近搜索
    recent = await history_service.get_recent(current_user.id, limit=limit)
    
    # 获取全局热门
    popular = await history_service.get_popular_keywords(limit=limit)
    
    # 合并去重
    suggestions = []
    seen = set()
    
    # 优先用户历史
    for h in recent:
        if h.keyword.lower().startswith(q.lower()) and h.keyword.lower() not in seen:
            suggestions.append({
                "keyword": h.keyword,
                "type": "recent",
            })
            seen.add(h.keyword.lower())
            if len(suggestions) >= limit:
                break
    
    # 补充热门
    if len(suggestions) < limit:
        for p in popular:
            if p["keyword"].lower().startswith(q.lower()) and p["keyword"].lower() not in seen:
                suggestions.append({
                    "keyword": p["keyword"],
                    "type": "popular",
                    "count": p["search_count"],
                })
                seen.add(p["keyword"].lower())
                if len(suggestions) >= limit:
                    break
    
    return {
        "success": True,
        "query": q,
        "suggestions": suggestions,
    }
