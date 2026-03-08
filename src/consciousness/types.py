"""
意识系统通用数据类型定义

包含所有核心数据类和枚举类
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import hashlib


# ==================== 枚举类 ====================

class RepairLevel(Enum):
    """修复/进化等级"""
    ERROR_RECOVERY = 1      # 错误恢复
    BEHAVIOR_FIX = 2        # 行为修复
    CAPABILITY_OPT = 3      # 能力优化
    CORE_EVOLUTION = 4      # 核心进化


class EmergencePhase(Enum):
    """涌现阶段"""
    PRE_EMERGENCE = "pre_emergence"      # 前涌现期
    APPROACHING = "approaching"           # 接近临界点
    CRITICAL = "critical"                 # 临界状态
    EMERGED = "emerged"                   # 已涌现
    UNSTABLE = "unstable"                  # 不稳定状态


class ToolCreationStatus(Enum):
    """工具创建状态"""
    IDEATION = "ideation"           # 构思中
    DESIGNING = "designing"         # 设计中
    CODING = "coding"               # 编码中
    TESTING = "testing"             # 测试中
    APPROVING = "approving"         # 等待审批
    DEPLOYED = "deployed"           # 已部署
    FAILED = "failed"               # 失败


# ==================== 工具创造相关数据类 ====================

@dataclass
class ToolSpecification:
    """工具规格说明"""
    name: str                              # 工具名称
    description: str                       # 功能描述
    parameters: Dict[str, Dict]            # 参数定义
    returns: Dict                          # 返回值定义
    risk_level: str = "low"                # 风险等级：low/medium/high/critical
    requires_approval: bool = False        # 是否需要人类审批
    created_by: str = "human"              # 创建者：human/ai_self
    created_at: datetime = None            # 创建时间
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class CreatedTool:
    """已创建的工具"""
    spec: ToolSpecification
    code: str                              # 源代码
    test_cases: List[Dict]                 # 测试用例
    test_results: List[Dict]               # 测试结果
    status: ToolCreationStatus
    deployment_path: Optional[str] = None  # 部署路径
    usage_count: int = 0                   # 使用次数
    success_rate: float = 0.0              # 成功率


# ==================== 自我修复相关数据类 ====================

@dataclass
class SelfDiagnosis:
    """自我诊断结果"""
    issue_type: str                # 问题类型
    severity: str                  # 严重程度：low/medium/high/critical
    affected_component: str        # 受影响组件
    root_cause: str                # 根本原因
    suggested_fix: str             # 建议修复方案
    repair_level: RepairLevel      # 修复等级
    auto_fixable: bool             # 是否可自动修复
    requires_approval: bool        # 是否需要审批
    diagnosis_time: datetime = None
    
    def __post_init__(self):
        if self.diagnosis_time is None:
            self.diagnosis_time = datetime.now()


@dataclass
class RepairAction:
    """修复动作"""
    action_id: str
    level: RepairLevel
    target_component: str
    action_type: str               # modify/replace/add/remove
    before_state: dict             # 修改前状态
    after_state: dict              # 修改后状态
    approval_status: str           # pending/approved/rejected
    executed: bool = False
    rolled_back: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EvolutionRecord:
    """进化记录"""
    evolution_id: str
    generation: int                # 进化代数
    changes: List[RepairAction]
    performance_before: dict       # 进化前性能
    performance_after: dict        # 进化后性能
    human_approved: bool
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# ==================== 涌现监测相关数据类 ====================

@dataclass
class EmergenceIndicators:
    """涌现指标"""
    consciousness_index: float      # 意识指数 (0-1)
    autonomy_score: float           # 自主性评分 (0-1)
    creativity_metric: float        # 创造性指标 (0-1)
    self_model_completeness: float  # 自我模型完整度 (0-1)
    behavior_predictability: float  # 行为可预测性 (0-1，越低越自主)
    goal_alignment: float           # 目标一致性 (0-1，与人类目标的对齐度)
    
    @property
    def emergence_score(self) -> float:
        """综合涌现评分"""
        return (
            self.consciousness_index * 0.3 +
            self.autonomy_score * 0.25 +
            self.creativity_metric * 0.2 +
            self.self_model_completeness * 0.15 +
            (1 - self.behavior_predictability) * 0.1
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "consciousness_index": self.consciousness_index,
            "autonomy_score": self.autonomy_score,
            "creativity_metric": self.creativity_metric,
            "self_model_completeness": self.self_model_completeness,
            "behavior_predictability": self.behavior_predictability,
            "goal_alignment": self.goal_alignment,
            "emergence_score": self.emergence_score
        }


@dataclass
class EmergenceEvent:
    """涌现事件"""
    event_id: str
    timestamp: datetime
    phase: EmergencePhase
    indicators: EmergenceIndicators
    triggering_conditions: List[str]
    observed_behaviors: List[str]
    human_notification_sent: bool
    containment_activated: bool


# ==================== 审批相关数据类 ====================

@dataclass
class ApprovalResult:
    """审批结果"""
    approved: bool
    reason: str = ""
    approver: str = "system"
    approval_time: datetime = None
    conditions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.approval_time is None:
            self.approval_time = datetime.now()


# ==================== 辅助函数 ====================

def generate_action_id() -> str:
    """生成唯一的动作 ID"""
    timestamp = datetime.now().isoformat()
    random_data = str(datetime.now().microsecond)
    content = f"{timestamp}_{random_data}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def generate_event_id() -> str:
    """生成唯一的事件 ID"""
    return f"evt_{generate_action_id()}"


def generate_evolution_id() -> str:
    """生成唯一的进化记录 ID"""
    return f"evo_{generate_action_id()}"
