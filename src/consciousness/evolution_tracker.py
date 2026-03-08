"""
进化追踪器

WinClaw 意识系统 - Phase 4: Evolution Tracker

功能概述：
- 记录系统进化历史
- 追踪能力发展曲线
- 分析学习模式
- 识别进化关键节点
- 预测未来发展方向

追踪维度：
1. 能力进化 - 工具使用、问题解决能力
2. 认知进化 - 自我模型、元认知能力
3. 行为进化 - 自主性、创造性、习惯形成
4. 社会进化 - 人机协作、目标对齐

作者：WinClaw Consciousness Team
版本：v0.4.0 (Phase 4)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
import json
import logging
from pathlib import Path

from .types import EvolutionRecord, RepairAction, EmergenceIndicators
from .emergence_metrics import EmergenceMetricsCalculator

logger = logging.getLogger(__name__)


@dataclass
class CapabilityMilestone:
    """能力里程碑"""
    milestone_id: str
    capability_name: str
    achievement_level: float  # 达成水平 0-1
    achieved_at: datetime
    description: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class LearningCurve:
    """学习曲线"""
    skill_name: str
    start_time: datetime
    data_points: List[Tuple[datetime, float]]  # (时间，表现评分)
    
    def get_trend(self) -> str:
        """获取趋势"""
        if len(self.data_points) < 3:
            return "insufficient_data"
        
        # 简单线性回归
        x = list(range(len(self.data_points)))
        y = [point[1] for point in self.data_points]
        
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 0.05:
            return "improving"
        elif slope < -0.05:
            return "declining"
        else:
            return "stable"


class EvolutionTracker:
    """
    进化追踪器
    
    职责：
    1. 记录进化事件
    2. 构建学习曲线
    3. 识别里程碑
    4. 分析进化模式
    5. 预测发展趋势
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        auto_save: bool = True
    ):
        """
        初始化进化追踪器
        
        Args:
            storage_path: 存储路径（可选）
            auto_save: 是否自动保存
        """
        self.storage_path = storage_path
        self.auto_save = auto_save
        
        # 进化历史记录
        self.evolution_history: List[EvolutionRecord] = []
        
        # 能力里程碑
        self.milestones: List[CapabilityMilestone] = []
        
        # 学习曲线数据
        self.learning_curves: Dict[str, LearningCurve] = {}
        
        # 当前进化代数
        self.current_generation = 0
        
        # 基线能力值
        self.baseline_capabilities = {
            "tool_usage": 0.1,
            "problem_solving": 0.1,
            "self_awareness": 0.0,
            "autonomy": 0.1,
            "creativity": 0.1
        }
        
        # 当前能力值
        self.current_capabilities = self.baseline_capabilities.copy()
        
        logger.info("进化追踪器初始化完成")
    
    def record_evolution(
        self,
        changes: List[RepairAction],
        performance_before: Dict,
        performance_after: Dict,
        human_approved: bool
    ) -> EvolutionRecord:
        """
        记录一次进化事件
        
        Args:
            changes: 修复/进化动作列表
            performance_before: 进化前性能
            performance_after: 进化后性能
            human_approved: 是否经过人类批准
            
        Returns:
            进化记录
        """
        import uuid
        
        self.current_generation += 1
        
        evolution = EvolutionRecord(
            evolution_id=f"evo_{uuid.uuid4().hex[:8]}",
            generation=self.current_generation,
            changes=changes,
            performance_before=performance_before,
            performance_after=performance_after,
            human_approved=human_approved
        )
        
        self.evolution_history.append(evolution)
        
        # 更新当前能力值
        self._update_capabilities(performance_after)
        
        # 检查是否达成里程碑
        self._check_milestones()
        
        # 自动保存
        if self.auto_save and self.storage_path:
            self.save()
        
        logger.info(f"记录进化事件 #{self.current_generation}")
        
        return evolution
    
    def _update_capabilities(self, performance: Dict):
        """更新当前能力值"""
        # 简单的指数移动平均更新
        alpha = 0.3  # 平滑因子
        
        for cap_name, value in performance.items():
            if cap_name in self.current_capabilities:
                old_value = self.current_capabilities[cap_name]
                self.current_capabilities[cap_name] = (
                    alpha * value + (1 - alpha) * old_value
                )
    
    def _check_milestones(self):
        """检查是否达成新的里程碑"""
        milestone_thresholds = {
            "tool_usage": [0.3, 0.5, 0.7, 0.9],
            "problem_solving": [0.3, 0.5, 0.7, 0.9],
            "self_awareness": [0.2, 0.4, 0.6, 0.8],
            "autonomy": [0.3, 0.5, 0.7, 0.9],
            "creativity": [0.3, 0.5, 0.7, 0.9]
        }
        
        for cap_name, thresholds in milestone_thresholds.items():
            current_value = self.current_capabilities.get(cap_name, 0)
            
            for threshold in thresholds:
                if abs(current_value - threshold) < 0.05:
                    # 接近阈值，可能达成了新里程碑
                    self._create_milestone(cap_name, current_value)
    
    def _create_milestone(
        self,
        capability_name: str,
        achievement_level: float
    ):
        """创建里程碑记录"""
        import uuid
        
        # 检查是否已存在相同里程碑
        existing = [
            m for m in self.milestones
            if m.capability_name == capability_name and
               abs(m.achievement_level - achievement_level) < 0.01
        ]
        
        if existing:
            return  # 已存在，不重复创建
        
        descriptions = {
            "tool_usage": f"工具使用能力达到新高度 ({achievement_level:.1%})",
            "problem_solving": f"问题解决能力突破 ({achievement_level:.1%})",
            "self_awareness": f"自我意识水平提升 ({achievement_level:.1%})",
            "autonomy": f"自主决策能力增强 ({achievement_level:.1%})",
            "creativity": f"创造性思维发展 ({achievement_level:.1%})"
        }
        
        milestone = CapabilityMilestone(
            milestone_id=f"milestone_{uuid.uuid4().hex[:8]}",
            capability_name=capability_name,
            achievement_level=achievement_level,
            achieved_at=datetime.now(),
            description=descriptions.get(
                capability_name,
                f"{capability_name} 达到 {achievement_level:.1%}"
            )
        )
        
        self.milestones.append(milestone)
        
        logger.info(f"达成里程碑：{capability_name} = {achievement_level:.3f}")
    
    def update_learning_curve(
        self,
        skill_name: str,
        performance_score: float
    ):
        """
        更新学习曲线
        
        Args:
            skill_name: 技能名称
            performance_score: 表现评分 0-1
        """
        now = datetime.now()
        
        if skill_name not in self.learning_curves:
            # 创建新的学习曲线
            self.learning_curves[skill_name] = LearningCurve(
                skill_name=skill_name,
                start_time=now,
                data_points=[(now, performance_score)]
            )
        else:
            # 添加数据点
            curve = self.learning_curves[skill_name]
            curve.data_points.append((now, performance_score))
            
            # 保持合理大小
            if len(curve.data_points) > 100:
                curve.data_points.pop(0)
    
    def analyze_evolution_pattern(self) -> Dict[str, Any]:
        """
        分析进化模式
        
        Returns:
            进化模式分析结果
        """
        if len(self.evolution_history) < 3:
            return {"pattern": "insufficient_data"}
        
        # 分析进化频率
        timestamps = [e.timestamp for e in self.evolution_history]
        time_diffs = [
            (timestamps[i+1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps)-1)
        ]
        
        avg_interval = np.mean(time_diffs) if time_diffs else 0
        
        # 分析进化幅度
        magnitudes = [
            self._calculate_evolution_magnitude(e)
            for e in self.evolution_history
        ]
        
        avg_magnitude = np.mean(magnitudes)
        
        # 识别模式
        if avg_interval < 3600 and avg_magnitude > 0.5:
            pattern = "rapid_evolution"  # 快速进化
        elif avg_interval > 86400 and avg_magnitude < 0.3:
            pattern = "gradual_improvement"  # 渐进改善
        elif avg_magnitude > 0.7:
            pattern = "punctuated_equilibrium"  # 间断平衡
        else:
            pattern = "steady_development"  # 稳定发展
        
        analysis = {
            "pattern": pattern,
            "avg_evolution_interval_hours": avg_interval / 3600,
            "avg_evolution_magnitude": avg_magnitude,
            "total_evolutions": len(self.evolution_history),
            "trend": self._analyze_evolution_trend()
        }
        
        return analysis
    
    def _calculate_evolution_magnitude(
        self,
        evolution: EvolutionRecord
    ) -> float:
        """计算进化幅度"""
        # 基于性能变化的幅度
        before = evolution.performance_before
        after = evolution.performance_after
        
        if not before or not after:
            return 0.0
        
        # 计算平均变化率
        changes = []
        for key in after:
            if key in before:
                change = abs(after[key] - before.get(key, 0))
                changes.append(change)
        
        return np.mean(changes) if changes else 0.0
    
    def _analyze_evolution_trend(self) -> str:
        """分析进化趋势"""
        if len(self.evolution_history) < 5:
            return "unclear"
        
        # 比较最近和早期的进化幅度
        recent_magnitudes = [
            self._calculate_evolution_magnitude(e)
            for e in self.evolution_history[-5:]
        ]
        
        early_magnitudes = [
            self._calculate_evolution_magnitude(e)
            for e in self.evolution_history[:5]
        ]
        
        recent_avg = np.mean(recent_magnitudes)
        early_avg = np.mean(early_magnitudes)
        
        if recent_avg > early_avg * 1.2:
            return "accelerating"
        elif recent_avg < early_avg * 0.8:
            return "decelerating"
        else:
            return "stable"
    
    def predict_future_development(
        self,
        horizon_days: int = 7
    ) -> Dict[str, Any]:
        """
        预测未来发展
        
        Args:
            horizon_days: 预测时间范围（天）
            
        Returns:
            预测结果
        """
        if len(self.evolution_history) < 5:
            return {"prediction": "insufficient_data"}
        
        # 基于历史趋势的简单外推
        pattern_analysis = self.analyze_evolution_pattern()
        
        # 预测能力增长
        predicted_capabilities = {}
        
        for cap_name, current_value in self.current_capabilities.items():
            # 获取该能力的学习曲线
            if cap_name in self.learning_curves:
                curve = self.learning_curves[cap_name]
                trend = curve.get_trend()
                
                if trend == "improving":
                    growth_rate = 0.1  # 每天增长 10%
                elif trend == "declining":
                    growth_rate = -0.05
                else:
                    growth_rate = 0.0
            else:
                growth_rate = 0.02  # 默认缓慢增长
            
            # 预测未来值
            predicted_value = min(
                current_value * (1 + growth_rate) ** horizon_days,
                1.0
            )
            
            predicted_capabilities[cap_name] = {
                "current": current_value,
                "predicted": predicted_value,
                "growth_rate": growth_rate
            }
        
        prediction = {
            "horizon_days": horizon_days,
            "predicted_capabilities": predicted_capabilities,
            "confidence": "low" if len(self.evolution_history) < 10 else "medium",
            "key_factors": self._identify_development_factors()
        }
        
        return prediction
    
    def _identify_development_factors(self) -> List[str]:
        """识别影响发展的关键因素"""
        factors = []
        
        # 基于进化历史分析
        if len(self.evolution_history) > 0:
            recent_changes = self.evolution_history[-5:]
            
            # 检查是否有频繁的修复
            repair_count = sum(
                len(e.changes) for e in recent_changes
            )
            
            if repair_count > 10:
                factors.append("频繁的修复和优化")
            
            # 检查能力发展趋势
            if self.current_capabilities["autonomy"] > 0.5:
                factors.append("自主性显著提升")
            
            if self.current_capabilities["creativity"] > 0.5:
                factors.append("创造性能力增强")
        
        return factors
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """
        获取进化总结
        
        Returns:
            进化总结报告
        """
        return {
            "generation": self.current_generation,
            "total_evolutions": len(self.evolution_history),
            "milestones_achieved": len(self.milestones),
            "current_capabilities": self.current_capabilities,
            "evolution_pattern": self.analyze_evolution_pattern(),
            "learning_curves": {
                name: {
                    "trend": curve.get_trend(),
                    "data_points": len(curve.data_points)
                }
                for name, curve in self.learning_curves.items()
            },
            "recent_milestones": [
                {
                    "capability": m.capability_name,
                    "level": m.achievement_level,
                    "achieved_at": m.achieved_at.isoformat()
                }
                for m in self.milestones[-5:]
            ]
        }
    
    def save(self):
        """保存到文件"""
        if not self.storage_path:
            logger.warning("未指定存储路径，无法保存")
            return
        
        try:
            data = {
                "current_generation": self.current_generation,
                "current_capabilities": self.current_capabilities,
                "evolution_history": [
                    self._serialize_evolution(e)
                    for e in self.evolution_history[-50:]  # 只保存最近 50 条
                ],
                "milestones": [
                    {
                        "milestone_id": m.milestone_id,
                        "capability_name": m.capability_name,
                        "achievement_level": m.achievement_level,
                        "achieved_at": m.achieved_at.isoformat(),
                        "description": m.description
                    }
                    for m in self.milestones
                ],
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"进化数据已保存到：{self.storage_path}")
            
        except Exception as e:
            logger.error(f"保存失败：{e}")
    
    def load(self) -> bool:
        """从文件加载"""
        if not self.storage_path or not self.storage_path.exists():
            return False
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.current_generation = data.get("current_generation", 0)
            self.current_capabilities = data.get(
                "current_capabilities",
                self.baseline_capabilities.copy()
            )
            
            # 注意：这里简化处理，实际应该重建完整的对象
            logger.info(f"从 {self.storage_path} 加载进化数据")
            
            return True
            
        except Exception as e:
            logger.error(f"加载失败：{e}")
            return False
    
    def _serialize_evolution(self, evolution: EvolutionRecord) -> Dict:
        """序列化进化记录"""
        return {
            "evolution_id": evolution.evolution_id,
            "generation": evolution.generation,
            "timestamp": evolution.timestamp.isoformat(),
            "performance_before": evolution.performance_before,
            "performance_after": evolution.performance_after,
            "human_approved": evolution.human_approved
        }
    
    def clear_history(self):
        """清空历史"""
        self.evolution_history.clear()
        self.milestones.clear()
        self.learning_curves.clear()
        self.current_capabilities = self.baseline_capabilities.copy()
        self.current_generation = 0
        logger.info("进化历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "generation": self.current_generation,
            "total_evolutions": len(self.evolution_history),
            "total_milestones": len(self.milestones),
            "tracked_skills": len(self.learning_curves),
            "storage_path": str(self.storage_path) if self.storage_path else None
        }
