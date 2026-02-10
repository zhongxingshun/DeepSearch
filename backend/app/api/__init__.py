"""
DeepSearch API 路由模块
版本: v1.0
"""

from app.api import auth, search, files, history, admin, health

__all__ = [
    "auth",
    "search", 
    "files",
    "history",
    "admin",
    "health",
]
