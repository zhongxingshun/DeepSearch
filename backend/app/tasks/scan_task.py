"""
目录扫描任务
版本: v1.0

扫描指定目录，发现新文件并创建处理任务
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Set

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import text

from app.config import settings
from app.tasks.db_engine import sync_engine

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.scan_task.scan_directory",
    queue="low",
    max_retries=3,
)
def scan_directory(
    self,
    directory: str = None,
    recursive: bool = True,
) -> dict:
    """
    扫描目录寻找新文件
    
    Args:
        directory: 要扫描的目录（默认为配置的存储目录）
        recursive: 是否递归扫描子目录
        
    Returns:
        扫描结果
    """
    scan_path = directory or settings.file_storage_path
    logger.info(f"开始扫描目录: {scan_path}")
    
    try:
        # 获取已存在的 MD5 列表
        existing_md5s = get_existing_md5s()
        
        # 扫描文件
        new_files = []
        scanned_count = 0
        
        for file_path in scan_files(scan_path, recursive):
            scanned_count += 1
            
            # 检查扩展名
            if not is_allowed_extension(file_path):
                continue
            
            # 计算 MD5
            file_md5 = calculate_md5(file_path)
            
            # 检查是否已存在
            if file_md5 in existing_md5s:
                continue
            
            new_files.append({
                "path": str(file_path),
                "md5": file_md5,
                "size": file_path.stat().st_size,
            })
        
        logger.info(f"扫描完成: 扫描 {scanned_count} 个文件，发现 {len(new_files)} 个新文件")
        
        # 处理新文件
        processed = 0
        for file_info in new_files:
            success = process_new_file(file_info)
            if success:
                processed += 1
        
        return {
            "success": True,
            "scanned_count": scanned_count,
            "new_files_count": len(new_files),
            "processed_count": processed,
            "message": f"扫描完成，处理了 {processed} 个新文件",
        }
        
    except Exception as e:
        logger.error(f"目录扫描失败: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="app.tasks.scan_task.scan_external_source",
    queue="low",
)
def scan_external_source(
    self,
    source_path: str,
    copy_to_storage: bool = True,
) -> dict:
    """
    扫描外部数据源（如 NAS）
    
    Args:
        source_path: 外部源路径
        copy_to_storage: 是否复制到本地存储
        
    Returns:
        扫描结果
    """
    logger.info(f"开始扫描外部源: {source_path}")
    
    if not os.path.exists(source_path):
        return {
            "success": False,
            "error": f"路径不存在: {source_path}",
        }
    
    # 调用目录扫描
    result = scan_directory.s(
        directory=source_path,
        recursive=True,
    ).apply()
    
    return result.get()


def scan_files(directory: str, recursive: bool = True) -> List[Path]:
    """生成目录中的文件列表"""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return []
    
    files = []
    
    if recursive:
        for root, dirs, filenames in os.walk(dir_path):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            
            for filename in filenames:
                if not filename.startswith("."):
                    files.append(Path(root) / filename)
    else:
        for item in dir_path.iterdir():
            if item.is_file() and not item.name.startswith("."):
                files.append(item)
    
    return files


def get_existing_md5s() -> Set[str]:
    """获取数据库中已存在的 MD5 列表"""
    engine = sync_engine
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT md5_hash FROM files WHERE md5_hash IS NOT NULL")
        )
        return {row[0] for row in result.fetchall()}


def is_allowed_extension(file_path: Path) -> bool:
    """检查文件扩展名是否允许"""
    ext = file_path.suffix.lower().lstrip(".")
    return ext in settings.allowed_extensions


def calculate_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """计算文件 MD5"""
    md5_hash = hashlib.md5()
    
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
    
    return md5_hash.hexdigest()


def process_new_file(file_info: dict) -> bool:
    """处理新发现的文件"""
    try:
        file_path = Path(file_info["path"])
        
        # 确定文件类型
        ext = file_path.suffix.lower().lstrip(".")
        file_type = get_file_type(ext)
        
        # 计算存储路径
        md5_hash = file_info["md5"]
        bucket = md5_hash[:2]
        storage_filename = f"{md5_hash}.{ext}"
        relative_path = f"{bucket}/{storage_filename}"
        
        # 复制到存储目录
        storage_path = Path(settings.file_storage_path) / relative_path
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not storage_path.exists():
            import shutil
            shutil.copy2(file_path, storage_path)
        
        # 创建数据库记录
        engine = sync_engine
        
        with engine.connect() as conn:
            # 插入文件记录
            result = conn.execute(
                text("""
                    INSERT INTO files (filename, file_path, file_size, file_type, md5_hash, index_status)
                    VALUES (:filename, :file_path, :file_size, :file_type, :md5_hash, 'pending')
                    ON CONFLICT (md5_hash) DO NOTHING
                    RETURNING id
                """),
                {
                    "filename": file_path.name,
                    "file_path": relative_path,
                    "file_size": file_info["size"],
                    "file_type": file_type,
                    "md5_hash": md5_hash,
                }
            )
            row = result.fetchone()
            
            if row:
                file_id = row[0]
                
                # 创建解析任务
                conn.execute(
                    text("""
                        INSERT INTO tasks (file_id, task_type, priority, status)
                        VALUES (:file_id, 'parse', 'low', 'pending')
                    """),
                    {"file_id": file_id}
                )
                
                conn.commit()
                
                # 触发解析任务
                from app.tasks.parse_task import parse_document
                parse_document.delay(
                    file_id=file_id,
                    file_path=relative_path,
                    file_type=file_type,
                )
                
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"处理文件失败: {file_info['path']}, error={str(e)}")
        return False


def get_file_type(extension: str) -> str:
    """根据扩展名获取文件类型"""
    type_mapping = {
        "pdf": "pdf",
        "doc": "word", "docx": "word",
        "xls": "excel", "xlsx": "excel",
        "ppt": "powerpoint", "pptx": "powerpoint",
        "txt": "text", "md": "markdown", "csv": "csv",
        "jpg": "image", "jpeg": "image", "png": "image",
        "gif": "image", "bmp": "image", "tiff": "image",
    }
    return type_mapping.get(extension.lower(), "other")
