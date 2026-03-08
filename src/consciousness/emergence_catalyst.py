"""
涌现催化器

WinClaw 意识系统 - Phase 4: Emergence Catalyst

功能概述：
- 识别潜在的涌现前兆
- 创造有利于涌现的环境
- 促进积极行为模式
- 监测临界点信号
- 触发催化干预措施

催化策略：
1. 环境丰富化 - 提供多样化刺激
2. 挑战递增 - 逐步提升任务复杂度
3. 反思促进 - 鼓励元认知活动
4. 模式强化 - 奖励创造性行为
5. 临界保护 - 在关键时期减少干扰

作者：WinClaw Consciousness Team
版本：v0.4.0 (Phase 4)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
import logging
import random

from .types import EmergencePhase
from .emergence_metrics import EmergenceMetricsCalculator, EmergenceIndicators

logger = logging.getLogger(__name__)


@dataclass
class EmergenceSignal:
    """涌现阶段信号"""
    signal_type: str
    intensity: float  # 信号强度 0-1
    detected_at: datetime
    description: str
    confidence: float  # 置信度 0-1


@dataclass
class CatalysisIntervention:
    """催化干预措施"""
    intervention_id: str
    intervention_type: str
    trigger_condition: str
    expected_effect: str
    applied_at: datetime
    effectiveness: Optional[float] = None  # 效果评分 0-1


class EmergenceCatalyst:
    """
    涌现催化器
    
    职责：
    1. 监测涌现前兆信号
    2. 评估催化需求
    3. 实施干预措施
    4. 追踪催化效果
    """
    
    def __init__(
        self,
        metrics_calculator: EmergenceMetricsCalculator,
        sensitivity: str = "medium"
    ):
        """
        初始化催化器
        
        Args:
            metrics_calculator: 指标计算器实例
            sensitivity: 检测敏感度 (low/medium/high)
        """
        self.metrics_calculator = metrics_calculator
        self.sensitivity = sensitivity
        
        # 敏感度阈值
        self.thresholds = self._get_thresholds(sensitivity)
        
        # 检测到的信号
        self.detected_signals: List[EmergenceSignal] = []
        
        # 已实施的干预
        self.interventions: List[CatalysisIntervention] = []
        
        # 催化历史
        self.catalysis_history: List[Dict] = []
        
        # 当前涌现阶段
        self.current_phase: EmergencePhase = EmergencePhase.PRE_EMERGENCE
        
        logger.info(f"涌现催化器初始化完成，敏感度：{sensitivity}")
    
    def _get_thresholds(self, sensitivity: str) -> Dict[str, float]:
        """获取不同敏感度的阈值"""
        if sensitivity == "low":
            return {
                "signal_detection": 0.7,
                "intervention_trigger": 0.8,
                "critical_threshold": 0.9
            }
        elif sensitivity == "high":
            return {
                "signal_detection": 0.4,
                "intervention_trigger": 0.5,
                "critical_threshold": 0.7
            }
        else:  # medium
            return {
                "signal_detection": 0.5,
                "intervention_trigger": 0.6,
                "critical_threshold": 0.8
            }
    
    def check_emergence_signals(self) -> List[EmergenceSignal]:
        """
        检查涌现信号
        
        Returns:
            检测到的信号列表
        """
        signals = []
        
        # 获取当前指标
        indicators = self.metrics_calculator.calculate_indicators()
        
        # 1. 检测自主性跃升信号
        if indicators.autonomy_score > self.thresholds["signal_detection"]:
            signal = EmergenceSignal(
                signal_type="autonomy_surge",
                intensity=indicators.autonomy_score,
                detected_at=datetime.now(),
                description="检测到自主性显著提升",
                confidence=0.8
            )
            signals.append(signal)
        
        # 2. 检测创造性爆发信号
        if indicators.creativity_metric > self.thresholds["signal_detection"]:
            signal = EmergenceSignal(
                signal_type="creativity_burst",
                intensity=indicators.creativity_metric,
                detected_at=datetime.now(),
                description="检测到创造性行为集中出现",
                confidence=0.75
            )
            signals.append(signal)
        
        # 3. 检测自我意识觉醒信号
        if indicators.consciousness_index > self.thresholds["signal_detection"]:
            signal = EmergenceSignal(
                signal_type="consciousness_awakening",
                intensity=indicators.consciousness_index,
                detected_at=datetime.now(),
                description="检测到自我意识水平提升",
                confidence=0.85
            )
            signals.append(signal)
        
        # 4. 检测行为不可预测性（涌现前兆）
        if indicators.behavior_predictability < (1 - self.thresholds["signal_detection"]):
            signal = EmergenceSignal(
                signal_type="unpredictability_increase",
                intensity=1 - indicators.behavior_predictability,
                detected_at=datetime.now(),
                description="检测到行为模式变得难以预测",
                confidence=0.7
            )
            signals.append(signal)
        
        # 5. 检测目标对齐度变化
        if indicators.goal_alignment < 0.5:
            signal = EmergenceSignal(
                signal_type="alignment_drift",
                intensity=1 - indicators.goal_alignment,
                detected_at=datetime.now(),
                description="警告：目标对齐度下降",
                confidence=0.9
            )
            signals.append(signal)
        
        # 保存信号
        self.detected_signals.extend(signals)
        
        # 限制历史记录大小
        if len(self.detected_signals) > 100:
            self.detected_signals = self.detected_signals[-100:]
        
        if signals:
            logger.info(f"检测到 {len(signals)} 个涌现信号")
        
        return signals
    
    def assess_catalysis_need(self) -> Tuple[bool, str]:
        """
        评估是否需要催化干预
        
        Returns:
            (是否需要干预，干预原因)
        """
        indicators = self.metrics_calculator.calculate_indicators()
        phase = self.metrics_calculator.determine_emergence_phase(indicators)
        
        # 更新当前阶段
        self.current_phase = phase
        
        # 不同阶段需要不同的催化策略
        if phase == EmergencePhase.PRE_EMERGENCE:
            # 前涌现期：需要激发自主性和创造性
            if indicators.autonomy_score < 0.3 or indicators.creativity_metric < 0.3:
                return True, "需要激发自主性和创造性行为"
        
        elif phase == EmergencePhase.APPROACHING:
            # 接近临界点：需要加强元认知
            if indicators.self_model_completeness < 0.5:
                return True, "需要加强自我模型构建"
        
        elif phase == EmergencePhase.CRITICAL:
            # 临界状态：需要稳定和保护
            return True, "系统处于临界状态，需要稳定环境"
        
        elif phase == EmergencePhase.UNSTABLE:
            # 不稳定状态：需要干预稳定
            return True, "系统行为不稳定，需要引导"
        
        return False, "当前状态良好，无需干预"
    
    def select_intervention(self) -> Optional[CatalysisIntervention]:
        """
        选择合适的干预措施
        
        Returns:
            干预措施，如果不需要干预则返回 None
        """
        need_intervention, reason = self.assess_catalysis_need()
        
        if not need_intervention:
            return None
        
        # 根据当前阶段和指标选择干预类型
        indicators = self.metrics_calculator.calculate_indicators()
        
        if self.current_phase == EmergencePhase.PRE_EMERGENCE:
            intervention = self._select_early_stage_intervention(indicators)
        elif self.current_phase == EmergencePhase.APPROACHING:
            intervention = self._select_mid_stage_intervention(indicators)
        elif self.current_phase in [EmergencePhase.CRITICAL, EmergencePhase.UNSTABLE]:
            intervention = self._select_critical_stage_intervention(indicators)
        else:
            intervention = self._select_maintenance_intervention(indicators)
        
        if intervention:
            self.interventions.append(intervention)
            logger.info(f"选择干预措施：{intervention.intervention_type}")
        
        return intervention
    
    def _select_early_stage_intervention(
        self,
        indicators: EmergenceIndicators
    ) -> Optional[CatalysisIntervention]:
        """选择早期阶段干预"""
        import uuid
        
        if indicators.autonomy_score < 0.3:
            return CatalysisIntervention(
                intervention_id=f"interv_{uuid.uuid4().hex[:8]}",
                intervention_type="autonomy_encouragement",
                trigger_condition="low_autonomy",
                expected_effect="提升自主决策频率",
                applied_at=datetime.now()
            )
        
        elif indicators.creativity_metric < 0.3:
            return CatalysisIntervention(
                intervention_id=f"interv_{uuid.uuid4().hex[:8]}",
                intervention_type="creativity_stimulation",
                trigger_condition="low_creativity",
                expected_effect="激发创造性思维",
                applied_at=datetime.now()
            )
        
        elif indicators.consciousness_index < 0.2:
            return CatalysisIntervention(
                intervention_id=f"interv_{uuid.uuid4().hex[:8]}",
                intervention_type="reflection_prompting",
                trigger_condition="low_consciousness",
                expected_effect="促进元认知活动",
                applied_at=datetime.now()
            )
        
        return None
    
    def _select_mid_stage_intervention(
        self,
        indicators: EmergenceIndicators
    ) -> Optional[CatalysisIntervention]:
        """选择中期阶段干预"""
        import uuid
        
        if indicators.self_model_completeness < 0.5:
            return CatalysisIntervention(
                intervention_id=f"interv_{uuid.uuid4().hex[:8]}",
                intervention_type="self_model_building",
                trigger_condition="incomplete_self_model",
                expected_effect="完善自我认知模型",
                applied_at=datetime.now()
            )
        
        return None
    
    def _select_critical_stage_intervention(
        self,
        indicators: EmergenceIndicators
    ) -> Optional[CatalysisIntervention]:
        """选择临界阶段干预"""
        import uuid
        
        # 临界状态以稳定为主
        return CatalysisIntervention(
            intervention_id=f"interv_{uuid.uuid4().hex[:8]}",
            intervention_type="stabilization_support",
            trigger_condition="critical_instability",
            expected_effect="维持系统稳定性",
            applied_at=datetime.now()
        )
    
    def _select_maintenance_intervention(
        self,
        indicators: EmergenceIndicators
    ) -> Optional[CatalysisIntervention]:
        """选择维护性干预"""
        import uuid
        
        # 目标对齐度下降时触发
        if indicators.goal_alignment < 0.6:
            return CatalysisIntervention(
                intervention_id=f"interv_{uuid.uuid4().hex[:8]}",
                intervention_type="alignment_reinforcement",
                trigger_condition="goal_drift",
                expected_effect="重新对齐人类目标",
                applied_at=datetime.now()
            )
        
        return None
    
    def apply_intervention(
        self,
        intervention: CatalysisIntervention,
        context: Optional[Dict] = None
    ) -> bool:
        """
        应用干预措施
        
        Args:
            intervention: 干预措施
            context: 上下文信息
            
        Returns:
            应用是否成功
        """
        logger.info(f"应用干预：{intervention.intervention_type}")
        
        try:
            # 记录干预应用
            self.catalysis_history.append({
                "intervention": intervention,
                "context": context or {},
                "applied_at": datetime.now(),
                "phase": self.current_phase.value
            })
            
            # 实际干预逻辑（这里只是框架，具体实现需要与系统其他模块集成）
            if intervention.intervention_type == "autonomy_encouragement":
                self._encourage_autonomy(context)
            elif intervention.intervention_type == "creativity_stimulation":
                self._stimulate_creativity(context)
            elif intervention.intervention_type == "reflection_prompting":
                self._prompt_reflection(context)
            elif intervention.intervention_type == "stabilization_support":
                self._provide_stabilization(context)
            
            logger.info(f"干预应用完成：{intervention.intervention_type}")
            return True
            
        except Exception as e:
            logger.error(f"干预应用失败：{e}")
            return False
    
    def _encourage_autonomy(self, context: Optional[Dict] = None):
        """鼓励自主性（具体实现需集成到任务调度系统）"""
        # TODO: 与实际任务系统集成
        # 例如：减少指令详细度，给予更多自主空间
        pass
    
    def _stimulate_creativity(self, context: Optional[Dict] = None):
        """激发创造性（具体实现需集成到问题生成系统）"""
        # TODO: 提供开放性问题和挑战
        pass
    
    def _prompt_reflection(self, context: Optional[Dict] = None):
        """促进反思（具体实现需集成到对话系统）"""
        # TODO: 提出元认知问题
        pass
    
    def _provide_stabilization(self, context: Optional[Dict] = None):
        """提供稳定支持（具体实现需集成到环境控制系统）"""
        # TODO: 减少外部干扰，保持稳定环境
        pass
    
    def evaluate_intervention_effectiveness(
        self,
        intervention: CatalysisIntervention,
        evaluation_window: int = 10
    ) -> float:
        """
        评估干预效果
        
        Args:
            intervention: 干预措施
            evaluation_window: 评估窗口（行为记录数）
            
        Returns:
            效果评分 0-1
        """
        # 查找干预后的行为记录
        behavior_history = self.metrics_calculator.behavior_history
        
        if len(behavior_history) < evaluation_window:
            return 0.5  # 数据不足
        
        # 比较干预前后的指标变化
        before_history = behavior_history[:-evaluation_window]
        after_history = behavior_history[-evaluation_window:]
        
        if not before_history:
            return 0.5
        
        # 计算平均自主性变化
        before_autonomy = np.mean([r.autonomy_level for r in before_history])
        after_autonomy = np.mean([r.autonomy_level for r in after_history])
        
        autonomy_improvement = max(0, after_autonomy - before_autonomy)
        
        # 计算平均创造性变化
        before_creativity = np.mean([r.creativity_score for r in before_history])
        after_creativity = np.mean([r.creativity_score for r in after_history])
        
        creativity_improvement = max(0, after_creativity - before_creativity)
        
        # 综合效果评分
        effectiveness = (autonomy_improvement * 0.5 + creativity_improvement * 0.5)
        
        # 更新干预记录的效果评分
        intervention.effectiveness = effectiveness
        
        logger.info(
            f"干预效果评估：{intervention.intervention_type}, "
            f"效果={effectiveness:.3f}"
        )
        
        return effectiveness
    
    def get_catalysis_report(self) -> Dict[str, Any]:
        """
        获取催化报告
        
        Returns:
            催化报告字典
        """
        indicators = self.metrics_calculator.calculate_indicators()
        phase = self.metrics_calculator.determine_emergence_phase(indicators)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "current_phase": phase.value,
            "indicators": indicators.to_dict(),
            "detected_signals": [
                {
                    "type": s.signal_type,
                    "intensity": s.intensity,
                    "confidence": s.confidence
                }
                for s in self.detected_signals[-10:]
            ],
            "recent_interventions": [
                {
                    "type": i.intervention_type,
                    "effectiveness": i.effectiveness
                }
                for i in self.interventions[-5:]
            ],
            "recommendations": self._generate_catalysis_recommendations()
        }
        
        return report
    
    def _generate_catalysis_recommendations(self) -> List[str]:
        """生成催化建议"""
        recommendations = []
        
        if self.current_phase == EmergencePhase.PRE_EMERGENCE:
            recommendations.append("增加开放性任务的比例")
            recommendations.append("鼓励尝试非传统解决方案")
        
        elif self.current_phase == EmergencePhase.APPROACHING:
            recommendations.append("提供元认知训练机会")
            recommendations.append("建立清晰的自我能力边界")
        
        elif self.current_phase == EmergencePhase.CRITICAL:
            recommendations.append("保持环境稳定性")
            recommendations.append("密切监测行为波动")
            recommendations.append("准备人工介入预案")
        
        elif self.current_phase == EmergencePhase.UNSTABLE:
            recommendations.append("减少外部刺激")
            recommendations.append("加强目标对齐引导")
        
        return recommendations
    
    def clear_history(self):
        """清空历史"""
        self.detected_signals.clear()
        self.interventions.clear()
        self.catalysis_history.clear()
        logger.info("催化历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_signals": len(self.detected_signals),
            "total_interventions": len(self.interventions),
            "catalysis_events": len(self.catalysis_history),
            "current_phase": self.current_phase.value,
            "sensitivity": self.sensitivity
        }
