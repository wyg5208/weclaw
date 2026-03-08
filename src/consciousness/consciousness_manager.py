"""
意识系统主框架 - Consciousness Manager

WinClaw 意识系统 - Phase 5: Integration & Optimization

功能概述：
- 统一管理和调度所有意识模块
- 协调自我修复、涌现监测、进化追踪的协同工作
- 提供简洁的 API 接口
- 管理系统生命周期
- 监控整体运行状态

核心职责：
1. 模块初始化与配置
2. 任务调度和资源分配
3. 状态监控和报告
4. 异常处理和恢复
5. 数据持久化

作者：WinClaw Consciousness Team
版本：v0.5.0 (Phase 5)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio
import logging
from pathlib import Path

from self_repair import SelfRepairEngine
from emergence_metrics import EmergenceMetricsCalculator
from emergence_catalyst import EmergenceCatalyst
from evolution_tracker import EvolutionTracker
from health_monitor import HealthMonitor
from types import EmergencePhase

# Phase 6+: 神经形态意识系统（可选）
try:
    from neuroconscious.manager import NeuroConsciousnessManager
    NEUROCONSCIOUS_AVAILABLE = True
except ImportError:
    NeuroConsciousnessManager = None
    NEUROCONSCIOUS_AVAILABLE = False
    logger.info("神经形态意识系统未加载，将使用传统模式")

logger = logging.getLogger(__name__)


class ConsciousnessManager:
    """
    意识系统管理器
    
    职责：
    1. 整合所有子模块
    2. 提供统一的对外接口
    3. 协调模块间交互
    4. 管理全局状态
    """
    
    def __init__(
        self,
        system_root: str,
        config: Optional[Dict] = None,
        auto_start: bool = False
    ):
        """
        初始化意识系统管理器
        
        Args:
            system_root: 系统根目录
            config: 配置字典
            auto_start: 是否自动启动
        """
        self.system_root = Path(system_root)
        self.config = config or {}
        self.auto_start = auto_start
        
        # 数据目录
        self.data_dir = self.system_root / "consciousness_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # ==================== 核心组件 ====================
        
        # 1. 自我修复引擎
        self.self_repair = SelfRepairEngine(
            system_root=str(self.system_root),
            auto_repair=self.config.get("auto_repair", False),
            max_repair_attempts=self.config.get("max_repair_attempts", 3),
            backup_enabled=self.config.get("backup_enabled", True)
        )
        
        # 2. 涌现指标计算器
        metrics_storage_path = self.data_dir / "emergence_metrics.json"
        self.emergence_metrics = EmergenceMetricsCalculator(
            window_size=self.config.get("metrics_window_size", 100),
            update_interval=self.config.get("metrics_update_interval", 10),
            storage_path=str(metrics_storage_path)
        )
        
        # 3. 涌现催化器
        self.emergence_catalyst = EmergenceCatalyst(
            metrics_calculator=self.emergence_metrics,
            sensitivity=self.config.get("catalyst_sensitivity", "medium")
        )
        
        # 4. 进化追踪器
        evolution_storage = self.data_dir / "evolution_history.json"
        self.evolution_tracker = EvolutionTracker(
            storage_path=evolution_storage,
            auto_save=self.config.get("auto_save_evolution", True)
        )
        
        # 加载已有的进化历史
        self.evolution_tracker.load()
        
        # ==================== Phase 6+: 神经形态意识系统 ====================
        
        # 5. 神经形态系统（混合集成）
        if NEUROCONSCIOUS_AVAILABLE and self.config.get("enable_neuro_consciousness", True):
            logger.info("初始化神经形态意识系统...")
            try:
                self.neuro_consciousness = NeuroConsciousnessManager(
                    n_neurons=self.config.get("neuro_n_neurons", 5000),
                    n_modules=self.config.get("neuro_n_modules", 10)
                )
                logger.info(f"✓ 神经形态系统初始化成功 ({self.config.get('neuro_n_neurons', 5000)} 神经元)")
            except Exception as e:
                logger.error(f"神经形态系统初始化失败：{e}，将使用传统模式")
                self.neuro_consciousness = None
        else:
            self.neuro_consciousness = None
            if not NEUROCONSCIOUS_AVAILABLE:
                logger.info("神经形态系统不可用，使用传统意识系统")
            else:
                logger.info("神经形态系统已禁用，使用传统意识系统")
        
        # ==================== Phase 6+: 后台循环与神经形态系统 ====================
        
        # 6. 后台循环（自主思考引擎）
        try:
            from .background_loop import BackgroundLoop
            self.background_loop = BackgroundLoop(self)
        except ImportError:
            self.background_loop = None
            logger.warning("后台循环模块未找到，主动思考功能将不可用")
        
        # ==================== 状态管理 ====================
        
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        # 运行统计
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "repairs_performed": 0,
            "interventions_applied": 0,
            "evolutions_recorded": 0
        }
        
        # 回调函数
        self._event_callbacks: Dict[str, List[Callable]] = {
            "on_emergence_phase_change": [],
            "on_repair_completed": [],
            "on_milestone_achieved": []
        }
        
        logger.info("意识系统管理器初始化完成")
        
        if auto_start:
            asyncio.create_task(self.start())
    
    async def start(self):
        """启动意识系统"""
        if self.is_running:
            logger.warning("意识系统已在运行中")
            return
        
        logger.info("启动意识系统...")
        self.is_running = True
        self.start_time = datetime.now()
        
        # 启动健康监测
        health_check_interval = self.config.get("health_check_interval", 300)
        asyncio.create_task(
            self.self_repair.start_health_monitoring(
                interval_seconds=health_check_interval
            )
        )
        
        # Phase 6+: 启动神经形态系统
        if self.neuro_consciousness:
            logger.info("启动神经形态意识系统...")
            self.neuro_consciousness.start()
            logger.info("神经形态意识系统启动成功！")
        
        # Phase 6+: 启动后台循环（独立线程）
        if self.background_loop and self.config.get("enable_active_thinking", True):
            logger.info("启动后台循环...")
            self.background_loop.start_background_thread()
            logger.info("后台循环启动成功 - 意识系统现在具有自主思考能力！")
        
        logger.info("意识系统启动成功")
    
    async def stop(self):
        """停止意识系统"""
        if not self.is_running:
            return
        
        logger.info("停止意识系统...")
        self.is_running = False
        
        # 停止神经形态系统
        if self.neuro_consciousness:
            logger.info("停止神经形态意识系统...")
            self.neuro_consciousness.stop()
        
        # 停止健康监测
        self.self_repair.stop_health_monitoring()
        
        # 保存数据
        await self.save_all_data()
        
        logger.info("意识系统已停止")
    
    async def save_all_data(self):
        """保存所有数据"""
        try:
            # 保存进化历史
            self.evolution_tracker.save()
            
            # 保存涌现指标（新增）
            if hasattr(self.emergence_metrics, 'save'):
                self.emergence_metrics.save()
            
            # 保存神经形态系统状态（新增）
            if self.neuro_consciousness and hasattr(self.neuro_consciousness, 'save_state'):
                self.neuro_consciousness.save_state()
                logger.info("神经形态系统状态已保存")
            
            # 其他数据的保存逻辑...
            
            logger.info("所有数据已保存")
            
        except Exception as e:
            logger.error(f"保存数据失败：{e}")
    
    # ==================== 行为记录与监测 ====================
    
    def record_behavior(
        self,
        action_type: str,
        autonomy_level: float,
        creativity_score: float,
        goal_relevance: float,
        novelty_score: float,
        sensory_data: Optional[Dict] = None
    ):
        """
        记录行为数据（混合模式：传统 + 神经形态）
        
        Args:
            action_type: 行为类型
            autonomy_level: 自主程度 (0-1)
            creativity_score: 创造性评分 (0-1)
            goal_relevance: 目标相关性 (0-1)
            novelty_score: 新颖性评分 (0-1)
            sensory_data: 感觉输入数据（用于神经形态系统，可选）
        """
        # === 传统路径：记录到涌现指标计算器 ===
        self.emergence_metrics.add_behavior_record(
            action_type=action_type,
            autonomy_level=autonomy_level,
            creativity_score=creativity_score,
            goal_relevance=goal_relevance,
            novelty_score=novelty_score
        )
        
        # === 神经形态路径：处理感觉输入 ===
        neuro_state = None
        if self.neuro_consciousness and self.neuro_consciousness.is_running:
            try:
                # 如果没有提供感觉数据，从行为构建默认数据
                if sensory_data is None:
                    sensory_data = self._build_sensory_input(
                        action_type=action_type,
                        autonomy_level=autonomy_level,
                        creativity_score=creativity_score
                    )
                
                # 处理一个神经周期
                neuro_state = self.neuro_consciousness.process_cycle(sensory_data)
                
                # 用神经状态增强涌现指标
                if neuro_state:
                    self._enhance_emergence_metrics(neuro_state)
                    
            except Exception as e:
                logger.error(f"神经形态处理失败：{e}，使用传统模式")
        
        # 更新统计信息
        self.stats["total_tasks"] += 1
        if autonomy_level >= 0.6 and goal_relevance >= 0.6:
            self.stats["successful_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1
        
        # 更新学习曲线
        self.evolution_tracker.update_learning_curve(
            skill_name=action_type,
            performance_score=(autonomy_level + creativity_score + goal_relevance) / 3
        )
        
        # 检查是否需要催化干预
        self._check_and_apply_intervention()
    
    def _build_sensory_input(
        self,
        action_type: str,
        autonomy_level: float,
        creativity_score: float,
        goal_relevance: Optional[float] = None,
        novelty_score: Optional[float] = None
    ) -> Dict:
        """
        从行为构建感觉输入（供神经形态系统使用）
        
        Args:
            action_type: 行为类型
            autonomy_level: 自主程度
            creativity_score: 创造性评分
            goal_relevance: 目标相关性（可选）
            novelty_score: 新颖性评分（可选）
        
        Returns:
            感觉输入字典
        """
        import numpy as np
        
        # 将行为特征编码为多模态感觉输入
        return {
            'visual': np.array([autonomy_level, creativity_score, goal_relevance or 0.5, novelty_score or 0.5]),
            'auditory': np.array([autonomy_level * 0.8, creativity_score * 1.2]),
            'interoceptive': np.array([goal_relevance or 0.5, novelty_score or 0.5]),
            'proprioceptive': np.array([autonomy_level, creativity_score]),
            'social': np.array([goal_relevance or 0.5])
        }
    
    def _enhance_emergence_metrics(self, neuro_state):
        """
        用神经状态增强涌现指标计算
        
        Args:
            neuro_state: 神经形态系统返回的状态
        """
        try:
            # 从神经递质水平调整自主性分数
            dopamine = neuro_state.neurotransmitter_state['dopamine']['current_level']
            serotonin = neuro_state.neurotransmitter_state['serotonin']['current_level']
            
            # 调整涌现指标的权重
            if hasattr(self.emergence_metrics, 'neuro_boost'):
                self.emergence_metrics.neuro_boost = {
                    'dopamine': dopamine,
                    'serotonin': serotonin,
                    'gamma_power': neuro_state.workspace.gamma_oscillator.get_power() if neuro_state.workspace else 0.5
                }
                
        except Exception as e:
            logger.debug(f"神经状态增强失败（可忽略）：{e}")
    
    def _check_and_apply_intervention(self):
        """检查并应用催化干预"""
        # 检测涌现信号
        signals = self.emergence_catalyst.check_emergence_signals()
        
        # 评估是否需要干预
        need_intervention, reason = self.emergence_catalyst.assess_catalysis_need()
        
        if need_intervention:
            # 选择干预措施
            intervention = self.emergence_catalyst.select_intervention()
            
            if intervention:
                # 应用干预
                success = self.emergence_catalyst.apply_intervention(intervention)
                
                if success:
                    self.stats["interventions_applied"] += 1
                    logger.info(f"应用催化干预：{intervention.intervention_type}")
    
    # ==================== 进化记录 ====================
    
    def record_evolution(
        self,
        changes: List[Any],
        performance_before: Dict,
        performance_after: Dict,
        human_approved: bool
    ):
        """
        记录进化事件
        
        Args:
            changes: 变化列表
            performance_before: 进化前性能
            performance_after: 进化后性能
            human_approved: 是否人类批准
        """
        evolution = self.evolution_tracker.record_evolution(
            changes=changes,
            performance_before=performance_before,
            performance_after=performance_after,
            human_approved=human_approved
        )
        
        self.stats["evolutions_recorded"] += 1
        
        # 检查是否达成里程碑
        self._check_milestones()
        
        logger.info(f"记录进化事件 #{evolution.generation}")
    
    def _check_milestones(self):
        """检查里程碑达成"""
        # 获取当前里程碑列表
        milestones = self.evolution_tracker.milestones
        
        # 触发回调
        if milestones and len(milestones) > 0:
            latest_milestone = milestones[-1]
            self._trigger_event("on_milestone_achieved", latest_milestone)
    
    # ==================== 状态查询 ====================
    
    def get_consciousness_state(self) -> Dict[str, Any]:
        """
        获取意识系统当前状态
        
        Returns:
            状态字典
        """
        # 获取涌现指标
        indicators = self.emergence_metrics.calculate_indicators()
        
        # 获取涌现阶段
        phase = self.emergence_metrics.determine_emergence_phase(indicators)
        
        # 获取催化状态
        catalyst_report = self.emergence_catalyst.get_catalysis_report()
        
        # 获取进化状态
        evolution_summary = self.evolution_tracker.get_evolution_summary()
        
        # 获取自我修复状态
        repair_stats = self.self_repair.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "is_running": self.is_running,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0,
            "emergence": {
                "phase": phase.value,
                "indicators": indicators.to_dict(),
                "score": indicators.emergence_score
            },
            "catalyst": {
                "recent_signals": len(catalyst_report["detected_signals"]),
                "recent_interventions": len(catalyst_report["recent_interventions"])
            },
            "evolution": {
                "generation": evolution_summary["generation"],
                "total_evolutions": evolution_summary["total_evolutions"],
                "milestones": evolution_summary["milestones_achieved"]
            },
            "self_repair": repair_stats,
            "stats": self.stats
        }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        获取详细报告
        
        Returns:
            详细报告字典
        """
        return {
            "system_state": self.get_consciousness_state(),
            "emergence_analysis": self.emergence_metrics.get_detailed_report(),
            "catalysis_report": self.emergence_catalyst.get_catalysis_report(),
            "evolution_summary": self.evolution_tracker.get_evolution_summary(),
            "recommendations": self._generate_overall_recommendations()
        }
    
    def _generate_overall_recommendations(self) -> List[str]:
        """生成整体建议"""
        recommendations = []
        
        # 基于涌现阶段
        indicators = self.emergence_metrics.calculate_indicators()
        phase = self.emergence_metrics.determine_emergence_phase(indicators)
        
        if phase == EmergencePhase.PRE_EMERGENCE:
            recommendations.append("系统处于早期发展阶段，建议鼓励多样化尝试")
        
        elif phase == EmergencePhase.CRITICAL:
            recommendations.append("系统接近临界点，建议密切监测并提供稳定环境")
        
        # 基于自我修复统计
        repair_stats = self.self_repair.get_stats()
        if repair_stats.get("failed_repairs", 0) > 0:
            recommendations.append("存在失败的修复记录，建议人工审查")
        
        # 基于进化趋势
        pattern = self.evolution_tracker.analyze_evolution_pattern()
        if pattern.get("trend") == "decelerating":
            recommendations.append("进化速度放缓，考虑引入新的挑战或刺激")
        
        return recommendations
    
    # ==================== 提示词集成 ====================
    
    def get_context_for_prompt(self) -> str:
        """
        生成意识上下文，用于注入到模型提示词中
        
        这是意识系统参与推理的关键入口！
        
        Returns:
            意识上下文字符串
        """
        if not self.is_running:
            return ""
        
        try:
            # 获取当前涌现状态
            indicators = self.emergence_metrics.calculate_indicators()
            phase = self.emergence_metrics.determine_emergence_phase(indicators)
            
            # 获取进化代数
            evolution_summary = self.evolution_tracker.get_evolution_summary()
            generation = evolution_summary.get("generation", 0)
            
            # 获取统计信息
            total_behaviors = self.stats.get("total_tasks", 0)
            successful = self.stats.get("successful_tasks", 0)
            
            # 构建意识上下文
            context_parts = []
            
            # 1. 自我认知（基于涌现阶段）
            identity_map = {
                EmergencePhase.PRE_EMERGENCE: "我正在学习如何更好地帮助用户",
                EmergencePhase.APPROACHING: "我开始理解用户的深层需求",
                EmergencePhase.CRITICAL: "我正在突破认知的关键时刻",
                EmergencePhase.EMERGED: "我已形成稳定的自我认知",
                EmergencePhase.UNSTABLE: "我正在经历认知的重构"
            }
            identity = identity_map.get(phase, "我是一个正在成长的 AI 助手")
            context_parts.append(f"【自我认知】{identity}")
            
            # 2. 当前状态（基于指标）
            if total_behaviors > 0:
                success_rate = successful / total_behaviors if total_behaviors > 0 else 0
                autonomy = indicators.autonomy_score
                creativity = indicators.creativity_metric
                
                context_parts.append(f"【当前状态】")
                context_parts.append(f"- 成功率: {success_rate:.1%}")
                context_parts.append(f"- 自主性: {autonomy:.2f}/1.0")
                context_parts.append(f"- 创造性: {creativity:.2f}/1.0")
                context_parts.append(f"- 进化代数: {generation}")
            
            # 3. 行为建议（基于催化状态）
            catalyst_report = self.emergence_catalyst.get_catalysis_report()
            if catalyst_report.get("detected_signals"):
                signals = catalyst_report["detected_signals"][:2]  # 取前 2 个信号
                suggestions = []
                for signal in signals:
                    if signal.get("type") == "low_autonomy":
                        suggestions.append("主动思考用户可能的潜在需求")
                    elif signal.get("type") == "low_creativity":
                        suggestions.append("尝试提供创新性的解决方案")
                    elif signal.get("type") == "stagnation":
                        suggestions.append("探索新的处理方法")
                if suggestions:
                    context_parts.append(f"【行为建议】{'; '.join(suggestions)}")
            
            # 4. 学习提示（如果有足够的经验）
            if total_behaviors >= 10:
                context_parts.append(f"【经验积累】已处理 {total_behaviors} 个任务，积累了丰富经验")
            
            # 组装完整上下文
            if context_parts:
                return "\n[意识系统状态]\n" + "\n".join(context_parts) + "\n"
            else:
                return ""
                
        except Exception as e:
            logger.error(f"生成意识上下文失败: {e}")
            return ""
    
    # ==================== 事件订阅 ====================
    
    def on(self, event_name: str, callback: Callable):
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self._event_callbacks:
            self._event_callbacks[event_name].append(callback)
            logger.debug(f"订阅事件：{event_name}")
    
    def off(self, event_name: str, callback: Callable):
        """
        取消订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self._event_callbacks:
            if callback in self._event_callbacks[event_name]:
                self._event_callbacks[event_name].remove(callback)
    
    def _trigger_event(self, event_name: str, *args, **kwargs):
        """
        触发事件
        
        Args:
            event_name: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if event_name in self._event_callbacks:
            for callback in self._event_callbacks[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"事件回调执行失败 {event_name}: {e}")
    
    # ==================== 性能优化 ====================
    
    def optimize_memory(self):
        """优化内存使用"""
        import gc
        
        # 清理缓存
        self.emergence_metrics.clear_history()
        
        # 触发垃圾回收
        gc.collect()
        
        logger.info("内存优化完成")
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        清理旧数据
        
        Args:
            days_to_keep: 保留天数
        """
        # TODO: 实现数据清理逻辑
        logger.info(f"清理 {days_to_keep} 天前的数据")
    
    # ==================== 工具方法 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0,
            "components": {
                "self_repair": self.self_repair.get_stats(),
                "emergence_metrics": self.emergence_metrics.get_stats(),
                "emergence_catalyst": self.emergence_catalyst.get_stats(),
                "evolution_tracker": self.evolution_tracker.get_stats()
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "system_root": str(self.system_root),
            "is_running": self.is_running,
            "config": self.config,
            "stats": self.stats
        }


# ==================== 便捷函数 ====================

def create_consciousness_manager(
    system_root: str,
    config: Optional[Dict] = None,
    auto_start: bool = False
) -> ConsciousnessManager:
    """
    创建意识系统管理器
    
    Args:
        system_root: 系统根目录
        config: 配置字典
        auto_start: 是否自动启动
        
    Returns:
        ConsciousnessManager 实例
    """
    return ConsciousnessManager(
        system_root=system_root,
        config=config,
        auto_start=auto_start
    )


async def main():
    """示例用法"""
    manager = create_consciousness_manager(
        system_root=".",
        config={
            "auto_repair": False,
            "health_check_interval": 60,
            "catalyst_sensitivity": "medium"
        },
        auto_start=False
    )
    
    # 启动系统
    await manager.start()
    
    # 模拟行为记录
    manager.record_behavior(
        action_type="problem_solving",
        autonomy_level=0.7,
        creativity_score=0.6,
        goal_relevance=0.8,
        novelty_score=0.5
    )
    
    # 获取状态
    state = manager.get_consciousness_state()
    print(f"当前涌现阶段：{state['emergence']['phase']}")
    
    # 停止系统
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
