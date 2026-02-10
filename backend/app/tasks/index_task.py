"""
索引更新任务
版本: v1.0

将解析后的文档内容索引到 Meilisearch
"""

from datetime import datetime
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import text

from app.config import settings
from app.tasks.db_engine import sync_engine

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.index_task.index_document",
    queue="low",
    max_retries=3,
    default_retry_delay=60,
)
def index_document(
    self,
    file_id: int,
    content: str,
) -> dict:
    """
    索引文档到 Meilisearch
    
    Args:
        file_id: 文件 ID
        content: 提取的文本内容
        
    Returns:
        索引结果
    """
    logger.info(f"开始索引文档: file_id={file_id}")
    
    try:
        # 获取文件信息
        file_info = get_file_info(file_id)
        if not file_info:
            raise ValueError(f"文件不存在: {file_id}")
        
        # 更新状态为处理中
        update_file_status(file_id, "processing")
        
        # 对内容进行中文分词增强
        content_segmented = ""
        try:
            from app.services.meilisearch_client import MeilisearchClient
            content_segmented = MeilisearchClient.chinese_segment(content)
        except Exception as e:
            logger.warning(f"中文分词失败: {e}")
            content_segmented = content
        
        # 准备文档数据
        doc_id = file_info["md5_hash"] or f"file_{file_id}"
        document = {
            "id": doc_id,
            "file_id": file_id,
            "filename": file_info["filename"],
            "content": content,
            "content_segmented": content_segmented,
            "file_type": file_info["file_type"],
            "file_size": file_info["file_size"],
            "file_path": file_info["file_path"],
            "uploaded_by": file_info["uploaded_by"],
            "created_at": file_info["created_at"],
        }
        
        # 添加到 Meilisearch
        import meilisearch
        
        client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
        index = client.index("documents")
        
        task = index.add_documents([document])
        
        logger.info(f"文档已添加到索引: file_id={file_id}, task_uid={task.task_uid}")
        
        # 更新状态为完成
        update_file_status(file_id, "completed", meilisearch_id=doc_id)
        update_task_status(file_id, "completed")
        
        return {
            "success": True,
            "file_id": file_id,
            "doc_id": doc_id,
            "task_uid": task.task_uid,
            "message": "索引成功",
        }
        
    except Exception as e:
        logger.error(f"索引失败: file_id={file_id}, error={str(e)}")
        update_file_status(file_id, "failed")
        update_task_status(file_id, "failed", str(e))
        
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="app.tasks.index_task.delete_document",
    queue="low",
)
def delete_document(self, doc_id: str) -> dict:
    """
    从 Meilisearch 删除文档
    """
    logger.info(f"删除索引文档: doc_id={doc_id}")
    
    try:
        import meilisearch
        
        client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
        index = client.index("documents")
        
        task = index.delete_document(doc_id)
        
        return {
            "success": True,
            "doc_id": doc_id,
            "task_uid": task.task_uid,
        }
        
    except Exception as e:
        logger.error(f"删除索引失败: doc_id={doc_id}, error={str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="app.tasks.index_task.reindex_all",
    queue="maintenance",
)
def reindex_all(self) -> dict:
    """
    重新索引所有文档
    """
    logger.info("开始重新索引所有文档")
    
    engine = sync_engine
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM files WHERE index_status = 'completed'")
        )
        rows = result.fetchall()
    
    count = 0
    for row in rows:
        from app.tasks.parse_task import parse_document
        parse_document.delay(
            file_id=row[0],
            file_path="",  # 将从数据库获取
            file_type="",
        )
        count += 1
    
    return {
        "success": True,
        "message": f"已触发 {count} 个文档的重新索引",
    }


def get_file_info(file_id: int) -> Optional[dict]:
    """获取文件信息"""
    engine = sync_engine
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, filename, file_path, file_type, file_size, 
                       md5_hash, uploaded_by, created_at
                FROM files WHERE id = :file_id
            """),
            {"file_id": file_id}
        )
        row = result.fetchone()
        
        if row:
            return {
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "file_type": row[3],
                "file_size": row[4],
                "md5_hash": row[5],
                "uploaded_by": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
            }
    
    return None


def update_file_status(
    file_id: int,
    status: str,
    meilisearch_id: Optional[str] = None
) -> None:
    """更新文件状态"""
    engine = sync_engine
    
    with engine.connect() as conn:
        if meilisearch_id:
            conn.execute(
                text("""
                    UPDATE files 
                    SET index_status = :status, meilisearch_id = :meili_id, updated_at = NOW()
                    WHERE id = :file_id
                """),
                {"status": status, "meili_id": meilisearch_id, "file_id": file_id}
            )
        else:
            conn.execute(
                text("""
                    UPDATE files 
                    SET index_status = :status, updated_at = NOW()
                    WHERE id = :file_id
                """),
                {"status": status, "file_id": file_id}
            )
        conn.commit()


def update_task_status(
    file_id: int,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """更新任务状态"""
    engine = sync_engine
    
    with engine.connect() as conn:
        if error_message:
            conn.execute(
                text("""
                    UPDATE tasks 
                    SET status = :status, error_message = :error, 
                        completed_at = NOW()
                    WHERE file_id = :file_id AND status != 'completed'
                """),
                {"status": status, "error": error_message, "file_id": file_id}
            )
        else:
            conn.execute(
                text("""
                    UPDATE tasks 
                    SET status = :status, completed_at = NOW()
                    WHERE file_id = :file_id AND status != 'completed'
                """),
                {"status": status, "file_id": file_id}
            )
        conn.commit()
