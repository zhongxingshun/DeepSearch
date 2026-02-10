"""
文件管理服务模块
版本: v1.0
"""

from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.file import File
from app.models.task import Task
from app.services.file_storage_service import FileStorageService, file_storage


class FileService:
    """文件管理服务"""

    def __init__(self, db: AsyncSession, storage: Optional[FileStorageService] = None):
        self.db = db
        self.storage = storage or file_storage

    async def upload_file(
        self,
        file: UploadFile,
        user_id: int,
        target_folder: Optional[str] = None,
    ) -> Tuple[File, bool, Optional[str]]:
        """
        上传单个文件
        
        Args:
            file: 上传的文件
            user_id: 上传用户 ID
            target_folder: 指定目标文件夹（可选，优先使用）
            
        Returns:
            (文件记录, 是否重复, 任务ID)
        """
        # 验证文件名
        if not file.filename:
            raise ValueError("文件名不能为空")
        
        # 验证扩展名
        if not self.storage.validate_extension(file.filename):
            allowed = ", ".join(settings.allowed_extensions)
            raise ValueError(f"不支持的文件类型，允许的类型: {allowed}")
        
        # 保存文件到存储
        md5_hash, file_path, file_size, is_duplicate = await self.storage.save_file(file)
        
        # 验证文件大小
        if not self.storage.validate_file_size(file_size):
            max_size = settings.max_upload_size / (1024 * 1024)
            raise ValueError(f"文件大小超过限制 ({max_size:.0f}MB)")
        
        # 检查数据库中是否已有记录（基于 MD5）
        existing = await self.get_file_by_md5(md5_hash)
        if existing:
            return existing, True, None
        
        # 创建文件记录
        file_type = self.storage.get_file_type(file.filename)
        
        # 确定文件夹路径：优先使用指定的 target_folder
        if target_folder:
            folder_path = target_folder if target_folder.startswith("/") else "/" + target_folder
            folder_path = folder_path.rstrip("/") or "/"
        elif "/" in file.filename:
            folder_part = file.filename.rsplit("/", 1)[0]
            folder_path = "/" + folder_part if not folder_part.startswith("/") else folder_part
        else:
            folder_path = "/"
        
        db_file = File(
            filename=file.filename,
            file_path=file_path,
            folder_path=folder_path,
            uploaded_by=user_id,
            file_size=file_size,
            file_type=file_type,
            md5_hash=md5_hash,
            index_status="pending",
        )
        self.db.add(db_file)
        await self.db.flush()
        
        # 创建解析任务
        task = Task(
            file_id=db_file.id,
            task_type="parse",
            priority="low",
            status="pending",
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(db_file)
        
        # 发送 Celery 异步任务
        try:
            from app.tasks.parse_task import parse_document
            celery_result = parse_document.delay(
                file_id=db_file.id,
                file_path=db_file.file_path,
                file_type=db_file.file_type,
            )
            # 更新 celery_task_id
            task.celery_task_id = celery_result.id
            await self.db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Celery 任务发送失败: {e}")
        
        return db_file, is_duplicate, task.celery_task_id

    async def upload_files(
        self,
        files: List[UploadFile],
        user_id: int,
    ) -> List[dict]:
        """
        批量上传文件
        
        Args:
            files: 上传的文件列表
            user_id: 上传用户 ID
            
        Returns:
            上传结果列表
        """
        results = []
        for file in files:
            try:
                db_file, is_duplicate, task_id = await self.upload_file(file, user_id)
                results.append({
                    "success": True,
                    "filename": file.filename,
                    "file_id": db_file.id,
                    "md5_hash": db_file.md5_hash,
                    "is_duplicate": is_duplicate,
                    "task_id": task_id,
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "filename": file.filename,
                    "error": str(e),
                })
        
        return results

    async def get_file_by_id(self, file_id: int) -> Optional[File]:
        """根据 ID 获取文件"""
        result = await self.db.execute(
            select(File).where(File.id == file_id)
        )
        return result.scalar_one_or_none()

    async def get_file_by_md5(self, md5_hash: str) -> Optional[File]:
        """根据 MD5 获取文件"""
        result = await self.db.execute(
            select(File).where(File.md5_hash == md5_hash)
        )
        return result.scalar_one_or_none()

    async def get_files(
        self,
        page: int = 1,
        page_size: int = 20,
        file_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        folder_path: Optional[str] = None,
    ) -> Tuple[List[File], int]:
        """
        获取文件列表（分页）
        
        Args:
            page: 页码
            page_size: 每页数量
            file_type: 文件类型过滤
            status: 索引状态过滤
            keyword: 文件名关键词
            folder_path: 文件夹路径过滤
            
        Returns:
            (文件列表, 总数)
        """
        query = select(File)
        count_query = select(func.count(File.id))
        
        # 应用过滤条件
        if file_type:
            query = query.where(File.file_type == file_type)
            count_query = count_query.where(File.file_type == file_type)
        
        if status:
            query = query.where(File.index_status == status)
            count_query = count_query.where(File.index_status == status)
        
        if keyword:
            query = query.where(File.filename.ilike(f"%{keyword}%"))
            count_query = count_query.where(File.filename.ilike(f"%{keyword}%"))
        
        if folder_path:
            query = query.where(File.folder_path == folder_path)
            count_query = count_query.where(File.folder_path == folder_path)
        
        # 获取总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页和排序
        query = query.order_by(desc(File.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        files = list(result.scalars().all())
        
        return files, total

    async def get_file_path(self, file_id: int) -> Optional[str]:
        """获取文件的完整存储路径"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return None
        
        full_path = await self.storage.get_file(file.file_path)
        return str(full_path) if full_path else None

    async def get_file_status(self, file_id: int) -> Optional[dict]:
        """获取文件的索引状态"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return None
        
        # 获取最新的任务状态
        result = await self.db.execute(
            select(Task)
            .where(Task.file_id == file_id)
            .order_by(desc(Task.created_at))
            .limit(1)
        )
        task = result.scalar_one_or_none()
        
        return {
            "id": file.id,
            "filename": file.filename,
            "index_status": file.index_status,
            "meilisearch_id": file.meilisearch_id,
            "task_status": task.status if task else None,
            "task_error": task.error_message if task else None,
            "updated_at": file.updated_at.isoformat(),
        }

    async def delete_file(self, file_id: int) -> bool:
        """删除文件（包括存储和数据库记录）"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return False
        
        # 删除存储中的文件
        await self.storage.delete_file(file.file_path)
        
        # 删除数据库记录
        await self.db.delete(file)
        await self.db.commit()
        
        return True

    async def update_index_status(
        self,
        file_id: int,
        status: str,
        meilisearch_id: Optional[str] = None,
    ) -> bool:
        """更新文件索引状态"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return False
        
        file.index_status = status
        if meilisearch_id:
            file.meilisearch_id = meilisearch_id
        
        await self.db.commit()
        return True

    async def get_stats(self) -> dict:
        """获取文件统计信息"""
        # 总文件数
        total_result = await self.db.execute(select(func.count(File.id)))
        total = total_result.scalar() or 0
        
        # 总大小
        size_result = await self.db.execute(select(func.sum(File.file_size)))
        total_size = size_result.scalar() or 0
        
        # 按状态统计
        status_result = await self.db.execute(
            select(File.index_status, func.count(File.id))
            .group_by(File.index_status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}
        
        # 按类型统计
        type_result = await self.db.execute(
            select(File.file_type, func.count(File.id))
            .group_by(File.file_type)
        )
        type_counts = {row[0]: row[1] for row in type_result.all()}
        
        return {
            "total_files": total,
            "total_size": total_size,
            "total_size_human": self._format_size(total_size),
            "by_status": status_counts,
            "by_type": type_counts,
        }

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    async def get_folders(self) -> list:
        """获取所有文件夹路径及其文件数"""
        from sqlalchemy import distinct
        
        result = await self.db.execute(
            select(File.folder_path, func.count(File.id).label('cnt'))
            .group_by(File.folder_path)
            .order_by(File.folder_path)
        )
        rows = result.all()
        
        folders = []
        for path, count in rows:
            name = path.rsplit('/', 1)[-1] if '/' in path and path != '/' else path
            if path == '/':
                name = '根目录'
            folders.append({
                'path': path,
                'name': name,
                'file_count': count,
            })
        return folders

    async def move_file(self, file_id: int, target_folder: str) -> File:
        """移动文件到指定文件夹"""
        file = await self.get_file_by_id(file_id)
        if not file:
            raise ValueError("文件不存在")
        
        # 规范化目标文件夹路径
        if not target_folder.startswith('/'):
            target_folder = '/' + target_folder
        target_folder = target_folder.rstrip('/')
        if not target_folder:
            target_folder = '/'
        
        file.folder_path = target_folder
        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def get_subfolders(self, parent_path: str) -> list:
        """获取指定路径下的直接子文件夹"""
        prefix = parent_path.rstrip('/') + '/' if parent_path != '/' else '/'
        
        result = await self.db.execute(
            select(File.folder_path, func.count(File.id).label('cnt'))
            .where(File.folder_path.like(f'{prefix}%'))
            .group_by(File.folder_path)
            .order_by(File.folder_path)
        )
        rows = result.all()
        
        # 提取直接子文件夹（不包含更深层级）
        subfolders = {}
        for path, count in rows:
            # 取父路径后的第一个段
            relative = path[len(prefix):]
            if '/' in relative:
                direct_child = relative.split('/')[0]
            else:
                direct_child = relative
            
            if direct_child:
                folder_full_path = prefix + direct_child
                if folder_full_path not in subfolders:
                    subfolders[folder_full_path] = {'path': folder_full_path, 'name': direct_child, 'file_count': 0}
                subfolders[folder_full_path]['file_count'] += count
        
        return list(subfolders.values())
