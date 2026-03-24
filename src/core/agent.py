"""Agent 核心循环 — ReAct 模式的 AI 智能体（Phase 1 重构版）。

重构变更：
- 接入 EventBus，推理全流程发布事件
- 使用 SessionManager 管理对话历史
- 使用 ModelSelector 选择模型
- 使用 CostTracker 记录费用
- Phase 4: 增加推理超时控制
- Phase 6: 集成意识系统，赋予 WinClaw 自我感知、自我修复和进化能力
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from src.core.event_bus import EventBus
from src.core.events import (
    AgentResponseEvent,
    AgentThinkingEvent,
    DeferredToolResultEvent,
    DeferredToolStartedEvent,
    ErrorEvent,
    EventType,
    FileGeneratedEvent,
    ModelCallEvent,
    ModelReasoningEvent,
    ModelResponseEvent,
    ModelUsageEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from src.core.prompts import (
    build_system_prompt,
    build_system_prompt_from_intent,
    detect_intent_with_confidence,
    DEFAULT_SYSTEM_PROMPT,
    CORE_SYSTEM_PROMPT,
    COMPANION_PROMPT_MODULE,
    IntentResult,
)
from src.core.tool_exposure import ToolExposureEngine
from src.core.session import SessionManager
from src.core.task_trace import TaskTraceCollector, create_trace_collector
from src.models.cost import CostTracker
from src.models.registry import ModelRegistry, UsageRecord
from src.models.selector import ModelSelector
from src.tools.registry import ToolRegistry

# Phase 6: 意识系统集成（已禁用）
# try:
#     from src.consciousness import ConsciousnessManager
#     from src.core.consciousness_integration import ConsciousnessEvaluator
#     CONSCIOUSNESS_ENABLED = True
# except ImportError:
#     CONSCIOUSNESS_ENABLED = False
#     ConsciousnessManager = None
#     ConsciousnessEvaluator = None
CONSCIOUSNESS_ENABLED = False
ConsciousnessManager = None
ConsciousnessEvaluator = None

logger = logging.getLogger(__name__)

# 默认推理超时时间（秒）
DEFAULT_INFERENCE_TIMEOUT = 120

# 流式响应单 chunk 超时（秒）
STREAM_CHUNK_TIMEOUT = 60

# 连续失败阈值
MAX_CONSECUTIVE_FAILURES = 3

# 单次工具调用数量上限（防止模型同时调用过多不相关工具）
MAX_TOOLS_PER_CALL = 3


# ------------------------------------------------------------------
# 任务执行状态跟踪器 - 解决锚定消息导致的重复执行问题
# ------------------------------------------------------------------

@dataclass
class ExecutionTracker:
    """跟踪任务执行状态，用于智能锚定消息决策。
    
    解决的问题：
    1. 已执行一半，提醒后反而重新来过
    2. 执行完毕了，结果一提醒又再来一次
    3. 缺乏执行过程的跟踪和反馈
    """
    
    # 最近成功的工具调用记录 (tool_name, action_name, args_hash)
    recent_success_calls: list[tuple[str, str, str]] = field(default_factory=list)
    
    # 连续成功计数
    consecutive_successes: int = 0
    
    # 总成功调用数
    total_successes: int = 0
    
    # 是否检测到可能完成（模型已经给出回复后又被锚定）
    potential_completion: bool = False
    
    # 已执行的操作摘要（用于提醒）
    executed_actions: list[str] = field(default_factory=list)
    
    def record_success(self, tool_name: str, action_name: str, args: dict) -> None:
        """记录一次成功的工具调用。"""
        import hashlib
        import json
        
        # 生成参数哈希（用于检测重复）
        args_str = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        
        call_key = (tool_name, action_name, args_hash)
        self.recent_success_calls.append(call_key)
        
        # 保持最近20次调用记录
        if len(self.recent_success_calls) > 20:
            self.recent_success_calls.pop(0)
        
        self.consecutive_successes += 1
        self.total_successes += 1
        
        # 记录操作摘要
        action_desc = f"{tool_name}.{action_name}"
        if action_desc not in self.executed_actions:
            self.executed_actions.append(action_desc)
    
    def record_failure(self) -> None:
        """记录一次失败，重置连续成功计数。"""
        self.consecutive_successes = 0
    
    def is_duplicate_call(self, tool_name: str, action_name: str, args: dict) -> bool:
        """检测是否为重复调用（最近3次内已有相同调用）。"""
        import hashlib
        import json
        
        args_str = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        call_key = (tool_name, action_name, args_hash)
        
        # 检查最近3次调用中是否有重复
        recent = self.recent_success_calls[-3:] if len(self.recent_success_calls) >= 3 else self.recent_success_calls
        return call_key in recent
    
    def get_status_summary(self) -> dict:
        """获取执行状态摘要。"""
        return {
            "total_successes": self.total_successes,
            "consecutive_successes": self.consecutive_successes,
            "recent_actions": self.executed_actions[-5:],  # 最近5个操作
            "potential_completion": self.potential_completion,
        }
    
    def should_suggest_completion(self) -> bool:
        """判断是否应该建议模型考虑任务已完成。"""
        # 连续3次以上成功且没有失败
        if self.consecutive_successes >= 3:
            return True
        # 总成功数超过5次
        if self.total_successes >= 5:
            return True
        return False
    
    def reset(self) -> None:
        """重置跟踪器状态（新对话时调用）。"""
        self.recent_success_calls.clear()
        self.consecutive_successes = 0
        self.total_successes = 0
        self.potential_completion = False
        self.executed_actions.clear()


async def _stream_with_timeout(
    stream: AsyncGenerator[Any, None],
    timeout: float,
):
    """带超时的异步生成器包装器。

    如果在指定时间内没有收到下一个 chunk，则抛出 TimeoutError。
    """
    while True:
        try:
            chunk = await asyncio.wait_for(stream.__anext__(), timeout=timeout)
            yield chunk
        except StopAsyncIteration:
            break


@dataclass
class AgentResponse:
    """Agent 单次交互的完整响应。"""

    content: str = ""
    tool_calls_count: int = 0
    total_tokens: int = 0
    steps: list[AgentStep] = field(default_factory=list)


@dataclass
class AgentStep:
    """Agent 推理的单个步骤。"""

    step_type: str  # "tool_call" | "tool_result" | "response"
    tool_name: str = ""
    tool_action: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: str = ""
    content: str = ""


class Agent:
    """AI 智能体核心。执行 ReAct 循环。

    Phase 1 架构：
    - EventBus: 每步推理发布事件
    - SessionManager: 管理对话历史和上下文截断
    - ModelSelector: 智能选择模型
    - CostTracker: 记录费用
    
    Phase 4 增强：
    - 推理超时控制

    Phase 6 增强：
    - 渐进式工具暴露（ToolExposureEngine）
    - 单次工具调用数量限制
    - 增强意图识别与置信度评估
    """

    def __init__(
        self,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        event_bus: EventBus | None = None,
        session_manager: SessionManager | None = None,
        model_selector: ModelSelector | None = None,
        cost_tracker: CostTracker | None = None,
        model_key: str = "deepseek-chat",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_steps: int = 60,
        inference_timeout: float = DEFAULT_INFERENCE_TIMEOUT,
        # Phase 6: 工具暴露策略配置
        enable_tool_tiering: bool = True,
        enable_schema_annotation: bool = True,
        failures_to_upgrade: int = 2,
        # Phase 6: 全链路追踪配置
        enable_trace: bool = True,
        trace_config: dict[str, Any] | None = None,
    ):
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.event_bus = event_bus or EventBus()
        
        # 【优化】懒加载重型组件，首次使用时才初始化
        self._session_manager = session_manager
        self._model_selector = model_selector
        self._cost_tracker = cost_tracker
        self._trace_collector = None
        
        # 立即初始化的轻量组件
        self.model_key = model_key
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.inference_timeout = inference_timeout

        # Phase 6: 工具暴露策略引擎
        self.tool_exposure = ToolExposureEngine(
            tool_registry,
            enabled=enable_tool_tiering,
            enable_annotation=enable_schema_annotation,
            failures_to_upgrade=failures_to_upgrade,
        )

        # Phase 6: 全链路追踪配置
        self._enable_trace = enable_trace
        self._trace_config = trace_config or {}
        
        # 任务执行状态跟踪器 - 用于智能锚定消息
        self._execution_tracker = ExecutionTracker()

        # 请求序列化锁：防止多路并发请求（本地+远程PWA）同时修改 session 历史
        # asyncio.Lock 必须在事件循环已启动后才能创建，使用懒加载
        self._chat_lock: asyncio.Lock | None = None

        # CFTA: 异步工具执行锁（独立于 chat_lock，不阻塞新的聊天请求）
        self._deferred_lock: asyncio.Lock | None = None
        # CFTA: 当前后台工具任务（新请求到达时可 cancel）
        self._deferred_task: asyncio.Task | None = None
        
        # Phase 6: 意识系统集成（已禁用）
        # 保持 CONSCIOUSNESS_ENABLED = False，不加载意识系统
        self.consciousness = None
        self.consciousness_evaluator = None
        logger.debug("意识系统已禁用（性能优化）")

    # 兼容旧接口
    @property
    def messages(self) -> list[dict[str, Any]]:
        """兼容旧接口：返回当前会话的消息列表。"""
        return self.session_manager.current_session.messages

    @property
    def chat_lock(self) -> asyncio.Lock:
        """懒加载聊天序列化锁（首次访问时在当前事件循环中创建）。"""
        if self._chat_lock is None:
            self._chat_lock = asyncio.Lock()
        return self._chat_lock

    @property
    def deferred_lock(self) -> asyncio.Lock:
        """CFTA: 懒加载异步工具执行锁。"""
        if self._deferred_lock is None:
            self._deferred_lock = asyncio.Lock()
        return self._deferred_lock
    
    # 【优化】懒加载重型组件的属性方法
    @property
    def session_manager(self):
        """懒加载会话管理器（首次访问时初始化）。"""
        if self._session_manager is None:
            from src.core.storage import ChatStorage
            storage = ChatStorage()
            self._session_manager = SessionManager(
                system_prompt=self.system_prompt,
                storage=storage,
            )
        return self._session_manager
    
    @property
    def model_selector(self):
        """懒加载模型选择器（首次访问时初始化）。"""
        if self._model_selector is None:
            self._model_selector = ModelSelector(
                self.model_registry, default_model=self.model_key,
            )
        return self._model_selector
    
    @property
    def cost_tracker(self):
        """懒加载费用跟踪器（首次访问时初始化）。"""
        if self._cost_tracker is None:
            self._cost_tracker = CostTracker()
        return self._cost_tracker
    
    @property
    def trace_collector(self):
        """懒加载任务追踪器（首次访问时初始化）。"""
        if self._trace_collector is None:
            self._trace_collector = create_trace_collector()
        return self._trace_collector

    def reset(self) -> None:
        """新建会话，保留旧会话到历史记录。
            
        不再清空当前会话，而是创建新会话并切换到它。
        旧会话的消息已在对话过程中保存到存储，历史记录不会丢失。
        """
        # 如果已初始化则创建新会话，未初始化则跳过
        if self._session_manager is not None:
            # 获取当前模型配置
            current_model = self.model_key or ""
            # 创建新会话（自动保存到存储，旧会话保留在历史中）
            self.session_manager.create_session(title="新对话", model_key=current_model)
            logger.info("已创建新会话，旧会话保留在历史记录中")
    
        # 重置执行状态跟踪器
        self._execution_tracker.reset()
    
        # Phase 6: 重置意识评估器（已禁用，始终为 None）
        # 不再需要
    
    def _build_smart_anchor_message(
        self,
        user_input: str,
        step_idx: int,
        tool_calls_count: int,
        consecutive_failures: int,
        tracker_status: dict,
    ) -> str:
        """构建智能锚定消息，根据执行状态动态调整内容。
        
        核心改进：
        1. 不再简单说"请继续推进"，而是根据状态给出不同指引
        2. 检测可能的完成状态，建议模型确认或总结
        3. 避免重复执行已完成的操作
        """
        total_successes = tracker_status.get("total_successes", 0)
        consecutive_successes = tracker_status.get("consecutive_successes", 0)
        recent_actions = tracker_status.get("recent_actions", [])
        
        # 基础状态信息
        status_lines = [
            f"[执行状态提醒]",
            f"原始请求：{user_input}",
            f"当前进度：第 {step_idx + 1} 步 / 共 {self.max_steps} 步",
            f"工具调用：{tool_calls_count} 次（成功 {total_successes} 次）",
        ]
        
        # 添加已执行操作摘要
        if recent_actions:
            actions_str = "、".join(recent_actions[-3:])  # 最近3个操作
            status_lines.append(f"已执行操作：{actions_str}")
        
        # 根据状态给出不同的指引
        if consecutive_failures >= 2:
            # 连续失败较多，建议检查问题
            status_lines.append(f"\n⚠️ 连续失败 {consecutive_failures} 次，建议检查：")
            status_lines.append("1. 参数是否正确")
            status_lines.append("2. 相关服务是否正常")
            status_lines.append("3. 是否需要调整策略")
            status_lines.append("\n请分析失败原因后再尝试，不要重复相同的操作。")
            
        elif self._execution_tracker.should_suggest_completion():
            # 多次成功，可能已接近完成
            status_lines.append(f"\n✅ 已连续成功执行 {consecutive_successes} 次操作。")
            status_lines.append("请评估：")
            status_lines.append("1. 任务目标是否已达成？")
            status_lines.append("2. 是否需要总结结果或进行确认？")
            status_lines.append("3. 如果已完成，请直接回复用户，不要继续执行不必要的操作。")
            
        elif total_successes > 0:
            # 有成功执行的操作，鼓励继续但避免重复
            status_lines.append(f"\n✓ 已成功执行 {total_successes} 次操作。")
            status_lines.append("请继续推进任务，但**不要重复已执行的操作**。")
            status_lines.append("如果任务已完成，请直接向用户报告结果。")
            
        else:
            # 初始阶段
            status_lines.append("\n请按计划推进任务。")
        
        return "\n".join(status_lines)
    
    async def cleanup(self) -> None:
        """清理 Agent 资源（包括意识系统）。"""
        # Phase 6: 停止意识系统
        if self.consciousness and self.consciousness.is_running:
            try:
                logger.info("正在停止意识系统...")
                await self.consciousness.stop()
                logger.info("意识系统已停止")
            except Exception as e:
                logger.error(f"意识系统清理失败：{e}")
    
    def _ensure_consciousness_started(self) -> None:
        """确保意识系统已启动（懒启动）。"""
        if not self.consciousness:
            logger.warning("意识系统未初始化")
            return
            
        if self.consciousness.is_running:
            return  # 已在运行
            
        try:
            import asyncio
            # 在有事件循环的上下文中启动
            try:
                loop = asyncio.get_running_loop()
                # 循环正在运行，创建任务
                asyncio.create_task(self.consciousness.start())
                logger.info("[意识] 懒启动任务已创建")
            except RuntimeError:
                # 没有运行的循环，尝试获取或创建
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.consciousness.start())
                else:
                    loop.run_until_complete(self.consciousness.start())
                logger.info("[意识] 意识系统已启动（懒启动）")
        except Exception as e:
            logger.error(f"意识系统懒启动失败：{e}")

    # ------------------------------------------------------------------
    # 文件生成检测
    # ------------------------------------------------------------------

    # 会触发文件生成事件的 (tool_name, action_name) 集合
    _FILE_GEN_ACTIONS: set[tuple[str, str]] = {
        ("file", "write"),
        ("file", "edit"),
        ("screen", "screenshot"),
        ("screen", "capture"),
    }

    async def _check_and_emit_file_generated(
        self,
        tool_name: str,
        action_name: str,
        result,
        session_id: str,
    ) -> None:
        """检查工具执行结果是否产生了文件，如果是则发出 FILE_GENERATED 事件。"""
        if not result.is_success:
            return

        # 兼容不同的字段名：path 和 file_path
        file_path = result.data.get("path", "") if result.data else ""
        if not file_path:
            file_path = result.data.get("file_path", "") if result.data else ""
        if not file_path:
            return

        # 只对写入/创建类操作发出事件
        from pathlib import Path as _P
        p = _P(file_path)
        if not p.exists() or not p.is_file():
            return

        # 判断是否为文件写入类动作
        is_file_gen = (tool_name, action_name) in self._FILE_GEN_ACTIONS
        # 对于未明确列出的动作，检查动作名是否包含文件生成相关的关键词
        file_gen_keywords = ("write", "save", "create", "export", "download", "generate", "capture", "screenshot")
        if not is_file_gen and any(kw in action_name.lower() for kw in file_gen_keywords):
            is_file_gen = True

        if is_file_gen:
            await self.event_bus.emit(
                EventType.FILE_GENERATED,
                FileGeneratedEvent(
                    file_path=file_path,
                    file_name=p.name,
                    source_tool=tool_name,
                    source_action=action_name,
                    file_size=p.stat().st_size,
                    session_id=session_id,
                ),
            )

    async def chat(self, user_input: str) -> AgentResponse:
        """处理用户输入，执行 ReAct 循环，返回最终回复。

        通过 chat_lock 序列化并发请求（本地 + 远程 PWA），
        防止多路请求同时写入 session 历史导致数据污染。

        Args:
            user_input: 用户的输入文本

        Returns:
            AgentResponse 包含最终回复、步骤详情、token 用量
        """
        async with self.chat_lock:
            return await self._chat_impl(user_input)

    async def _chat_impl(self, user_input: str) -> AgentResponse:
        """chat() 的内部实现（已持有 chat_lock）。"""
        # Phase 6: 确保意识系统已启动（懒启动）
        self._ensure_consciousness_started()
        
        response = AgentResponse()
        session = self.session_manager.current_session
        session_id = session.id

        # Phase 6: 创建全链路追踪采集器
        trace_config = self._trace_config.copy()
        trace_config["enabled"] = self._enable_trace
        trace_collector = create_trace_collector(
            session_id=session_id,
            user_input=user_input,
            config=trace_config,
        )

        # 【关键修复】清理未完成的 tool_calls（避免 API 报错）
        # 当用户在工具执行期间发送新消息时，需要补全缺失的 tool 响应
        cleaned = self.session_manager.cleanup_incomplete_tool_calls()
        if cleaned > 0:
            logger.warning("已补全 %d 条缺失的 tool 响应消息", cleaned)

        # 添加用户消息
        self.session_manager.add_message(role="user", content=user_input)

        # 发布用户输入事件
        await self.event_bus.emit(EventType.USER_INPUT, {
            "text": user_input,
            "session_id": session_id,
        })

        # Phase 6: 增强意图识别 + 渐进式工具暴露
        intent_result = detect_intent_with_confidence(user_input)
        self.tool_exposure.reset()  # 新对话重置暴露策略状态

        # 获取工具 schema（通过暴露引擎分层过滤 + 标注）
        tools = self.tool_exposure.get_schemas(intent_result)

        # Phase 6: 记录意图识别和工具暴露
        exposed_tool_names = [s["function"]["name"].split("_")[0] for s in tools]
        trace_collector.set_intent(
            intent_result,
            tier=self.tool_exposure.current_tier,
            exposed_tools=exposed_tool_names,
        )

        logger.info(
            "意图识别: primary=%s, confidence=%.2f, intents=%s, tier=%s, schemas=%d",
            intent_result.primary_intent, intent_result.confidence,
            intent_result.intents, self.tool_exposure.current_tier, len(tools),
        )

        # 选择模型
        model_cfg = self.model_selector.select_for_task(
            needs_function_calling=bool(tools),
            model_key=self.model_key,
        )

        # 动态构建 System Prompt（使用增强版意图结果）
        dynamic_system_prompt = build_system_prompt_from_intent(intent_result)
        
        # Phase 6+: 注入意识系统上下文
        if self.consciousness and self.consciousness.is_running:
            try:
                consciousness_context = self.consciousness.get_context_for_prompt()
                if consciousness_context:
                    dynamic_system_prompt += consciousness_context
                    logger.debug("意识上下文已注入提示词")
            except Exception as e:
                logger.error(f"注入意识上下文失败: {e}")
        
        self.session_manager.update_system_prompt(dynamic_system_prompt)

        # 连续失败计数器
        consecutive_failures = 0

        # ReAct 循环
        for step_idx in range(self.max_steps):
            # 发布思考事件
            await self.event_bus.emit(EventType.AGENT_THINKING, AgentThinkingEvent(
                step=step_idx + 1,
                max_steps=self.max_steps,
                model_key=model_cfg.key,
                session_id=session_id,
            ))

            # 获取截断后的消息
            messages = self.session_manager.get_messages(
                max_tokens=model_cfg.context_window,
            )

            # 任务锚定机制：智能锚定，根据执行状态动态调整（Phase 6+ 增强：防重复执行）
            if step_idx >= 3 and step_idx % 3 == 0:
                # 获取执行状态摘要
                tracker_status = self._execution_tracker.get_status_summary()
                
                # 构建智能锚定消息
                anchor_content = self._build_smart_anchor_message(
                    user_input=user_input,
                    step_idx=step_idx,
                    tool_calls_count=response.tool_calls_count,
                    consecutive_failures=consecutive_failures,
                    tracker_status=tracker_status,
                )
                anchor_message = {
                    "role": "user",
                    "content": anchor_content,
                }
                messages = messages + [anchor_message]

            # 发布模型调用事件
            await self.event_bus.emit(EventType.MODEL_CALL, ModelCallEvent(
                model_key=model_cfg.key,
                model_id=model_cfg.id,
                message_count=len(messages),
                has_tools=bool(tools),
                session_id=session_id,
            ))

            # 调用模型（带超时）
            try:
                model_response = await asyncio.wait_for(
                    self.model_registry.chat(
                        model_key=model_cfg.key,
                        messages=messages,
                        tools=tools if tools else None,
                    ),
                    timeout=self.inference_timeout,
                )
            except asyncio.TimeoutError:
                logger.error("模型调用超时 (%s 秒)", self.inference_timeout)
                            
                # Phase 6: 记录错误到意识系统
                if self.consciousness:
                    try:
                        diagnosis = self.consciousness.self_repair.diagnose_issue(
                            error_type="TimeoutError",
                            context={
                                "message": f"模型调用超时 ({self.inference_timeout}秒)",
                                "step": step_idx,
                                "session_id": session_id
                            }
                        )
                        logger.debug(f"意识诊断：{diagnosis}")
                    except Exception as diag_error:
                        logger.error(f"意识诊断失败：{diag_error}")
                            
                await self.event_bus.emit(EventType.MODEL_ERROR, ErrorEvent(
                    source="model",
                    message=f"模型调用超时 ({self.inference_timeout}秒)",
                    error_type="TimeoutError",
                    session_id=session_id,
                ))
                response.content = f"抱歉，AI 模型响应超时，请稍后重试或简化您的问题。"
                trace_collector.finalize(status="error", tokens=response.total_tokens, response_preview=response.content)
                trace_collector.flush()
                return response
            except Exception as e:
                logger.error("模型调用失败：%s", e)
                            
                # Phase 6: 记录错误到意识系统并尝试自我修复
                if self.consciousness:
                    try:
                        diagnosis = self.consciousness.self_repair.diagnose_issue(
                            error_type=type(e).__name__,
                            context={
                                "message": str(e),
                                "step": step_idx,
                                "session_id": session_id
                            }
                        )
                                    
                        # 尝试自动修复
                        if diagnosis and diagnosis.suggested_repair:
                            repair_result = self.consciousness.self_repair.repair_error(diagnosis)
                                        
                            if repair_result and repair_result.success:
                                logger.info("意识系统自我修复成功，重试模型调用...")
                                # 修复成功，可以尝试调整参数后重试
                                # 这里简单处理，直接返回错误信息
                                pass
                                    
                        logger.debug(f"意识诊断：{diagnosis}")
                    except Exception as diag_error:
                        logger.error(f"意识诊断失败：{diag_error}")
                            
                await self.event_bus.emit(EventType.MODEL_ERROR, ErrorEvent(
                    source="model",
                    message=str(e),
                    error_type=type(e).__name__,
                    session_id=session_id,
                ))
                response.content = f"抱歉，AI 模型调用失败：{e}"
                trace_collector.finalize(status="error", tokens=response.total_tokens, response_preview=response.content)
                trace_collector.flush()
                return response

            # 解析模型响应
            choice = model_response.choices[0]
            message = choice.message

            # 记录 token 用量
            usage = getattr(model_response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0)
                response.total_tokens += tokens
                self.session_manager.update_tokens(tokens)

                # 记录费用
                usage_record = UsageRecord(
                    model_key=model_cfg.key,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0),
                    completion_tokens=getattr(usage, "completion_tokens", 0),
                    total_tokens=tokens,
                    cost=(
                        getattr(usage, "prompt_tokens", 0) * model_cfg.cost_input
                        + getattr(usage, "completion_tokens", 0) * model_cfg.cost_output
                    ) / 1_000_000,
                )
                self.cost_tracker.record(usage_record, session_id=session_id)

                await self.event_bus.emit(EventType.MODEL_USAGE, ModelUsageEvent(
                    model_key=model_cfg.key,
                    prompt_tokens=usage_record.prompt_tokens,
                    completion_tokens=usage_record.completion_tokens,
                    total_tokens=tokens,
                    cost=usage_record.cost,
                    session_id=session_id,
                ))
            
            # 解析模型响应
            tool_calls = getattr(message, "tool_calls", None)
            content = getattr(message, "content", "") or ""
            
            # Phase 6: 记录模型推理到意识系统（思考过程）
            if self.consciousness and self.consciousness.is_running:
                try:
                    # 评估思考质量
                    thinking_metrics = {
                        "autonomy_level": 0.7,  # 自主思考
                        "creativity_score": 0.5,  # 中等创造性
                        "goal_relevance": 0.8,  # 高度相关
                        "novelty_score": 0.4   # 常规推理
                    }
                    
                    # 如果有工具调用，说明在规划行动
                    if tool_calls:
                        thinking_metrics["autonomy_level"] = 0.8
                        thinking_metrics["goal_relevance"] = 0.9
                    
                    self.consciousness.record_behavior(
                        action_type="model_reasoning",
                        autonomy_level=thinking_metrics["autonomy_level"],
                        creativity_score=thinking_metrics["creativity_score"],
                        goal_relevance=thinking_metrics["goal_relevance"],
                        novelty_score=thinking_metrics["novelty_score"]
                    )
                    logger.info(f"[意识] 行为已记录: model_reasoning, 总数={len(self.consciousness.emergence_metrics.behavior_history)}")
                except Exception as e:
                    logger.error(f"模型推理意识记录失败：{e}")
            
            # 发布模型响应事件
            await self.event_bus.emit(EventType.MODEL_RESPONSE, ModelResponseEvent(
                model_key=model_cfg.key,
                has_tool_calls=bool(tool_calls),
                content_preview=content[:100],
                session_id=session_id,
            ))

            if not tool_calls:
                # 模型给出了最终回复
                response.content = content
                response.steps.append(AgentStep(
                    step_type="response",
                    content=content,
                ))
                self.session_manager.add_assistant_message(content)

                await self.event_bus.emit(EventType.AGENT_RESPONSE, AgentResponseEvent(
                    content=content,
                    total_steps=step_idx + 1,
                    total_tokens=response.total_tokens,
                    tool_calls_count=response.tool_calls_count,
                    session_id=session_id,
                ))

                logger.info("Agent 最终回复（%d 步，%d tokens）", step_idx + 1, response.total_tokens)
                trace_collector.finalize(
                    status="completed",
                    tokens=response.total_tokens,
                    response_preview=response.content,
                )
                trace_collector.flush()
                return response

            # 有 tool calls，需要执行工具
            assistant_msg_tool_calls = []
            for tc in tool_calls:
                func_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                assistant_msg_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                    },
                })

            # 单次工具调用数量限制
            if len(tool_calls) > MAX_TOOLS_PER_CALL:
                logger.warning(
                    "单次工具调用数量(%d)超过上限(%d)，拒绝执行",
                    len(tool_calls), MAX_TOOLS_PER_CALL,
                )
                reject_msg = (
                    f"[系统] 单次工具调用数量({len(tool_calls)})超过限制({MAX_TOOLS_PER_CALL})，"
                    f"请分步执行，每步最多调用 {MAX_TOOLS_PER_CALL} 个工具。"
                )
                self.session_manager.add_assistant_message(
                    content=content,
                    tool_calls=assistant_msg_tool_calls,
                )
                # 为每个 tool_call 都添加拒绝消息（API 要求每个 tool_call 必须有对应 tool 消息）
                for tc in tool_calls:
                    self.session_manager.add_tool_message(
                        tool_call_id=tc.id,
                        content=reject_msg,
                    )
                continue

            self.session_manager.add_assistant_message(
                content=content,
                tool_calls=assistant_msg_tool_calls,
            )

            # 逐个执行 tool calls
            for tc_idx, tc in enumerate(tool_calls):
                func_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
            
                response.tool_calls_count += 1
            
                resolved = self.tool_registry.resolve_function_name(func_name)
                tool_name = resolved[0] if resolved else func_name
                action_name = resolved[1] if resolved else ""
            
                # Phase 6: 检查工具是否已废弃
                tool_cfg = self.tool_registry.get_tool_config(tool_name)
                if tool_cfg.get("deprecated", False):
                    deprecation_msg = tool_cfg.get("deprecation_message", "此工具已废弃")
                    migrate_to = tool_cfg.get("migrate_to", "")
                    logger.warning(
                        "调用已废弃工具：%s (替代：%s)",
                        tool_name, migrate_to or "无",
                    )
                    # 返回废弃提示消息
                    result_msg = f"[已废弃] {deprecation_msg}"
                    if migrate_to:
                        result_msg += f"\n请使用 {migrate_to} 替代。"
                    self.session_manager.add_tool_message(
                        tool_call_id=tc.id,
                        content=result_msg,
                    )
                    continue
            
                # 发布工具调用事件
                await self.event_bus.emit(EventType.TOOL_CALL, ToolCallEvent(
                    tool_name=tool_name,
                    action_name=action_name,
                    arguments=arguments,
                    function_name=func_name,
                    session_id=session_id,
                ))
            
                step = AgentStep(
                    step_type="tool_call",
                    tool_name=tool_name,
                    tool_action=action_name,
                    tool_args=arguments,
                )
            
                # 执行工具
                result = await self.tool_registry.call_function(func_name, arguments)
                step.tool_result = result.to_message(failure_count=consecutive_failures)
                response.steps.append(step)
            
                # Phase 6: 记录工具调用到追踪
                trace_collector.add_tool_call(
                    step=step_idx + 1,
                    function_name=func_name,
                    arguments=arguments,
                    status=result.status.value,
                    duration_ms=result.duration_ms,
                    error=result.error,
                    output=result.output,
                )
            
                # 连续失败检测 + 执行跟踪器更新
                if result.status.value != "success":
                    consecutive_failures += 1
                    # 更新执行跟踪器
                    self._execution_tracker.record_failure()
                    upgrade_info = self.tool_exposure.report_failure()
                    # Phase 6: 记录层级升级
                    if upgrade_info:
                        trace_collector.add_tier_upgrade(upgrade_info[0], upgrade_info[1])
                    logger.warning(
                        "工具调用失败 (%d/%d): %s.%s",
                        consecutive_failures, MAX_CONSECUTIVE_FAILURES,
                        tool_name, action_name
                    )
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        error_msg = (
                            f"抱歉，连续 {consecutive_failures} 次工具调用失败，任务终止。\n"
                            f"请检查：\n"
                            f"1. 相关服务是否正常运行\n"
                            f"2. 参数是否正确\n"
                            f"3. 网络连接是否稳定"
                        )
                                    
                        # 【关键修复】为剩余未处理的 tool_call 都添加错误消息
                        # 确保每个 tool_call 都有对应的 tool 结果消息
                        for remaining_tc in tool_calls[tc_idx:]:
                            # 跳过当前这个（已经在上面处理过了）
                            if remaining_tc == tc:
                                continue
                            self.session_manager.add_tool_message(
                                tool_call_id=remaining_tc.id,
                                content=f"[错误] 任务因连续失败而终止，此工具未执行",
                            )
                                    
                        response.content = error_msg
                        self.session_manager.add_assistant_message(error_msg)
                        await self.event_bus.emit(EventType.AGENT_ERROR, ErrorEvent(
                            source="agent",
                            message=f"连续 {consecutive_failures} 次工具调用失败",
                            session_id=session_id,
                        ))
                        # Phase 6: 完成追踪并写入
                        trace_collector.finalize(
                            status="error",
                            tokens=response.total_tokens,
                            response_preview=error_msg,
                        )
                        trace_collector.flush()
                        return response
                else:
                    consecutive_failures = 0  # 成功则重置计数器
                    self.tool_exposure.report_success()
                                
                    # 更新执行跟踪器 - 记录成功的工具调用
                    self._execution_tracker.record_success(tool_name, action_name, arguments)
                                
                    # Phase 6: 记录到意识系统
                    if self.consciousness and self.consciousness.is_running:
                        try:
                            # 使用默认指标评估工具调用
                            metrics = {
                                "autonomy_level": 0.8,  # 工具调用是主动行为
                                "creativity_score": 0.5,  # 中等创造性
                                "goal_relevance": 0.9,  # 高度相关
                                "novelty_score": 0.3   # 工具调用是常规操作
                            }
                                        
                            # 如果有评估器，使用它计算指标
                            if self.consciousness_evaluator:
                                try:
                                    eval_metrics = self.consciousness_evaluator.evaluate_tool_call(
                                        tool_name=tool_name,
                                        result=result,
                                        user_input=user_input,
                                        context={"step": step_idx, "session_id": session_id}
                                    )
                                    metrics.update(eval_metrics)
                                except Exception:
                                    pass  # 使用默认指标
                                        
                            # 记录行为到意识系统
                            self.consciousness.record_behavior(
                                action_type=f"tool_usage:{tool_name}.{action_name}",
                                autonomy_level=metrics["autonomy_level"],
                                creativity_score=metrics["creativity_score"],
                                goal_relevance=metrics["goal_relevance"],
                                novelty_score=metrics["novelty_score"]
                            )
                            logger.info(f"[意识] 行为已记录：tool_usage, 总数={len(self.consciousness.emergence_metrics.behavior_history)}")
                        except Exception as e:
                            logger.error(f"意识记录失败：{e}")

                # 发布工具结果事件
                await self.event_bus.emit(EventType.TOOL_RESULT, ToolResultEvent(
                    tool_name=tool_name,
                    action_name=action_name,
                    status=result.status.value,
                    output=result.output[:500] if result.output else "",
                    error=result.error,
                    duration_ms=result.duration_ms,
                    session_id=session_id,
                ))

                logger.info(
                    "  工具 %s.%s → %s (%.0fms)",
                    tool_name, action_name,
                    result.status.value, result.duration_ms,
                )

                # 检测文件生成
                await self._check_and_emit_file_generated(
                    tool_name, action_name, result, session_id,
                )

                # 将工具结果加入对话历史
                tool_result_content = result.to_message(failure_count=consecutive_failures)
                # 如果有 html_image，添加到内容中（用于 GUI 直接显示图片）
                if result.is_success and result.data:
                    html_img = result.data.get("html_image")
                    if html_img:
                        tool_result_content = f"{result.output}\n\n{html_img}"

                self.session_manager.add_tool_message(
                    tool_call_id=tc.id,
                    content=tool_result_content,
                )

        # 超过最大步数
        response.content = "（任务执行步数已达上限，请尝试拆分为更小的任务）"
        self.session_manager.add_assistant_message(response.content)

        await self.event_bus.emit(EventType.AGENT_ERROR, ErrorEvent(
            source="agent",
            message="达到最大步数限制",
            session_id=session_id,
        ))

        trace_collector.finalize(
            status="max_steps",
            tokens=response.total_tokens,
            response_preview=response.content,
        )
        trace_collector.flush()

        return response

    async def chat_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """流式处理用户输入，yield 文本片段。

        通过 chat_lock 序列化并发请求（本地 + 远程 PWA）：
        锁在生成器整个生命周期内保持持有，确保 session 历史不被
        并发请求污染。后续请求会等待当前请求完成后再开始。

        与 chat() 使用相同的 ReAct 循环逻辑，但对最终文本回复进行流式输出：
        - 工具调用步骤：内部收集完整 tool_calls 后执行，不 yield
        - 文本回复：逐 chunk yield 给调用方
        - 工具调用信息通过 EventBus 事件传递

        Args:
            user_input: 用户的输入文本

        Yields:
            str: 模型生成的文本片段
        """
        # 等待获取锁（串行化所有请求：本地 UI + 远程 PWA）
        await self.chat_lock.acquire()
        try:
            async for chunk in self._chat_stream_impl(user_input):
                yield chunk
        finally:
            self.chat_lock.release()

    async def _chat_stream_impl(self, user_input: str) -> AsyncGenerator[str, None]:
        """chat_stream() 的内部实现（已持有 chat_lock）。"""
        session = self.session_manager.current_session
        session_id = session.id
        total_tokens = 0
        tool_calls_count = 0

        # Phase 6: 创建全链路追踪采集器
        trace_config = self._trace_config.copy()
        trace_config["enabled"] = self._enable_trace
        trace_collector = create_trace_collector(
            session_id=session_id,
            user_input=user_input,
            config=trace_config,
        )

        # 添加用户消息
        self.session_manager.add_message(role="user", content=user_input)

        # 发布用户输入事件
        await self.event_bus.emit(EventType.USER_INPUT, {
            "text": user_input,
            "session_id": session_id,
        })

        # Phase 6: 增强意图识别 + 渐进式工具暴露
        intent_result = detect_intent_with_confidence(user_input)
        self.tool_exposure.reset()

        # 获取工具 schema（通过暴露引擎分层过滤 + 标注）
        tools = self.tool_exposure.get_schemas(intent_result)

        # Phase 6: 记录意图识别和工具暴露
        exposed_tool_names = [s["function"]["name"].split("_")[0] for s in tools]
        trace_collector.set_intent(
            intent_result,
            tier=self.tool_exposure.current_tier,
            exposed_tools=exposed_tool_names,
        )

        logger.info(
            "流式模式意图识别: primary=%s, confidence=%.2f, intents=%s, tier=%s, schemas=%d",
            intent_result.primary_intent, intent_result.confidence,
            intent_result.intents, self.tool_exposure.current_tier, len(tools),
        )

        # 选择模型
        model_cfg = self.model_selector.select_for_task(
            needs_function_calling=bool(tools),
            model_key=self.model_key,
        )

        # 动态构建 System Prompt（使用增强版意图结果）
        dynamic_system_prompt = build_system_prompt_from_intent(intent_result)
        
        # Phase 6+: 注入意识系统上下文
        if self.consciousness and self.consciousness.is_running:
            try:
                consciousness_context = self.consciousness.get_context_for_prompt()
                if consciousness_context:
                    dynamic_system_prompt += consciousness_context
                    logger.debug("意识上下文已注入提示词")
            except Exception as e:
                logger.error(f"注入意识上下文失败: {e}")
        
        self.session_manager.update_system_prompt(dynamic_system_prompt)

        # 连续失败计数器
        consecutive_failures = 0

        # ReAct 循环
        for step_idx in range(self.max_steps):
            # 发布思考事件
            await self.event_bus.emit(EventType.AGENT_THINKING, AgentThinkingEvent(
                step=step_idx + 1,
                max_steps=self.max_steps,
                model_key=model_cfg.key,
                session_id=session_id,
            ))

            # 获取截断后的消息
            messages = self.session_manager.get_messages(
                max_tokens=model_cfg.context_window,
            )

            # 任务锚定机制：智能锚定，根据执行状态动态调整（Phase 6+ 增强：防重复执行）
            if step_idx >= 3 and step_idx % 3 == 0:
                # 获取执行状态摘要
                tracker_status = self._execution_tracker.get_status_summary()
                
                # 构建智能锚定消息
                anchor_content = self._build_smart_anchor_message(
                    user_input=user_input,
                    step_idx=step_idx,
                    tool_calls_count=tool_calls_count,
                    consecutive_failures=consecutive_failures,
                    tracker_status=tracker_status,
                )
                anchor_message = {
                    "role": "user",
                    "content": anchor_content,
                }
                messages = messages + [anchor_message]

            # 发布模型调用事件
            await self.event_bus.emit(EventType.MODEL_CALL, ModelCallEvent(
                model_key=model_cfg.key,
                model_id=model_cfg.id,
                message_count=len(messages),
                has_tools=bool(tools),
                session_id=session_id,
            ))

            # 流式调用模型（带超时）
            try:
                collected_content = ""
                collected_tool_calls: list[dict] = []
                last_usage = None
            
                # 使用超时包装器处理流
                # 本地 Ollama 模型可能需要更长时间，使用更长的超时
                chunk_timeout = STREAM_CHUNK_TIMEOUT
                if model_cfg.provider == "ollama":
                    chunk_timeout = 300  # Ollama 本地模型 5 分钟超时
                            
                stream = self.model_registry.chat_stream(
                    model_key=model_cfg.key,
                    messages=messages,
                    tools=tools if tools else None,
                )
                            
                async for chunk in _stream_with_timeout(stream, chunk_timeout):
                    choice = chunk.choices[0] if chunk.choices else None
                    if choice is None:
                        # 可能是最后一个 chunk 只含 usage
                        usage = getattr(chunk, "usage", None)
                        if usage:
                            last_usage = usage
                        continue

                    delta = choice.delta

                    # 收集思考过程 (reasoning_content) - DeepSeek等模型支持
                    delta_reasoning = getattr(delta, "reasoning_content", None) or ""
                    if delta_reasoning:
                        await self.event_bus.emit(EventType.MODEL_REASONING, ModelReasoningEvent(
                            reasoning=delta_reasoning,
                            is_delta=True,
                            is_complete=False,
                            session_id=session_id,
                        ))

                    # 收集文本内容
                    delta_content = getattr(delta, "content", None) or ""
                    if delta_content:
                        collected_content += delta_content
                        yield delta_content  # 实时 yield 文本片段

                    # 收集 tool_calls（增量拼接）
                    delta_tool_calls = getattr(delta, "tool_calls", None)
                    if delta_tool_calls:
                        for dtc in delta_tool_calls:
                            idx = dtc.index
                            # 扩展列表
                            while len(collected_tool_calls) <= idx:
                                collected_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                })
                            tc_entry = collected_tool_calls[idx]
                            if dtc.id:
                                tc_entry["id"] = dtc.id
                            if dtc.function:
                                if dtc.function.name:
                                    tc_entry["function"]["name"] += dtc.function.name
                                if dtc.function.arguments:
                                    tc_entry["function"]["arguments"] += dtc.function.arguments

                    # 从 chunk 提取 usage（部分 provider 在最后一个 chunk 附带）
                    usage = getattr(chunk, "usage", None)
                    if usage:
                        last_usage = usage

                # 记录 token 用量
                if last_usage:
                    tokens = getattr(last_usage, "total_tokens", 0)
                    total_tokens += tokens
                    self.session_manager.update_tokens(tokens)
                    self.model_registry.record_stream_usage(model_cfg.key, last_usage)

                    usage_record = UsageRecord(
                        model_key=model_cfg.key,
                        prompt_tokens=getattr(last_usage, "prompt_tokens", 0),
                        completion_tokens=getattr(last_usage, "completion_tokens", 0),
                        total_tokens=tokens,
                        cost=(
                            getattr(last_usage, "prompt_tokens", 0) * model_cfg.cost_input
                            + getattr(last_usage, "completion_tokens", 0) * model_cfg.cost_output
                        ) / 1_000_000,
                    )
                    self.cost_tracker.record(usage_record, session_id=session_id)

                    await self.event_bus.emit(EventType.MODEL_USAGE, ModelUsageEvent(
                        model_key=model_cfg.key,
                        prompt_tokens=usage_record.prompt_tokens,
                        completion_tokens=usage_record.completion_tokens,
                        total_tokens=tokens,
                        cost=usage_record.cost,
                        session_id=session_id,
                    ))

                # 发布模型响应事件
                has_tool_calls = bool(collected_tool_calls)
                await self.event_bus.emit(EventType.MODEL_RESPONSE, ModelResponseEvent(
                    model_key=model_cfg.key,
                    has_tool_calls=has_tool_calls,
                    content_preview=collected_content[:100],
                    session_id=session_id,
                ))

                # 发送思考过程完成事件
                await self.event_bus.emit(EventType.MODEL_REASONING, ModelReasoningEvent(
                    reasoning="",
                    is_delta=False,
                    is_complete=True,
                    session_id=session_id,
                ))

                if not has_tool_calls:
                    # 最终回复（文本已通过 yield 流式输出）
                    self.session_manager.add_assistant_message(collected_content)

                    await self.event_bus.emit(EventType.AGENT_RESPONSE, AgentResponseEvent(
                        content=collected_content,
                        total_steps=step_idx + 1,
                        total_tokens=total_tokens,
                        tool_calls_count=tool_calls_count,
                        session_id=session_id,
                    ))

                    logger.info(
                        "Agent 流式回复（%d 步，%d tokens）",
                        step_idx + 1, total_tokens,
                    )
                    trace_collector.finalize(
                        status="completed",
                        tokens=total_tokens,
                        response_preview=collected_content,
                    )
                    trace_collector.flush()
                    return

                # 有 tool calls，执行工具
                assistant_msg_tool_calls = []
                for tc_entry in collected_tool_calls:
                    assistant_msg_tool_calls.append({
                        "id": tc_entry["id"],
                        "type": "function",
                        "function": {
                            "name": tc_entry["function"]["name"],
                            "arguments": tc_entry["function"]["arguments"],
                        },
                    })

                # 单次工具调用数量限制
                if len(collected_tool_calls) > MAX_TOOLS_PER_CALL:
                    logger.warning(
                        "流式模式: 单次工具调用数量(%d)超过上限(%d)，拒绝执行",
                        len(collected_tool_calls), MAX_TOOLS_PER_CALL,
                    )
                    reject_msg = (
                        f"[系统] 单次工具调用数量({len(collected_tool_calls)})超过限制({MAX_TOOLS_PER_CALL})，"
                        f"请分步执行，每步最多调用 {MAX_TOOLS_PER_CALL} 个工具。"
                    )
                    self.session_manager.add_assistant_message(
                        content=collected_content,
                        tool_calls=assistant_msg_tool_calls,
                    )
                    for tc_entry in collected_tool_calls:
                        self.session_manager.add_tool_message(
                            tool_call_id=tc_entry["id"],
                            content=reject_msg,
                        )
                    continue

                self.session_manager.add_assistant_message(
                    content=collected_content,
                    tool_calls=assistant_msg_tool_calls,
                )

                # 逐个执行 tool calls
                for tc_idx, tc_entry in enumerate(collected_tool_calls):
                    func_name = tc_entry["function"]["name"]
                    try:
                        arguments = json.loads(tc_entry["function"]["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}
                
                    tool_calls_count += 1
                
                    resolved = self.tool_registry.resolve_function_name(func_name)
                    tool_name = resolved[0] if resolved else func_name
                    action_name = resolved[1] if resolved else ""
                
                    # Phase 6: 检查工具是否已废弃
                    tool_cfg = self.tool_registry.get_tool_config(tool_name)
                    if tool_cfg.get("deprecated", False):
                        deprecation_msg = tool_cfg.get("deprecation_message", "此工具已废弃")
                        migrate_to = tool_cfg.get("migrate_to", "")
                        logger.warning(
                            "调用已废弃工具：%s (替代：%s)",
                            tool_name, migrate_to or "无",
                        )
                        # 返回废弃提示消息
                        result_msg = f"[已废弃] {deprecation_msg}"
                        if migrate_to:
                            result_msg += f"\n请使用 {migrate_to} 替代。"
                        self.session_manager.add_tool_message(
                            tool_call_id=tc_entry["id"],
                            content=result_msg,
                        )
                        continue
                
                    # 发布工具调用事件
                    await self.event_bus.emit(EventType.TOOL_CALL, ToolCallEvent(
                        tool_name=tool_name,
                        action_name=action_name,
                        arguments=arguments,
                        function_name=func_name,
                        session_id=session_id,
                    ))
                
                    # 执行工具
                    result = await self.tool_registry.call_function(func_name, arguments)
                
                    # Phase 6: 记录工具调用到追踪
                    trace_collector.add_tool_call(
                        step=step_idx + 1,
                        function_name=func_name,
                        arguments=arguments,
                        status=result.status.value,
                        duration_ms=result.duration_ms,
                        error=result.error,
                        output=result.output,
                    )
                
                    # 获取 html_image 用于 GUI 显示（不发送到 AI）
                    html_image = ""
                    if result.is_success and result.data:
                        html_image = result.data.get("html_image", "")
                
                    # 发布工具结果事件（包含 html_image 用于 GUI 显示）
                    await self.event_bus.emit(EventType.TOOL_RESULT, ToolResultEvent(
                        tool_name=tool_name,
                        action_name=action_name,
                        status=result.status.value,
                        output=result.output[:500] if result.output else "",
                        error=result.error,
                        duration_ms=result.duration_ms,
                        session_id=session_id,
                        html_image=html_image,
                    ))
                
                    logger.info(
                        "  工具 %s.%s → %s (%.0fms)",
                        tool_name, action_name,
                        result.status.value, result.duration_ms,
                    )
                
                    # 连续失败检测 + 执行跟踪器更新
                    if result.status.value != "success":
                        consecutive_failures += 1
                        # 更新执行跟踪器
                        self._execution_tracker.record_failure()
                        upgrade_info = self.tool_exposure.report_failure()
                        # Phase 6: 记录层级升级
                        if upgrade_info:
                            trace_collector.add_tier_upgrade(upgrade_info[0], upgrade_info[1])
                        logger.warning(
                            "工具调用失败 (%d/%d): %s.%s",
                            consecutive_failures, MAX_CONSECUTIVE_FAILURES,
                            tool_name, action_name
                        )
                        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            error_msg = (
                                f"\n抱歉，连续 {consecutive_failures} 次工具调用失败，任务终止。\n"
                                f"请检查相关服务是否正常运行。"
                            )
                                            
                            # 【关键修复】为剩余未处理的 tool_call 都添加错误消息
                            # 确保每个 tool_call 都有对应的 tool 结果消息
                            for remaining_tc in collected_tool_calls[tc_idx:]:
                                # 跳过当前这个（已经在上面处理过了）
                                if remaining_tc == tc_entry:
                                    continue
                                self.session_manager.add_tool_message(
                                    tool_call_id=remaining_tc["id"],
                                    content=f"[错误] 任务因连续失败而终止，此工具未执行",
                                )
                                            
                            self.session_manager.add_assistant_message(error_msg)
                            await self.event_bus.emit(EventType.AGENT_ERROR, ErrorEvent(
                                source="agent",
                                message=f"连续 {consecutive_failures} 次工具调用失败",
                                session_id=session_id,
                            ))
                            trace_collector.finalize(
                                status="error",
                                tokens=total_tokens,
                                response_preview=error_msg,
                            )
                            trace_collector.flush()
                            yield error_msg
                            return
                    else:
                        consecutive_failures = 0  # 成功则重置计数器
                        self.tool_exposure.report_success()
                                        
                        # 更新执行跟踪器 - 记录成功的工具调用
                        self._execution_tracker.record_success(tool_name, action_name, arguments)
                
                    # 检测文件生成
                    await self._check_and_emit_file_generated(
                        tool_name, action_name, result, session_id,
                    )
                
                    # 将工具结果加入对话历史
                    tool_result_content = result.to_message(failure_count=consecutive_failures)
                    if result.is_success and result.data and result.data.get("base64"):
                        tool_result_content = result.output
                
                    self.session_manager.add_tool_message(
                        tool_call_id=tc_entry["id"],
                        content=tool_result_content,
                    )

            except asyncio.TimeoutError:
                logger.error("流式模型响应超时")
                await self.event_bus.emit(EventType.MODEL_ERROR, ErrorEvent(
                    source="model",
                    message=f"流式响应超时 ({STREAM_CHUNK_TIMEOUT}秒无响应)",
                    error_type="TimeoutError",
                    session_id=session_id,
                ))
                error_msg = "\n抱歉，AI 模型响应超时，请稍后重试。"
                trace_collector.finalize(status="error", tokens=total_tokens, response_preview=error_msg)
                trace_collector.flush()
                yield error_msg
                return
            except Exception as e:
                logger.error("流式模型调用失败: %s", e)
                await self.event_bus.emit(EventType.MODEL_ERROR, ErrorEvent(
                    source="model",
                    message=str(e),
                    error_type=type(e).__name__,
                    session_id=session_id,
                ))
                error_msg = f"\n抱歉，AI 模型调用失败: {e}"
                trace_collector.finalize(status="error", tokens=total_tokens, response_preview=error_msg)
                trace_collector.flush()
                yield error_msg
                return

        # 超过最大步数
        max_step_msg = "（任务执行步数已达上限，请尝试拆分为更小的任务）"
        self.session_manager.add_assistant_message(max_step_msg)

        await self.event_bus.emit(EventType.AGENT_ERROR, ErrorEvent(
            source="agent",
            message="达到最大步数限制",
            session_id=session_id,
        ))

        trace_collector.finalize(status="max_steps", tokens=total_tokens, response_preview=max_step_msg)
        trace_collector.flush()

        yield max_step_msg

    # ------------------------------------------------------------------
    # CFTA: Chat-First, Tools-Async — 语音模式快速聊天 + 异步工具
    # ------------------------------------------------------------------

    async def chat_stream_voice_fast(self, user_input: str) -> AsyncGenerator[str, None]:
        """语音模式快速聊天流（无工具），最小化首 token 延迟。

        差异点与标准 chat_stream：
        - 不做工具暴露，不传 tools 给模型
        - 使用轻量 system prompt（核心 + 陪伴模块）
        - 仅做流式文本输出，不支持 tool_calls
        - 单次模型调用，不进入 ReAct 循环

        Args:
            user_input: 用户的输入文本

        Yields:
            str: 模型生成的文本片段
        """
        await self.chat_lock.acquire()
        try:
            async for chunk in self._chat_stream_voice_fast_impl(user_input):
                yield chunk
        finally:
            self.chat_lock.release()

    async def _chat_stream_voice_fast_impl(
        self, user_input: str
    ) -> AsyncGenerator[str, None]:
        """语音快速聊天内部实现（已持有 chat_lock）。"""
        session = self.session_manager.current_session
        session_id = session.id

        # 【关键修复】清理未完成的 tool_calls
        cleaned = self.session_manager.cleanup_incomplete_tool_calls()
        if cleaned > 0:
            logger.warning("[CFTA-fast] 已补全 %d 条缺失的 tool 响应消息", cleaned)

        # 添加用户消息
        self.session_manager.add_message(role="user", content=user_input)

        # 轻量系统提示词（不含工具指南）
        lightweight_prompt = CORE_SYSTEM_PROMPT + "\n\n" + COMPANION_PROMPT_MODULE
        self.session_manager.update_system_prompt(lightweight_prompt)

        # 选择模型（无需 function calling）
        model_cfg = self.model_selector.select_for_task(
            needs_function_calling=False,
            model_key=self.model_key,
        )

        messages = self.session_manager.get_messages(
            max_tokens=model_cfg.context_window,
        )

        logger.info(
            "[CFTA] 快速聊天模式: model=%s, messages=%d, tools=None",
            model_cfg.key, len(messages),
        )

        # 发布模型调用事件
        await self.event_bus.emit(EventType.MODEL_CALL, ModelCallEvent(
            model_key=model_cfg.key,
            model_id=model_cfg.id,
            message_count=len(messages),
            has_tools=False,
            session_id=session_id,
        ))

        collected_content = ""
        last_usage = None

        chunk_timeout = STREAM_CHUNK_TIMEOUT
        if model_cfg.provider == "ollama":
            chunk_timeout = 300

        try:
            stream = self.model_registry.chat_stream(
                model_key=model_cfg.key,
                messages=messages,
                tools=None,  # 关键: 不传工具，减少 prompt token
            )

            async for chunk in _stream_with_timeout(stream, chunk_timeout):
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    usage = getattr(chunk, "usage", None)
                    if usage:
                        last_usage = usage
                    continue

                delta = choice.delta
                delta_content = getattr(delta, "content", None) or ""
                if delta_content:
                    collected_content += delta_content
                    yield delta_content

                usage = getattr(chunk, "usage", None)
                if usage:
                    last_usage = usage

        except asyncio.TimeoutError:
            logger.error("[CFTA] 快速聊天流式响应超时")
            yield "\n抱歉，响应超时，请稍后重试。"
            return
        except Exception as e:
            logger.error("[CFTA] 快速聊天模型调用失败: %s", e)
            yield f"\n抱歉，聊天失败: {e}"
            return

        # 记录 token 用量
        if last_usage:
            tokens = getattr(last_usage, "total_tokens", 0)
            self.session_manager.update_tokens(tokens)
            self.model_registry.record_stream_usage(model_cfg.key, last_usage)

            usage_record = UsageRecord(
                model_key=model_cfg.key,
                prompt_tokens=getattr(last_usage, "prompt_tokens", 0),
                completion_tokens=getattr(last_usage, "completion_tokens", 0),
                total_tokens=tokens,
                cost=(
                    getattr(last_usage, "prompt_tokens", 0) * model_cfg.cost_input
                    + getattr(last_usage, "completion_tokens", 0) * model_cfg.cost_output
                ) / 1_000_000,
            )
            self.cost_tracker.record(usage_record, session_id=session_id)

            await self.event_bus.emit(EventType.MODEL_USAGE, ModelUsageEvent(
                model_key=model_cfg.key,
                prompt_tokens=usage_record.prompt_tokens,
                completion_tokens=usage_record.completion_tokens,
                total_tokens=tokens,
                cost=usage_record.cost,
                session_id=session_id,
            ))

        # 发布模型响应事件
        await self.event_bus.emit(EventType.MODEL_RESPONSE, ModelResponseEvent(
            model_key=model_cfg.key,
            has_tool_calls=False,
            content_preview=collected_content[:100],
            session_id=session_id,
        ))

        # 写入 session 历史
        self.session_manager.add_assistant_message(collected_content)

        await self.event_bus.emit(EventType.AGENT_RESPONSE, AgentResponseEvent(
            content=collected_content,
            total_steps=1,
            total_tokens=getattr(last_usage, "total_tokens", 0) if last_usage else 0,
            tool_calls_count=0,
            session_id=session_id,
        ))

        logger.info("[CFTA] 快速聊天完成，共 %d 字符", len(collected_content))

    async def process_deferred_tools(
        self, user_input: str, fast_reply: str, session_id: str,
    ) -> str | None:
        """CFTA Phase 2: 后台异步执行工具检测与调用。

        在 Phase 1 快速聊天完成后调用。带完整的 tool schema
        重新调用模型，如果模型认为需要工具则执行，否则静默退出。

        此方法使用 deferred_lock 而非 chat_lock，
        因此不会阻塞新的聊天请求。

        Args:
            user_input: 原始用户输入
            fast_reply: Phase 1 的快速回复内容
            session_id: 会话 ID

        Returns:
            工具执行结果摘要文本，或 None（无需工具）
        """
        async with self.deferred_lock:
            # 发布异步工具开始事件
            await self.event_bus.emit(
                EventType.DEFERRED_TOOL_STARTED,
                DeferredToolStartedEvent(
                    user_input=user_input,
                    session_id=session_id,
                ),
            )

            # 意图识别 + 工具暴露
            intent_result = detect_intent_with_confidence(user_input)
            self.tool_exposure.reset()
            tools = self.tool_exposure.get_schemas(intent_result)

            if not tools:
                logger.info("[CFTA-deferred] 无可用工具，静默退出")
                return None

            logger.info(
                "[CFTA-deferred] 异步工具检测: intents=%s, schemas=%d",
                intent_result.intents, len(tools),
            )

            # 选择模型（需要 function calling）
            model_cfg = self.model_selector.select_for_task(
                needs_function_calling=True,
                model_key=self.model_key,
            )

            # 动态构建 System Prompt（带工具指南）
            dynamic_system_prompt = build_system_prompt_from_intent(intent_result)

            # 构建特殊的 messages：包含快速回复上下文 + 工具检测指令
            deferred_system_msg = (
                dynamic_system_prompt
                + "\n\n[异步工具模式] 你已经对用户做了快速回复，"
                "\n现在请判断用户的请求是否需要调用工具来完成。"
                "\n如果需要工具，请直接调用；如果不需要，请回复 '[CFTA_NO_TOOL]'。"
            )

            # 构建专用的消息列表（不污染主 session）
            deferred_messages = [
                {"role": "system", "content": deferred_system_msg},
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": fast_reply},
                {
                    "role": "user",
                    "content": (
                        "请检查上面的对话，判断是否需要调用工具来完成用户的请求。"
                        "如果需要，请直接调用工具；如果不需要，请回复 '[CFTA_NO_TOOL]'。"
                    ),
                },
            ]

            # 调用模型（带工具，非流式）
            try:
                model_response = await asyncio.wait_for(
                    self.model_registry.chat(
                        model_key=model_cfg.key,
                        messages=deferred_messages,
                        tools=tools,
                    ),
                    timeout=self.inference_timeout,
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                logger.warning("[CFTA-deferred] 模型调用超时或被取消")
                return None
            except Exception as e:
                logger.error("[CFTA-deferred] 模型调用失败: %s", e)
                return None

            # 解析响应
            choice = model_response.choices[0]
            message = choice.message
            tool_calls = getattr(message, "tool_calls", None)
            content = getattr(message, "content", "") or ""

            # 记录 token 用量
            usage = getattr(model_response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0)
                self.session_manager.update_tokens(tokens)
                usage_record = UsageRecord(
                    model_key=model_cfg.key,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0),
                    completion_tokens=getattr(usage, "completion_tokens", 0),
                    total_tokens=tokens,
                    cost=(
                        getattr(usage, "prompt_tokens", 0) * model_cfg.cost_input
                        + getattr(usage, "completion_tokens", 0) * model_cfg.cost_output
                    ) / 1_000_000,
                )
                self.cost_tracker.record(usage_record, session_id=session_id)

            if not tool_calls:
                # 模型认为不需要工具
                logger.info("[CFTA-deferred] 模型未返回工具调用，静默退出")
                return None

            # --- 有工具调用，执行工具 ---
            logger.info(
                "[CFTA-deferred] 检测到 %d 个工具调用，开始后台执行",
                len(tool_calls),
            )

            executed_tools: list[str] = []
            result_parts: list[str] = []

            for tc in tool_calls:
                func_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                resolved = self.tool_registry.resolve_function_name(func_name)
                tool_name = resolved[0] if resolved else func_name
                action_name = resolved[1] if resolved else ""

                # 发布工具调用事件
                await self.event_bus.emit(EventType.TOOL_CALL, ToolCallEvent(
                    tool_name=tool_name,
                    action_name=action_name,
                    arguments=arguments,
                    function_name=func_name,
                    session_id=session_id,
                ))

                # 执行工具
                result = await self.tool_registry.call_function(func_name, arguments)

                # 发布工具结果事件
                await self.event_bus.emit(EventType.TOOL_RESULT, ToolResultEvent(
                    tool_name=tool_name,
                    action_name=action_name,
                    status=result.status.value,
                    output=result.output[:500] if result.output else "",
                    error=result.error,
                    duration_ms=result.duration_ms,
                    session_id=session_id,
                ))

                logger.info(
                    "[CFTA-deferred]   %s.%s → %s (%.0fms)",
                    tool_name, action_name,
                    result.status.value, result.duration_ms,
                )

                executed_tools.append(f"{tool_name}.{action_name}")
                if result.is_success:
                    result_parts.append(
                        f"{tool_name}.{action_name}: {result.output[:200]}"
                    )
                else:
                    result_parts.append(
                        f"{tool_name}.{action_name}: 失败 - {result.error}"
                    )

                # 检测文件生成
                await self._check_and_emit_file_generated(
                    tool_name, action_name, result, session_id,
                )

            # 构建结果摘要
            summary = "\n".join(result_parts)

            # 将工具执行结果追加到 session 历史
            # 使用 chat_lock 保护 session 写入
            async with self.chat_lock:
                self.session_manager.add_message(
                    role="assistant",
                    content=f"[后台任务完成] {summary}",
                )

            # 发布异步工具结果事件
            await self.event_bus.emit(
                EventType.DEFERRED_TOOL_RESULT,
                DeferredToolResultEvent(
                    result_summary=summary,
                    tool_names=executed_tools,
                    session_id=session_id,
                ),
            )

            logger.info(
                "[CFTA-deferred] 异步工具执行完成: %s", executed_tools,
            )
            return summary

    def cancel_deferred_tools(self) -> None:
        """CFTA: 取消正在进行的后台工具任务。

        在新的用户输入到达时调用，避免过时的异步任务继续执行。
        """
        if self._deferred_task and not self._deferred_task.done():
            self._deferred_task.cancel()
            logger.info("[CFTA] 已取消后台工具任务")
            self._deferred_task = None
