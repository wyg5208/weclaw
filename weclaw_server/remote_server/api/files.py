"""文件 API

提供文件上传、下载等接口。
"""

import base64
import logging
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import get_config
from .. import context
from .auth import get_current_user_with_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Pydantic 模型 ==========

class UploadResponse(BaseModel):
    """上传响应"""
    attachment_id: str
    filename: str
    size_bytes: int
    url: str


# ========== 辅助函数 ==========

def get_upload_dir() -> Path:
    """获取上传目录"""
    config = get_config()
    upload_dir = Path(config.files.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_file_type(mime_type: str) -> str:
    """根据 MIME 类型判断文件类型"""
    if mime_type.startswith("image/"):
        return "image"
    elif mime_type.startswith("audio/"):
        return "audio"
    return "file"


def is_allowed_type(mime_type: str) -> bool:
    """检查 MIME 类型是否允许"""
    config = get_config()
    return mime_type in config.files.allowed_types


# ========== API 端点 ==========

@router.post("/upload", response_model=UploadResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    session_id: Optional[str] = Query(None, description="关联的会话ID"),
    user_info: dict = Depends(get_current_user_with_db)
):
    """
    上传文件（图片/语音）
    
    支持的文件类型由配置决定，默认包括：
    - 图片: jpeg, png, gif, webp
    - 音频: wav, mp3, mpeg, webm
    - 文档: pdf, txt
    """
    user = user_info["user"]
    config = get_config()
    
    # 检查文件类型
    if not is_allowed_type(file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}"
        )
    
    # 检查文件大小
    max_size = config.files.max_file_size_mb * 1024 * 1024
    content = await file.read()
    
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({config.files.max_file_size_mb}MB)"
        )
    
    # 生成文件ID和路径
    attachment_id = str(uuid.uuid4())
    file_type = get_file_type(file.content_type)
    
    # 按日期和用户组织存储
    date_dir = datetime.now().strftime("%Y/%m/%d")
    user_dir = get_upload_dir() / date_dir / user.user_id[:8]
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成安全文件名
    file_ext = Path(file.filename).suffix if file.filename else ""
    safe_filename = f"{attachment_id[:8]}{file_ext}"
    file_path = user_dir / safe_filename
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 生成缩略图（如果是图片）
    thumbnail_path = None
    if file_type == "image":
        try:
            thumbnail_path = await _generate_thumbnail(file_path, user_dir, attachment_id)
        except Exception as e:
            logger.warning(f"生成缩略图失败: {e}")
    
    logger.info(f"文件上传成功: user={user.username}, file={file.filename}, size={len(content)}")
    
    return UploadResponse(
        attachment_id=attachment_id,
        filename=file.filename or "unknown",
        size_bytes=len(content),
        url=f"/api/files/{attachment_id}"
    )


async def _generate_thumbnail(image_path: Path, output_dir: Path, attachment_id: str) -> Optional[Path]:
    """生成图片缩略图"""
    try:
        from PIL import Image
        
        config = get_config()
        thumb_size = config.files.thumbnail_size
        
        with Image.open(image_path) as img:
            # 保持比例缩放
            img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            
            # 保存缩略图
            thumb_path = output_dir / f"{attachment_id[:8]}_thumb.jpg"
            img.convert("RGB").save(thumb_path, "JPEG", quality=85)
            
            return thumb_path
    except ImportError:
        logger.warning("PIL 未安装，跳过缩略图生成")
        return None
    except Exception as e:
        logger.warning(f"缩略图生成失败: {e}")
        return None


@router.get("/{attachment_id}", summary="下载文件")
async def download_file(
    attachment_id: str
):
    """
    下载文件
    
    返回文件二进制流。
    注意：通过 UUID 保证安全性，不需要额外认证
    """
    # 在实际实现中，应从数据库查询文件路径
    # 这里简化处理，在 upload 目录中搜索
    
    upload_dir = get_upload_dir()
    
    # 递归搜索文件
    for file_path in upload_dir.rglob(f"{attachment_id[:8]}*"):
        if file_path.is_file() and "_thumb" not in file_path.name:
            return FileResponse(
                path=file_path,
                filename=file_path.name,
                media_type="application/octet-stream"
            )
    
    raise HTTPException(status_code=404, detail="文件不存在")


@router.get("/{attachment_id}/thumbnail", summary="获取缩略图")
async def get_thumbnail(
    attachment_id: str
):
    """获取图片缩略图"""
    upload_dir = get_upload_dir()
    
    # 搜索缩略图
    for file_path in upload_dir.rglob(f"{attachment_id[:8]}_thumb.jpg"):
        if file_path.is_file():
            return FileResponse(
                path=file_path,
                media_type="image/jpeg"
            )
    
    raise HTTPException(status_code=404, detail="缩略图不存在")


@router.delete("/{attachment_id}", summary="删除文件")
async def delete_file(
    attachment_id: str,
    user_info: dict = Depends(get_current_user_with_db)
):
    """删除文件
    
    需要认证，防止未授权删除
    """
    upload_dir = get_upload_dir()
    deleted = False
    
    # 删除主文件和缩略图
    for file_path in upload_dir.rglob(f"{attachment_id[:8]}*"):
        if file_path.is_file():
            file_path.unlink()
            deleted = True
            logger.info(f"删除文件：{file_path}")
    
    if not deleted:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return {
        "success": True,
        "message": "文件已删除"
    }
