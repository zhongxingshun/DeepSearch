"""
文档解析任务
版本: v1.0

使用 kreuzberg 进行文档文本提取
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from app.config import settings

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.parse_task.parse_document",
    queue="low",
    max_retries=3,
    default_retry_delay=60,
)
def parse_document(
    self,
    file_id: int,
    file_path: str,
    file_type: str,
) -> dict:
    """
    解析文档并提取文本
    
    Args:
        file_id: 文件 ID
        file_path: 文件相对路径
        file_type: 文件类型
        
    Returns:
        解析结果
    """
    logger.info(f"开始解析文档: file_id={file_id}, path={file_path}")
    
    try:
        # 构建完整路径
        full_path = Path(settings.file_storage_path) / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"文件不存在: {full_path}")
        
        # 提取文本
        content = extract_text(full_path, file_type)
        
        logger.info(f"文档解析完成: file_id={file_id}, 内容长度={len(content)}")
        
        # 更新数据库状态
        update_file_status(file_id, "parsed")
        
        # 触发索引任务
        from app.tasks.index_task import index_document
        index_document.delay(
            file_id=file_id,
            content=content,
        )
        
        return {
            "success": True,
            "file_id": file_id,
            "content_length": len(content),
            "message": "解析成功，已触发索引任务",
        }
        
    except Exception as e:
        logger.error(f"文档解析失败: file_id={file_id}, error={str(e)}")
        update_file_status(file_id, "failed", str(e))
        
        # 重试
        raise self.retry(exc=e)


def extract_text(file_path: Path, file_type: str) -> str:
    """
    提取文档文本
    
    使用 kreuzberg 库进行文本提取。
    如果常规提取结果太少（疑似图片型文档），自动启用 OCR。
    对于图片类型，直接走 OCR 路径。
    """
    # 图片文件：直接走 OCR 路径（kreuzberg 对纯图片无法提取文本）
    if file_type == "image":
        logger.info(f"图片文件，直接启用 OCR 提取文字: {file_path.name}")
        try:
            content = _paddleocr_file(str(file_path))
            if content and content.strip():
                logger.info(f"图片 OCR 完成: {file_path.name}, 提取 {len(content)} 字符")
                return content.strip()
            else:
                logger.info(f"图片 OCR 未识别到文字: {file_path.name}")
                return ""
        except Exception as e:
            logger.warning(f"图片 OCR 失败: {file_path.name}, {e}")
            return ""
    
    try:
        import asyncio
        import kreuzberg
        
        # 第一阶段：常规文本提取
        result = asyncio.run(kreuzberg.extract_file(str(file_path)))
        
        content = ""
        if result and result.content:
            content = result.content.strip()
        
        # 检查内容是否足够丰富
        # 剔除 markdown 图片引用 ![...](...)、空白、标点后统计真正的文字量
        import re
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', content)       # 去除图片引用
        clean_text = re.sub(r'[#*_\-=|>\[\](){}]', '', clean_text) # 去除 markdown 符号
        clean_text = re.sub(r'\s+', '', clean_text)                 # 去除空白
        meaningful_chars = len(clean_text)
        
        if meaningful_chars < 50 and file_type in ("pdf", "powerpoint"):
            logger.info(f"常规提取有效内容过少({meaningful_chars}字符)，启用 OCR: {file_path.name}")
            ocr_content = _extract_with_ocr(file_path, file_type)
            if ocr_content:
                # 同样对 OCR 结果做清洗统计
                ocr_clean = re.sub(r'!\[.*?\]\(.*?\)', '', ocr_content)
                ocr_clean = re.sub(r'\s+', '', ocr_clean)
                if len(ocr_clean) > meaningful_chars:
                    content = ocr_content.strip()
                    logger.info(f"OCR 提取完成: {len(content)} 字符")
        
        return content
        
    except ImportError:
        logger.warning("kreuzberg 未安装，使用备用提取方法")
        return fallback_extract(file_path, file_type)
    except Exception as e:
        logger.warning(f"kreuzberg 提取失败: {e}, 使用备用方法")
        return fallback_extract(file_path, file_type)


def _extract_with_ocr(file_path: Path, file_type: str) -> str:
    """使用 PaddleOCR 从图片型文档中提取文本"""
    extension = file_path.suffix.lower()
    
    # Office 文档（PPTX/DOCX/XLSX）：解压提取图片后逐张 OCR
    if extension in (".pptx", ".docx", ".xlsx", ".ppt", ".doc"):
        return _ocr_office_images(file_path)
    
    # 图片文件：直接用 PaddleOCR 识别
    if extension in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
        logger.info(f"图片文件启用 OCR: {file_path.name}")
        try:
            return _paddleocr_file(str(file_path))
        except Exception as e:
            logger.warning(f"图片 OCR 失败: {file_path.name}, {e}")
            return ""
    
    # PDF：直接用 PaddleOCR（不走 kreuzberg，避免它额外加载 server 重模型占 2G 内存）
    if extension == ".pdf":
        try:
            return _paddleocr_file(str(file_path))
        except Exception as e:
            logger.warning(f"PDF PaddleOCR 失败: {e}")
            return ""
    
    # 其他格式回退
    try:
        return _paddleocr_file(str(file_path))
    except Exception as e:
        logger.warning(f"PaddleOCR 提取失败: {e}")
        return ""


# PaddleOCR 单例，避免重复初始化模型
_paddle_ocr_instance = None

def _get_paddleocr():
    """获取 PaddleOCR 单例（轻量版，节省内存）"""
    global _paddle_ocr_instance
    if _paddle_ocr_instance is None:
        import os
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        from paddleocr import PaddleOCR
        _paddle_ocr_instance = PaddleOCR(
            lang='ch',
            text_detection_model_name='PP-OCRv5_mobile_det',
            text_recognition_model_name='PP-OCRv5_mobile_rec',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PaddleOCR 初始化完成（PP-OCRv5 mobile）")
    return _paddle_ocr_instance


def _paddleocr_file(file_path: str) -> str:
    """用 PaddleOCR 直接识别单个图片/文件"""
    ocr = _get_paddleocr()
    results = ocr.predict(file_path)

    all_texts = []
    for res in results:
        if 'rec_texts' in res and res['rec_texts']:
            all_texts.extend(res['rec_texts'])

    return "\n".join(all_texts)


def _ocr_office_images(file_path: Path) -> str:
    """从 Office 文档中提取嵌入的图片并逐张 PaddleOCR"""
    import zipfile
    import tempfile
    
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}
    
    try:
        all_text = []
        
        with zipfile.ZipFile(file_path) as zf:
            image_entries = sorted([
                n for n in zf.namelist()
                if any(n.lower().endswith(ext) for ext in image_extensions)
                and ("media/" in n or "image" in n.lower())
            ])
            
            if not image_entries:
                logger.info(f"Office 文档中未找到图片: {file_path.name}")
                return ""
            
            logger.info(f"Office 文档中发现 {len(image_entries)} 张图片，开始 PaddleOCR")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                for img_name in image_entries:
                    try:
                        img_data = zf.read(img_name)
                        
                        # 跳过太小的图片（图标等）
                        if len(img_data) < 10240:  # < 10KB
                            continue
                        
                        img_path = Path(tmpdir) / Path(img_name).name
                        img_path.write_bytes(img_data)
                        
                        text = _paddleocr_file(str(img_path))
                        if text and text.strip():
                            all_text.append(text.strip())
                        
                    except Exception as e:
                        logger.debug(f"OCR 单张图片失败: {img_name}, {e}")
                        continue
        
        combined = "\n\n".join(all_text)
        logger.info(f"Office 图片 OCR 完成: 提取 {len(all_text)} 张图片，共 {len(combined)} 字符")
        return combined
        
    except Exception as e:
        logger.warning(f"Office 图片 OCR 失败: {e}")
        return ""


def fallback_extract(file_path: Path, file_type: str) -> str:
    """备用文本提取方法"""
    extension = file_path.suffix.lower()
    
    # 纯文本文件
    if extension in [".txt", ".md", ".csv", ".log"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            pass
    
    # PDF 文件
    if extension == ".pdf":
        try:
            import subprocess
            result = subprocess.run(
                ["pdftotext", "-layout", str(file_path), "-"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
    
    # Office 文档 (使用 LibreOffice)
    if extension in [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
        try:
            import subprocess
            import tempfile
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # 转换为 PDF
                subprocess.run(
                    [
                        "soffice",
                        "--headless",
                        "--convert-to", "txt:Text",
                        "--outdir", tmpdir,
                        str(file_path),
                    ],
                    capture_output=True,
                    timeout=300,
                )
                
                # 读取转换后的文本
                txt_file = Path(tmpdir) / f"{file_path.stem}.txt"
                if txt_file.exists():
                    with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read()
        except Exception:
            pass
    
    return ""


def update_file_status(
    file_id: int,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """更新文件状态"""
    from sqlalchemy import text
    from app.tasks.db_engine import sync_engine
    
    # 使用共享同步引擎
    engine = sync_engine
    
    with engine.connect() as conn:
        if error_message:
            conn.execute(
                text("""
                    UPDATE files 
                    SET index_status = :status, updated_at = NOW()
                    WHERE id = :file_id
                """),
                {"status": status, "file_id": file_id}
            )
            
            # 更新任务错误信息
            conn.execute(
                text("""
                    UPDATE tasks 
                    SET status = 'failed', error_message = :error, completed_at = NOW()
                    WHERE file_id = :file_id AND status != 'completed'
                """),
                {"error": error_message, "file_id": file_id}
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
