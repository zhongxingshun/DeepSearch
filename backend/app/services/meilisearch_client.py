"""
Meilisearch 客户端封装
版本: v1.1

优化中文搜索支持：
- 使用 jieba 分词对文档内容进行预处理
- 搜索时自动对中文查询进行分词
- 配置 Meilisearch 的分隔符和字典以更好支持中文
"""

import logging
import re
from typing import Any, Dict, List, Optional

import meilisearch
from meilisearch.errors import MeilisearchApiError

from app.config import settings

logger = logging.getLogger(__name__)


class MeilisearchClient:
    """Meilisearch 客户端封装"""

    # 默认索引名
    INDEX_NAME = "documents"

    # 可搜索字段
    SEARCHABLE_ATTRIBUTES = [
        "content",
        "filename",
        "file_type",
    ]

    # 可过滤字段
    FILTERABLE_ATTRIBUTES = [
        "file_type",
        "file_id",
        "uploaded_by",
        "created_at",
    ]

    # 可排序字段
    SORTABLE_ATTRIBUTES = [
        "created_at",
        "file_size",
    ]

    # 显示字段
    DISPLAYED_ATTRIBUTES = [
        "id",
        "file_id",
        "filename",
        "file_type",
        "file_size",
        "file_path",
        "content",
        "created_at",
        "uploaded_by",
    ]

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        self.url = url or settings.meili_url
        self.api_key = api_key or settings.meili_master_key
        self._client: Optional[meilisearch.Client] = None

    @property
    def client(self) -> meilisearch.Client:
        """获取 Meilisearch 客户端（延迟初始化）"""
        if self._client is None:
            self._client = meilisearch.Client(self.url, self.api_key)
        return self._client

    def get_index(self) -> meilisearch.index.Index:
        """获取文档索引"""
        return self.client.index(self.INDEX_NAME)

    @staticmethod
    def chinese_segment(text: str) -> str:
        """
        对文本进行中文分词处理
        
        使用 jieba 分词，在原文基础上添加空格分隔的分词结果，
        使 Meilisearch 能够正确匹配中文词语。
        
        Args:
            text: 原始文本
            
        Returns:
            原文 + 分词后的文本（用空格分隔）
        """
        if not text:
            return ""
        
        try:
            import jieba
            
            # 提取中文部分进行分词
            # 保留原文，同时追加分词结果供索引使用
            segmented_words = jieba.cut_for_search(text)
            segmented = " ".join(segmented_words)
            
            # 返回：原文 + 换行 + 分词版本
            # 这样既保留上下文语义，又能匹配短词
            return f"{text}\n\n{segmented}"
            
        except ImportError:
            logger.warning("jieba 未安装，跳过中文分词")
            return text
        except Exception as e:
            logger.warning(f"中文分词失败: {e}")
            return text

    @staticmethod
    def segment_query(query: str) -> str:
        """
        对搜索查询进行分词优化
        
        Args:
            query: 用户输入的搜索关键词
            
        Returns:
            分词后的查询字符串
        """
        if not query:
            return query
        
        # 检查是否包含中文字符
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
        if not has_chinese:
            return query
        
        try:
            import jieba
            words = jieba.cut_for_search(query)
            segmented = " ".join(words)
            return segmented
        except ImportError:
            return query
        except Exception:
            return query

    async def init_index(self) -> bool:
        """
        初始化索引（创建索引并配置中文搜索优化）
        
        Returns:
            是否成功
        """
        try:
            # 创建索引
            self.client.create_index(
                self.INDEX_NAME,
                {"primaryKey": "id"}
            )
        except MeilisearchApiError as e:
            # 索引已存在，忽略
            if "index_already_exists" not in str(e):
                raise

        # 配置索引设置
        index = self.get_index()
        
        # 设置可搜索字段（content_segmented 是分词后的字段，优先级最高）
        index.update_searchable_attributes([
            "content_segmented",
            "content",
            "filename",
            "file_type",
        ])
        
        # 设置可过滤字段
        index.update_filterable_attributes(self.FILTERABLE_ATTRIBUTES)
        
        # 设置可排序字段
        index.update_sortable_attributes(self.SORTABLE_ATTRIBUTES)
        
        # 设置显示字段
        index.update_displayed_attributes(
            self.DISPLAYED_ATTRIBUTES + ["content_segmented"]
        )
        
        # 配置中文搜索优化
        index.update_settings({
            "typoTolerance": {
                "enabled": True,
                "minWordSizeForTypos": {
                    "oneTypo": 2,
                    "twoTypos": 4,
                },
            },
            "pagination": {
                "maxTotalHits": 10000,
            },
            # 优化排序规则：精确匹配优先
            "rankingRules": [
                "words",
                "typo",
                "proximity",
                "attribute",
                "sort",
                "exactness",
            ],
        })
        
        logger.info("Meilisearch 索引初始化完成（已启用中文分词优化）")
        return True

    async def add_document(
        self,
        doc_id: str,
        file_id: int,
        filename: str,
        content: str,
        file_type: str,
        file_size: int,
        file_path: str,
        uploaded_by: Optional[int] = None,
        created_at: Optional[str] = None,
    ) -> str:
        """
        添加文档到索引（自动进行中文分词增强）
        
        Args:
            doc_id: 文档 ID (通常为 MD5)
            file_id: 关联的文件 ID
            filename: 文件名
            content: 文档内容（已提取的文本）
            file_type: 文件类型
            file_size: 文件大小
            file_path: 文件路径
            uploaded_by: 上传用户 ID
            created_at: 创建时间 (ISO 格式)
            
        Returns:
            任务 ID
        """
        # 对内容进行中文分词增强
        content_segmented = self.chinese_segment(content)
        
        document = {
            "id": doc_id,
            "file_id": file_id,
            "filename": filename,
            "content": content,
            "content_segmented": content_segmented,
            "file_type": file_type,
            "file_size": file_size,
            "file_path": file_path,
            "uploaded_by": uploaded_by,
            "created_at": created_at,
        }
        
        index = self.get_index()
        task = index.add_documents([document], primary_key="id")

        return str(task.task_uid)

    async def add_documents(self, documents: List[Dict[str, Any]]) -> str:
        """批量添加文档"""
        index = self.get_index()
        task = index.add_documents(documents, primary_key="id")
        return str(task.task_uid)

    async def delete_document(self, doc_id: str) -> str:
        """删除文档"""
        index = self.get_index()
        task = index.delete_document(doc_id)
        return str(task.task_uid)

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[str] = None,
        sort: Optional[List[str]] = None,
        attributes_to_highlight: Optional[List[str]] = None,
        highlight_pre_tag: str = "<mark>",
        highlight_post_tag: str = "</mark>",
        attributes_to_crop: Optional[List[str]] = None,
        crop_length: int = 200,
    ) -> Dict[str, Any]:
        """
        执行全文搜索（自动对中文查询进行分词优化）
        
        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            filters: 过滤条件 (如 "file_type = 'pdf'")
            sort: 排序字段 (如 ["created_at:desc"])
            attributes_to_highlight: 高亮字段
            highlight_pre_tag: 高亮前缀标签
            highlight_post_tag: 高亮后缀标签
            attributes_to_crop: 裁剪字段
            crop_length: 裁剪长度
            
        Returns:
            搜索结果
        """
        index = self.get_index()
        
        # 对中文查询进行分词
        segmented_query = self.segment_query(query)
        logger.info(f"搜索: 原始查询='{query}', 分词后='{segmented_query}'")
        
        # 构建搜索参数
        search_params: Dict[str, Any] = {
            "offset": (page - 1) * page_size,
            "limit": page_size,
            "highlightPreTag": highlight_pre_tag,
            "highlightPostTag": highlight_post_tag,
            "attributesToHighlight": attributes_to_highlight or [
                "content", "content_segmented", "filename"
            ],
            "attributesToCrop": attributes_to_crop or ["content"],
            "cropLength": crop_length,
            "showMatchesPosition": True,
            "showRankingScore": True,
        }
        
        if filters:
            search_params["filter"] = filters
        
        if sort:
            search_params["sort"] = sort
        
        # 执行搜索
        results = index.search(segmented_query, search_params)
        
        return {
            "hits": results.get("hits", []),
            "total": results.get("estimatedTotalHits", 0),
            "query": query,
            "processing_time_ms": results.get("processingTimeMs", 0),
            "page": page,
            "page_size": page_size,
        }

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档"""
        try:
            index = self.get_index()
            return index.get_document(doc_id)
        except MeilisearchApiError:
            return None

    async def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            index = self.get_index()
            return index.get_stats()
        except MeilisearchApiError:
            return {"numberOfDocuments": 0}

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.health()
            return True
        except Exception:
            return False

    async def create_snapshot(self) -> str:
        """创建快照"""
        task = self.client.create_snapshot()
        return str(task.task_uid)


# 全局实例
meili_client = MeilisearchClient()
