"""
DeepSearch 业务服务模块
版本: v1.0
"""

from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.file_storage_service import FileStorageService, file_storage
from app.services.file_service import FileService
from app.services.meilisearch_client import MeilisearchClient, meili_client
from app.services.search_service import SearchService, SearchHistoryService

__all__ = [
    "AuthService",
    "AuditService",
    "FileStorageService",
    "file_storage",
    "FileService",
    "MeilisearchClient",
    "meili_client",
    "SearchService",
    "SearchHistoryService",
]
