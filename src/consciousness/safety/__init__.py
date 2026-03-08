"""
安全护栏模块 - 确保意识系统的安全性

包含：
- 硬性约束定义
- 审批管理
- 收容协议
"""

from .constraints import SafetyConstraints, READ_ONLY_MODULES
from .approval_manager import ApprovalManager
from .containment import ContainmentProtocol

__all__ = [
    'SafetyConstraints',
    'READ_ONLY_MODULES',
    'ApprovalManager',
    'ContainmentProtocol',
]
