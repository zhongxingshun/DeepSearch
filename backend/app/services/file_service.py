"""
文件管理服务模块
版本: v1.0
"""

import logging
from datetime import datetime
from pathlib import PurePosixPath
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from fastapi import UploadFile
from sqlalchemy import delete, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.file import File
from app.models.task import Task
from app.services.file_storage_service import FileStorageService, file_storage
from app.services.meilisearch_client import meili_client

logger = logging.getLogger(__name__)


class FileService:
    """文件管理服务"""

    def __init__(self, db: AsyncSession, storage: Optional[FileStorageService] = None):
        self.db = db
        self.storage = storage or file_storage

    @staticmethod
    def normalize_folder_path(folder_path: str) -> str:
        """规范化文件夹路径"""
        return FileStorageService.normalize_folder_path(folder_path)

    @staticmethod
    def _folder_name(path: str) -> str:
        if path == "/":
            return "根目录"
        return PurePosixPath(path).name or path

    @staticmethod
    def normalize_source_url(source_url: Optional[str]) -> Optional[str]:
        """规范化源链接"""
        if source_url is None:
            return None

        normalized = source_url.strip()
        if not normalized:
            return None

        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("源链接必须是合法的 http/https 地址")

        return normalized

    @staticmethod
    def validate_name(name: str, label: str) -> str:
        """校验文件名/文件夹名"""
        normalized = (name or "").strip()
        if not normalized:
            raise ValueError(f"{label}不能为空")
        if normalized in {".", ".."}:
            raise ValueError(f"{label}不合法")
        invalid_chars = {"/", "\\", "\0"}
        if any(char in normalized for char in invalid_chars):
            raise ValueError(f"{label}不能包含 / 或 \\")
        return normalized

    @staticmethod
    def join_folder_with_name(folder_path: str, name: str) -> str:
        """拼接文件夹路径和名称"""
        normalized_folder = FileService.normalize_folder_path(folder_path)
        if normalized_folder == "/":
            return f"/{name}"
        return f"{normalized_folder}/{name}"

    async def _sync_file_to_search_index(self, file: File) -> None:
        """将最新文件元数据同步到搜索索引。"""
        doc_id = file.meilisearch_id or file.md5_hash or f"file_{file.id}"
        try:
            existing_doc = await meili_client.get_document(doc_id)
        except Exception as exc:
            logger.warning("读取 Meilisearch 文档失败，file_id=%s, error=%s", file.id, exc)
            return

        if not existing_doc:
            return

        document = dict(existing_doc)
        document.update(
            {
                "id": doc_id,
                "file_id": file.id,
                "filename": file.filename,
                "file_type": file.file_type,
                "file_size": file.file_size,
                "file_path": file.file_path,
                "folder_path": file.folder_path,
                "uploaded_by": file.uploaded_by,
                "created_at": file.created_at.isoformat() if file.created_at else None,
            }
        )
        await meili_client.update_document(document)

    @staticmethod
    def _collect_ancestor_paths(path: str) -> list[str]:
        normalized = FileService.normalize_folder_path(path)
        if normalized == "/":
            return ["/"]

        parts = [part for part in normalized.split("/") if part]
        ancestors = ["/"]
        for idx in range(len(parts)):
            ancestors.append("/" + "/".join(parts[: idx + 1]))
        return ancestors

    async def _folder_file_counts(self) -> dict[str, int]:
        result = await self.db.execute(
            select(File.folder_path, func.count(File.id).label("cnt"))
            .group_by(File.folder_path)
            .order_by(File.folder_path)
        )

        counts: dict[str, int] = {"/": 0}
        for path, count in result.all():
            normalized = self.normalize_folder_path(path)
            for ancestor in self._collect_ancestor_paths(normalized):
                counts[ancestor] = counts.get(ancestor, 0) + count
        return counts

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
            folder_path = self.normalize_folder_path(target_folder)
        elif "/" in file.filename:
            folder_part = file.filename.rsplit("/", 1)[0]
            folder_path = self.normalize_folder_path(folder_part)
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

        task: Optional[Task] = None

        if file_type == "archive":
            db_file.index_status = "processing"
            task = Task(
                file_id=db_file.id,
                task_type="index",
                priority="low",
                status="pending",
            )
            self.db.add(task)
            await self.db.commit()
            await self.db.refresh(db_file)

            try:
                from app.tasks.index_task import index_document

                celery_result = index_document.delay(
                    file_id=db_file.id,
                    content="",
                )
                task.celery_task_id = celery_result.id
                await self.db.commit()
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(f"压缩包索引任务发送失败: {e}")

            return db_file, is_duplicate, task.celery_task_id

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

    async def retry_file_processing(self, file_id: int) -> str:
        """重新提交文件解析任务。"""
        file = await self.get_file_by_id(file_id)
        if not file:
            raise ValueError("文件不存在")

        full_path = await self.storage.get_file(file.file_path)
        if not full_path:
            raise ValueError("源文件不存在，无法重新上传")

        file.index_status = "pending"
        file.meilisearch_id = None

        task = Task(
            file_id=file.id,
            task_type="parse",
            priority="low",
            status="pending",
        )
        self.db.add(task)
        await self.db.flush()

        try:
            from app.tasks.parse_task import parse_document

            celery_result = parse_document.delay(
                file_id=file.id,
                file_path=file.file_path,
                file_type=file.file_type,
            )
            task.celery_task_id = celery_result.id
            await self.db.commit()
            return celery_result.id
        except Exception as exc:
            task.status = "failed"
            task.error_message = f"任务提交失败: {exc}"
            await self.db.commit()
            raise ValueError("重新上传任务提交失败") from exc

    async def _delete_file_records(self, file_ids: list[int]) -> tuple[list[int], list[int]]:
        """显式删除任务和文件记录，避免触发 ORM 关系加载。"""
        unique_ids = list(dict.fromkeys(file_ids))
        if not unique_ids:
            return [], []

        result = await self.db.execute(
            select(File.id, File.file_path).where(File.id.in_(unique_ids))
        )
        rows = result.all()

        existing_map = {row.id: row.file_path for row in rows}
        deleted_ids = [file_id for file_id in unique_ids if file_id in existing_map]
        missing_ids = [file_id for file_id in unique_ids if file_id not in existing_map]

        for file_id in deleted_ids:
            await self.storage.delete_file(existing_map[file_id])

        await self.db.execute(delete(Task).where(Task.file_id.in_(deleted_ids)))
        await self.db.execute(delete(File).where(File.id.in_(deleted_ids)))
        await self.db.commit()

        return deleted_ids, missing_ids

    async def delete_file(self, file_id: int) -> bool:
        """删除文件（包括存储和数据库记录）"""
        deleted_ids, _ = await self._delete_file_records([file_id])
        return bool(deleted_ids)

    async def delete_files(self, file_ids: list[int]) -> dict:
        """批量删除文件"""
        deleted_ids, missing_ids = await self._delete_file_records(file_ids)

        return {
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "missing_ids": missing_ids,
        }

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
        counts = await self._folder_file_counts()
        all_paths = set(counts.keys()) | set(self.storage.list_virtual_folders())

        folders = []
        for path in sorted(all_paths):
            folders.append({
                "path": path,
                "name": self._folder_name(path),
                "file_count": counts.get(path, 0),
            })
        return folders

    async def move_file(self, file_id: int, target_folder: str) -> File:
        """移动文件到指定文件夹"""
        file = await self.get_file_by_id(file_id)
        if not file:
            raise ValueError("文件不存在")
        
        # 规范化目标文件夹路径
        target_folder = self.normalize_folder_path(target_folder)

        self.storage.create_virtual_folder(target_folder)
        
        file.folder_path = target_folder
        await self.db.flush()
        await self._sync_file_to_search_index(file)
        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def rename_file(self, file_id: int, new_filename: str) -> File:
        """在线重命名单个文件"""
        file = await self.get_file_by_id(file_id)
        if not file:
            raise ValueError("文件不存在")

        normalized_name = self.validate_name(new_filename, "文件名")
        if normalized_name == file.filename:
            return file

        existing = await self.db.execute(
            select(File.id).where(
                File.folder_path == file.folder_path,
                File.filename == normalized_name,
                File.id != file.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("同一文件夹下已存在同名文件")

        file.filename = normalized_name
        await self.db.flush()
        await self._sync_file_to_search_index(file)
        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def update_source_url(self, file_id: int, source_url: Optional[str]) -> File:
        """更新文件源链接"""
        file = await self.get_file_by_id(file_id)
        if not file:
            raise ValueError("文件不存在")

        file.source_url = self.normalize_source_url(source_url)
        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def get_subfolders(self, parent_path: str) -> list:
        """获取指定路径下的直接子文件夹"""
        normalized_parent = self.normalize_folder_path(parent_path)
        prefix = normalized_parent.rstrip("/") + "/" if normalized_parent != "/" else "/"
        counts = await self._folder_file_counts()
        all_paths = set(counts.keys()) | set(self.storage.list_virtual_folders())

        subfolders: dict[str, dict] = {}
        for path in all_paths:
            if path in {"/", normalized_parent} or not path.startswith(prefix):
                continue

            relative = path[len(prefix):]
            if not relative:
                continue

            direct_child = relative.split("/")[0]
            folder_full_path = prefix + direct_child
            subfolders[folder_full_path] = {
                "path": folder_full_path,
                "name": direct_child,
                "file_count": counts.get(folder_full_path, 0),
            }

        return sorted(subfolders.values(), key=lambda item: item["path"])

    async def create_folder(self, folder_path: str) -> dict:
        """创建空文件夹"""
        normalized = self.normalize_folder_path(folder_path)
        if normalized == "/":
            raise ValueError("根目录无需创建")

        self.storage.create_virtual_folder(normalized)
        return {
            "path": normalized,
            "name": self._folder_name(normalized),
            "file_count": 0,
        }

    async def rename_folder(self, folder_path: str, new_name: str) -> dict:
        """重命名文件夹并同步其下所有文件记录"""
        source_path = self.normalize_folder_path(folder_path)
        if source_path == "/":
            raise ValueError("根目录不允许重命名")

        normalized_name = self.validate_name(new_name, "文件夹名")
        parent_path = str(PurePosixPath(source_path).parent)
        parent_path = self.normalize_folder_path(parent_path)
        target_path = self.join_folder_with_name(parent_path, normalized_name)

        if target_path == source_path:
            return {
                "old_path": source_path,
                "path": target_path,
                "name": normalized_name,
            }

        all_folders = set(self.storage.list_virtual_folders())
        if source_path not in all_folders:
            file_count_result = await self.db.execute(
                select(func.count(File.id)).where(
                    (File.folder_path == source_path)
                    | (File.folder_path.like(f"{source_path}/%"))
                )
            )
            if not (file_count_result.scalar() or 0):
                raise ValueError("文件夹不存在")

        if target_path in all_folders:
            raise ValueError("同级目录下已存在同名文件夹")

        conflict_result = await self.db.execute(
            select(func.count(File.id)).where(
                (File.folder_path == target_path)
                | (File.folder_path.like(f"{target_path}/%"))
            )
        )
        if conflict_result.scalar() or 0:
            raise ValueError("同级目录下已存在同名文件夹")

        prefix = f"{source_path}/"
        file_result = await self.db.execute(
            select(File).where(
                (File.folder_path == source_path)
                | (File.folder_path.like(f"{source_path}/%"))
            )
        )
        files_to_update = list(file_result.scalars().all())

        for file in files_to_update:
            suffix = file.folder_path[len(source_path):]
            file.folder_path = target_path + suffix

        renamed_virtual_folder = False
        try:
            self.storage.rename_virtual_folder(source_path, target_path)
            renamed_virtual_folder = True
        except ValueError as exc:
            if str(exc) == "文件夹不存在":
                self.storage.create_virtual_folder(target_path)
            else:
                raise

        await self.db.flush()

        for file in files_to_update:
            await self._sync_file_to_search_index(file)

        await self.db.commit()

        return {
            "old_path": source_path,
            "path": target_path,
            "name": normalized_name,
            "renamed_virtual_folder": renamed_virtual_folder,
        }

    async def delete_folder(self, folder_path: str) -> None:
        """递归删除文件夹及其所有文件、子文件夹"""
        normalized = self.normalize_folder_path(folder_path)
        if normalized == "/":
            raise ValueError("根目录不允许删除")

        existing_files = await self.db.execute(
            select(File.id).where(
                (File.folder_path == normalized)
                | (File.folder_path.like(f"{normalized}/%"))
            )
        )
        file_ids = [file_id for file_id in existing_files.scalars().all()]
        if file_ids:
            await self._delete_file_records(file_ids)

        target_folders = [
            path for path in self.storage.list_virtual_folders()
            if path == normalized or path.startswith(f"{normalized}/")
        ]
        for path in sorted(target_folders, key=lambda item: item.count("/"), reverse=True):
            self.storage.delete_virtual_folder(path)

    async def get_folder_delete_summary(self, folder_path: str) -> dict:
        """获取删除文件夹前的影响范围统计"""
        normalized = self.normalize_folder_path(folder_path)
        if normalized == "/":
            raise ValueError("根目录不允许删除")

        file_count_result = await self.db.execute(
            select(func.count(File.id)).where(
                (File.folder_path == normalized)
                | (File.folder_path.like(f"{normalized}/%"))
            )
        )
        file_count = file_count_result.scalar() or 0

        subfolder_count = len([
            path for path in self.storage.list_virtual_folders()
            if path.startswith(f"{normalized}/")
        ])

        return {
            "path": normalized,
            "file_count": file_count,
            "subfolder_count": subfolder_count,
        }
