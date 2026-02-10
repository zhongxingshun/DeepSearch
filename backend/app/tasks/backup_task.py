"""
备份任务
版本: v1.0

执行数据库和 Meilisearch 备份
"""

import os
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
from celery.utils.log import get_task_logger

from app.config import settings

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.backup_task.run_backup",
    queue="maintenance",
    max_retries=3,
)
def run_backup(self) -> dict:
    """
    执行完整备份
    
    包括:
    - PostgreSQL 数据库备份
    - Meilisearch 快照
    - 配置文件备份
    """
    logger.info("开始执行备份任务")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(settings.backup_storage_path) / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "timestamp": timestamp,
        "backup_dir": str(backup_dir),
        "database": None,
        "meilisearch": None,
        "config": None,
    }
    
    try:
        # 1. 备份 PostgreSQL
        results["database"] = backup_postgresql(backup_dir)
        
        # 2. 备份 Meilisearch
        results["meilisearch"] = backup_meilisearch()
        
        # 3. 备份配置文件
        results["config"] = backup_config(backup_dir)
        
        # 4. 清理旧备份
        cleanup_result = cleanup_old_backups()
        results["cleanup"] = cleanup_result
        
        logger.info(f"备份完成: {results}")
        
        return {
            "success": True,
            "results": results,
            "message": "备份完成",
        }
        
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.backup_task.backup_database",
    queue="maintenance",
)
def backup_database() -> dict:
    """单独执行数据库备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(settings.backup_storage_path) / f"db_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    result = backup_postgresql(backup_dir)
    
    return {
        "success": result.get("success", False),
        "backup_dir": str(backup_dir),
        "result": result,
    }


def backup_postgresql(backup_dir: Path) -> dict:
    """备份 PostgreSQL 数据库"""
    logger.info("开始备份 PostgreSQL")
    
    backup_file = backup_dir / "database.sql.gz"
    
    try:
        # 构建 pg_dump 命令
        pg_dump_cmd = [
            "pg_dump",
            "-h", settings.db_host,
            "-p", str(settings.db_port),
            "-U", settings.db_user,
            "-d", settings.db_name,
            "-F", "c",  # 自定义格式
            "-Z", "9",  # 最大压缩
            "-f", str(backup_file.with_suffix(".dump")),
        ]
        
        # 设置环境变量
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.db_password
        
        # 执行备份
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,  # 1小时超时
        )
        
        if result.returncode != 0:
            raise Exception(f"pg_dump 失败: {result.stderr}")
        
        # 获取文件大小
        dump_file = backup_file.with_suffix(".dump")
        size = dump_file.stat().st_size if dump_file.exists() else 0
        
        logger.info(f"PostgreSQL 备份完成: {dump_file}, 大小: {size} bytes")
        
        return {
            "success": True,
            "file": str(dump_file),
            "size": size,
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "备份超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_meilisearch() -> dict:
    """创建 Meilisearch 快照"""
    logger.info("开始备份 Meilisearch")
    
    try:
        import meilisearch
        
        client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
        task = client.create_snapshot()
        
        logger.info(f"Meilisearch 快照任务已创建: task_uid={task.task_uid}")
        
        return {
            "success": True,
            "task_uid": task.task_uid,
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_config(backup_dir: Path) -> dict:
    """备份配置文件"""
    logger.info("开始备份配置文件")
    
    config_dir = backup_dir / "config"
    config_dir.mkdir(exist_ok=True)
    
    copied_files = []
    base_dir = Path("/app")  # Docker 容器中的路径
    
    # 要备份的配置文件
    config_files = [
        base_dir / ".env",
        base_dir / "docker-compose.yml",
        base_dir / "nginx" / "nginx.conf",
    ]
    
    for src in config_files:
        if src.exists():
            dst = config_dir / src.name
            shutil.copy2(src, dst)
            copied_files.append(str(dst))
    
    return {
        "success": True,
        "files": copied_files,
    }


@shared_task(
    name="app.tasks.backup_task.cleanup_old_backups",
    queue="maintenance",
)
def cleanup_old_backups() -> dict:
    """清理旧备份"""
    logger.info("开始清理旧备份")
    
    backup_path = Path(settings.backup_storage_path)
    retention_days = settings.backup_retention_days
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    deleted = []
    
    for item in backup_path.iterdir():
        if item.is_dir():
            # 尝试从目录名解析日期
            try:
                dir_date = datetime.strptime(item.name[:8], "%Y%m%d")
                if dir_date < cutoff_date:
                    shutil.rmtree(item)
                    deleted.append(str(item))
                    logger.info(f"删除旧备份: {item}")
            except ValueError:
                continue
    
    return {
        "success": True,
        "deleted_count": len(deleted),
        "deleted": deleted,
    }
