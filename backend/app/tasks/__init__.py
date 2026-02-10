"""
DeepSearch Celery 任务模块
版本: v1.0
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.config import settings

# 创建 Celery 应用
celery_app = Celery(
    "deepsearch",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

# ============================================
# Celery 基础配置
# ============================================
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务设置
    task_track_started=True,
    task_time_limit=600,  # 10 分钟超时
    task_soft_time_limit=540,  # 9 分钟软超时
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 结果设置
    result_expires=3600,  # 结果保留 1 小时
    
    # Worker 设置
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# ============================================
# 队列配置 (优先级队列)
# ============================================
celery_app.conf.task_queues = (
    Queue("high", routing_key="high"),
    Queue("low", routing_key="low"),
    Queue("maintenance", routing_key="maintenance"),
)

celery_app.conf.task_default_queue = "low"
celery_app.conf.task_default_routing_key = "low"

# 任务路由
celery_app.conf.task_routes = {
    "app.tasks.parse_task.*": {"queue": "low"},
    "app.tasks.index_task.*": {"queue": "low"},
    "app.tasks.scan_task.*": {"queue": "low"},
    "app.tasks.backup_task.*": {"queue": "maintenance"},
    "app.tasks.cleanup_task.*": {"queue": "maintenance"},
}

# ============================================
# 定时任务配置 (Celery Beat)
# ============================================
celery_app.conf.beat_schedule = {
    # 每日凌晨 2:00 执行备份
    "daily-backup": {
        "task": "app.tasks.backup_task.run_backup",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "maintenance"},
    },
    # 每日凌晨 3:00 清理日志
    "daily-cleanup": {
        "task": "app.tasks.cleanup_task.cleanup_logs",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "maintenance"},
    },
    # 每小时扫描新文件
    "hourly-scan": {
        "task": "app.tasks.scan_task.scan_directory",
        "schedule": crontab(minute=0),  # 每小时整点
        "options": {"queue": "low"},
    },
}

# ============================================
# 重试配置
# ============================================
celery_app.conf.task_annotations = {
    "*": {
        "autoretry_for": (Exception,),
        "retry_kwargs": {"max_retries": 3},
        "retry_backoff": True,
        "retry_backoff_max": 600,
        "retry_jitter": True,
    }
}

# 自动发现任务
celery_app.autodiscover_tasks([
    "app.tasks.parse_task",
    "app.tasks.index_task",
    "app.tasks.scan_task",
    "app.tasks.backup_task",
    "app.tasks.cleanup_task",
])
