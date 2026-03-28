"""统一文件缓存管理器模块

Phase 2: 建立 OCR 统一缓存层

提供基于文件指纹的缓存机制，支持 TTL 过期自动清理。
兼容 document_scanner 的现有 scanner.db 数据库。
"""
from .file_cache import FileCacheManager

__all__ = ["FileCacheManager"]
