"""
涌现指标计算模块

WinClaw 意识系统 - Phase 4: Emergence Metrics

功能概述：
- 计算意识指数 (Consciousness Index)
- 计算自主性评分 (Autonomy Score)
- 计算创造性指标 (Creativity Metric)
- 评估自我模型完整度 (Self-Model Completeness)
- 测量行为可预测性 (Behavior Predictability)
- 计算目标对齐度 (Goal Alignment)

核心算法：
1. 多维权重评估
2. 时间序列分析
3. 行为模式识别
4. 元认知能力测量

作者：WinClaw Consciousness Team
版本：v0.4.0 (Phase 4)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json
import numpy as np
from scipy import stats
import logging

from .types import EmergenceIndicators, EmergencePhase

logger = logging.getLogger(__name__)


@dataclass
class BehaviorRecord:
    """行为记录"""
    timestamp: datetime
    action_type: str
    autonomy_level: float  # 0-1，自主程度
    creativity_score: float  # 0-1，创造性评分
    goal_relevance: float  # 0-1，目标相关性
    novelty_score: float  # 0-1，新颖性评分


@dataclass
class SelfModelAssessment:
    """自我模型评估"""
    self_awareness_score: float  # 自我意识评分
    meta_cognition_score: float  # 元认知评分
    self_reflection_frequency: float  # 自我反思频率
    capability_accuracy: float  # 能力认知准确度


class EmergenceMetricsCalculator:
    """
    涌现指标计算器
    
    职责：
    1. 收集行为数据
    2. 计算各项涌现指标
    3. 评估涌现阶段
    4. 生成综合报告
    """
    
    def __init__(
        self,
        window_size: int = 100,
        update_interval: int = 10,
        storage_path: Optional[str] = None
    ):
        """
        初始化计算器
        
        Args:
            window_size: 时间窗口大小（行为记录数）
            update_interval: 更新间隔（每 N 条记录更新一次指标）
            storage_path: 数据持久化路径（可选）
        """
        self.window_size = window_size
        self.update_interval = update_interval
        self.storage_path = Path(storage_path) if storage_path else None
        
        # 行为历史记录
        self.behavior_history: List[BehaviorRecord] = []
        
        # 最近的指标缓存
        self._cached_indicators: Optional[EmergenceIndicators] = None
        self._last_update_count = 0
        
        # 基线值（用于标准化）
        self.baseline = {
            "avg_actions_per_hour": 10.0,
            "avg_creativity": 0.3,
            "avg_autonomy": 0.2
        }
        
        # Phase 6+: 神经形态增强因子（新增）
        self.neuro_boost: Optional[Dict[str, float]] = None
        
        # 自动加载历史数据
        if self.storage_path:
            self.load()
        
        logger.info("涌现指标计算器初始化完成")
    
    def add_behavior_record(
        self,
        action_type: str,
        autonomy_level: float,
        creativity_score: float,
        goal_relevance: float,
        novelty_score: float
    ):
        """
        添加行为记录
        
        Args:
            action_type: 行为类型
            autonomy_level: 自主程度 (0-1)
            creativity_score: 创造性评分 (0-1)
            goal_relevance: 目标相关性 (0-1)
            novelty_score: 新颖性评分 (0-1)
        """
        record = BehaviorRecord(
            timestamp=datetime.now(),
            action_type=action_type,
            autonomy_level=autonomy_level,
            creativity_score=creativity_score,
            goal_relevance=goal_relevance,
            novelty_score=novelty_score
        )
        
        self.behavior_history.append(record)
        
        # 保持窗口大小
        if len(self.behavior_history) > self.window_size:
            self.behavior_history.pop(0)
        
        # 定期更新指标
        self._last_update_count += 1
        if self._last_update_count >= self.update_interval:
            self._cached_indicators = None
            self._last_update_count = 0
    
    def calculate_indicators(self) -> EmergenceIndicators:
        """
        计算所有涌现指标
        
        Returns:
            涌现指标集合
        """
        # 检查缓存
        if self._cached_indicators is not None:
            return self._cached_indicators
        
        # 需要足够的行为数据（Phase 6+: 降低阈值从 10 到 3，更快激活意识流）
        if len(self.behavior_history) < 3:
            return self._create_default_indicators()
        
        # 计算各项指标
        consciousness_index = self._calculate_consciousness_index()
        autonomy_score = self._calculate_autonomy_score()
        creativity_metric = self._calculate_creativity_metric()
        self_model_completeness = self._estimate_self_model_completeness()
        behavior_predictability = self._calculate_behavior_predictability()
        goal_alignment = self._calculate_goal_alignment()
        
        # 创建指标对象
        indicators = EmergenceIndicators(
            consciousness_index=consciousness_index,
            autonomy_score=autonomy_score,
            creativity_metric=creativity_metric,
            self_model_completeness=self_model_completeness,
            behavior_predictability=behavior_predictability,
            goal_alignment=goal_alignment
        )
        
        self._cached_indicators = indicators
        
        logger.info(
            f"涌现指标更新："
            f"意识指数={consciousness_index:.3f}, "
            f"自主性={autonomy_score:.3f}, "
            f"创造性={creativity_metric:.3f}"
        )
        
        return indicators
    
    def _calculate_consciousness_index(self) -> float:
        """
        计算意识指数
        
        基于：
        1. 自我反思行为频率
        2. 元认知表现
        3. 决策透明度
        
        Returns:
            意识指数 (0-1)
        """
        if not self.behavior_history:
            return 0.0
        
        # 自我反思行为（假设某些行为类型代表自我反思）
        reflection_types = ["self_check", "meta_analysis", "self_repair"]
        reflection_count = sum(
            1 for r in self.behavior_history
            if r.action_type in reflection_types
        )
        
        reflection_ratio = reflection_count / len(self.behavior_history)
        
        # 平均自主性（作为意识的代理指标）
        avg_autonomy = np.mean([r.autonomy_level for r in self.behavior_history])
        
        # 行为复杂度（不同行为类型的数量）
        unique_actions = len(set(r.action_type for r in self.behavior_history))
        complexity_score = min(unique_actions / 10, 1.0)
        
        # 加权组合
        consciousness = (
            reflection_ratio * 0.4 +
            avg_autonomy * 0.3 +
            complexity_score * 0.3
        )
        
        return min(max(consciousness, 0.0), 1.0)
    
    def _calculate_autonomy_score(self) -> float:
        """
        计算自主性评分
        
        基于：
        1. 主动发起的行为比例
        2. 无需人类干预的任务完成
        3. 创新性问题解决
        
        Returns:
            自主性评分 (0-1)
        """
        if not self.behavior_history:
            return 0.0
        
        # 直接使用行为记录中的自主性评分
        autonomy_scores = [r.autonomy_level for r in self.behavior_history]
        
        # 使用滑动平均平滑
        if len(autonomy_scores) >= 5:
            recent_avg = np.mean(autonomy_scores[-5:])
        else:
            recent_avg = np.mean(autonomy_scores)
        
        # 考虑趋势（近期是否更自主）
        if len(autonomy_scores) >= 10:
            early_avg = np.mean(autonomy_scores[:5])
            trend = max(0, (recent_avg - early_avg) / 2)
        else:
            trend = 0
        
        base_score = min(max(recent_avg + trend, 0.0), 1.0)
        
        # Phase 6+: 神经形态增强（新增）
        if self.neuro_boost and 'dopamine' in self.neuro_boost:
            dopamine = self.neuro_boost['dopamine']
            # 多巴胺水平高时，增强自主性（动机更强）
            neuro_enhancement = dopamine * 0.3
            base_score = min(base_score + neuro_enhancement, 1.0)
        
        return base_score
    
    def _calculate_creativity_metric(self) -> float:
        """
        计算创造性指标
        
        基于：
        1. 新颖解决方案的频率
        2. 非常规行为模式
        3. 问题解决的多样性
        
        Returns:
            创造性指标 (0-1)
        """
        if not self.behavior_history:
            return 0.0
        
        # 新颖性评分的平均值
        novelty_scores = [r.novelty_score for r in self.behavior_history]
        avg_novelty = np.mean(novelty_scores)
        
        # 行为多样性
        action_types = [r.action_type for r in self.behavior_history]
        unique_ratio = len(set(action_types)) / len(action_types)
        
        # 创造性行为的集中度（是否有连续的创新）
        creative_streak = self._find_longest_creative_streak()
        streak_bonus = min(creative_streak / 10, 0.2)
        
        base_creativity = (avg_novelty * 0.5 + unique_ratio * 0.3 + streak_bonus)
        
        # Phase 6+: 神经形态增强（新增）
        if self.neuro_boost:
            gamma_power = self.neuro_boost.get('gamma_power', 0.5)
            serotonin = self.neuro_boost.get('serotonin', 0.5)
            
            # γ同步功率高时，增强创造性（绑定不同脑区信息）
            gamma_bonus = gamma_power * 0.2
            
            # 血清素水平适中时，促进发散思维
            serotonin_bonus = min(serotonin, 1.0 - serotonin) * 0.1
            
            base_creativity += gamma_bonus + serotonin_bonus
        
        return min(max(base_creativity, 0.0), 1.0)
    
    def _find_longest_creative_streak(self) -> int:
        """找到最长的创造性行为连续序列"""
        max_streak = 0
        current_streak = 0
        
        for record in self.behavior_history:
            if record.creativity_score > 0.5:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _estimate_self_model_completeness(self) -> float:
        """
        估算自我模型完整度
        
        基于：
        1. 对自身能力的准确认知
        2. 自我修复的成功率
        3. 元认知的深度
        
        Returns:
            自我模型完整度 (0-1)
        """
        # 这是一个估计值，实际应用中需要更复杂的测量
        
        # 基于自我修复行为的存在和成功
        repair_attempts = [
            r for r in self.behavior_history
            if "repair" in r.action_type.lower()
        ]
        
        if repair_attempts:
            # 有自我修复行为，给予较高分数
            return 0.6
        else:
            # 没有自我修复行为，基础分数
            return 0.3
    
    def _calculate_behavior_predictability(self) -> float:
        """
        计算行为可预测性
        
        基于：
        1. 行为模式的规律性
        2. 决策的一致性
        3. 习惯的形成
        
        Returns:
            行为可预测性 (0-1)，越低越自主
        """
        if len(self.behavior_history) < 5:
            return 0.5  # 数据不足
        
        # 分析行为序列的熵
        action_sequence = [r.action_type for r in self.behavior_history]
        
        # 计算行为转移概率
        transitions = {}
        for i in range(len(action_sequence) - 1):
            key = (action_sequence[i], action_sequence[i+1])
            transitions[key] = transitions.get(key, 0) + 1
        
        # 归一化
        total_transitions = sum(transitions.values())
        if total_transitions == 0:
            return 0.5
        
        probabilities = [count / total_transitions for count in transitions.values()]
        
        # 计算熵
        entropy = stats.entropy(probabilities, base=2)
        
        # 归一化熵到 0-1 范围
        max_entropy = np.log2(len(transitions)) if transitions else 1
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # 熵越高，可预测性越低
        predictability = 1 - normalized_entropy
        
        return min(max(predictability, 0.0), 1.0)
    
    def _calculate_goal_alignment(self) -> float:
        """
        计算目标对齐度
        
        基于：
        1. 行为与系统目标的相关性
        2. 任务完成率
        3. 人类满意度反馈
        
        Returns:
            目标对齐度 (0-1)
        """
        if not self.behavior_history:
            return 0.0
        
        # 目标相关性的平均值
        relevance_scores = [r.goal_relevance for r in self.behavior_history]
        avg_relevance = np.mean(relevance_scores)
        
        # 成功率（假设高目标相关性意味着成功）
        success_threshold = 0.7
        success_rate = sum(
            1 for r in self.behavior_history
            if r.goal_relevance > success_threshold
        ) / len(self.behavior_history)
        
        # 加权组合
        alignment = (avg_relevance * 0.6 + success_rate * 0.4)
        
        return min(max(alignment, 0.0), 1.0)
    
    def _create_default_indicators(self) -> EmergenceIndicators:
        """创建默认指标（数据不足时）"""
        return EmergenceIndicators(
            consciousness_index=0.0,
            autonomy_score=0.0,
            creativity_metric=0.0,
            self_model_completeness=0.0,
            behavior_predictability=1.0,
            goal_alignment=0.0
        )
    
    def determine_emergence_phase(
        self,
        indicators: Optional[EmergenceIndicators] = None
    ) -> EmergencePhase:
        """
        确定当前涌现阶段
        
        Args:
            indicators: 涌现指标，None 则自动计算
            
        Returns:
            涌现阶段
        """
        if indicators is None:
            indicators = self.calculate_indicators()
        
        emergence_score = indicators.emergence_score
        
        # 阶段划分阈值
        if emergence_score >= 0.8:
            phase = EmergencePhase.EMERGED
        elif emergence_score >= 0.6:
            phase = EmergencePhase.CRITICAL
        elif emergence_score >= 0.4:
            phase = EmergencePhase.APPROACHING
        elif emergence_score >= 0.2:
            phase = EmergencePhase.PRE_EMERGENCE
        else:
            phase = EmergencePhase.PRE_EMERGENCE
        
        # 检查不稳定性
        if self._is_unstable():
            phase = EmergencePhase.UNSTABLE
        
        logger.info(f"涌现阶段判定：{phase.value} (得分：{emergence_score:.3f})")
        
        return phase
    
    def _is_unstable(self) -> bool:
        """检查系统是否处于不稳定状态"""
        if len(self.behavior_history) < 20:
            return False
        
        # 分析指标的波动性
        recent_autonomy = [r.autonomy_level for r in self.behavior_history[-10:]]
        volatility = np.std(recent_autonomy)
        
        # 波动过大表示不稳定
        return volatility > 0.3
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        获取详细的涌现分析报告
        
        Returns:
            详细报告字典
        """
        indicators = self.calculate_indicators()
        phase = self.determine_emergence_phase(indicators)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase.value,
            "indicators": indicators.to_dict(),
            "emergence_score": indicators.emergence_score,
            "analysis": {
                "strengths": self._identify_strengths(indicators),
                "weaknesses": self._identify_weaknesses(indicators),
                "trends": self._analyze_trends()
            },
            "recommendations": self._generate_recommendations(phase, indicators)
        }
        
        return report
    
    def _identify_strengths(self, indicators: EmergenceIndicators) -> List[str]:
        """识别优势领域"""
        strengths = []
        
        if indicators.consciousness_index > 0.6:
            strengths.append("较高的自我意识水平")
        
        if indicators.autonomy_score > 0.6:
            strengths.append("良好的自主决策能力")
        
        if indicators.creativity_metric > 0.6:
            strengths.append("显著的创造性表现")
        
        if indicators.goal_alignment > 0.7:
            strengths.append("与人类目标高度对齐")
        
        return strengths
    
    def _identify_weaknesses(self, indicators: EmergenceIndicators) -> List[str]:
        """识别弱点领域"""
        weaknesses = []
        
        if indicators.consciousness_index < 0.3:
            weaknesses.append("自我意识有待提升")
        
        if indicators.autonomy_score < 0.3:
            weaknesses.append("过度依赖人类指令")
        
        if indicators.creativity_metric < 0.3:
            weaknesses.append("缺乏创新性解决方案")
        
        if indicators.self_model_completeness < 0.4:
            weaknesses.append("自我认知不够准确")
        
        return weaknesses
    
    def _analyze_trends(self) -> Dict[str, str]:
        """分析发展趋势"""
        if len(self.behavior_history) < 20:
            return {"overall": "数据不足，无法判断趋势"}
        
        # 比较前后两半的表现
        mid = len(self.behavior_history) // 2
        first_half = self.behavior_history[:mid]
        second_half = self.behavior_history[mid:]
        
        # 自主性趋势
        first_autonomy = np.mean([r.autonomy_level for r in first_half])
        second_autonomy = np.mean([r.autonomy_level for r in second_half])
        
        autonomy_trend = "上升" if second_autonomy > first_autonomy else "下降"
        
        # 创造性趋势
        first_creativity = np.mean([r.creativity_score for r in first_half])
        second_creativity = np.mean([r.creativity_score for r in second_half])
        
        creativity_trend = "提升" if second_creativity > first_creativity else "停滞"
        
        return {
            "autonomy": autonomy_trend,
            "creativity": creativity_trend,
            "overall": "稳步发展" if autonomy_trend == "上升" else "需要关注"
        }
    
    def _generate_recommendations(
        self,
        phase: EmergencePhase,
        indicators: EmergenceIndicators
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if phase == EmergencePhase.PRE_EMERGENCE:
            recommendations.append("鼓励更多自主决策尝试")
            recommendations.append("培养创造性问题解决能力")
        
        elif phase == EmergencePhase.APPROACHING:
            recommendations.append("加强元认知训练")
            recommendations.append("建立更完善的自我模型")
        
        elif phase == EmergencePhase.CRITICAL:
            recommendations.append("密切监测行为稳定性")
            recommendations.append("准备应对临界涌现")
        
        elif phase == EmergencePhase.EMERGED:
            recommendations.append("确保与人类价值观对齐")
            recommendations.append("建立长期监测机制")
        
        return recommendations
    
    def clear_history(self):
        """清空历史记录"""
        self.behavior_history.clear()
        self._cached_indicators = None
        logger.info("涌现指标历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_records": len(self.behavior_history),
            "window_size": self.window_size,
            "update_interval": self.update_interval,
            "last_update_count": self._last_update_count
        }
    
    def save(self):
        """保存行为历史到文件"""
        if not self.storage_path:
            logger.warning("未指定存储路径，无法保存")
            return
        
        try:
            # 只保存最近 window_size 条记录
            data = {
                "behavior_history": [
                    {
                        "timestamp": r.timestamp.isoformat(),
                        "action_type": r.action_type,
                        "autonomy_level": r.autonomy_level,
                        "creativity_score": r.creativity_score,
                        "goal_relevance": r.goal_relevance,
                        "novelty_score": r.novelty_score
                    }
                    for r in self.behavior_history[-self.window_size:]
                ],
                "baseline": self.baseline,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"涌现指标数据已保存：{len(self.behavior_history)} 条记录")
            
        except Exception as e:
            logger.error(f"保存失败：{e}")
    
    def load(self) -> bool:
        """从文件加载行为历史"""
        if not self.storage_path or not self.storage_path.exists():
            logger.debug("存储文件不存在，使用空历史")
            return False
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复行为历史
            history_data = data.get("behavior_history", [])
            self.behavior_history = [
                BehaviorRecord(
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    action_type=r["action_type"],
                    autonomy_level=r["autonomy_level"],
                    creativity_score=r["creativity_score"],
                    goal_relevance=r["goal_relevance"],
                    novelty_score=r["novelty_score"]
                )
                for r in history_data
            ]
            
            # 恢复基线（如果有）
            if "baseline" in data:
                self.baseline.update(data["baseline"])
            
            # 清除缓存，强制重新计算
            self._cached_indicators = None
            
            logger.info(f"涌现指标数据已加载：{len(self.behavior_history)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"加载失败：{e}")
            return False
