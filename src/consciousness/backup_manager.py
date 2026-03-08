"""
备份管理器

WinClaw 意识系统 - Phase 3: Backup Manager

功能概述：
- 创建系统状态快照
- 管理备份文件
- 执行回滚操作
- 清理过期备份

备份策略：
1. 修复前备份 - 在执行修复前自动创建
2. 定期备份 - 按固定时间间隔创建
3. 事件触发备份 - 重大变更时创建
4. 增量备份 - 只备份变化的部分

作者：WinClaw Consciousness Team
版本：v0.3.0 (Phase 3)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
import shutil
import tarfile
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
    """
    备份管理器
    
    职责：
    1. 创建备份快照
    2. 存储和管理备份
    3. 恢复备份
    4. 清理过期备份
    """
    
    def __init__(
        self,
        system_root: Path,
        backup_dir: Optional[Path] = None,
        max_backups: int = 10,
        auto_cleanup: bool = True
    ):
        """
        初始化备份管理器
        
        Args:
            system_root: 系统根目录
            backup_dir: 备份存储目录（默认在系统根目录下）
            max_backups: 最大保留备份数量
            auto_cleanup: 是否自动清理过期备份
        """
        self.system_root = system_root
        self.backup_dir = backup_dir or (system_root / "backups")
        self.max_backups = max_backups
        self.auto_cleanup = auto_cleanup
        
        # 确保备份目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份元数据
        self.backups: Dict[str, Dict] = {}
        self._load_metadata()
        
        logger.info(f"备份管理器初始化完成，备份目录：{self.backup_dir}")
    
    async def create_snapshot(
        self,
        name: Optional[str] = None,
        paths: Optional[List[Path]] = None,
        description: str = ""
    ) -> str:
        """
        创建系统快照
        
        Args:
            name: 备份名称（可选，默认使用时间戳）
            paths: 要备份的路径列表（None 表示备份关键目录）
            description: 备份描述
            
        Returns:
            备份 ID
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = name or f"backup_{timestamp}"
        
        logger.info(f"开始创建备份：{backup_id}")
        
        try:
            # 确定要备份的路径
            if paths is None:
                paths = self._get_critical_paths()
            
            # 创建备份压缩包
            backup_file = self.backup_dir / f"{backup_id}.tar.gz"
            
            await self._create_archive(backup_file, paths)
            
            # 记录元数据
            metadata = {
                "backup_id": backup_id,
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "description": description,
                "paths": [str(p) for p in paths],
                "size_bytes": backup_file.stat().st_size,
                "checksum": self._calculate_checksum(backup_file)
            }
            
            self.backups[backup_id] = metadata
            self._save_metadata()
            
            logger.info(
                f"备份创建成功：{backup_id}, "
                f"大小：{metadata['size_bytes'] / 1024:.1f}KB"
            )
            
            # 自动清理过期备份
            if self.auto_cleanup:
                await self.cleanup_old_backups()
            
            return backup_id
            
        except Exception as e:
            logger.error(f"创建备份失败：{e}")
            raise
    
    async def restore_snapshot(
        self,
        backup_id: str,
        verify: bool = True
    ) -> bool:
        """
        恢复系统快照
        
        Args:
            backup_id: 备份 ID
            verify: 是否验证备份完整性
            
        Returns:
            恢复是否成功
        """
        logger.info(f"开始恢复备份：{backup_id}")
        
        try:
            # 检查备份是否存在
            if backup_id not in self.backups:
                logger.error(f"备份不存在：{backup_id}")
                return False
            
            backup_file = self.backup_dir / f"{backup_id}.tar.gz"
            
            if not backup_file.exists():
                logger.error(f"备份文件不存在：{backup_file}")
                return False
            
            # 验证备份完整性
            if verify:
                checksum = self._calculate_checksum(backup_file)
                if checksum != self.backups[backup_id]["checksum"]:
                    logger.error("备份文件校验失败")
                    return False
            
            # 创建临时备份（以防恢复失败）
            emergency_backup = await self.create_snapshot(
                name=f"emergency_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="恢复前的紧急备份"
            )
            
            logger.info(f"已创建紧急备份：{emergency_backup}")
            
            # 解压并恢复
            success = await self._extract_archive(backup_file)
            
            if success:
                logger.info(f"备份恢复成功：{backup_id}")
                
                # 删除紧急备份（如果恢复成功）
                await self.delete_backup(emergency_backup)
                
                return True
            else:
                logger.error("备份恢复失败")
                
                # 尝试回滚到紧急备份
                logger.warning("尝试回滚到紧急备份...")
                await self.restore_snapshot(emergency_backup, verify=False)
                
                return False
            
        except Exception as e:
            logger.error(f"恢复备份失败：{e}")
            return False
    
    async def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            删除是否成功
        """
        try:
            if backup_id not in self.backups:
                logger.warning(f"备份不存在，无法删除：{backup_id}")
                return False
            
            backup_file = self.backup_dir / f"{backup_id}.tar.gz"
            
            if backup_file.exists():
                backup_file.unlink()
                logger.debug(f"已删除备份文件：{backup_file}")
            
            # 从元数据中移除
            del self.backups[backup_id]
            self._save_metadata()
            
            logger.info(f"已删除备份：{backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除备份失败：{e}")
            return False
    
    async def cleanup_old_backups(
        self,
        keep_count: Optional[int] = None
    ) -> int:
        """
        清理旧备份
        
        Args:
            keep_count: 保留的备份数量（None 使用默认值）
            
        Returns:
            删除的备份数量
        """
        keep = keep_count or self.max_backups
        
        if len(self.backups) <= keep:
            logger.debug("无需清理备份")
            return 0
        
        # 按时间排序
        sorted_backups = sorted(
            self.backups.items(),
            key=lambda x: x[1]["created_at"],
            reverse=True
        )
        
        # 删除多余的备份
        deleted_count = 0
        for backup_id, _ in sorted_backups[keep:]:
            if await self.delete_backup(backup_id):
                deleted_count += 1
        
        logger.info(f"清理了 {deleted_count} 个旧备份")
        return deleted_count
    
    async def list_backups(
        self,
        limit: int = 10,
        include_details: bool = True
    ) -> List[Dict]:
        """
        列出备份
        
        Args:
            limit: 返回数量限制
            include_details: 是否包含详细信息
            
        Returns:
            备份列表
        """
        # 按时间倒序排列
        sorted_backups = sorted(
            self.backups.values(),
            key=lambda x: x["created_at"],
            reverse=True
        )
        
        backups_list = sorted_backups[:limit]
        
        if not include_details:
            # 只返回基本信息
            return [
                {
                    "backup_id": b["backup_id"],
                    "created_at": b["created_at"],
                    "description": b["description"]
                }
                for b in backups_list
            ]
        
        return backups_list
    
    async def get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """
        获取备份详细信息
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            备份信息
        """
        return self.backups.get(backup_id)
    
    def _get_critical_paths(self) -> List[Path]:
        """获取关键路径列表"""
        critical_paths = [
            self.system_root / "src" / "consciousness",
            self.system_root / "config",
            self.system_root / ".env"
        ]
        
        # 过滤掉不存在的路径
        return [p for p in critical_paths if p.exists()]
    
    async def _create_archive(self, archive_path: Path, paths: List[Path]):
        """
        创建压缩归档
        
        Args:
            archive_path: 归档文件路径
            paths: 要归档的路径列表
        """
        def _compress():
            with tarfile.open(archive_path, "w:gz") as tar:
                for path in paths:
                    if path.exists():
                        # 使用相对路径
                        arcname = path.relative_to(self.system_root)
                        tar.add(path, arcname=arcname)
        
        await asyncio.to_thread(_compress)
    
    async def _extract_archive(self, archive_path: Path) -> bool:
        """
        解压归档
        
        Args:
            archive_path: 归档文件路径
            
        Returns:
            解压是否成功
        """
        def _decompress():
            try:
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(path=self.system_root)
                return True
            except Exception as e:
                logger.error(f"解压失败：{e}")
                return False
        
        return await asyncio.to_thread(_decompress)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        计算文件校验和
        
        Args:
            file_path: 文件路径
            
        Returns:
            MD5 校验和
        """
        import hashlib
        
        hash_md5 = hashlib.md5()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def _load_metadata(self):
        """加载备份元数据"""
        metadata_file = self.backup_dir / "backups.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.backups = json.load(f)
                logger.debug(f"已加载 {len(self.backups)} 个备份元数据")
            except Exception as e:
                logger.error(f"加载备份元数据失败：{e}")
                self.backups = {}
        else:
            self.backups = {}
    
    def _save_metadata(self):
        """保存备份元数据"""
        metadata_file = self.backup_dir / "backups.json"
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.backups, f, indent=2, ensure_ascii=False)
            logger.debug("已保存备份元数据")
        except Exception as e:
            logger.error(f"保存备份元数据失败：{e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        total_size = sum(
            b.get("size_bytes", 0) for b in self.backups.values()
        )
        
        return {
            "total_backups": len(self.backups),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / 1024 / 1024,
            "max_backups": self.max_backups,
            "backup_directory": str(self.backup_dir)
        }
