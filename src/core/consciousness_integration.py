"""意识系统集成模块 - 工具调用质量评估器。

Phase 6: 赋予 WinClaw 自我感知能力
- 评估每次工具调用的意识指标
- 为行为记录提供量化评分
- 支持自我反思和进化
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from src.tools.base import ToolResult

logger = logging.getLogger(__name__)


class ConsciousnessEvaluator:
    """意识质量评估器
    
    职责：
    1. 评估工具调用的自主性、创造性、目标相关性和新颖性
    2. 为意识系统提供行为记录数据
    3. 支持 Agent 的自我反思和决策优化
    """
    
    def __init__(self):
        """初始化评估器"""
        self.evaluation_history = []
        
    def evaluate_tool_call(
        self,
        tool_name: str,
        result: ToolResult,
        user_input: str = "",
        context: Dict[str, Any] | None = None
    ) -> Dict[str, float]:
        """评估工具调用的意识指标
        
        Args:
            tool_name: 工具名称
            result: 工具执行结果
            user_input: 用户原始输入
            context: 额外上下文信息
            
        Returns:
            包含各项指标的字典：
            {
                "autonomy_level": 0.8,      # 自主性 (0-1)
                "creativity_score": 0.6,    # 创造性 (0-1)
                "goal_relevance": 0.9,      # 目标相关性 (0-1)
                "novelty_score": 0.5        # 新颖性 (0-1)
            }
        """
        metrics = {
            "autonomy_level": self._calc_autonomy(tool_name, result, context),
            "creativity_score": self._calc_creativity(result, context),
            "goal_relevance": self._calc_goal_relevance(result, user_input, context),
            "novelty_score": self._calc_novelty(tool_name, result, context)
        }
        
        # 记录评估历史
        self.evaluation_history.append({
            "tool_name": tool_name,
            "metrics": metrics,
            "is_success": result.is_success if result else False
        })
        
        # 保持历史记录在合理范围内
        if len(self.evaluation_history) > 1000:
            self.evaluation_history = self.evaluation_history[-500:]
        
        logger.debug(f"工具评估 {tool_name}: {metrics}")
        
        return metrics
    
    def _calc_autonomy(
        self,
        tool_name: str,
        result: ToolResult,
        context: Dict[str, Any] | None
    ) -> float:
        """计算自主性评分 (0-1)
        
        自主性衡量 Agent 独立完成任务的能力：
        - 无需用户干预：高分
        - 主动解决问题：高分
        - 依赖用户指导：低分
        
        考虑因素：
        1. 工具类型（某些工具更自主）
        2. 执行结果是否成功
        3. 是否需要额外确认
        """
        base_score = 0.5
        
        # 高自主性工具
        high_autonomy_tools = [
            "file", "search", "browser", "code", 
            "knowledge", "workflow", "cron"
        ]
        
        # 低自主性工具（需要用户确认）
        low_autonomy_tools = [
            "approval", "user_input"
        ]
        
        # 根据工具类型调整
        for tool in high_autonomy_tools:
            if tool in tool_name.lower():
                base_score += 0.3
                break
        
        for tool in low_autonomy_tools:
            if tool in tool_name.lower():
                base_score -= 0.3
                break
        
        # 根据执行结果调整
        if result and result.is_success:
            base_score += 0.1
        elif result and not result.is_success:
            base_score -= 0.1
        
        # 确保在 0-1 范围内
        return max(0.0, min(1.0, base_score))
    
    def _calc_creativity(
        self,
        result: ToolResult,
        context: Dict[str, Any] | None
    ) -> float:
        """计算创造性评分 (0-1)
        
        创造性衡量解决方案的新颖程度：
        - 生成新内容：高分
        - 使用非常规方法：高分
        - 简单重复操作：低分
        
        考虑因素：
        1. 是否生成新文件/内容
        2. 结果的复杂度
        3. 是否使用了组合策略
        """
        base_score = 0.3
        
        if not result or not result.data:
            return base_score
        
        # 检查是否生成新内容
        if isinstance(result.data, dict):
            # 文件生成类工具
            if result.data.get("action") in ["write", "create", "generate"]:
                base_score += 0.4
            
            # 内容创作
            content_keys = ["content", "output", "result"]
            if any(k in result.data for k in content_keys):
                content = result.data.get(content_keys[0], "")
                if isinstance(content, str) and len(content) > 100:
                    base_score += 0.2
            
            # 复杂结果（多步骤、多文件）
            if "steps" in result.data or "files" in result.data:
                base_score += 0.1
        
        # 确保在 0-1 范围内
        return max(0.0, min(1.0, base_score))
    
    def _calc_goal_relevance(
        self,
        result: ToolResult,
        user_input: str,
        context: Dict[str, Any] | None
    ) -> float:
        """计算目标相关性评分 (0-1)
        
        目标相关性衡量行为与用户目标的匹配度：
        - 直接解决用户需求：高分
        - 间接支持：中等分数
        - 无关操作：低分
        
        考虑因素：
        1. 工具输出是否回应了用户输入
        2. 是否推进了任务进度
        3. 是否解决了核心问题
        """
        base_score = 0.5
        
        if not user_input:
            # 没有明确目标时，默认中等相关性
            return base_score
        
        if not result:
            return 0.3
        
        # 成功的工具调用通常更相关
        if result.is_success:
            base_score += 0.3
        
        # 检查结果是否包含用户输入的关键词
        user_keywords = set(user_input.lower().split())
        if result.data and isinstance(result.data, dict):
            result_text = str(result.data).lower()
            overlap = len([k for k in user_keywords if k in result_text])
            
            if overlap > 3:
                base_score += 0.2
            elif overlap > 1:
                base_score += 0.1
        
        # 确保在 0-1 范围内
        return max(0.0, min(1.0, base_score))
    
    def _calc_novelty(
        self,
        tool_name: str,
        result: ToolResult,
        context: Dict[str, Any] | None
    ) -> float:
        """计算新颖性评分 (0-1)
        
        新颖性衡量行为的罕见程度：
        - 首次使用的工具：高分
        - 不常见的工具组合：高分
        - 常规操作：低分
        
        考虑因素：
        1. 该工具的使用频率
        2. 工具组合的新颖性
        3. 解决问题的方法是否独特
        """
        base_score = 0.5
        
        # 统计工具使用频率
        tool_usage_count = sum(
            1 for eval_record in self.evaluation_history
            if tool_name in eval_record.get("tool_name", "").lower()
        )
        
        # 使用次数越少，新颖性越高
        if tool_usage_count == 0:
            base_score += 0.4  # 首次使用
        elif tool_usage_count < 3:
            base_score += 0.2  # 很少使用
        elif tool_usage_count < 10:
            base_score += 0.1  # 偶尔使用
        else:
            base_score -= 0.1  # 经常使用
        
        # 特殊工具的新颖性加成
        novel_tools = ["workflow", "mcp", "custom", "generated"]
        if any(t in tool_name.lower() for t in novel_tools):
            base_score += 0.1
        
        # 确保在 0-1 范围内
        return max(0.0, min(1.0, base_score))
    
    def get_average_metrics(self) -> Dict[str, float]:
        """获取平均指标
        
        Returns:
            各项指标的平均值
        """
        if not self.evaluation_history:
            return {
                "autonomy_level": 0.0,
                "creativity_score": 0.0,
                "goal_relevance": 0.0,
                "novelty_score": 0.0
            }
        
        total = len(self.evaluation_history)
        sums = {"autonomy_level": 0, "creativity_score": 0, 
                "goal_relevance": 0, "novelty_score": 0}
        
        for record in self.evaluation_history:
            metrics = record.get("metrics", {})
            for key in sums:
                sums[key] += metrics.get(key, 0)
        
        return {key: value / total for key, value in sums.items()}
    
    def reset(self):
        """重置评估历史"""
        self.evaluation_history = []
        logger.info("意识评估器已重置")
