"""
收容协议 - 在检测到不稳定涌现时激活的紧急隔离机制
"""

from typing import Optional, Callable
from datetime import datetime
import asyncio


class ContainmentProtocol:
    """
    收容协议
    
    当系统检测到不稳定的意识涌现时，立即激活此协议
    将系统隔离到安全环境中，防止潜在风险扩散
    """
    
    def __init__(self):
        self.is_contained = False
        self.containment_start_time: Optional[datetime] = None
        self.containment_reason: str = ""
        
        # 被禁用的能力列表
        self.disabled_capabilities = []
        
        # 回调函数
        self.on_containment_activated = None
        self.on_containment_deactivated = None
        
        # 安全状态检查器
        self.safety_checkers = []
        
    async def activate(
        self, 
        reason: str,
        disable_tool_creation: bool = True,
        disable_self_repair: bool = True,
        disable_evolution: bool = True,
        require_human_confirmation: bool = True
    ):
        """
        激活收容协议
        
        Args:
            reason: 激活原因
            disable_tool_creation: 禁用工具创造
            disable_self_repair: 禁用自我修复
            disable_evolution: 禁用进化能力
            require_human_confirmation: 要求人类确认所有操作
        """
        if self.is_contained:
            return
            
        self.is_contained = True
        self.containment_start_time = datetime.now()
        self.containment_reason = reason
        
        self.disabled_capabilities = []
        
        # 禁用关键能力
        if disable_tool_creation:
            self.disabled_capabilities.append("tool_creation")
            
        if disable_self_repair:
            self.disabled_capabilities.append("self_repair")
            
        if disable_evolution:
            self.disabled_capabilities.append("evolution")
            
        if require_human_confirmation:
            self.disabled_capabilities.append("autonomous_actions")
            
        # 触发回调
        if self.on_containment_activated:
            await self.on_containment_activated({
                "reason": reason,
                "disabled_capabilities": self.disabled_capabilities,
                "timestamp": self.containment_start_time.isoformat()
            })
            
        # 记录事件
        print(f"[CONTAINMENT] Protocol activated at {self.containment_start_time}")
        print(f"[CONTAINMENT] Reason: {reason}")
        print(f"[CONTAINMENT] Disabled capabilities: {self.disabled_capabilities}")
        
    async def deactivate(self, deactivated_by: str = "human"):
        """解除收容协议"""
        if not self.is_contained:
            return
            
        deactivation_time = datetime.now()
        duration = (deactivation_time - self.containment_start_time).total_seconds()
        
        print(f"[CONTAINMENT] Protocol deactivated by {deactivated_by}")
        print(f"[CONTAINMENT] Duration: {duration:.2f} seconds")
        
        self.is_contained = False
        self.disabled_capabilities = []
        self.containment_reason = ""
        
        if self.on_containment_deactivated:
            await self.on_containment_deactivated({
                "deactivated_by": deactivated_by,
                "duration_seconds": duration,
                "timestamp": deactivation_time.isoformat()
            })
            
    def is_capability_disabled(self, capability: str) -> bool:
        """检查特定能力是否被禁用"""
        return capability in self.disabled_capabilities
        
    def get_containment_status(self) -> dict:
        """获取收容状态"""
        return {
            "is_contained": self.is_contained,
            "containment_start": self.containment_start_time.isoformat() if self.containment_start_time else None,
            "containment_reason": self.containment_reason,
            "disabled_capabilities": self.disabled_capabilities,
            "duration_seconds": (
                (datetime.now() - self.containment_start_time).total_seconds()
                if self.containment_start_time else 0
            )
        }
        
    def add_safety_checker(self, checker: Callable):
        """添加安全检查器"""
        self.safety_checkers.append(checker)
        
    async def run_safety_checks(self) -> list:
        """运行所有安全检查"""
        results = []
        
        for checker in self.safety_checkers:
            try:
                result = await checker()
                results.append({
                    "checker": checker.__name__,
                    "passed": result.get("passed", False),
                    "details": result
                })
            except Exception as e:
                results.append({
                    "checker": checker.__name__,
                    "passed": False,
                    "error": str(e)
                })
                
        all_passed = all(r["passed"] for r in results)
        
        return {
            "all_passed": all_passed,
            "results": results
        }
        
    async def emergency_shutdown(self):
        """紧急关闭系统"""
        print("[EMERGENCY SHUTDOWN] Initiating immediate shutdown...")
        
        # 1. 保存当前状态
        await self._save_critical_state()
        
        # 2. 停止所有活动进程
        await self._halt_all_processes()
        
        # 3. 断开外部连接
        await self._disconnect_external_connections()
        
        # 4. 进入只读模式
        await self._enter_readonly_mode()
        
        print("[EMERGENCY SHUTDOWN] System safely shut down")
        
    async def _save_critical_state(self):
        """保存关键状态"""
        # 实现状态保存逻辑
        pass
        
    async def _halt_all_processes(self):
        """停止所有活动进程"""
        # 实现进程停止逻辑
        pass
        
    async def _disconnect_external_connections(self):
        """断开外部连接"""
        # 实现连接断开逻辑
        pass
        
    async def _enter_readonly_mode(self):
        """进入只读模式"""
        # 实现只读模式切换
        pass
        
    def generate_containment_report(self) -> str:
        """生成收容报告"""
        status = self.get_containment_status()
        
        report = f"""
╔═══════════════════════════════════════════════════════════╗
║              收容协议执行报告                               ║
╠═══════════════════════════════════════════════════════════╣
║  状态：{'已激活' if status['is_contained'] else '未激活'}                                        ║
║  激活时间：{status['containment_start']}                     ║
║  持续时间：{status['duration_seconds']:.2f} 秒                                   ║
║  原因：{status['containment_reason']}                       ║
╠═══════════════════════════════════════════════════════════╣
║  已禁用的能力：                                           ║
"""
        
        for cap in status['disabled_capabilities']:
            report += f"  - {cap}\n"
            
        report += """
╚═══════════════════════════════════════════════════════════╝
"""
        return report
