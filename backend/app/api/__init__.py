"""
DeepSearch API 路由模块
版本: v1.0
"""

from app.api import auth, search, files, history, admin, health, share

__all__ = [
    "auth",
    "search", 
    "files",
    "history",
    "admin",
    "health",
    "share",
]
