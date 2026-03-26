"""
文件存储服务模块
版本: v1.0
"""

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

import aiofiles
import aiofiles.os
from fastapi import UploadFile

from app.config import settings


class FileStorageService:
    """文件存储服务 - 基于 MD5 分桶策略"""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.file_storage_path)
        self.virtual_folder_root = self.base_path / ".folders"
        self._ensure_base_directories()

    def _ensure_base_directories(self) -> None:
        """确保基础目录存在（256个分桶目录）"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.virtual_folder_root.mkdir(parents=True, exist_ok=True)
        # 创建 00-ff 共 256 个子目录
        for i in range(256):
            bucket = f"{i:02x}"
            (self.base_path / bucket).mkdir(exist_ok=True)

    @staticmethod
    def normalize_folder_path(folder_path: str) -> str:
        """规范化虚拟文件夹路径"""
        cleaned = (folder_path or "").strip()
        if not cleaned:
            return "/"
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned
        cleaned = cleaned.rstrip("/")
        return cleaned or "/"

    def get_virtual_folder_disk_path(self, folder_path: str) -> Path:
        """获取虚拟文件夹在磁盘上的路径"""
        normalized = self.normalize_folder_path(folder_path)
        if normalized == "/":
            return self.virtual_folder_root
        relative_parts = [part for part in normalized.split("/") if part]
        return self.virtual_folder_root.joinpath(*relative_parts)

    def create_virtual_folder(self, folder_path: str) -> str:
        """创建虚拟文件夹"""
        normalized = self.normalize_folder_path(folder_path)
        self.get_virtual_folder_disk_path(normalized).mkdir(parents=True, exist_ok=True)
        return normalized

    def delete_virtual_folder(self, folder_path: str) -> None:
        """删除虚拟文件夹（仅空目录）"""
        normalized = self.normalize_folder_path(folder_path)
        if normalized == "/":
            raise ValueError("根目录不允许删除")

        disk_path = self.get_virtual_folder_disk_path(normalized)
        if not disk_path.exists():
            raise ValueError("文件夹不存在")
        if any(disk_path.iterdir()):
            raise ValueError("文件夹非空，无法删除")

        disk_path.rmdir()

    def list_virtual_folders(self) -> list[str]:
        """列出所有虚拟文件夹路径"""
        folders: list[str] = []
        if not self.virtual_folder_root.exists():
            return folders

        for path in self.virtual_folder_root.rglob("*"):
            if path.is_dir():
                relative = path.relative_to(self.virtual_folder_root).as_posix()
                folders.append("/" + relative if relative != "." else "/")

        return sorted(set(folders))

    @staticmethod
    def calculate_md5(file: BinaryIO, chunk_size: int = 8192) -> str:
        """
        流式计算文件 MD5
        
        Args:
            file: 文件对象
            chunk_size: 读取块大小
            
        Returns:
            MD5 哈希值（32位小写）
        """
        md5_hash = hashlib.md5()
        while chunk := file.read(chunk_size):
            md5_hash.update(chunk)
        file.seek(0)  # 重置文件指针
        return md5_hash.hexdigest()

    @staticmethod
    async def calculate_md5_async(
        file: UploadFile,
        chunk_size: int = 8192
    ) -> str:
        """
        异步流式计算文件 MD5
        
        Args:
            file: FastAPI UploadFile 对象
            chunk_size: 读取块大小
            
        Returns:
            MD5 哈希值
        """
        md5_hash = hashlib.md5()
        await file.seek(0)
        while chunk := await file.read(chunk_size):
            md5_hash.update(chunk)
        await file.seek(0)
        return md5_hash.hexdigest()

    def get_bucket(self, md5_hash: str) -> str:
        """获取文件的存储桶名称（MD5 前两位）"""
        return md5_hash[:2].lower()

    def get_storage_path(self, md5_hash: str, extension: str) -> Path:
        """
        获取文件的完整存储路径
        
        Args:
            md5_hash: 文件 MD5
            extension: 文件扩展名
            
        Returns:
            完整存储路径
        """
        bucket = self.get_bucket(md5_hash)
        filename = f"{md5_hash}.{extension.lower()}"
        return self.base_path / bucket / filename

    def get_relative_path(self, md5_hash: str, extension: str) -> str:
        """获取相对存储路径"""
        bucket = self.get_bucket(md5_hash)
        filename = f"{md5_hash}.{extension.lower()}"
        return f"{bucket}/{filename}"

    async def file_exists(self, md5_hash: str, extension: str) -> bool:
        """检查文件是否已存在（用于去重）"""
        path = self.get_storage_path(md5_hash, extension)
        return await aiofiles.os.path.exists(path)

    async def save_file(
        self,
        file: UploadFile,
        md5_hash: Optional[str] = None,
    ) -> Tuple[str, str, int, bool]:
        """
        保存上传的文件
        
        Args:
            file: FastAPI UploadFile 对象
            md5_hash: 预计算的 MD5（可选）
            
        Returns:
            (md5_hash, file_path, file_size, is_duplicate)
        """
        # 计算 MD5
        if md5_hash is None:
            md5_hash = await self.calculate_md5_async(file)
        
        # 获取扩展名
        extension = self._get_extension(file.filename or "unknown")
        
        # 检查是否已存在（去重）
        storage_path = self.get_storage_path(md5_hash, extension)
        is_duplicate = await aiofiles.os.path.exists(storage_path)
        
        if is_duplicate:
            # 文件已存在，获取大小
            stat = await aiofiles.os.stat(storage_path)
            file_size = stat.st_size
        else:
            # 保存新文件
            file_size = await self._save_to_disk(file, storage_path)
        
        relative_path = self.get_relative_path(md5_hash, extension)
        
        return md5_hash, relative_path, file_size, is_duplicate

    async def _save_to_disk(
        self,
        file: UploadFile,
        target_path: Path,
        chunk_size: int = 65536
    ) -> int:
        """将文件保存到磁盘"""
        await file.seek(0)
        total_size = 0
        
        async with aiofiles.open(target_path, "wb") as f:
            while chunk := await file.read(chunk_size):
                await f.write(chunk)
                total_size += len(chunk)
        
        return total_size

    async def get_file(self, file_path: str) -> Optional[Path]:
        """
        获取文件的完整路径
        
        Args:
            file_path: 相对存储路径
            
        Returns:
            完整路径，不存在则返回 None
        """
        full_path = self.base_path / file_path
        if await aiofiles.os.path.exists(full_path):
            return full_path
        return None

    async def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 相对存储路径
            
        Returns:
            是否删除成功
        """
        full_path = self.base_path / file_path
        try:
            if await aiofiles.os.path.exists(full_path):
                await aiofiles.os.remove(full_path)
                return True
        except Exception:
            pass
        return False

    async def get_file_size(self, file_path: str) -> Optional[int]:
        """获取文件大小"""
        full_path = self.base_path / file_path
        try:
            if await aiofiles.os.path.exists(full_path):
                stat = await aiofiles.os.stat(full_path)
                return stat.st_size
        except Exception:
            pass
        return None

    @staticmethod
    def _get_extension(filename: str) -> str:
        """提取文件扩展名"""
        if "." in filename:
            return filename.rsplit(".", 1)[1].lower()
        return "bin"

    @staticmethod
    def get_file_type(filename: str) -> str:
        """根据文件名获取文件类型"""
        ext = FileStorageService._get_extension(filename)
        type_mapping = {
            # 文档
            "pdf": "pdf",
            "doc": "word",
            "docx": "word",
            "xls": "excel",
            "xlsx": "excel",
            "ppt": "powerpoint",
            "pptx": "powerpoint",
            "txt": "text",
            "md": "markdown",
            "csv": "csv",
            "rtf": "richtext",
            # 图片
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gif": "image",
            "bmp": "image",
            "tiff": "image",
            "tif": "image",
            "zip": "archive",
            "rar": "archive",
        }
        return type_mapping.get(ext, "other")

    def validate_extension(self, filename: str) -> bool:
        """验证文件扩展名是否允许"""
        ext = self._get_extension(filename)
        return ext in settings.allowed_extensions

    def validate_file_size(self, size: int) -> bool:
        """验证文件大小是否允许"""
        return size <= settings.max_upload_size


# 全局实例
file_storage = FileStorageService()
