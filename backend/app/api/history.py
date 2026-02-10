"""
搜索历史 API 路由
版本: v1.0
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.search import SearchHistoryItem, SearchHistoryResponse
from app.schemas.common import ResponseBase, PaginationMeta
from app.services.search_service import SearchHistoryService

router = APIRouter()


@router.get("", response_model=SearchHistoryResponse)
@router.get("/", response_model=SearchHistoryResponse)
async def get_search_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="过滤关键词"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取搜索历史
    
    - 返回当前用户的搜索历史
    - 支持分页和关键词过滤
    """
    history_service = SearchHistoryService(db)
    
    histories, total = await history_service.get_history(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        keyword=keyword,
    )
    
    return SearchHistoryResponse(
        success=True,
        data=[
            SearchHistoryItem(
                id=h.id,
                keyword=h.keyword,
                result_count=h.result_count,
                created_at=h.created_at,
            )
            for h in histories
        ],
        total=total,
    )


@router.get("/recent")
async def get_recent_history(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取最近的搜索历史"""
    history_service = SearchHistoryService(db)
    
    histories = await history_service.get_recent(
        user_id=current_user.id,
        limit=limit,
    )
    
    return {
        "success": True,
        "data": [
            {
                "id": h.id,
                "keyword": h.keyword,
                "result_count": h.result_count,
                "created_at": h.created_at.isoformat(),
            }
            for h in histories
        ],
    }


@router.get("/popular")
async def get_popular_keywords(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取热门搜索关键词
    
    - 返回用户自己的热门搜索
    """
    history_service = SearchHistoryService(db)
    
    keywords = await history_service.get_popular_keywords(
        user_id=current_user.id,
        limit=limit,
    )
    
    return {
        "success": True,
        "data": keywords,
    }


@router.get("/popular/global")
async def get_global_popular_keywords(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取全局热门搜索关键词
    
    - 返回所有用户的热门搜索
    """
    history_service = SearchHistoryService(db)
    
    keywords = await history_service.get_popular_keywords(
        user_id=None,  # 全局
        limit=limit,
    )
    
    return {
        "success": True,
        "data": keywords,
    }


@router.delete("/{history_id}", response_model=ResponseBase)
async def delete_search_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除单条搜索历史"""
    history_service = SearchHistoryService(db)
    
    success = await history_service.delete_history(
        user_id=current_user.id,
        history_id=history_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="搜索历史不存在",
        )
    
    return ResponseBase(message="删除成功")


@router.delete("", response_model=ResponseBase)
@router.delete("/", response_model=ResponseBase)
async def clear_search_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    清除全部搜索历史
    
    - 删除当前用户的所有搜索历史
    """
    history_service = SearchHistoryService(db)
    
    count = await history_service.clear_history(current_user.id)
    
    return ResponseBase(message=f"已清除 {count} 条搜索历史")
