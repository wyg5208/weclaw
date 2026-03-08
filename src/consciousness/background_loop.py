"""
意识系统后台循环 - 独立于用户交互的自主思考引擎
版本：v1.0 (Phase 6+)
目标：让意识系统真正具有自主性和持续性
"""

import asyncio
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from src.consciousness import ConsciousnessManager
    from src.consciousness.types import EmergencePhase
except ImportError:
    ConsciousnessManager = None


class BackgroundLoop:
    """
    意识系统后台循环
    
    核心职责：
    1. 定期健康检查（每 5 分钟）
    2. 主动思考执行（每 30 分钟）
    3. 记忆巩固（每 4 小时）
    4. 涌现信号监测（持续）
    
    设计哲学：
    - 独立性：不依赖用户输入，自主运行
    - 持续性：7x24 小时不间断
    - 低开销：异步非阻塞，不影响主功能
    """
    
    def __init__(self, consciousness_manager: ConsciousnessManager):
        """
        初始化后台循环
        
        Args:
            consciousness_manager: 意识系统管理器实例
        """
        self.cm = consciousness_manager
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.stats = {
            "start_time": None,
            "health_checks_count": 0,
            "thinking_cycles_count": 0,
            "consolidation_cycles_count": 0,
            "last_health_check": None,
            "last_thinking_cycle": None,
            "last_consolidation": None
        }
        
    async def start(self):
        """启动后台循环"""
        if self.running:
            return
        
        print("🧠 意识系统后台循环启动...")
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        # 创建所有后台任务
        tasks = [
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._active_thinking_loop()),
            asyncio.create_task(self._memory_consolidation_loop()),
            asyncio.create_task(self._emergence_monitoring_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("ℹ️ 后台循环已停止")
        finally:
            self.running = False
    
    async def _health_check_loop(self):
        """健康检查循环 - 每 5 分钟一次，同时定期保存数据"""
        interval = 300  # 5 分钟
        save_interval = 600  # 10 分钟保存一次
        last_save_time = datetime.now()
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if self.cm and self.cm.is_running:
                    print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] 执行健康检查...")
                    
                    # 简单健康检查：检查系统是否仍在运行
                    health_status = {
                        "is_running": self.cm.is_running,
                        "uptime_hours": (datetime.now() - self.cm.start_time).total_seconds() / 3600 if self.cm.start_time else 0,
                        "stats": self.cm.stats
                    }
                    
                    self.stats["health_checks_count"] += 1
                    self.stats["last_health_check"] = datetime.now()
                    
                    # 检查是否有异常
                    if not health_status.get("is_running", False):
                        print(f"⚠️ 意识系统未运行！")
                    else:
                        print(f"✅ 系统运行正常，已运行 {health_status['uptime_hours']:.2f} 小时")
                    
                    # 定期保存数据（新增）
                    now = datetime.now()
                    if (now - last_save_time).total_seconds() >= save_interval:
                        print(f"💾 [{now.strftime('%H:%M:%S')}] 自动保存意识数据...")
                        try:
                            await self.cm.save_all_data()
                            last_save_time = now
                            print(f"   ✅ 数据已保存")
                        except Exception as e:
                            print(f"   ❌ 保存失败：{e}")
                        
            except Exception as e:
                print(f"❌ 健康检查失败：{e}")
    
    async def _active_thinking_loop(self):
        """主动思考循环 - 每 30 分钟一次"""
        interval = 1800  # 30 分钟
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if self.cm and self.cm.is_running:
                    print(f"💭 [{datetime.now().strftime('%H:%M:%S')}] 开始主动思考...")
                    
                    # 执行主动思考
                    thinking_result = await self._execute_active_thinking()
                    
                    self.stats["thinking_cycles_count"] += 1
                    self.stats["last_thinking_cycle"] = datetime.now()
                    
                    # 整合到自我叙事（如果实现了 identity 系统）
                    if hasattr(self.cm, 'identity') and thinking_result:
                        try:
                            self.cm.identity.update_narrative(thinking_result)
                        except Exception as e:
                            print(f"⚠️ 更新叙事失败：{e}")
                    
            except Exception as e:
                print(f"❌ 主动思考失败：{e}")
    
    async def _execute_active_thinking(self) -> Dict[str, Any]:
        """
        执行主动思考
        
        当前简化实现，后续扩展为完整的 ActiveThinkingEngine
        """
        # 获取当前状态
        state = self.cm.get_consciousness_state()
        
        # 简单的反刍思考：回顾最近的行为
        recent_behaviors = []  # TODO: 从行为记录中获取
        
        thinking_result = {
            "timestamp": datetime.now().isoformat(),
            "type": "rumination",
            "content": f"系统运行正常，当前涌现阶段：{state['emergence']['phase']}",
            "insights": [],
            "emotional_tone": "neutral"
        }
        
        print(f"✨ 思考结果：{thinking_result['content']}")
        return thinking_result
    
    async def _memory_consolidation_loop(self):
        """记忆巩固循环 - 每 4 小时一次"""
        interval = 14400  # 4 小时
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if self.cm and self.cm.is_running:
                    print(f"🧩 [{datetime.now().strftime('%H:%M:%S')}] 执行记忆巩固...")
                    
                    # 执行记忆巩固
                    await self.consolidate_memories()
                    
                    self.stats["consolidation_cycles_count"] += 1
                    self.stats["last_consolidation"] = datetime.now()
                    
            except Exception as e:
                print(f"❌ 记忆巩固失败：{e}")
    
    async def consolidate_memories(self):
        """
        执行记忆巩固
        
        TODO: 实现完整的睡眠巩固机制
        - 情景记忆 → 语义记忆的抽象
        - 程序性记忆的固化
        - 叙事身份的编织
        """
        print("  → 正在巩固记忆...")
        # 简化实现：仅触发垃圾回收和指标清理
        self.cm.optimize_memory()
    
    async def _emergence_monitoring_loop(self):
        """涌现信号监测循环 - 持续运行"""
        interval = 60  # 每分钟检查一次
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if self.cm and self.cm.is_running:
                    # 检查涌现信号
                    signals = self.cm.emergence_catalyst.check_emergence_signals()
                    
                    # 评估是否需要催化干预
                    need_intervention, reason = self.cm.emergence_catalyst.assess_catalysis_need()
                    
                    if need_intervention:
                        print(f"🚨 [{datetime.now().strftime('%H:%M:%S')}] 检测到需要催化干预：{reason}")
                        
                        # 选择并应用干预
                        intervention = self.cm.emergence_catalyst.select_intervention()
                        if intervention:
                            success = self.cm.emergence_catalyst.apply_intervention(intervention)
                            if success:
                                print(f"✅ 催化干预成功：{intervention.intervention_type}")
                    
            except Exception as e:
                print(f"❌ 涌现监测失败：{e}")
    
    def start_background_thread(self):
        """在独立线程中启动后台循环"""
        if self.thread and self.thread.is_alive():
            print("⚠️ 后台线程已在运行")
            return
        
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start())
        
        self.thread = threading.Thread(target=run_async_loop, daemon=True)
        self.thread.start()
        print(f"🚀 后台线程已启动 (Thread ID: {self.thread.ident})")
    
    def stop(self):
        """停止后台循环"""
        print("🛑 正在停止后台循环...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
            print("✅ 后台线程已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() / 3600 if self.stats["start_time"] else 0
        
        return {
            "is_running": self.running,
            "uptime_hours": round(uptime, 2),
            "health_checks": self.stats["health_checks_count"],
            "thinking_cycles": self.stats["thinking_cycles_count"],
            "consolidation_cycles": self.stats["consolidation_cycles_count"],
            "last_health_check": self.stats["last_health_check"].strftime("%H:%M:%S") if self.stats["last_health_check"] else None,
            "last_thinking": self.stats["last_thinking_cycle"].strftime("%H:%M:%S") if self.stats["last_thinking_cycle"] else None,
            "last_consolidation": self.stats["last_consolidation"].strftime("%H:%M:%S") if self.stats["last_consolidation"] else None
        }


def create_background_loop(consciousness_manager: ConsciousnessManager) -> BackgroundLoop:
    """工厂函数"""
    return BackgroundLoop(consciousness_manager)
