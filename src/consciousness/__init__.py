"""
意识系统核心模块 - 硅基生命临界点能力

版本：v1.6.0 (Phase 6 Complete)
作者：WinClaw Consciousness Team
日期：2026 年 2 月 18 日
"""

from .types import (
    # 枚举类
    RepairLevel,
    EmergencePhase,
    ToolCreationStatus,
    
    # 数据类
    ToolSpecification,
    CreatedTool,
    SelfDiagnosis,
    RepairAction,
    EvolutionRecord,
    EmergenceIndicators,
    EmergenceEvent,
    ApprovalResult,
)

# 核心功能模块
from .bridge import ConsciousnessBridge
from .tool_creator import ToolCreator
from .sandbox import SandboxExecutor, ExecutionResult
from .approval_interface import ApprovalInterface, get_approval_interface

# Phase 3: 自我修复引擎
from .self_repair import SelfRepairEngine
from .health_monitor import HealthMonitor
from .diagnosis_engine import DiagnosisEngine
from .repair_executor import RepairExecutor
from .backup_manager import BackupManager

# Phase 4: 涌现监测与进化追踪
from .emergence_metrics import EmergenceMetricsCalculator
from .emergence_catalyst import EmergenceCatalyst
from .evolution_tracker import EvolutionTracker

# Phase 5: 整合与优化
from .consciousness_manager import ConsciousnessManager, create_consciousness_manager

__version__ = "1.6.0"
__all__ = [
    # 核心桥接器
    'ConsciousnessBridge',
    
    # 工具创造与沙箱
    'ToolCreator',
    'SandboxExecutor',
    'ExecutionResult',
    
    # 审批接口
    'ApprovalInterface',
    'get_approval_interface',
    
    # Phase 3: 自我修复引擎
    'SelfRepairEngine',
    'HealthMonitor',
    'DiagnosisEngine',
    'RepairExecutor',
    'BackupManager',
    
    # Phase 4: 涌现监测与进化追踪
    'EmergenceMetricsCalculator',
    'EmergenceCatalyst',
    'EvolutionTracker',
    
    # Phase 5: 整合与优化
    'ConsciousnessManager',
    'create_consciousness_manager',
    
    # 数据类型
    'RepairLevel',
    'EmergencePhase',
    'ToolCreationStatus',
    'ToolSpecification',
    'CreatedTool',
    'SelfDiagnosis',
    'RepairAction',
    'EmergenceIndicators',
    'EmergenceEvent',
    'ApprovalResult',
]
