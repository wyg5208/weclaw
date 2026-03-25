"""主动陪伴系统核心引擎 — 决策"何时"、"说什么"、"怎么说"。

本模块是 WeClaw AI 桌面助手主动陪伴系统的大脑，负责：
- CooldownManager: 防骚扰冷却机制，控制主动交互频率
- MoodDetector: 情绪检测，根据用户文本分析情绪
- OpportunityDetector: 时机检测，监听用户行为检测关怀时机
- InteractionOrchestrator: 交互编排，管理主动交互的执行流程
- CompanionEngine: 核心调度器，整合所有组件进行决策

使用示例:
    from src.core.companion_engine import CompanionEngine
    from src.core.event_bus import EventBus
    
    event_bus = EventBus()
    engine = CompanionEngine(event_bus)
    await engine.on_cron_trigger("morning_greeting")
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator

from src.core.companion_topics import (
    CareTopic,
    CareTopicRegistry,
    INFERENCE_RULES,
    MOOD_KEYWORDS,
    get_time_slot,
)
from src.core.event_bus import EventBus
from src.core.events import EventType

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".winclaw" / "winclaw_tools.db"


# ============================================================================
# CooldownManager — 防骚扰冷却机制
# ============================================================================

class CooldownManager:
    """防骚扰冷却机制。
    
    控制主动交互的频率，防止对用户造成骚扰。
    支持以下特性：
    - 每日交互预算（可动态调整）
    - 连续忽略检测
    - 拒绝惩罚（被拒绝后延长冷却期）
    - 状态持久化到 SQLite
    
    Attributes:
        daily_budget: 每日主动交互配额
        min_budget: 最小配额下限
        max_budget: 最大配额上限
        consecutive_limit: 允许的连续忽略次数
        rejection_penalty_hours: 被拒绝后的惩罚冷却时长（小时）
    """
    
    def __init__(self, db_path: Path):
        """初始化冷却管理器。
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.daily_budget: int = 5
        self.min_budget: int = 2
        self.max_budget: int = 8
        self.consecutive_limit: int = 2
        self.rejection_penalty_hours: int = 4
        self._interaction_lock: asyncio.Lock = asyncio.Lock()
        self._db_path = db_path
        self._current_topic_id: str | None = None
        
        # 从数据库恢复状态
        self._load_state()
    
    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接的上下文管理器。"""
        conn = sqlite3.connect(str(self._db_path))
        try:
            yield conn
        finally:
            conn.close()
    
    def _load_state(self) -> None:
        """从数据库加载持久化状态。"""
        try:
            with self._conn() as conn:
                # 加载每日预算
                row = conn.execute(
                    "SELECT value FROM companion_state WHERE key = 'daily_budget'"
                ).fetchone()
                if row:
                    self.daily_budget = int(row[0])
                
                # 检查是否需要重置每日计数（新的一天）
                row = conn.execute(
                    "SELECT value FROM companion_state WHERE key = 'last_reset_date'"
                ).fetchone()
                today = datetime.now().strftime("%Y-%m-%d")
                if not row or row[0] != today:
                    self.reset_daily_count()
        except sqlite3.OperationalError:
            # 表可能不存在，忽略
            pass
    
    def _save_state(self, key: str, value: str) -> None:
        """保存状态到数据库。"""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO companion_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
            conn.commit()
    
    def _get_state(self, key: str, default: str = "") -> str:
        """从数据库获取状态。"""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT value FROM companion_state WHERE key = ?", (key,)
                ).fetchone()
                return row[0] if row else default
        except sqlite3.OperationalError:
            return default
    
    def can_interact(self) -> bool:
        """检查是否可以进行主动交互。
        
        Returns:
            True 如果可以交互，False 如果受限
        """
        # 检查每日配额
        daily_count = self.get_daily_count()
        if daily_count >= self.daily_budget:
            logger.debug("每日配额已用完: %d/%d", daily_count, self.daily_budget)
            return False
        
        # 检查拒绝惩罚冷却期
        last_rejection = self._get_state("last_rejection_time")
        if last_rejection:
            try:
                rejection_time = datetime.fromisoformat(last_rejection)
                penalty_end = rejection_time + timedelta(hours=self.rejection_penalty_hours)
                if datetime.now() < penalty_end:
                    logger.debug("仍在拒绝惩罚期内，需等待至 %s", penalty_end)
                    return False
            except ValueError:
                pass
        
        # 检查连续忽略次数
        consecutive_ignores = int(self._get_state("consecutive_ignores", "0"))
        if consecutive_ignores >= self.consecutive_limit:
            logger.debug("连续忽略次数过多: %d", consecutive_ignores)
            return False
        
        return True
    
    async def acquire_interaction_lock(self, topic_id: str) -> bool:
        """尝试获取交互锁。
        
        同一时间只允许一个主动交互进行。
        
        Args:
            topic_id: 要执行的主题 ID
            
        Returns:
            True 如果成功获取锁，False 如果锁已被占用
        """
        if self._interaction_lock.locked():
            logger.debug("交互锁已被占用，topic_id: %s", self._current_topic_id)
            return False
        
        await self._interaction_lock.acquire()
        self._current_topic_id = topic_id
        return True
    
    def release_interaction_lock(self) -> None:
        """释放交互锁。"""
        self._current_topic_id = None
        if self._interaction_lock.locked():
            self._interaction_lock.release()
    
    def record_interaction(self, topic_id: str, outcome: str) -> None:
        """记录一次交互结果。
        
        Args:
            topic_id: 主题 ID
            outcome: 结果类型 (completed/ignored/rejected/triggered)
        """
        now = datetime.now().isoformat()
        
        # 更新主题的最后交互时间
        self._save_state(f"last_interaction_{topic_id}", now)
        
        # 更新每日计数
        daily_count = self.get_daily_count()
        self._save_state("daily_count", str(daily_count + 1))
        
        # 处理不同的结果
        if outcome == "rejected":
            # 被拒绝，记录惩罚开始时间
            self._save_state("last_rejection_time", now)
            self._save_state("consecutive_ignores", "0")  # 重置忽略计数
            logger.info("用户拒绝了主动关怀，进入 %d 小时冷却期", self.rejection_penalty_hours)
        elif outcome == "ignored":
            # 被忽略，增加连续忽略计数
            consecutive = int(self._get_state("consecutive_ignores", "0"))
            self._save_state("consecutive_ignores", str(consecutive + 1))
            logger.debug("用户忽略了主动关怀，连续忽略: %d", consecutive + 1)
        elif outcome in ("completed", "triggered"):
            # 成功完成，重置连续忽略计数
            self._save_state("consecutive_ignores", "0")
    
    def hours_since(self, topic_id: str) -> float:
        """获取距离上次交互的小时数。
        
        Args:
            topic_id: 主题 ID
            
        Returns:
            小时数，如果从未交互过返回无穷大
        """
        last_time = self._get_state(f"last_interaction_{topic_id}")
        if not last_time:
            return float("inf")
        
        try:
            last_dt = datetime.fromisoformat(last_time)
            delta = datetime.now() - last_dt
            return delta.total_seconds() / 3600
        except ValueError:
            return float("inf")
    
    def get_daily_count(self) -> int:
        """获取今日已交互次数。
        
        Returns:
            今日交互次数
        """
        return int(self._get_state("daily_count", "0"))
    
    def reset_daily_count(self) -> None:
        """重置每日计数（每天自动调用）。"""
        today = datetime.now().strftime("%Y-%m-%d")
        self._save_state("daily_count", "0")
        self._save_state("last_reset_date", today)
        self._save_state("consecutive_ignores", "0")
        logger.debug("每日计数已重置")
    
    def adjust_budget(self, user_response: str, consecutive_ignores: int) -> None:
        """根据用户反馈调整每日配额。
        
        Args:
            user_response: 用户反馈类型 (positive/negative/neutral)
            consecutive_ignores: 连续忽略次数
        """
        old_budget = self.daily_budget
        
        if user_response == "positive":
            # 正面反馈，可能增加配额
            if consecutive_ignores == 0:
                self.daily_budget = min(self.daily_budget + 1, self.max_budget)
        elif user_response == "negative" or consecutive_ignores >= 2:
            # 负面反馈或多次忽略，减少配额
            self.daily_budget = max(self.daily_budget - 1, self.min_budget)
        
        if self.daily_budget != old_budget:
            self._save_state("daily_budget", str(self.daily_budget))
            logger.info("每日配额调整: %d → %d", old_budget, self.daily_budget)


# ============================================================================
# MoodDetector — 情绪检测
# ============================================================================

class MoodDetector:
    """关键词匹配情绪检测器。
    
    通过分析用户文本中的关键词来推断情绪状态。
    支持识别积极、消极、中性情绪，以及压力、疲惫等子情绪。
    """
    
    def detect_mood_from_text(self, text: str) -> dict[str, Any]:
        """从文本检测情绪。
        
        Args:
            text: 用户输入的文本
            
        Returns:
            包含情绪信息的字典:
            - mood: "positive"/"negative"/"neutral"
            - sub_mood: "stressed"/"tired"/None
            - confidence: 置信度 (0.0-1.0)
            - matched_keyword: 匹配到的关键词或 None
        """
        if not text:
            return {
                "mood": "neutral",
                "sub_mood": None,
                "confidence": 0.0,
                "matched_keyword": None,
            }
        
        text_lower = text.lower()
        
        # 检查各类情绪关键词
        positive_matches = []
        negative_matches = []
        stressed_matches = []
        tired_matches = []
        
        for keyword in MOOD_KEYWORDS.get("positive", []):
            if keyword in text_lower:
                positive_matches.append(keyword)
        
        for keyword in MOOD_KEYWORDS.get("negative", []):
            if keyword in text_lower:
                negative_matches.append(keyword)
        
        for keyword in MOOD_KEYWORDS.get("stressed", []):
            if keyword in text_lower:
                stressed_matches.append(keyword)
        
        for keyword in MOOD_KEYWORDS.get("tired", []):
            if keyword in text_lower:
                tired_matches.append(keyword)
        
        # 计算情绪得分
        positive_score = len(positive_matches)
        negative_score = len(negative_matches) + len(stressed_matches) + len(tired_matches)
        
        # 决定主情绪
        if positive_score > negative_score:
            mood = "positive"
            matched = positive_matches[0] if positive_matches else None
            confidence = min(0.5 + positive_score * 0.15, 1.0)
        elif negative_score > positive_score:
            mood = "negative"
            matched = (negative_matches or stressed_matches or tired_matches)[0]
            confidence = min(0.5 + negative_score * 0.15, 1.0)
        else:
            mood = "neutral"
            matched = None
            confidence = 0.3 if (positive_score + negative_score) == 0 else 0.5
        
        # 决定子情绪
        sub_mood = None
        if stressed_matches:
            sub_mood = "stressed"
        elif tired_matches:
            sub_mood = "tired"
        
        return {
            "mood": mood,
            "sub_mood": sub_mood,
            "confidence": confidence,
            "matched_keyword": matched,
        }
    
    def get_mood_adjusted_topic_score(self, topic: CareTopic, mood: dict[str, Any]) -> float:
        """根据情绪调整关怀主题分数。
        
        Args:
            topic: 关怀主题
            mood: 情绪检测结果
            
        Returns:
            调整后的分数增量（可正可负）
        """
        adjustment = 0.0
        sub_mood = mood.get("sub_mood")
        mood_type = mood.get("mood", "neutral")
        
        if sub_mood == "stressed":
            # 压力状态：提升情感关怀，降低琐事
            if topic.category == "emotional":
                adjustment += 15
            elif topic.category == "lifestyle" and topic.topic_id == "diary_nudge":
                adjustment -= 20
            elif topic.category == "finance":
                adjustment -= 20
        
        elif sub_mood == "tired":
            # 疲惫状态：减少日记提醒，提升心情关怀
            if topic.topic_id == "diary_nudge":
                adjustment -= 10
            elif topic.topic_id == "mood_check":
                adjustment += 10
            elif topic.category == "health" and topic.topic_id == "exercise_nudge":
                adjustment -= 15  # 疲惫时不提醒运动
        
        # 情绪类型调整
        if mood_type == "negative":
            # 消极情绪时，提升情感关怀类主题
            if topic.category == "emotional":
                adjustment += 10
        elif mood_type == "positive":
            # 积极情绪时，可以适当提醒任务类
            if topic.category == "lifestyle":
                adjustment += 5
        
        return adjustment


# ============================================================================
# OpportunityDetector — 时机检测器
# ============================================================================

class OpportunityDetector:
    """通过 EventBus 监听用户行为，检测关怀时机。
    
    监听工具调用和 Agent 响应事件，根据用户行为推断
    是否需要触发上下文相关的主动关怀。
    """
    
    def __init__(self, event_bus: EventBus):
        """初始化时机检测器。
        
        Args:
            event_bus: 事件总线实例
        """
        self._event_bus = event_bus
        self._engine: CompanionEngine | None = None
        self._setup_listeners()
    
    def set_engine(self, engine: CompanionEngine) -> None:
        """设置关联的 CompanionEngine。
        
        Args:
            engine: 主引擎实例
        """
        self._engine = engine
    
    def _setup_listeners(self) -> None:
        """设置事件监听器。"""
        # 监听工具调用事件
        self._event_bus.on(
            EventType.TOOL_CALL,
            self._on_tool_call,
            priority=200
        )
        # 监听 Agent 响应事件
        self._event_bus.on(
            EventType.AGENT_RESPONSE,
            self._on_agent_response,
            priority=200
        )
    
    async def _on_tool_call(self, event_type: str, data: Any) -> None:
        """处理工具调用事件。
        
        Args:
            event_type: 事件类型
            data: 事件数据 (ToolCallEvent 或 dict)
        """
        if self._engine is None:
            return
        
        # 安全获取属性
        tool_name = getattr(data, "tool_name", None) or (data.get("tool_name") if isinstance(data, dict) else None)
        action_name = getattr(data, "action_name", None) or (data.get("action_name") if isinstance(data, dict) else None)
        arguments = getattr(data, "arguments", {}) or (data.get("arguments", {}) if isinstance(data, dict) else {})
        
        if not tool_name:
            return
        
        logger.debug("检测到工具调用: %s.%s", tool_name, action_name)
        
        # 检查各种关怀时机
        try:
            await self._check_inference_rules(tool_name, arguments)
            await self._check_travel_intent(tool_name, arguments)
            await self._check_budget_alert(tool_name, arguments)
            await self._check_health_concern(tool_name, arguments)
        except Exception as e:
            logger.error("时机检测异常: %s", e)
    
    async def _on_agent_response(self, event_type: str, data: Any) -> None:
        """处理 Agent 响应事件。
        
        Args:
            event_type: 事件类型
            data: 事件数据 (AgentResponseEvent 或 dict)
        """
        if self._engine is None:
            return
        
        # 安全获取内容
        content = getattr(data, "content", None) or (data.get("content") if isinstance(data, dict) else None)
        if not content:
            return
        
        # 可以在这里分析 Agent 的响应，检测是否有需要跟进的关怀时机
        # 例如：Agent 完成了某个任务后，可能需要后续关怀
        pass
    
    async def _check_travel_intent(self, tool_name: str, arguments: dict) -> None:
        """检查旅行意图 → 建议旅游攻略。
        
        Args:
            tool_name: 工具名称
            arguments: 调用参数
        """
        if tool_name != "search":
            return
        
        query = str(arguments.get("query", "")).lower()
        travel_keywords = ["机票", "酒店", "旅游", "景点", "攻略", "订票", "住宿"]
        
        if any(kw in query for kw in travel_keywords):
            logger.info("检测到旅行意图: %s", query)
            await self._engine.suggest_contextual_care(
                "suggest_travel_guide",
                {"query": query, "detected_keywords": [kw for kw in travel_keywords if kw in query]}
            )
    
    async def _check_budget_alert(self, tool_name: str, arguments: dict) -> None:
        """检查大额支出 → 预算提醒。
        
        Args:
            tool_name: 工具名称
            arguments: 调用参数
        """
        if tool_name != "finance":
            return
        
        amount = arguments.get("amount", 0)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return
        
        # 大额支出阈值（可配置）
        threshold = 1000
        if amount >= threshold:
            logger.info("检测到大额支出: %.2f", amount)
            await self._engine.suggest_contextual_care(
                "budget_alert",
                {"amount": amount, "threshold": threshold}
            )
    
    async def _check_health_concern(self, tool_name: str, arguments: dict) -> None:
        """检查异常健康指标 → 就医建议。
        
        Args:
            tool_name: 工具名称
            arguments: 调用参数
        """
        if tool_name != "health":
            return
        
        # 检查血压
        bp_systolic = arguments.get("bp_systolic")
        bp_diastolic = arguments.get("bp_diastolic")
        
        if bp_systolic is not None:
            try:
                bp_sys = int(bp_systolic)
                if bp_sys >= 140:
                    logger.info("检测到高血压: %d", bp_sys)
                    await self._engine.suggest_contextual_care(
                        "health_alert",
                        {"metric_name": "血压", "value": bp_sys, "threshold": 140}
                    )
                    return
            except (TypeError, ValueError):
                pass
        
        # 检查血糖
        blood_glucose = arguments.get("blood_glucose")
        if blood_glucose is not None:
            try:
                glucose = float(blood_glucose)
                if glucose >= 7.0:
                    logger.info("检测到高血糖: %.1f", glucose)
                    await self._engine.suggest_contextual_care(
                        "health_alert",
                        {"metric_name": "血糖", "value": glucose, "threshold": 7.0}
                    )
            except (TypeError, ValueError):
                pass
    
    async def _check_inference_rules(self, tool_name: str, arguments: dict) -> None:
        """检查通用推断规则。
        
        Args:
            tool_name: 工具名称
            arguments: 调用参数
        """
        if self._engine is None:
            return
        
        # 将参数转为字符串进行关键词匹配
        args_text = " ".join(str(v) for v in arguments.values() if v)
        
        for rule in INFERENCE_RULES:
            if rule.tool != tool_name:
                continue
            
            # 检查关键词匹配
            matched_keywords = [kw for kw in rule.keyword_match if kw in args_text]
            if not matched_keywords:
                continue
            
            logger.info("推断规则匹配: tool=%s, keywords=%s, infer=%s", 
                       tool_name, matched_keywords, rule.infer)
            
            # 如果有关联动作，触发上下文关怀
            if rule.action:
                await self._engine.suggest_contextual_care(
                    rule.action,
                    {
                        "inferred": rule.infer,
                        "confidence": rule.confidence,
                        "matched_keywords": matched_keywords,
                    }
                )


# ============================================================================
# InteractionOrchestrator — 交互编排器
# ============================================================================

class InteractionOrchestrator:
    """管理主动交互的执行流程。
    
    负责：
    - 检查用户活跃状态（是否忙碌/空闲）
    - 构建个性化消息
    - 发起主动关怀并记录结果
    - 通过 EventBus 通知 UI 层
    """
    
    # 自定义事件类型
    COMPANION_CARE_TRIGGERED = "companion:care_triggered"
    COMPANION_CARE_COMPLETED = "companion:care_completed"
    
    def __init__(self, cooldown: CooldownManager, event_bus: EventBus):
        """初始化交互编排器。
        
        Args:
            cooldown: 冷却管理器
            event_bus: 事件总线
        """
        self._cooldown = cooldown
        self._event_bus = event_bus
        self._last_user_input_time: datetime | None = None
        
        # 监听用户输入事件来追踪活跃度
        self._event_bus.on(
            EventType.USER_INPUT,
            self._on_user_input,
            priority=200
        )
    
    async def _on_user_input(self, event_type: str, data: Any) -> None:
        """处理用户输入事件，更新最后活跃时间。"""
        self._last_user_input_time = datetime.now()
    
    def _is_user_busy(self) -> bool:
        """检查用户是否忙碌。
        
        如果 30 秒内有用户输入，认为用户正在活跃交互中。
        
        Returns:
            True 如果用户正忙，False 如果空闲
        """
        if self._last_user_input_time is None:
            return False
        
        elapsed = (datetime.now() - self._last_user_input_time).total_seconds()
        return elapsed < 30
    
    def _is_user_idle_for(self, minutes: int) -> bool:
        """检查用户是否空闲了指定分钟数。
        
        Args:
            minutes: 空闲分钟数阈值
            
        Returns:
            True 如果用户已空闲足够时间
        """
        if self._last_user_input_time is None:
            # 从未有过输入，认为可以交互
            return True
        
        elapsed = (datetime.now() - self._last_user_input_time).total_seconds()
        return elapsed >= minutes * 60
    
    def _build_message(self, topic: CareTopic, context: dict[str, Any]) -> str:
        """构建个性化消息。
        
        使用 context 填充 prompt_template 中的变量。
        
        Args:
            topic: 关怀主题
            context: 上下文数据，用于变量替换
            
        Returns:
            构建好的消息文本
        """
        template = topic.prompt_template
        
        # 使用 context 进行变量替换
        try:
            # 准备默认值
            defaults = {
                "weather_hint": "天气不错",
                "schedule_hint": "今天",
                "person_name": "朋友",
                "days_left": "几",
                "child_name": "孩子",
                "contact_name": "朋友",
                "metric_name": "指标",
            }
            
            # 合并 context 和默认值
            format_args = {**defaults, **context}
            
            # 格式化模板
            message = template.format(**format_args)
        except KeyError as e:
            logger.warning("消息模板变量缺失: %s", e)
            message = template  # 使用原始模板
        except Exception as e:
            logger.error("消息构建失败: %s", e)
            message = template
        
        return message
    
    async def initiate_care(self, topic: CareTopic, context: dict[str, Any]) -> dict[str, Any]:
        """发起一次主动关怀。
        
        Args:
            topic: 关怀主题
            context: 上下文数据
            
        Returns:
            结果记录:
            - topic_id: 主题 ID
            - message: 消息内容
            - outcome: 结果 (triggered/deferred/blocked)
        """
        result = {
            "topic_id": topic.topic_id,
            "message": "",
            "outcome": "blocked",
        }
        
        # 1. 尝试获取交互锁
        if not await self._cooldown.acquire_interaction_lock(topic.topic_id):
            logger.debug("无法获取交互锁，跳过: %s", topic.topic_id)
            result["outcome"] = "blocked"
            return result
        
        try:
            # 2. 检查是否可以交互
            if not self._cooldown.can_interact():
                logger.debug("冷却检查未通过，跳过: %s", topic.topic_id)
                result["outcome"] = "blocked"
                return result
            
            # 3. 检查用户是否忙碌
            if self._is_user_busy():
                logger.debug("用户正忙，延迟关怀: %s", topic.topic_id)
                result["outcome"] = "deferred"
                return result
            
            # 4. 构建消息
            message = self._build_message(topic, context)
            result["message"] = message
            
            # 5. 通过 EventBus 发布关怀触发事件（由 UI 层响应显示）
            await self._event_bus.emit(
                self.COMPANION_CARE_TRIGGERED,
                {
                    "topic_id": topic.topic_id,
                    "topic_name": topic.name,
                    "category": topic.category,
                    "message": message,
                    "priority": topic.priority,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            # 6. 记录交互
            self._cooldown.record_interaction(topic.topic_id, "triggered")
            result["outcome"] = "triggered"
            
            logger.info("主动关怀已触发: %s - %s", topic.topic_id, message[:50])
            
        finally:
            # 7. 释放锁
            self._cooldown.release_interaction_lock()
        
        return result


# ============================================================================
# CompanionEngine — 核心调度器
# ============================================================================

class CompanionEngine:
    """主动陪伴系统核心引擎。
    
    整合所有子组件（CooldownManager、MoodDetector、OpportunityDetector、
    InteractionOrchestrator），实现主动关怀的决策和调度。
    
    主要职责：
    - 计算主题的执行分数
    - 响应定时触发和上下文触发
    - 管理状态持久化
    - 处理应用启动/关闭事件
    """
    
    def __init__(self, event_bus: EventBus, db_path: Path | None = None):
        """初始化主动陪伴引擎。
        
        Args:
            event_bus: 事件总线实例
            db_path: 数据库路径，默认为 ~/.winclaw/winclaw_tools.db
        """
        self._event_bus = event_bus
        self._db_path = db_path or _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        # 子组件
        self._topic_registry = CareTopicRegistry()
        self._cooldown = CooldownManager(self._db_path)
        self._mood_detector = MoodDetector()
        self._orchestrator = InteractionOrchestrator(self._cooldown, self._event_bus)
        
        # OpportunityDetector 需要引用 engine，延迟初始化
        self._opportunity_detector = OpportunityDetector(self._event_bus)
        self._opportunity_detector.set_engine(self)
        
        # 当前用户情绪（缓存）
        self._current_mood: dict[str, Any] = {"mood": "neutral", "sub_mood": None, "confidence": 0.0}
        
        # 监听用户输入以更新情绪
        self._event_bus.on(EventType.USER_INPUT, self._on_user_input, priority=300)
        
        # 定时调度器任务
        self._scheduler_task: asyncio.Task | None = None
        
        self._initialized = True
        logger.info("CompanionEngine 初始化完成")
    
    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接的上下文管理器。"""
        conn = sqlite3.connect(str(self._db_path))
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """初始化数据库表。"""
        with self._conn() as conn:
            # 关怀日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companion_care_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    user_responded INTEGER DEFAULT 0,
                    user_response TEXT,
                    outcome TEXT,
                    data_collected TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_care_log_topic
                ON companion_care_log(topic_id, triggered_at DESC)
            """)
            
            # 状态表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companion_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
        logger.debug("数据库表初始化完成")
    
    async def _on_user_input(self, event_type: str, data: Any) -> None:
        """处理用户输入，更新情绪检测。"""
        text = getattr(data, "text", None) or (data.get("text") if isinstance(data, dict) else None)
        if text:
            self._current_mood = self._mood_detector.detect_mood_from_text(text)
            logger.debug("用户情绪更新: %s", self._current_mood)
    
    # === 核心评分算法 ===
    
    def calculate_interaction_score(self, topic: CareTopic) -> float:
        """计算主题此刻的执行分数。
        
        综合考虑优先级、时段匹配度、冷却期、紧急度、用户状态等因素。
        
        Args:
            topic: 关怀主题
            
        Returns:
            执行分数 (0-100)，越高越应该执行
        """
        # 基础分数：优先级 * 10
        score = topic.priority * 10
        
        # 1. 时段匹配度 +0~20
        current_slot = get_time_slot()
        if current_slot in topic.best_time_slots:
            score += 20
        elif topic.best_time_slots:
            score += 5  # 不在最佳时段，但仍可执行
        
        # 2. 冷却期硬性检查
        hours = self._cooldown.hours_since(topic.topic_id)
        if hours < topic.min_interval_hours:
            logger.debug("主题 %s 仍在冷却期 (%.1f < %d 小时)", 
                        topic.topic_id, hours, topic.min_interval_hours)
            return 0
        
        # 3. 紧急度加成 +0~30 (基于接近冷却期结束的程度)
        cooldown_ratio = min(hours / topic.min_interval_hours, 2.0)
        urgency_bonus = min((cooldown_ratio - 1) * 15, 30)
        score += urgency_bonus
        
        # 4. 特殊紧急情况（如生日临近）
        if topic.topic_id == "birthday_remind":
            context = self._build_context(topic)
            days_left = context.get("days_left_raw", 999)
            if days_left <= 3:
                score += 30
            elif days_left <= 7:
                score += 15
        
        # 5. 用户空闲度 +/-0~20
        if self._orchestrator._is_user_idle_for(5):
            score += 10  # 空闲 5 分钟以上
        if self._orchestrator._is_user_idle_for(15):
            score += 10  # 空闲 15 分钟以上
        if self._orchestrator._is_user_busy():
            score -= 20  # 用户正忙
        
        # 6. 情绪调节 +/-0~15
        mood_adjustment = self._mood_detector.get_mood_adjusted_topic_score(
            topic, self._current_mood
        )
        score += mood_adjustment
        
        # 7. 每日预算检查
        if not self._cooldown.can_interact():
            logger.debug("每日预算已用完或处于冷却期")
            return 0
        
        return max(0, min(100, score))
    
    # === 定时触发入口 ===
    
    async def on_cron_trigger(self, topic_id: str) -> dict[str, Any] | None:
        """被 CronTool 定时任务调用。
        
        Args:
            topic_id: 要触发的主题 ID
            
        Returns:
            交互结果，如果未执行则返回 None
        """
        topic = self._topic_registry.get(topic_id)
        if not topic:
            logger.warning("未找到主题: %s", topic_id)
            return None
        
        if not topic.enabled:
            logger.debug("主题已禁用: %s", topic_id)
            return None
        
        score = self.calculate_interaction_score(topic)
        logger.info("定时触发评分: %s = %.1f", topic_id, score)
        
        # 阈值检查
        threshold = 30
        if score <= threshold:
            logger.debug("分数未达阈值 (%d)，跳过: %s", threshold, topic_id)
            return None
        
        # 构建上下文并发起关怀
        context = self._build_context(topic)
        result = await self._orchestrator.initiate_care(topic, context)
        
        # 记录日志
        self.log_care(
            topic_id=topic_id,
            trigger_type="scheduled",
            interaction_type="text",
            outcome=result["outcome"],
        )
        
        return result
    
    # === 用户主动请求关怀入口 ===
    
    async def on_user_care_request(self, user_message: str = "") -> bool:
        """用户主动请求关怀时调用。
        
        绕过冷却限制，立即选择一个合适的关怀主题并触发。
        
        Args:
            user_message: 用户的原始消息
            
        Returns:
            是否成功触发关怀
        """
        logger.info("用户主动请求关怀: %s", user_message[:50] if user_message else "<空>")
        
        try:
            # 1. 获取当前时段适合的关怀主题
            current_slot = get_time_slot()
            candidates = self._topic_registry.get_by_time_slot(current_slot)
            
            # 如果当前时段没有候选，使用所有启用的主题
            if not candidates:
                candidates = self._topic_registry.get_enabled()
            
            if not candidates:
                logger.warning("没有可用的关怀主题")
                return False
            
            # 2. 按上次触发时间排序，选最久没触发的主题
            # 排除建档类主题（onboarding_*），这些不适合用户主动触发
            candidates = [t for t in candidates if not t.topic_id.startswith("onboarding_")]
            
            if not candidates:
                logger.warning("排除建档主题后没有可用的关怀主题")
                return False
            
            # 按上次触发时间排序（越久越优先）
            def get_hours_since(topic: CareTopic) -> float:
                return self._cooldown.hours_since(topic.topic_id)
            
            candidates_sorted = sorted(candidates, key=get_hours_since, reverse=True)
            selected_topic = candidates_sorted[0]
            
            logger.info("选中主题: %s (距上次触发 %.1f 小时)", 
                       selected_topic.topic_id, get_hours_since(selected_topic))
            
            # 3. 构建上下文并生成消息
            context = self._build_context(selected_topic)
            context["user_message"] = user_message
            
            # 使用 orchestrator 的消息构建方法
            message = self._orchestrator._build_message(selected_topic, context)
            
            # 4. 直接 emit 事件（绕过冷却检查和锁）
            await self._event_bus.emit(
                self._orchestrator.COMPANION_CARE_TRIGGERED,
                {
                    "topic_id": selected_topic.topic_id,
                    "topic_name": selected_topic.name,
                    "category": selected_topic.category,
                    "message": message,
                    "priority": selected_topic.priority,
                    "trigger_type": "user_request",  # 标识为用户主动请求
                    "timestamp": datetime.now().isoformat(),
                    "context": {"user_message": user_message},
                }
            )
            
            # 5. 记录日志（不记录到冷却管理器的每日计数，因为是用户主动请求）
            self.log_care(
                topic_id=selected_topic.topic_id,
                trigger_type="user_request",
                interaction_type="text",
                outcome="triggered",
                data_collected=f"user_message: {user_message[:100]}",
            )
            
            logger.info("用户主动关怀已触发: %s - %s", selected_topic.topic_id, message[:50])
            return True
            
        except Exception as e:
            logger.error("用户主动关怀触发失败: %s", e, exc_info=True)
            return False
    
    # === 上下文触发入口 ===
    
    async def suggest_contextual_care(self, action: str, context: dict[str, Any]) -> None:
        """被 OpportunityDetector 调用，处理上下文触发的关怀。
        
        Args:
            action: 触发动作标识
            context: 上下文数据
        """
        logger.info("上下文关怀触发: action=%s, context=%s", action, context)
        
        # 根据 action 映射到具体的主题
        action_topic_map = {
            "suggest_travel_guide": None,  # 暂无对应主题，可通过 AI 对话处理
            "budget_alert": "finance_review",
            "health_alert": "medical_remind",
            "schedule_bp_monitoring": "health_checkin",
        }
        
        topic_id = action_topic_map.get(action)
        if topic_id:
            topic = self._topic_registry.get(topic_id)
            if topic and topic.enabled:
                # 上下文触发可以降低阈值
                score = self.calculate_interaction_score(topic)
                if score > 20:  # 较低的阈值
                    merged_context = {**self._build_context(topic), **context}
                    result = await self._orchestrator.initiate_care(topic, merged_context)
                    
                    self.log_care(
                        topic_id=topic_id,
                        trigger_type="contextual",
                        interaction_type="text",
                        outcome=result["outcome"],
                        data_collected=str(context),
                    )
        else:
            # 对于没有预定义主题的 action，发布事件让 AI 处理
            await self._event_bus.emit(
                "companion:contextual_suggestion",
                {
                    "action": action,
                    "context": context,
                    "timestamp": datetime.now().isoformat(),
                }
            )
    
    # === 上下文构建 ===
    
    def _build_context(self, topic: CareTopic) -> dict[str, Any]:
        """构建关怀上下文。
        
        从 user_profile 等数据源获取个性化数据。
        
        Args:
            topic: 关怀主题
            
        Returns:
            上下文数据字典
        """
        context: dict[str, Any] = {}
        
        # 基础上下文
        now = datetime.now()
        context["current_time"] = now.strftime("%H:%M")
        context["current_date"] = now.strftime("%Y-%m-%d")
        context["time_slot"] = get_time_slot()
        
        # 天气提示（简化实现）
        hour = now.hour
        if hour < 10:
            context["weather_hint"] = "早晨空气清新"
        elif hour < 14:
            context["weather_hint"] = "中午阳光明媚"
        elif hour < 18:
            context["weather_hint"] = "下午时光正好"
        else:
            context["weather_hint"] = "夜幕降临"
        
        # 日程提示
        context["schedule_hint"] = "今天"
        
        # 尝试从数据库获取用户信息
        try:
            user_name = self.get_state("user_name")
            if user_name:
                context["user_name"] = user_name
        except Exception:
            pass
        
        # 生日相关
        if topic.topic_id == "birthday_remind":
            # 这里应该从 user_profile 查询即将到来的生日
            # 简化实现：返回默认值
            context["person_name"] = "朋友"
            context["days_left"] = "几"
            context["days_left_raw"] = 999
        
        # 儿童成长相关
        if topic.topic_id == "child_growth":
            context["child_name"] = self.get_state("child_name", "宝宝")
        
        # 社交维护相关
        if topic.topic_id == "social_maintain":
            context["contact_name"] = "朋友"
        
        return context
    
    # === 状态管理 ===
    
    def get_state(self, key: str, default: str = "") -> str:
        """获取持久化状态。
        
        Args:
            key: 状态键
            default: 默认值
            
        Returns:
            状态值
        """
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT value FROM companion_state WHERE key = ?", (key,)
                ).fetchone()
                return row[0] if row else default
        except sqlite3.OperationalError:
            return default
    
    def set_state(self, key: str, value: str) -> None:
        """设置持久化状态。
        
        Args:
            key: 状态键
            value: 状态值
        """
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO companion_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
            conn.commit()
    
    # === 关怀日志 ===
    
    def log_care(
        self,
        topic_id: str,
        trigger_type: str,
        interaction_type: str,
        outcome: str,
        user_response: str = "",
        data_collected: str = "",
    ) -> None:
        """记录一次关怀交互。
        
        Args:
            topic_id: 主题 ID
            trigger_type: 触发类型 (scheduled/contextual/reactive)
            interaction_type: 交互类型 (text/voice)
            outcome: 结果 (completed/ignored/rejected/deferred/triggered)
            user_response: 用户响应内容
            data_collected: 收集的数据
        """
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO companion_care_log
                (topic_id, triggered_at, trigger_type, interaction_type,
                 user_responded, user_response, outcome, data_collected, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                topic_id, now, trigger_type, interaction_type,
                1 if user_response else 0, user_response, outcome, data_collected, now
            ))
            conn.commit()
        logger.debug("关怀日志已记录: %s - %s - %s", topic_id, trigger_type, outcome)
    
    # === 离线恢复 ===
    
    async def on_app_started(self) -> None:
        """应用启动时检查错过的关键任务。"""
        logger.info("CompanionEngine 启动检查")
        
        # 检查是否需要重置每日计数
        last_reset = self.get_state("last_reset_date")
        today = datetime.now().strftime("%Y-%m-%d")
        if last_reset != today:
            self._cooldown.reset_daily_count()
        
        # 检查是否有错过的紧急任务（如生日）
        # 这里可以扫描所有启用的主题，检查是否有紧急的需要立即触发
        for topic in self._topic_registry.get_enabled():
            if topic.priority >= 8:  # 高优先级主题
                hours = self._cooldown.hours_since(topic.topic_id)
                if hours > topic.min_interval_hours * 1.5:
                    # 超过冷却期 50%，可能是错过了
                    logger.info("检测到可能错过的高优先级任务: %s", topic.topic_id)
    
    async def on_app_shutdown(self) -> None:
        """应用关闭时保存状态。"""
        logger.info("CompanionEngine 关闭，保存状态")
        
        # 停止调度器
        await self.stop_scheduler()
        
        # 保存当前情绪状态
        self.set_state("last_mood", self._current_mood.get("mood", "neutral"))
        self.set_state("last_shutdown_time", datetime.now().isoformat())

    # === 每日任务推送 ===

    async def send_daily_task_message(self, message: str) -> None:
        """发送每日任务推送消息。

        通过 EventBus 发布事件，UI 层接收后显示在对话栏。

        Args:
            message: 每日任务消息内容
        """
        logger.info("发送每日任务推送")

        # 通过 EventBus 发布事件
        await self._event_bus.emit(
            EventType.COMPANION_CARE_TRIGGERED,
            {
                "message": f"📋 {message}",
                "topic_id": "daily_task",
                "trigger_type": "scheduled",
            }
        )

        # 记录日志
        self._log_care_interaction(
            topic_id="daily_task",
            trigger_type="scheduled",
            outcome="pushed",
        )

    # === 定时调度器 ===
    
    async def start_scheduler(self) -> None:
        """启动内置定时调度。
        
        使用 asyncio 创建后台任务，定期调用关怀检查。
        默认每30分钟检查一次是否有合适的关怀时机。
        """
        if self._scheduler_task is not None:
            logger.debug("调度器已在运行，跳过重复启动")
            return  # 已启动
        
        self._scheduler_task = asyncio.ensure_future(self._scheduler_loop())
        logger.info("CompanionEngine 调度器已启动")
    
    async def _scheduler_loop(self) -> None:
        """定时调度循环。
        
        每30分钟检查一次当前时段的所有关怀主题，
        根据评分决定是否触发主动关怀。
        """
        while True:
            try:
                # 等待30分钟
                await asyncio.sleep(30 * 60)
                
                # 获取当前时段适合的主题
                current_slot = get_time_slot()
                topics = self._topic_registry.get_by_time_slot(current_slot)
                
                logger.info("调度器检查：时段=%s, 候选主题数=%d", current_slot, len(topics))
                
                # 遍历当前时段的主题，尝试触发
                for topic in topics:
                    if not topic.enabled:
                        continue
                    
                    # 计算评分
                    score = self.calculate_interaction_score(topic)
                    if score > 30:  # 阈值
                        logger.info("调度器触发主题: %s (score=%.1f)", topic.topic_id, score)
                        try:
                            await self.on_cron_trigger(topic.topic_id)
                        except Exception as e:
                            logger.error("主题 %s 触发失败: %s", topic.topic_id, e)
                        # 每次只触发一个主题，避免骚扰
                        break
                
            except asyncio.CancelledError:
                logger.info("调度器循环被取消")
                break
            except Exception as e:
                logger.error("陪伴调度异常: %s", e)
                # 异常后等1分钟重试
                await asyncio.sleep(60)
    
    async def stop_scheduler(self) -> None:
        """停止调度器。"""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
            logger.info("CompanionEngine 调度器已停止")
    
    # === 属性 ===
    
    @property
    def topic_registry(self) -> CareTopicRegistry:
        """获取主题注册表。"""
        return self._topic_registry
    
    @property
    def cooldown(self) -> CooldownManager:
        """获取冷却管理器。"""
        return self._cooldown
    
    @property
    def mood_detector(self) -> MoodDetector:
        """获取情绪检测器。"""
        return self._mood_detector
    
    @property
    def orchestrator(self) -> InteractionOrchestrator:
        """获取交互编排器。"""
        return self._orchestrator
    
    @property
    def opportunity_detector(self) -> OpportunityDetector:
        """获取时机检测器。"""
        return self._opportunity_detector
