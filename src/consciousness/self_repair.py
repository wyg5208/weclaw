"""
自我修复引擎核心模块

WinClaw 意识系统 - Phase 3: Self-Repair Engine

功能概述：
- 统筹调度健康检查、诊断、修复执行
- 管理修复流程和状态
- 与审批接口集成
- 记录修复历史

架构设计：
    HealthMonitor → DiagnosisEngine → RepairExecutor
         ↓              ↓                    ↓
    BackupManager ← SelfRepairEngine → ApprovalInterface

作者：WinClaw Consciousness Team
版本：v0.3.0 (Phase 3)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
from pathlib import Path

from .types import (
    SelfDiagnosis,
    RepairAction,
    EvolutionRecord,
    RepairLevel
)
from .health_monitor import HealthMonitor
from .diagnosis_engine import DiagnosisEngine
from .repair_executor import RepairExecutor
from .backup_manager import BackupManager

logger = logging.getLogger(__name__)


class SelfRepairEngine:
    """
    自我修复引擎
    
    核心职责：
    1. 定期健康检查调度
    2. 问题诊断和修复方案制定
    3. 修复执行和验证
    4. 备份和回滚管理
    5. 修复历史记录
    """
    
    def __init__(
        self,
        system_root: str,
        auto_repair: bool = False,
        max_repair_attempts: int = 3,
        backup_enabled: bool = True
    ):
        """
        初始化自我修复引擎
        
        Args:
            system_root: 系统根目录
            auto_repair: 是否启用自动修复（需要审批）
            max_repair_attempts: 最大修复尝试次数
            backup_enabled: 是否启用备份
        """
        self.system_root = Path(system_root)
        self.auto_repair = auto_repair
        self.max_repair_attempts = max_repair_attempts
        self.backup_enabled = backup_enabled
        
        # 子组件初始化
        self.health_monitor = HealthMonitor(self)
        self.diagnosis_engine = DiagnosisEngine()
        self.repair_executor = RepairExecutor(self.system_root)
        self.backup_manager = BackupManager(self.system_root) if backup_enabled else None
        
        # 状态管理
        self.is_running = False
        self.current_diagnosis: Optional[SelfDiagnosis] = None
        self.repair_history: List[EvolutionRecord] = []
        self.active_repairs: Dict[str, RepairAction] = {}
        
        # 统计信息
        self.stats = {
            "total_diagnoses": 0,
            "total_repairs": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "rollbacks_performed": 0
        }
        
        logger.info("自我修复引擎初始化完成")
    
    async def start_health_monitoring(
        self,
        interval_seconds: int = 300,
        components: Optional[List[str]] = None
    ):
        """
        启动健康监测
        
        Args:
            interval_seconds: 检查间隔（秒）
            components: 要监测的组件列表
        """
        logger.info(f"启动健康监测，间隔：{interval_seconds}秒")
        self.is_running = True
        
        while self.is_running:
            try:
                # 执行健康检查
                health_report = await self.health_monitor.check_all_components(components)
                
                # 检查是否有问题
                if health_report.critical_issues or health_report.warnings:
                    logger.warning(
                        f"发现 {len(health_report.critical_issues)} 个严重问题，"
                        f"{len(health_report.warnings)} 个警告"
                    )
                    
                    # 自动诊断
                    for issue in health_report.critical_issues:
                        await self.diagnose_and_repair(issue)
                
                # 等待下次检查
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"健康监测失败：{e}")
                await asyncio.sleep(interval_seconds)
    
    def stop_health_monitoring(self):
        """停止健康监测"""
        logger.info("停止健康监测")
        self.is_running = False
    
    async def diagnose_and_repair(
        self,
        issue_description: str,
        max_attempts: Optional[int] = None
    ) -> Optional[EvolutionRecord]:
        """
        诊断问题并尝试修复
        
        Args:
            issue_description: 问题描述
            max_attempts: 最大尝试次数
            
        Returns:
            进化记录（如果修复成功）
        """
        attempts = 0
        max_att = max_attempts or self.max_repair_attempts
        
        while attempts < max_att:
            try:
                # 1. 诊断问题
                diagnosis = await self.diagnosis_engine.analyze(
                    issue_description,
                    self.system_root
                )
                
                self.stats["total_diagnoses"] += 1
                self.current_diagnosis = diagnosis
                
                logger.info(
                    f"诊断完成：{diagnosis.issue_type}, "
                    f"严重程度：{diagnosis.severity}, "
                    f"可自动修复：{diagnosis.auto_fixable}"
                )
                
                # 2. 判断是否需要修复
                if not diagnosis.suggested_fix:
                    logger.warning("无法生成修复方案")
                    return None
                
                # 3. 创建修复动作
                repair_action = self._create_repair_action(diagnosis)
                
                # 4. 是否需要审批
                if diagnosis.requires_approval:
                    logger.info("修复需要人类审批")
                    # TODO: 调用审批接口
                    # approved = await approval_interface.request_approval(repair_action)
                    # if not approved:
                    #     return None
                    logger.warning("审批功能尚未集成，跳过自动修复")
                    return None
                
                # 5. 执行修复
                if not diagnosis.auto_fixable:
                    logger.info("需要人工干预的修复")
                    return None
                
                # 6. 创建备份（如果需要）
                backup_id = None
                if self.backup_enabled and diagnosis.repair_level in [
                    RepairLevel.BEHAVIOR_FIX,
                    RepairLevel.CAPABILITY_OPT,
                    RepairLevel.CORE_EVOLUTION
                ]:
                    backup_id = await self.backup_manager.create_snapshot(
                        f"pre_repair_{diagnosis.issue_type}"
                    )
                    logger.info(f"创建备份：{backup_id}")
                
                # 7. 执行修复
                success = await self.repair_executor.execute(repair_action)
                
                if success:
                    logger.info("修复成功")
                    self.stats["successful_repairs"] += 1
                    
                    # 8. 验证修复效果
                    verified = await self._verify_repair(diagnosis)
                    
                    if verified:
                        # 9. 记录进化
                        evolution = self._record_evolution(
                            diagnosis,
                            repair_action,
                            backup_id
                        )
                        
                        self.repair_history.append(evolution)
                        self.stats["total_repairs"] += 1
                        
                        return evolution
                    else:
                        logger.warning("修复效果验证失败，尝试回滚")
                        await self._rollback_if_needed(backup_id)
                
                else:
                    logger.error("修复执行失败")
                    self.stats["failed_repairs"] += 1
                    await self._rollback_if_needed(backup_id)
                
                attempts += 1
                
            except Exception as e:
                logger.error(f"诊断修复过程失败 (尝试 {attempts + 1}/{max_att}): {e}")
                attempts += 1
        
        logger.error(f"达到最大尝试次数 {max_att}，放弃修复")
        return None
    
    def _create_repair_action(self, diagnosis: SelfDiagnosis) -> RepairAction:
        """
        根据诊断结果创建修复动作
        
        Args:
            diagnosis: 诊断结果
            
        Returns:
            修复动作
        """
        import uuid
        
        action_id = f"repair_{uuid.uuid4().hex[:8]}"
        
        return RepairAction(
            action_id=action_id,
            level=diagnosis.repair_level,
            target_component=diagnosis.affected_component,
            action_type="modify",  # TODO: 根据诊断结果确定具体类型
            before_state={"issue": diagnosis.root_cause},
            after_state={"fix": diagnosis.suggested_fix},
            approval_status="pending" if diagnosis.requires_approval else "approved"
        )
    
    async def _verify_repair(self, diagnosis: SelfDiagnosis) -> bool:
        """
        验证修复效果
        
        Args:
            diagnosis: 诊断结果
            
        Returns:
            验证是否通过
        """
        logger.info("验证修复效果...")
        
        # 重新检查受影响组件
        health_report = await self.health_monitor.check_component(
            diagnosis.affected_component
        )
        
        # 检查问题是否解决
        issue_resolved = not any(
            issue.description == diagnosis.root_cause
            for issue in health_report.critical_issues
        )
        
        if issue_resolved:
            logger.info("修复效果验证通过")
            return True
        else:
            logger.warning("修复效果验证未通过")
            return False
    
    async def _rollback_if_needed(self, backup_id: Optional[str]):
        """
        必要时回滚到备份状态
        
        Args:
            backup_id: 备份 ID
        """
        if backup_id and self.backup_enabled:
            logger.info(f"执行回滚：{backup_id}")
            await self.backup_manager.restore_snapshot(backup_id)
            self.stats["rollbacks_performed"] += 1
    
    def _record_evolution(
        self,
        diagnosis: SelfDiagnosis,
        repair_action: RepairAction,
        backup_id: Optional[str]
    ) -> EvolutionRecord:
        """
        记录进化历史
        
        Args:
            diagnosis: 诊断结果
            repair_action: 修复动作
            backup_id: 备份 ID
            
        Returns:
            进化记录
        """
        import uuid
        
        # 计算当前进化代数
        generation = len(self.repair_history) + 1
        
        # 获取性能指标（前后对比）
        performance_before = {"issues": 1}
        performance_after = {"issues": 0}
        
        return EvolutionRecord(
            evolution_id=f"evo_{uuid.uuid4().hex[:8]}",
            generation=generation,
            changes=[repair_action],
            performance_before=performance_before,
            performance_after=performance_after,
            human_approved=not diagnosis.requires_approval
        )
    
    def get_repair_history(
        self,
        limit: int = 10,
        component: Optional[str] = None
    ) -> List[EvolutionRecord]:
        """
        获取修复历史
        
        Args:
            limit: 返回数量限制
            component: 组件过滤器
            
        Returns:
            进化记录列表
        """
        history = self.repair_history[-limit:]
        
        if component:
            history = [
                record for record in history
                if any(
                    change.target_component == component
                    for change in record.changes
                )
            ]
        
        return history
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        return self.stats.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            字典数据
        """
        return {
            "is_running": self.is_running,
            "auto_repair": self.auto_repair,
            "stats": self.stats,
            "total_history": len(self.repair_history),
            "active_repairs": len(self.active_repairs)
        }
