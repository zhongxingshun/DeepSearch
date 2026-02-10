"""
清理任务
版本: v1.0

清理过期日志、临时文件等
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import text

from app.config import settings
from app.tasks.db_engine import sync_engine

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.cleanup_task.cleanup_logs",
    queue="maintenance",
)
def cleanup_logs(
    self,
    retention_days: int = 90,
) -> dict:
    """
    清理旧的审计日志
    
    Args:
        retention_days: 日志保留天数
    """
    logger.info(f"开始清理审计日志（保留 {retention_days} 天）")
    
    try:
        engine = sync_engine
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with engine.connect() as conn:
            # 统计要删除的数量
            count_result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM audit_logs 
                    WHERE created_at < :cutoff
                """),
                {"cutoff": cutoff_date}
            )
            count = count_result.scalar() or 0
            
            if count > 0:
                # 删除旧日志
                conn.execute(
                    text("""
                        DELETE FROM audit_logs 
                        WHERE created_at < :cutoff
                    """),
                    {"cutoff": cutoff_date}
                )
                conn.commit()
        
        logger.info(f"清理完成: 删除 {count} 条审计日志")
        
        return {
            "success": True,
            "deleted_count": count,
            "cutoff_date": cutoff_date.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"清理审计日志失败: {str(e)}")
        raise


@shared_task(
    bind=True,
    name="app.tasks.cleanup_task.cleanup_search_history",
    queue="maintenance",
)
def cleanup_search_history(
    self,
    retention_days: int = 30,
) -> dict:
    """
    清理旧的搜索历史
    """
    logger.info(f"开始清理搜索历史（保留 {retention_days} 天）")
    
    try:
        engine = sync_engine
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with engine.connect() as conn:
            count_result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM search_history 
                    WHERE created_at < :cutoff
                """),
                {"cutoff": cutoff_date}
            )
            count = count_result.scalar() or 0
            
            if count > 0:
                conn.execute(
                    text("""
                        DELETE FROM search_history 
                        WHERE created_at < :cutoff
                    """),
                    {"cutoff": cutoff_date}
                )
                conn.commit()
        
        logger.info(f"清理完成: 删除 {count} 条搜索历史")
        
        return {
            "success": True,
            "deleted_count": count,
        }
        
    except Exception as e:
        logger.error(f"清理搜索历史失败: {str(e)}")
        raise


@shared_task(
    bind=True,
    name="app.tasks.cleanup_task.cleanup_temp_files",
    queue="maintenance",
)
def cleanup_temp_files(
    self,
    max_age_hours: int = 24,
) -> dict:
    """
    清理临时文件
    """
    logger.info(f"开始清理临时文件（{max_age_hours} 小时以上）")
    
    import shutil
    
    temp_dirs = [
        Path("/tmp/deepsearch"),
        Path(settings.file_storage_path) / "temp",
    ]
    
    deleted_count = 0
    freed_space = 0
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    for temp_dir in temp_dirs:
        if not temp_dir.exists():
            continue
        
        for item in temp_dir.iterdir():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff_time:
                    if item.is_file():
                        freed_space += item.stat().st_size
                        item.unlink()
                    elif item.is_dir():
                        for f in item.rglob("*"):
                            if f.is_file():
                                freed_space += f.stat().st_size
                        shutil.rmtree(item)
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"清理失败: {item}, error={str(e)}")
    
    logger.info(f"清理完成: 删除 {deleted_count} 项，释放 {freed_space} bytes")
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "freed_space": freed_space,
        "freed_space_human": format_size(freed_space),
    }


@shared_task(
    bind=True,
    name="app.tasks.cleanup_task.cleanup_failed_tasks",
    queue="maintenance",
)
def cleanup_failed_tasks(
    self,
    retention_days: int = 7,
) -> dict:
    """
    清理失败的任务记录
    """
    logger.info(f"开始清理失败任务（保留 {retention_days} 天）")
    
    try:
        engine = sync_engine
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with engine.connect() as conn:
            count_result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM tasks 
                    WHERE status = 'failed' AND created_at < :cutoff
                """),
                {"cutoff": cutoff_date}
            )
            count = count_result.scalar() or 0
            
            if count > 0:
                conn.execute(
                    text("""
                        DELETE FROM tasks 
                        WHERE status = 'failed' AND created_at < :cutoff
                    """),
                    {"cutoff": cutoff_date}
                )
                conn.commit()
        
        logger.info(f"清理完成: 删除 {count} 个失败任务记录")
        
        return {
            "success": True,
            "deleted_count": count,
        }
        
    except Exception as e:
        logger.error(f"清理失败任务失败: {str(e)}")
        raise


@shared_task(
    name="app.tasks.cleanup_task.run_all_cleanup",
    queue="maintenance",
)
def run_all_cleanup() -> dict:
    """执行所有清理任务"""
    logger.info("开始执行全部清理任务")
    
    results = {
        "logs": cleanup_logs.s(retention_days=90).apply().get(),
        "search_history": cleanup_search_history.s(retention_days=30).apply().get(),
        "temp_files": cleanup_temp_files.s(max_age_hours=24).apply().get(),
        "failed_tasks": cleanup_failed_tasks.s(retention_days=7).apply().get(),
    }
    
    return {
        "success": True,
        "results": results,
    }


def format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
