"""
关怀主题定义与注册表模块

本模块是 WeClaw AI 桌面助手主动陪伴系统的核心组件，定义了：
- CareTopic: 关怀主题的数据结构
- CareTopicRegistry: 主题注册与查询管理
- 预定义关怀主题（早安问候、心情关怀、健康打卡等）
- 建档序列（OnboardingStep）: 渐进式用户信息收集策略
- 推断规则（InferenceRule）: 从用户行为推断档案信息
- 情绪关键词表: 用于情绪识别
- 时间段辅助函数

使用示例:
    from src.core.companion_topics import CareTopicRegistry, get_time_slot
    
    registry = CareTopicRegistry()
    current_slot = get_time_slot()
    topics = registry.get_by_time_slot(current_slot)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CareTopic:
    """
    关怀主题数据类
    
    定义单个关怀主题的所有属性，包括触发条件、时间约束和对话模板。
    
    Attributes:
        topic_id: 唯一标识符
        name: 显示名称
        category: 主题分类 (health/finance/social/family/emotional/lifestyle)
        priority: 优先级 (1-10, 10为最高)
        min_interval_hours: 最小触发间隔（小时）
        best_time_slots: 最佳触发时段列表 ["morning", "afternoon", "evening"]
        prompt_template: 对话模板，支持 {变量} 替换
        requires_profile: 依赖的用户档案字段列表
        enabled: 是否启用
    """
    topic_id: str
    name: str
    category: str
    priority: int
    min_interval_hours: int
    best_time_slots: list[str] = field(default_factory=list)
    prompt_template: str = ""
    requires_profile: list[str] = field(default_factory=list)
    enabled: bool = True


class CareTopicRegistry:
    """
    关怀主题注册表
    
    管理所有关怀主题的注册、查询和过滤操作。
    初始化时自动注册所有预定义主题。
    
    Example:
        registry = CareTopicRegistry()
        morning_topics = registry.get_by_time_slot("morning")
        health_topics = registry.get_by_category("health")
    """
    
    def __init__(self):
        """初始化注册表并注册默认主题"""
        self._topics: dict[str, CareTopic] = {}
        self._register_defaults()
    
    def register(self, topic: CareTopic) -> None:
        """
        注册一个关怀主题
        
        Args:
            topic: 要注册的 CareTopic 实例
        """
        self._topics[topic.topic_id] = topic
    
    def get(self, topic_id: str) -> CareTopic | None:
        """
        根据 ID 获取主题
        
        Args:
            topic_id: 主题唯一标识符
            
        Returns:
            CareTopic 实例，如果不存在则返回 None
        """
        return self._topics.get(topic_id)
    
    def get_by_category(self, category: str) -> list[CareTopic]:
        """
        获取指定分类的所有主题
        
        Args:
            category: 分类名称 (health/finance/social/family/emotional/lifestyle)
            
        Returns:
            该分类下的所有 CareTopic 列表
        """
        return [t for t in self._topics.values() if t.category == category]
    
    def get_enabled(self) -> list[CareTopic]:
        """
        获取所有已启用的主题
        
        Returns:
            所有 enabled=True 的 CareTopic 列表
        """
        return [t for t in self._topics.values() if t.enabled]
    
    def get_by_time_slot(self, slot: str) -> list[CareTopic]:
        """
        获取适合指定时间段的主题
        
        Args:
            slot: 时间段 ("morning", "afternoon", "evening")
            
        Returns:
            best_time_slots 包含该时段的 CareTopic 列表
        """
        return [t for t in self._topics.values() if slot in t.best_time_slots and t.enabled]
    
    def _register_defaults(self) -> None:
        """注册所有预定义的关怀主题"""
        default_topics = [
            # 日常关怀主题
            CareTopic(
                topic_id="morning_greeting",
                name="早安问候",
                category="lifestyle",
                priority=5,
                min_interval_hours=24,
                best_time_slots=["morning"],
                prompt_template="早上好呀！今天{weather_hint}，{schedule_hint}有什么计划吗？"
            ),
            CareTopic(
                topic_id="mood_check",
                name="心情关怀",
                category="emotional",
                priority=7,
                min_interval_hours=12,
                best_time_slots=["afternoon", "evening"],
                prompt_template="今天过得怎么样呀？最近心情如何？"
            ),
            CareTopic(
                topic_id="diary_nudge",
                name="日记提醒",
                category="lifestyle",
                priority=4,
                min_interval_hours=24,
                best_time_slots=["evening"],
                prompt_template="忙了一天了，要不要简单记几句日记？把今天的想法写下来～"
            ),
            CareTopic(
                topic_id="health_checkin",
                name="健康打卡",
                category="health",
                priority=6,
                min_interval_hours=48,
                best_time_slots=["morning", "evening"],
                prompt_template="最近身体状况怎么样？要不要记录一下今天的健康数据？"
            ),
            CareTopic(
                topic_id="finance_review",
                name="财务回顾",
                category="finance",
                priority=3,
                min_interval_hours=168,
                best_time_slots=["morning"],
                prompt_template="这周的收支情况还记得吗？要不要一起回顾一下？"
            ),
            CareTopic(
                topic_id="birthday_remind",
                name="生日提醒",
                category="social",
                priority=9,
                min_interval_hours=8760,
                best_time_slots=["morning"],
                prompt_template="{person_name}的生日就在{days_left}天后了！要不要准备一下？",
                requires_profile=["social_contacts"]
            ),
            CareTopic(
                topic_id="child_growth",
                name="儿童成长",
                category="family",
                priority=6,
                min_interval_hours=720,
                best_time_slots=["morning"],
                prompt_template="有段时间没记录{child_name}的身高体重了，最近量过吗？",
                requires_profile=["has_children", "family_members"]
            ),
            CareTopic(
                topic_id="medical_remind",
                name="就医提醒",
                category="health",
                priority=8,
                min_interval_hours=168,
                best_time_slots=["morning"],
                prompt_template="注意到你最近的{metric_name}数据偏高，建议找时间去医院检查一下比较放心",
                requires_profile=["health_data"]
            ),
            CareTopic(
                topic_id="social_maintain",
                name="社交维护",
                category="social",
                priority=4,
                min_interval_hours=336,
                best_time_slots=["morning"],
                prompt_template="好久没联系{contact_name}了，要不要发个消息问候一下？",
                requires_profile=["social_contacts"]
            ),
            CareTopic(
                topic_id="exercise_nudge",
                name="运动提醒",
                category="health",
                priority=5,
                min_interval_hours=24,
                best_time_slots=["afternoon"],
                prompt_template="今天有活动活动身体吗？适当运动对健康很有帮助哦～"
            ),
            # 建档系列主题
            CareTopic(
                topic_id="onboarding_name",
                name="初始建档-称呼",
                category="lifestyle",
                priority=3,
                min_interval_hours=72,
                best_time_slots=["morning", "afternoon", "evening"],
                prompt_template="对了，我还不知道怎么称呼你呢？你希望我叫你什么？"
            ),
            CareTopic(
                topic_id="onboarding_children",
                name="初始建档-家庭",
                category="family",
                priority=3,
                min_interval_hours=72,
                best_time_slots=["morning", "afternoon", "evening"],
                prompt_template="你家里有小朋友吗？如果有的话，我可以帮你记录他们的成长数据哦"
            ),
            CareTopic(
                topic_id="onboarding_health",
                name="初始建档-健康",
                category="health",
                priority=3,
                min_interval_hours=72,
                best_time_slots=["morning", "afternoon", "evening"],
                prompt_template="你平时有什么特别关注的健康指标吗？比如血压、血糖之类的"
            ),
            CareTopic(
                topic_id="onboarding_social",
                name="初始建档-社交",
                category="social",
                priority=3,
                min_interval_hours=72,
                best_time_slots=["morning", "afternoon", "evening"],
                prompt_template="有没有特别重要的朋友或家人的生日需要我帮你记住？"
            ),
            CareTopic(
                topic_id="onboarding_birthday",
                name="初始建档-生日",
                category="lifestyle",
                priority=3,
                min_interval_hours=72,
                best_time_slots=["morning", "afternoon", "evening"],
                prompt_template="对了，你的生日是哪天呀？到时候我可以给你准备惊喜"
            ),
        ]
        
        for topic in default_topics:
            self.register(topic)


# ============================================================================
# 建档序列定义
# ============================================================================

@dataclass
class OnboardingStep:
    """
    建档步骤数据类
    
    定义渐进式用户信息收集的单个步骤。
    
    Attributes:
        field: 对应的 user_profile 键名
        topic_id: 对应的 CareTopic topic_id
        timing: 触发时机类型
            - first_idle_after_first_use: 首次使用后的首个空闲时刻
            - after_N_conversations: N 次对话后
            - after_N_days: N 天后
            - after_tool_first_use: 首次使用相关工具后
            - natural_conversation_fit: 自然对话契合时
        timing_value: 时机参数值（用于 after_N_conversations 和 after_N_days）
    """
    field: str
    topic_id: str
    timing: str
    timing_value: int = 0


ONBOARDING_SEQUENCE: list[OnboardingStep] = [
    OnboardingStep("user_name", "onboarding_name", "first_idle_after_first_use"),
    OnboardingStep("has_children", "onboarding_children", "after_N_conversations", 3),
    OnboardingStep("health_concerns", "onboarding_health", "after_tool_first_use"),
    OnboardingStep("important_contacts", "onboarding_social", "after_N_days", 7),
    OnboardingStep("birthday", "onboarding_birthday", "natural_conversation_fit"),
]


# ============================================================================
# 推断规则
# ============================================================================

@dataclass
class InferenceRule:
    """
    推断规则数据类
    
    定义从用户行为和关键词推断用户档案信息的规则。
    
    Attributes:
        tool: 触发此规则的工具名称
        keyword_match: 需要匹配的关键词列表（任意一个匹配即触发）
        infer: 推断结果字典 {档案键: 推断值}
        confidence: 推断置信度 (0.0-1.0)
        action: 可选的触发动作标识
    """
    tool: str
    keyword_match: list[str]
    infer: dict[str, Any]
    confidence: float = 0.8
    action: str = ""


INFERENCE_RULES: list[InferenceRule] = [
    InferenceRule(
        tool="finance",
        keyword_match=["幼儿园", "学费", "奶粉", "尿布", "童装", "儿童"],
        infer={"has_children": "true"},
        confidence=0.8
    ),
    InferenceRule(
        tool="search",
        keyword_match=["机票", "酒店", "旅游", "景点", "攻略"],
        infer={"travel_intent": "true"},
        confidence=0.7,
        action="suggest_travel_guide"
    ),
    InferenceRule(
        tool="health",
        keyword_match=["高血压", "血压偏高"],
        infer={"hypertension_risk": "true"},
        confidence=0.9,
        action="schedule_bp_monitoring"
    ),
    InferenceRule(
        tool="finance",
        keyword_match=["房贷", "房租", "租金"],
        infer={"has_housing_expense": "true"},
        confidence=0.9
    ),
    InferenceRule(
        tool="search",
        keyword_match=["宝宝", "育儿", "早教", "母婴"],
        infer={"has_children": "true"},
        confidence=0.7
    ),
]

# 置信度阈值：低于此值的推断需要用户确认
CONFIDENCE_THRESHOLD: float = 0.8


# ============================================================================
# 情绪关键词表
# ============================================================================

MOOD_KEYWORDS: dict[str, list[str]] = {
    "positive": [
        "开心", "高兴", "不错", "很好", "太棒了", 
        "谢谢", "喜欢", "满意", "棒", "好的", "哈哈"
    ],
    "negative": [
        "累", "烦", "难过", "不开心", "压力大", 
        "焦虑", "担心", "难受", "郁闷", "伤心"
    ],
    "stressed": [
        "忙死了", "压力大", "受不了", "崩溃", "烦死了", 
        "没时间", "头疼", "焦头烂额"
    ],
    "tired": [
        "累", "困", "疲惫", "没精神", "想睡觉", 
        "好困", "太累了", "精力不足"
    ],
}


# ============================================================================
# 用户主动请求关怀关键词
# ============================================================================

USER_CARE_REQUEST_KEYWORDS: list[str] = [
    "关心我", "想问我", "向我提问", "提问我", "你想知道什么",
    "有没有想问", "问我点什么", "关心一下", "陪伴我", "聊聊天",
    "care about me", "ask me", "talk to me",
    "今天有什么想问", "有什么想了解", "想了解我什么",
]


# ============================================================================
# 时间段辅助函数
# ============================================================================

def get_time_slot() -> str:
    """
    获取当前时间段
    
    根据当前小时判断所处的时间段：
    - morning: 6:00-12:00
    - afternoon: 12:00-18:00
    - evening: 18:00-6:00
    
    Returns:
        时间段字符串 ("morning", "afternoon", "evening")
    """
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "evening"
