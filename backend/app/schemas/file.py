"""
文件 Schema 定义
版本: v1.0
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FileBase(BaseModel):
    """文件基础模型"""

    filename: str = Field(..., description="文件名")


class FileCreate(FileBase):
    """创建文件记录"""

    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型")
    md5_hash: Optional[str] = Field(None, description="MD5 哈希")


class FileResponse(FileBase):
    """文件响应"""

    id: int
    file_path: str
    folder_path: str = "/"
    display_name: str = ""
    uploaded_by: Optional[int]
    file_size: int
    file_size_human: str
    file_type: str
    source_url: Optional[str] = None
    md5_hash: Optional[str]
    index_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """文件列表响应"""

    success: bool = True
    data: list[FileResponse]
    total: int
    page: int
    page_size: int


class FileStatusResponse(BaseModel):
    """文件状态响应"""

    id: int
    filename: str
    index_status: str  # pending, processing, completed, failed
    error_message: Optional[str] = None
    updated_at: str  # ISO 格式字符串


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    success: bool = True
    message: str = "文件上传成功"
    file_id: int
    filename: str
    md5_hash: str
    is_duplicate: bool = False
    task_id: Optional[str] = None


class FileMoveRequest(BaseModel):
    """文件移动请求"""
    target_folder: str = Field(..., description="目标文件夹路径")


class FileRenameRequest(BaseModel):
    """文件重命名请求"""
    filename: str = Field(..., min_length=1, max_length=255, description="新的文件名")


class FileSourceUrlUpdateRequest(BaseModel):
    """文件源链接更新请求"""
    source_url: Optional[str] = Field(None, description="源链接，可为空")


class FolderInfo(BaseModel):
    """文件夹信息"""
    path: str
    name: str
    file_count: int
    children: List['FolderInfo'] = []


class FolderListResponse(BaseModel):
    """文件夹列表响应"""
    success: bool = True
    folders: List[FolderInfo]
    current_path: str = "/"


class FolderCreateRequest(BaseModel):
    """创建文件夹请求"""
    path: str = Field(..., description="文件夹路径")


class FolderRenameRequest(BaseModel):
    """重命名文件夹请求"""
    path: str = Field(..., description="当前文件夹路径")
    new_name: str = Field(..., min_length=1, max_length=100, description="新的文件夹名称")


class FileBatchDeleteRequest(BaseModel):
    """批量删除文件请求"""
    file_ids: List[int] = Field(..., min_length=1, description="待删除的文件 ID 列表")
