"""
审批管理器 - 管理所有需要人类确认的操作
"""

from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from dataclasses import dataclass


@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    request_type: str          # tool_creation/evolution/repair/emergency
    description: str
    risk_level: str            # low/medium/high/critical
    details: dict
    submitted_at: datetime
    status: str = "pending"    # pending/approved/rejected
    decided_at: Optional[datetime] = None
    decision_by: Optional[str] = None
    decision_reason: Optional[str] = None


class ApprovalManager:
    """
    审批管理器
    
    负责收集、展示和记录所有需要人类审批的请求
    """
    
    def __init__(self):
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.decided_requests: Dict[str, ApprovalRequest] = {}
        self.approval_threshold = 0.5  # 默认审批阈值
        self.auto_approve_below = "low"  # 自动批准的风险等级
        
        # 回调函数
        self.on_request_submitted = None
        self.on_request_decided = None
        
    async def submit_request(
        self,
        request_type: str,
        description: str,
        risk_level: str,
        details: dict
    ) -> str:
        """提交审批请求"""
        import hashlib
        request_id = hashlib.md5(
            f"{request_type}_{description}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        request = ApprovalRequest(
            request_id=request_id,
            request_type=request_type,
            description=description,
            risk_level=risk_level,
            details=details,
            submitted_at=datetime.now()
        )
        
        self.pending_requests[request_id] = request
        
        # 触发回调通知 UI
        if self.on_request_submitted:
            await self.on_request_submitted(request)
            
        return request_id
        
    async def decide_request(
        self,
        request_id: str,
        approved: bool,
        decided_by: str = "human",
        reason: str = ""
    ) -> bool:
        """对请求做出决策"""
        if request_id not in self.pending_requests:
            return False
            
        request = self.pending_requests.pop(request_id)
        request.status = "approved" if approved else "rejected"
        request.decided_at = datetime.now()
        request.decision_by = decided_by
        request.decision_reason = reason
        
        self.decided_requests[request_id] = request
        
        # 触发回调
        if self.on_request_decided:
            await self.on_request_decided(request)
            
        return True
        
    async def check_auto_approval(self, risk_level: str) -> bool:
        """检查是否可以自动审批"""
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        
        if risk_order.get(risk_level, 3) <= risk_order.get(self.auto_approve_below, 0):
            return True
            
        return False
        
    def increase_approval_threshold(self):
        """提高审批阈值（安全模式）"""
        self.approval_threshold = 1.0  # 所有操作都需要审批
        self.auto_approve_below = None  # 禁止自动审批
        
    def decrease_approval_threshold(self):
        """降低审批阈值（正常模式）"""
        self.approval_threshold = 0.5
        self.auto_approve_below = "low"
        
    def get_pending_count(self) -> int:
        """获取待审批数量"""
        return len(self.pending_requests)
        
    def list_pending_requests(self) -> List[ApprovalRequest]:
        """列出所有待审批请求"""
        return list(self.pending_requests.values())
        
    def get_request_history(self, limit: int = 50) -> List[ApprovalRequest]:
        """获取审批历史"""
        sorted_requests = sorted(
            self.decided_requests.values(),
            key=lambda x: x.decided_at or datetime.min,
            reverse=True
        )
        return sorted_requests[:limit]
        
    async def wait_for_decision(
        self, 
        request_id: str, 
        timeout_seconds: float = 300
    ) -> Optional[bool]:
        """等待人类决策（异步）"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            if request_id not in self.pending_requests:
                # 请求已被决策
                if request_id in self.decided_requests:
                    return self.decided_requests[request_id].status == "approved"
                return None
                
            await asyncio.sleep(1)  # 每秒检查一次
            
        # 超时
        return None
        
    def export_audit_log(self, filepath: str):
        """导出审计日志"""
        import json
        
        audit_data = {
            "pending_requests": [
                {
                    "request_id": r.request_id,
                    "type": r.request_type,
                    "description": r.description,
                    "risk_level": r.risk_level,
                    "submitted_at": r.submitted_at.isoformat()
                }
                for r in self.pending_requests.values()
            ],
            "decided_requests": [
                {
                    "request_id": r.request_id,
                    "type": r.request_type,
                    "description": r.description,
                    "risk_level": r.risk_level,
                    "status": r.status,
                    "decided_by": r.decision_by,
                    "reason": r.decision_reason,
                    "decided_at": r.decided_at.isoformat() if r.decided_at else None
                }
                for r in self.decided_requests.values()
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False)
