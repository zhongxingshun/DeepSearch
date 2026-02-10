"""
搜索服务模块
版本: v1.0
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.file import File
from app.models.search_history import SearchHistory
from app.services.meilisearch_client import MeilisearchClient, meili_client


class SearchService:
    """搜索服务"""

    def __init__(
        self,
        db: AsyncSession,
        meili: Optional[MeilisearchClient] = None
    ):
        self.db = db
        self.meili = meili or meili_client

    async def search(
        self,
        keyword: str,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        file_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        record_history: bool = True,
    ) -> Dict[str, Any]:
        """
        执行全文搜索
        
        Args:
            keyword: 搜索关键词
            user_id: 用户 ID
            page: 页码
            page_size: 每页数量
            file_type: 文件类型过滤
            sort_by: 排序字段 (created_at, file_size)
            sort_order: 排序方向 (asc, desc)
            record_history: 是否记录搜索历史
            
        Returns:
            搜索结果
        """
        # 构建过滤条件
        filters = None
        if file_type:
            filters = f"file_type = '{file_type}'"
        
        # 构建排序
        sort = None
        if sort_by and sort_by in ["created_at", "file_size"]:
            sort = [f"{sort_by}:{sort_order}"]
        
        # 记录开始时间
        start_time = datetime.utcnow()
        
        # 执行搜索
        results = await self.meili.search(
            query=keyword,
            page=page,
            page_size=page_size,
            filters=filters,
            sort=sort,
        )
        
        # 计算查询时间
        query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # 处理搜索结果
        processed_hits = await self._process_hits(results.get("hits", []), query=keyword)
        
        total = results.get("total", 0)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # 记录搜索历史
        if record_history and keyword.strip():
            await self._record_history(user_id, keyword, total)
        
        return {
            "success": True,
            "keyword": keyword,
            "results": processed_hits,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "query_time_ms": round(query_time_ms, 2),
        }

    @staticmethod
    def _build_centered_snippet(
        content: str,
        query: str,
        snippet_len: int = 300,
        highlight_pre: str = "<mark>",
        highlight_post: str = "</mark>",
    ) -> str:
        """
        构建以匹配词为中心的摘要片段
        
        直接在原始 content 中查找搜索词位置，
        向前后各扩展约一半窗口，让关键词出现在中间。
        
        Args:
            content: 原始文本内容
            query: 搜索关键词（原始用户输入）
            snippet_len: 摘要总长度（不含高亮标签）
            highlight_pre: 高亮前标签
            highlight_post: 高亮后标签
        """
        if not content:
            return ""
        
        # 清理 content 中的 markdown 图片标签（减少噪音）
        import re
        clean_content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        clean_content = re.sub(r'\n{2,}', '\n', clean_content).strip()
        
        if not query:
            if len(clean_content) <= snippet_len:
                return clean_content
            return clean_content[:snippet_len] + "..."
        
        # 在内容中查找关键词（不区分大小写）
        search_term = query.strip()
        content_lower = clean_content.lower()
        term_lower = search_term.lower()
        
        match_pos = content_lower.find(term_lower)
        
        # 如果直接查找不到，尝试用 jieba 分词后的各个词
        if match_pos < 0:
            try:
                import jieba
                words = [w for w in jieba.cut(search_term) if len(w.strip()) > 0]
                for word in words:
                    pos = content_lower.find(word.lower())
                    if pos >= 0:
                        match_pos = pos
                        search_term = word  # 使用找到的子词
                        term_lower = word.lower()
                        break
            except ImportError:
                pass
        
        if match_pos < 0:
            # 还是找不到，返回开头内容
            if len(clean_content) <= snippet_len:
                return clean_content
            return clean_content[:snippet_len] + "..."
        
        # 计算窗口：让匹配词居中
        half_window = snippet_len // 2
        term_len = len(search_term)
        
        win_start = max(0, match_pos - half_window)
        win_end = min(len(clean_content), match_pos + term_len + half_window)
        
        # 如果窗口不够长，扩展另一侧
        actual_len = win_end - win_start
        if actual_len < snippet_len:
            if win_start == 0:
                win_end = min(len(clean_content), win_end + (snippet_len - actual_len))
            elif win_end == len(clean_content):
                win_start = max(0, win_start - (snippet_len - actual_len))
        
        snippet = clean_content[win_start:win_end]
        
        # 在摘要中高亮所有匹配的关键词
        # 同时高亮原始搜索词和分词后的各个词
        highlight_terms = [search_term]
        try:
            import jieba
            words = [w.strip() for w in jieba.cut(query.strip()) if len(w.strip()) > 1]
            highlight_terms.extend(words)
        except ImportError:
            pass
        
        # 去重
        seen = set()
        unique_terms = []
        for t in highlight_terms:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_terms.append(t)
        
        # 收集所有匹配区间
        all_ranges = []
        snippet_lower = snippet.lower()
        for term in unique_terms:
            term_l = term.lower()
            start = 0
            while True:
                pos = snippet_lower.find(term_l, start)
                if pos < 0:
                    break
                all_ranges.append((pos, pos + len(term)))
                start = pos + 1
        
        if not all_ranges:
            # 没有找到任何匹配，直接返回
            prefix = "..." if win_start > 0 else ""
            suffix = "..." if win_end < len(clean_content) else ""
            return f"{prefix}{snippet}{suffix}"
        
        # 合并重叠区间
        all_ranges.sort()
        merged = [all_ranges[0]]
        for cur_start, cur_end in all_ranges[1:]:
            prev_start, prev_end = merged[-1]
            if cur_start <= prev_end:
                merged[-1] = (prev_start, max(prev_end, cur_end))
            else:
                merged.append((cur_start, cur_end))
        
        # 从后往前插入高亮标签
        snippet_chars = list(snippet)
        for hl_start, hl_end in reversed(merged):
            snippet_chars.insert(hl_end, highlight_post)
            snippet_chars.insert(hl_start, highlight_pre)
        
        snippet = "".join(snippet_chars)
        
        # 添加省略号
        prefix = "..." if win_start > 0 else ""
        suffix = "..." if win_end < len(clean_content) else ""
        
        return f"{prefix}{snippet}{suffix}"

    async def _process_hits(self, hits: List[Dict], query: str = "") -> List[Dict]:
        """处理搜索命中结果"""
        processed = []
        
        for hit in hits:
            content = hit.get("content", "")
            
            # 构建以匹配词为中心的摘要
            content_snippet = self._build_centered_snippet(
                content=content,
                query=query,
                snippet_len=300,
            )
            
            processed.append({
                "id": hit.get("id"),
                "file_id": hit.get("file_id"),
                "filename": hit.get("filename"),
                "file_type": hit.get("file_type"),
                "file_size": hit.get("file_size"),
                "file_path": hit.get("file_path"),
                "content_snippet": content_snippet,
                "score": hit.get("_rankingScore", 0),
                "highlights": [],
                "created_at": hit.get("created_at"),
            })
        
        return processed

    async def _record_history(
        self,
        user_id: int,
        keyword: str,
        result_count: int
    ) -> None:
        """记录搜索历史"""
        history = SearchHistory(
            user_id=user_id,
            keyword=keyword.strip()[:500],  # 限制长度
            result_count=result_count,
        )
        self.db.add(history)
        await self.db.commit()

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档详情"""
        return await self.meili.get_document(doc_id)


class SearchHistoryService:
    """搜索历史服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_history(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
    ) -> Tuple[List[SearchHistory], int]:
        """
        获取用户搜索历史
        
        Args:
            user_id: 用户 ID
            page: 页码
            page_size: 每页数量
            keyword: 过滤关键词
            
        Returns:
            (历史列表, 总数)
        """
        query = select(SearchHistory).where(
            SearchHistory.user_id == user_id
        )
        count_query = select(func.count(SearchHistory.id)).where(
            SearchHistory.user_id == user_id
        )
        
        if keyword:
            query = query.where(
                SearchHistory.keyword.ilike(f"%{keyword}%")
            )
            count_query = count_query.where(
                SearchHistory.keyword.ilike(f"%{keyword}%")
            )
        
        # 获取总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页查询
        query = query.order_by(desc(SearchHistory.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        histories = list(result.scalars().all())
        
        return histories, total

    async def get_recent(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[SearchHistory]:
        """获取最近的搜索历史"""
        query = select(SearchHistory).where(
            SearchHistory.user_id == user_id
        ).order_by(
            desc(SearchHistory.created_at)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_popular_keywords(
        self,
        user_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取热门搜索关键词
        
        Args:
            user_id: 用户 ID (可选，为空则返回全局热门)
            limit: 返回数量
            
        Returns:
            热门关键词列表
        """
        query = select(
            SearchHistory.keyword,
            func.count(SearchHistory.id).label("count"),
            func.sum(SearchHistory.result_count).label("total_results")
        ).group_by(
            SearchHistory.keyword
        ).order_by(
            desc("count")
        ).limit(limit)
        
        if user_id:
            query = query.where(SearchHistory.user_id == user_id)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "keyword": row[0],
                "search_count": row[1],
                "total_results": row[2] or 0,
            }
            for row in rows
        ]

    async def delete_history(self, user_id: int, history_id: int) -> bool:
        """删除单条搜索历史"""
        query = select(SearchHistory).where(
            SearchHistory.id == history_id,
            SearchHistory.user_id == user_id,
        )
        result = await self.db.execute(query)
        history = result.scalar_one_or_none()
        
        if history:
            await self.db.delete(history)
            await self.db.commit()
            return True
        
        return False

    async def clear_history(self, user_id: int) -> int:
        """清除用户全部搜索历史"""
        from sqlalchemy import delete
        
        stmt = delete(SearchHistory).where(
            SearchHistory.user_id == user_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount
