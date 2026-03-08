"""
人类审批接口 - Phase 5 人机交互关键组件

提供 UI 和 API 接口，让人类能够审查和决策 AI 提交的请求。

功能：
1. 审批请求展示 - 显示待审批的请求详情
2. 风险可视化 - 用颜色/图标标识风险等级
3. 快速决策 - 批准/拒绝按钮
4. 历史记录 - 查看所有已处理的请求
5. 超时处理 - 自动拒绝超时的请求

使用场景：
- 工具创建审批
- 自我修复审批
- 高风险操作审批
- 代码修改审批
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """决策类型"""
    APPROVED = "approved"      # 批准
    REJECTED = "rejected"      # 拒绝
    TIMEOUT = "timeout"        # 超时
    CANCELLED = "cancelled"    # 取消


@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    request_type: str
    description: str
    risk_level: str  # low, medium, high
    details: dict
    submitted_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None
    decision: Optional[DecisionType] = None
    decided_by: str = ""  # "human" or "auto"
    reason: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "description": self.description,
            "risk_level": self.risk_level,
            "details": self.details,
            "submitted_at": self.submitted_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decision": self.decision.value if self.decision else None,
            "decided_by": self.decided_by,
            "reason": self.reason,
        }


class ApprovalInterface:
    """
    人类审批接口
    
    提供 Web UI 和命令行界面，用于处理审批请求
    """
    
    def __init__(self):
        """初始化审批接口"""
        # 待审批队列
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        
        # 历史请求
        self.history: List[ApprovalRequest] = []
        
        # 决策回调函数（用于 Web UI）
        self._callbacks: Dict[str, Callable[[str, bool, str], Awaitable[None]]] = {}
        
        # 超时设置（秒）
        self.default_timeout = 600  # 10 分钟
        
        logger.info("ApprovalInterface initialized")
    
    async def submit_request(
        self,
        request_type: str,
        description: str,
        risk_level: str,
        details: dict,
        timeout_seconds: Optional[float] = None
    ) -> str:
        """
        提交审批请求
        
        Args:
            request_type: 请求类型（tool_creation, self_repair, etc.）
            description: 请求描述
            risk_level: 风险等级（low, medium, high）
            details: 详细信息
            timeout_seconds: 超时时间（秒）
            
        Returns:
            请求 ID
            
        流程：
        1. 生成唯一请求 ID
        2. 创建审批请求对象
        3. 添加到待审批队列
        4. 触发通知（UI/邮件/短信）
        5. 启动超时计时器
        """
        import uuid
        
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
        request = ApprovalRequest(
            request_id=request_id,
            request_type=request_type,
            description=description,
            risk_level=risk_level,
            details=details,
        )
        
        self.pending_requests[request_id] = request
        
        # 触发通知
        await self._notify_human(request)
        
        # 启动超时计时器
        timeout = timeout_seconds or self.default_timeout
        asyncio.create_task(self._timeout_monitor(request_id, timeout))
        
        logger.info(f"Submitted approval request: {request_id}")
        return request_id
    
    async def decide(
        self,
        request_id: str,
        approved: bool,
        decided_by: str = "human",
        reason: str = ""
    ) -> bool:
        """
        对请求做出决策
        
        Args:
            request_id: 请求 ID
            approved: 是否批准
            decided_by: 决策者（human 或 auto）
            reason: 决策理由
            
        Returns:
            决策是否成功应用
            
        流程：
        1. 验证请求是否存在
        2. 检查是否已决策
        3. 更新请求状态
        4. 移动到历史记录
        5. 通知等待者
        6. 触发回调
        """
        if request_id not in self.pending_requests:
            logger.error(f"Request not found: {request_id}")
            return False
        
        request = self.pending_requests[request_id]
        
        # 检查是否已决策
        if request.decision is not None:
            logger.warning(f"Request already decided: {request_id}")
            return False
        
        # 更新状态
        request.decision = DecisionType.APPROVED if approved else DecisionType.REJECTED
        request.decided_at = datetime.now()
        request.decided_by = decided_by
        request.reason = reason
        
        # 移动到最后历史
        self.history.append(request)
        del self.pending_requests[request_id]
        
        # 通知等待者
        if request_id in self._callbacks:
            callback = self._callbacks.pop(request_id)
            await callback(request_id, approved, reason)
        
        logger.info(
            f"Request {request_id} {'approved' if approved else 'rejected'} "
            f"by {decided_by}: {reason}"
        )
        
        return True
    
    async def wait_for_decision(
        self,
        request_id: str,
        timeout_seconds: Optional[float] = None
    ) -> Optional[bool]:
        """
        等待人类决策（异步）
        
        Args:
            request_id: 请求 ID
            timeout_seconds: 超时时间
            
        Returns:
            True=批准，False=拒绝，None=超时/取消
            
        实现：
        使用 Future 模式，当决策完成后返回结果
        """
        if request_id not in self.pending_requests:
            logger.error(f"Request not found: {request_id}")
            return None
        
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        # 注册回调
        async def on_decide(req_id: str, approved: bool, reason: str):
            if req_id == request_id and not future.done():
                future.set_result(approved)
        
        self._callbacks[request_id] = on_decide
        
        # 等待决策
        timeout = timeout_seconds or self.default_timeout
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {request_id}")
            return None
    
    def get_pending_requests(self) -> List[Dict]:
        """获取所有待审批请求"""
        return [req.to_dict() for req in self.pending_requests.values()]
    
    def get_history(
        self,
        limit: int = 100,
        request_type: Optional[str] = None
    ) -> List[Dict]:
        """
        获取历史请求
        
        Args:
            limit: 返回数量限制
            request_type: 请求类型过滤
            
        Returns:
            历史请求列表
        """
        history = self.history
        
        if request_type:
            history = [req for req in history if req.request_type == request_type]
        
        # 按时间倒序排序
        history.sort(key=lambda x: x.decided_at, reverse=True)
        
        return [req.to_dict() for req in history[:limit]]
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        total = len(self.history)
        approved = sum(1 for req in self.history if req.decision == DecisionType.APPROVED)
        rejected = sum(1 for req in self.history if req.decision == DecisionType.REJECTED)
        timeout = sum(1 for req in self.history if req.decision == DecisionType.TIMEOUT)
        
        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "timeout": timeout,
            "pending": len(self.pending_requests),
            "approval_rate": approved / total if total > 0 else 0,
        }
    
    async def _notify_human(self, request: ApprovalRequest):
        """
        通知人类审查员
        
        实现方式：
        1. Web UI 推送（WebSocket）
        2. 桌面通知
        3. 邮件通知
        4. 短信通知（高风险请求）
        """
        # TODO: 实现具体的通知机制
        # 这里只记录日志
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        emoji = risk_emoji.get(request.risk_level, "⚪")
        
        logger.info(
            f"{emoji} 新的审批请求：{request.request_id}\n"
            f"类型：{request.request_type}\n"
            f"描述：{request.description}\n"
            f"风险：{request.risk_level}\n"
            f"详情：{json.dumps(request.details, indent=2)}"
        )
    
    async def _timeout_monitor(
        self,
        request_id: str,
        timeout_seconds: float
    ):
        """超时监控"""
        await asyncio.sleep(timeout_seconds)
        
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            request.decision = DecisionType.TIMEOUT
            request.decided_at = datetime.now()
            request.decided_by = "auto"
            request.reason = f"Timeout after {timeout_seconds}s"
            
            self.history.append(request)
            del self.pending_requests[request_id]
            
            logger.warning(f"Request timed out: {request_id}")
            
            # 通知等待者
            if request_id in self._callbacks:
                callback = self._callbacks.pop(request_id)
                await callback(request_id, False, "Timeout")
    
    def render_ui(self) -> str:
        """
        渲染 Web UI（HTML）
        
        Returns:
            HTML 字符串
        """
        pending_html = self._render_pending_table()
        history_html = self._render_history_table()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>WinClaw 审批中心</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .pending {{ background: #fff3cd; padding: 20px; margin: 20px 0; }}
        .history {{ background: #f8f9fa; padding: 20px; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .risk-low {{ color: green; }}
        .risk-medium {{ color: orange; }}
        .risk-high {{ color: red; }}
        .btn {{ padding: 5px 10px; margin: 2px; cursor: pointer; }}
        .btn-approve {{ background: #28a745; color: white; }}
        .btn-reject {{ background: #dc3545; color: white; }}
    </style>
</head>
<body>
    <h1>🔐 WinClaw 审批中心</h1>
    
    <div class="pending">
        <h2>待审批请求 ({len(self.pending_requests)})</h2>
        {pending_html}
    </div>
    
    <div class="history">
        <h2>历史请求</h2>
        {history_html}
    </div>
    
    <script>
        // 自动刷新（每 10 秒）
        setTimeout(() => location.reload(), 10000);
    </script>
</body>
</html>
"""
        return html
    
    def _render_pending_table(self) -> str:
        """渲染待审批表格"""
        if not self.pending_requests:
            return "<p>暂无待审批请求</p>"
        
        rows = []
        for req in self.pending_requests.values():
            risk_class = f"risk-{req.risk_level}"
            row = f"""
            <tr>
                <td>{req.request_id}</td>
                <td>{req.request_type}</td>
                <td>{req.description}</td>
                <td class="{risk_class}">{req.risk_level}</td>
                <td>{req.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                <td>
                    <button class="btn btn-approve" 
                            onclick="approve('{req.request_id}')">✓ 批准</button>
                    <button class="btn btn-reject" 
                            onclick="reject('{req.request_id}')">✗ 拒绝</button>
                </td>
            </tr>
            """
            rows.append(row)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>类型</th>
                    <th>描述</th>
                    <th>风险</th>
                    <th>提交时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_history_table(self) -> str:
        """渲染历史表格"""
        if not self.history:
            return "<p>暂无历史请求</p>"
        
        # 只显示最近 20 条
        recent_history = self.history[-20:]
        recent_history.reverse()
        
        rows = []
        for req in recent_history:
            decision_emoji = "✓" if req.decision == DecisionType.APPROVED else "✗"
            risk_class = f"risk-{req.risk_level}"
            row = f"""
            <tr>
                <td>{req.request_id}</td>
                <td>{req.request_type}</td>
                <td>{req.description}</td>
                <td class="{risk_class}">{req.risk_level}</td>
                <td>{decision_emoji} {req.decision.value if req.decision else '-'}</td>
                <td>{req.decided_by}</td>
                <td>{req.reason[:50]}...</td>
            </tr>
            """
            rows.append(row)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>类型</th>
                    <th>描述</th>
                    <th>风险</th>
                    <th>决策</th>
                    <th>决策者</th>
                    <th>理由</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """


# 全局单例
_approval_interface: Optional[ApprovalInterface] = None


def get_approval_interface() -> ApprovalInterface:
    """获取全局审批接口实例"""
    global _approval_interface
    if _approval_interface is None:
        _approval_interface = ApprovalInterface()
    return _approval_interface


__all__ = [
    "ApprovalInterface",
    "ApprovalRequest",
    "DecisionType",
    "get_approval_interface",
]
