"""Weclaw GUI 应用程序。

整合 Qt UI、异步桥接、Agent 核心，提供完整的桌面应用体验。
支持：
- Agent 推理结果流式推送到 UI
- 工具调用状态实时显示
- 模型切换、会话管理
- 系统托盘 + 全局快捷键 + 设置 + 主题 (Sprint 2.2)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

from src.core.agent import Agent
from src.core.error_handler import install_error_handler, ErrorInfo
from src.core.workflow import WorkflowEngine
from src.core.workflow_loader import WorkflowLoader
from src.core.generated_files import GeneratedFilesManager
from src.models.registry import ModelRegistry
from src.tools.base import ToolResultStatus
from src.tools.registry import create_default_registry

from .async_bridge import AsyncBridge, TaskRunner, create_application, setup_async_bridge
from .hotkey import GlobalHotkey
from .keystore import inject_keys_to_env, needs_setup
from .main_window import MainWindow
from .settings_dialog import SettingsDialog
from .theme import Theme, apply_theme, get_stylesheet, get_theme_colors
from .tray import SystemTray

logger = logging.getLogger(__name__)


class GuiAgent(QObject):
    """GUI 封装的 Agent，处理流式输出和状态更新。

    将 Agent 的异步 chat 调用包装为 Qt 信号，
    使 UI 可以实时响应推理过程。
    """

    # 信号
    message_started = Signal()  # 开始生成
    message_chunk = Signal(str)  # 流式文本块
    message_finished = Signal(str)  # 完整消息
    tool_call_started = Signal(str, str)  # (tool_name, action)
    tool_call_finished = Signal(str, str, str)  # (tool_name, action, result_preview)
    error_occurred = Signal(str)  # 错误信息
    usage_updated = Signal(int, int, float)  # (input_tokens, output_tokens, cost)
    tts_requested = Signal(str)  # 请求 TTS 朗读
    reasoning_started = Signal()  # 思考过程开始
    reasoning_chunk = Signal(str)  # 思考内容块
    reasoning_finished = Signal()  # 思考过程完成
    cron_job_status = Signal(str, str, str)  # (job_id, status, description) 定时任务状态
    companion_care_message = Signal(str, str)  # (message, interaction_type) 陪伴消息

    def __init__(self, agent: Agent, model_registry: ModelRegistry) -> None:
        super().__init__()
        self._agent = agent
        self._model_registry = model_registry
        self._tts_enabled = False  # TTS 开关状态
        self._cron_sub_ids: list[tuple[str, int]] = []  # 定时任务事件订阅ID
        self._companion_sub_ids: list[tuple[str, int]] = []  # 陪伴事件订阅ID
        
        # 订阅定时任务事件
        self._subscribe_cron_events()
        # 订阅陪伴事件
        self._subscribe_companion_events()

    def _subscribe_cron_events(self) -> None:
        """订阅定时任务事件。"""
        async def _on_cron_job(event_type, data):
            # data 是 CronJobEvent 类型
            self.cron_job_status.emit(data.job_id, data.status, data.description)
        
        try:
            from src.core.events import EventType
            sub_started = self._agent.event_bus.on(EventType.CRON_JOB_STARTED, _on_cron_job)
            sub_finished = self._agent.event_bus.on(EventType.CRON_JOB_FINISHED, _on_cron_job)
            sub_error = self._agent.event_bus.on(EventType.CRON_JOB_ERROR, _on_cron_job)
            self._cron_sub_ids.append((EventType.CRON_JOB_STARTED, sub_started))
            self._cron_sub_ids.append((EventType.CRON_JOB_FINISHED, sub_finished))
            self._cron_sub_ids.append((EventType.CRON_JOB_ERROR, sub_error))
        except Exception as e:
            logger.warning(f"订阅定时任务事件失败: {e}")

    def _subscribe_companion_events(self) -> None:
        """订阅陪伴事件。"""
        async def _on_companion_care(event_type, data):
            # data 是 dict 或 CompanionCareEvent 类型
            message = data.get("message", "") if isinstance(data, dict) else getattr(data, "message", "")
            interaction_type = data.get("interaction_type", "text") if isinstance(data, dict) else getattr(data, "interaction_type", "text")
            if message:
                self.companion_care_message.emit(message, interaction_type)
        
        try:
            from src.core.events import EventType
            sub_care = self._agent.event_bus.on(
                EventType.COMPANION_CARE_TRIGGERED,
                _on_companion_care
            )
            self._companion_sub_ids.append((EventType.COMPANION_CARE_TRIGGERED, sub_care))
            logger.debug("已订阅陪伴事件")
        except Exception as e:
            logger.warning(f"订阅陪伴事件失败: {e}")

    def set_tts_enabled(self, enabled: bool) -> None:
        """设置 TTS 开关。"""
        self._tts_enabled = enabled

    async def chat(self, message: str) -> None:
        """发送消息并流式接收回复。

        流程：
        1. 发出 message_started 信号
        2. 调用 Agent.chat_stream() 流式获取回复
        3. 实时发出 message_chunk 信号（真正的流式）
        4. 工具调用通过 EventBus 事件自动传递
        5. 发出 message_finished 信号
        6. 更新用量信息
        """
        self.message_started.emit()

        try:
            full_content = ""

            # 订阅工具调用事件，实时通知 UI
            _tool_sub_ids: list[tuple[str, int]] = []
            _reasoning_started = False

            async def _on_tool_call(event_type, data):
                self.tool_call_started.emit(data.tool_name, data.action_name)

            async def _on_tool_result(event_type, data):
                result_preview = (data.output or "")[:200]
                self.tool_call_finished.emit(
                    data.tool_name, data.action_name, result_preview
                )
                # 如果有 html_image，发送到 GUI 显示
                if hasattr(data, 'html_image') and data.html_image:
                    self.message_chunk.emit(data.html_image)

            async def _on_reasoning(event_type, data):
                nonlocal _reasoning_started
                if data.is_delta and data.reasoning:
                    if not _reasoning_started:
                        self.reasoning_started.emit()
                        _reasoning_started = True
                    self.reasoning_chunk.emit(data.reasoning)
                elif data.is_complete:
                    self.reasoning_finished.emit()
                    _reasoning_started = False

            sub_tc = self._agent.event_bus.on("tool_call", _on_tool_call)
            sub_tr = self._agent.event_bus.on("tool_result", _on_tool_result)
            sub_rn = self._agent.event_bus.on("model_reasoning", _on_reasoning)
            _tool_sub_ids.append(("tool_call", sub_tc))
            _tool_sub_ids.append(("tool_result", sub_tr))
            _tool_sub_ids.append(("model_reasoning", sub_rn))

            try:
                async for chunk in self._agent.chat_stream(message):
                    full_content += chunk
                    self.message_chunk.emit(chunk)
            finally:
                # 取消工具事件订阅
                for evt_name, sub_id in _tool_sub_ids:
                    self._agent.event_bus.off(evt_name, sub_id)
                # 确保思考过程标记为完成
                if _reasoning_started:
                    self.reasoning_finished.emit()

            if full_content:
                self.message_finished.emit(full_content)

                # 如果 TTS 开启,请求朗读
                if self._tts_enabled:
                    self.tts_requested.emit(full_content)

            # 更新用量
            cost = self._model_registry.total_cost
            prompt_tokens = self._model_registry.total_prompt_tokens
            completion_tokens = self._model_registry.total_completion_tokens
            self.usage_updated.emit(prompt_tokens, completion_tokens, cost)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Agent chat 失败: %s", e, exc_info=True)
            self.error_occurred.emit(str(e))


class WinClawGuiApp:
    """WinClaw GUI 应用程序主类。"""

    def __init__(self) -> None:
        self._app: QApplication | None = None
        self._bridge: AsyncBridge | None = None
        self._window: MainWindow | None = None
        self._agent: Agent | None = None
        self._gui_agent: GuiAgent | None = None
        self._task_runner: TaskRunner | None = None
        self._model_registry: ModelRegistry | None = None
        self._tool_registry: object | None = None
        self._model_key_map: dict[str, str] = {}
        self._tray: SystemTray | None = None
        self._hotkey: GlobalHotkey | None = None
        self._current_theme = Theme.LIGHT
        
        # 当前运行的聊天任务（用于取消）
        self._current_chat_task: asyncio.Task | None = None
        
        # 语音功能状态
        self._recording_task = None  # 当前录音任务
        self._tts_enabled = False  # TTS 开关
        self._whisper_model = "base"  # Whisper 模型
        
        # 工作流组件
        self._workflow_engine: WorkflowEngine | None = None
        self._workflow_loader: WorkflowLoader | None = None

        # 生成文件管理器
        self._generated_files_manager = GeneratedFilesManager()
        
        # MCP 客户端管理器
        self._mcp_manager: object | None = None  # MCPClientManager

        # 历史会话缓存
        self._cached_history: list = []

        # 远程 PWA 请求追踪
        self._remote_request_active: bool = False
        self._remote_username: str = ""

        # 后台工作线程引用（用于正确清理）
        self._knowledge_worker = None

        # 懒加载标志
        self._gen_space_loaded = False

    @staticmethod
    def _load_dotenv() -> None:
        """加载 .env 文件到环境变量（不覆盖已有值）。

        查找顺序：
        1. winclaw/.env（项目根目录）
        2. 当前工作目录/.env
        """
        try:
            from dotenv import load_dotenv
        except ImportError:
            logger.debug("python-dotenv 未安装，跳过 .env 加载")
            return

        # winclaw 项目根目录 = src/../ = gui_app.py 所在的 src/ui 的上两级
        project_root = Path(__file__).resolve().parent.parent.parent
        env_path = project_root / ".env"

        if not env_path.exists():
            # 回退到当前工作目录
            env_path = Path.cwd() / ".env"

        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            logger.info("已加载 .env 配置: %s", env_path)
        else:
            logger.debug("未找到 .env 文件")

    def run(self) -> int:
        """运行应用程序。返回退出码。"""
        # 创建 Qt 应用
        self._app = create_application()

        # 加载 .env 文件（不覆盖已有环境变量）
        self._load_dotenv()

        # 初始化国际化（必须在 QApplication 创建后）
        from src.i18n import get_i18n_manager
        get_i18n_manager()

        # 从 keyring 注入密钥到环境变量
        injected = inject_keys_to_env()
        if injected:
            logger.info("从安全存储注入了 %d 个 API Key", injected)

        # 安装全局异常处理器
        self._setup_global_error_handler()

        # 设置异步桥接
        self._bridge = setup_async_bridge(self._app)

        # 初始化核心组件
        try:
            self._initialize_components()
        except Exception as e:
            QMessageBox.critical(
                None,
                "初始化错误",
                f"应用程序初始化失败:\n{e}\n\n请检查配置文件和 API Key 设置。",
            )
            return 1

        # 应用主题（先尝试从配置文件加载）
        try:
            # Python 3.11+ 内置 tomllib，否则使用 tomli
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            
            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                saved_theme = config.get("app", {}).get("theme", "light")
                self._current_theme = Theme(saved_theme)
        except Exception:
            self._current_theme = Theme.LIGHT
        
        apply_theme(self._app, self._current_theme)

        # 创建主窗口
        self._window = MainWindow(
                    self._bridge,
                    tool_registry=self._tool_registry,
                    model_registry=self._model_registry,
                    minimize_to_tray=True
                )

        # 同步聊天区域主题
        self._apply_chat_theme(self._current_theme)
        self._setup_signals()

        # 系统托盘
        self._tray = SystemTray(self._window, self._app)
        self._tray.new_session_requested.connect(self._window._on_new_session)
        self._tray.settings_requested.connect(self._open_settings)
        self._tray.show()

        # 全局快捷键
        self._hotkey = GlobalHotkey()
        self._hotkey.triggered.connect(self._toggle_window)
        self._hotkey.start()

        self._window.show()
        self._window.set_connection_status(True)

        # 预加载历史会话列表（同步快速读取，不阻塞 UI）
        self._preload_history_sessions()

        # 首次启动引导
        if needs_setup():
            self._open_settings()

        # 启动事件循环
        try:
            loop = self._bridge._loop
            if loop is not None:
                with loop:
                    loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

        return 0

    def _initialize_components(self) -> None:
        """初始化核心组件（模型注册表、工具注册表、Agent）。"""
        # 模型注册表
        self._model_registry = ModelRegistry()
        all_models = self._model_registry.list_models()
        available_models = self._model_registry.list_available_models()

        if not all_models:
            raise RuntimeError("未找到任何模型配置，请检查 config/models.toml")

        # 检查是否有可用的远程大模型（API Key 已配置）
        if not available_models:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "需要配置 API Key",
                "欢迎使用 WeClaw！\n\n"
                "检测到您还没有配置任何 AI 模型的 API Key。\n\n"
                "请点击菜单【帮助】->【设置】，在【API 密钥】选项卡中配置至少一个模型的 API Key 后才能使用。\n\n"
                "支持的模型包括：DeepSeek、OpenAI GPT、Claude、Gemini、智谱 GLM、Kimi、通义千问等。",
                QMessageBox.StandardButton.Ok
            )
            logger.warning("没有可用的模型，用户尚未配置 API Key")

        # 工具注册表
        self._tool_registry = create_default_registry()
        
        # 为 CronTool 设置 Agent 依赖（用于执行 AI 任务）
        cron_tool = self._tool_registry.get_tool("cron")
        if cron_tool and hasattr(cron_tool, "set_agent_dependencies"):
            cron_tool.set_agent_dependencies(self._model_registry, self._tool_registry)

        # 选择默认模型（从可用模型中选择）
        default_key = "deepseek-chat"
        if self._model_registry.get(default_key) is None or not self._model_registry.get(default_key).is_available:
            # 如果默认模型不可用，选择第一个可用模型
            if available_models:
                default_key = available_models[0].key
            else:
                # 如果没有可用模型，使用第一个模型（即使用户还没配置 API Key）
                default_key = all_models[0].key
                logger.info("使用第一个模型作为默认：%s", default_key)

        # 创建 Agent
        self._agent = Agent(
            model_registry=self._model_registry,
            tool_registry=self._tool_registry,
            model_key=default_key,
        )
        
        # 【关键】将 agent 设置到 bridge，以便 MainWindow 可以访问意识系统
        if self._bridge:
            self._bridge._agent = self._agent  # 直接设置属性

        # 更新 CronTool 的 event_bus（用于发布任务执行状态）
        if cron_tool and hasattr(cron_tool, "set_agent_dependencies"):
            cron_tool.set_agent_dependencies(self._model_registry, self._tool_registry, self._agent.event_bus)

        # 初始化陪伴引擎（在 Agent 和 EventBus 创建之后）
        self._companion_engine = None
        try:
            from src.core.companion_engine import CompanionEngine
            self._companion_engine = CompanionEngine(
                event_bus=self._agent.event_bus,
            )
            logger.info("CompanionEngine 初始化成功")
            
            # 启动陪伴调度器（通过 bridge 在异步环境中执行）
            if self._bridge and self._bridge._loop:
                import asyncio
                asyncio.run_coroutine_threadsafe(
                    self._companion_engine.start_scheduler(),
                    self._bridge._loop
                )
                logger.info("CompanionEngine 调度器启动任务已提交")
        except Exception as e:
            logger.warning(f"CompanionEngine 初始化失败: {e}")

        # 创建 GUI Agent 包装器
        self._gui_agent = GuiAgent(self._agent, self._model_registry)

        # 任务运行器
        if self._bridge is not None:
            self._task_runner = TaskRunner(self._bridge)
        
        # 初始化工作流引擎和加载器
        self._workflow_engine = WorkflowEngine(
            tool_registry=self._tool_registry,
            event_bus=self._agent.event_bus,
        )
        self._workflow_loader = WorkflowLoader(self._workflow_engine)
        loaded_count = self._workflow_loader.load_all_templates()
        logger.info(f"已加载 {loaded_count} 个工作流模板")

        # 构建 name -> key 映射（使用所有模型）
        for m in all_models:
            self._model_key_map[m.name] = m.key
        
        # 初始化 MCP 客户端管理器（异步初始化）
        self._initialize_mcp()

    def _initialize_mcp(self) -> None:
        """初始化 MCP 客户端管理器并连接已启用的 Server。"""
        import json
        from pathlib import Path
        from src.core.mcp_client import MCPClientManager, MCPServerConfig
        
        # 创建管理器
        self._mcp_manager = MCPClientManager()
        
        # 加载配置
        config_path = Path(__file__).parent.parent.parent / "config" / "mcp_servers.json"
        if not config_path.exists():
            logger.debug("MCP 配置文件不存在")
            return
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            servers = data.get("mcpServers", {})
            enabled_servers = [
                MCPServerConfig.from_dict(name, cfg)
                for name, cfg in servers.items()
                if cfg.get("enabled", False)
            ]
            
            if not enabled_servers:
                logger.debug("没有启用的 MCP Server")
                return
            
            # 异步并行连接 MCP Server
            async def _connect_single_server(config):
                """连接单个 MCP Server。"""
                try:
                    success = await self._mcp_manager.connect_server(config)
                    if success:
                        # 注册到工具注册表
                        from src.tools.mcp_bridge import create_mcp_bridge_tools
                        create_mcp_bridge_tools(
                            self._mcp_manager,
                            self._tool_registry
                        )
                except Exception as e:
                    logger.warning("连接 MCP Server %s 失败: %s", config.name, e)
            
            async def _connect_mcp_servers():
                """并行连接所有 MCP Server。"""
                import asyncio
                # 使用 asyncio.gather 并行执行所有连接任务
                await asyncio.gather(
                    *[_connect_single_server(config) for config in enabled_servers],
                    return_exceptions=True
                )
            
            # 使用异步桥接执行
            if self._bridge and self._bridge._loop:
                import asyncio
                future = asyncio.run_coroutine_threadsafe(
                    _connect_mcp_servers(),
                    self._bridge._loop
                )
                # 不等待完成，让它在后台连接
                logger.info("MCP Server 连接任务已启动")
                
        except Exception as e:
            logger.warning("加载 MCP 配置失败: %s", e)

    def _setup_signals(self) -> None:
        """设置 UI 信号与 Agent 的连接。"""
        if not self._window or not self._gui_agent:
            return

        # 用户发送消息 → 触发 Agent chat
        self._window.message_sent.connect(self._on_user_message)
        self._window.message_with_attachments.connect(self._on_user_message_with_attachments)

        # 停止按钮
        self._window.stop_requested.connect(self._on_stop)

        # 模型切换
        self._window.model_changed.connect(self._on_model_changed)

        # Agent → UI 信号连接
        def safe_set_tool_status(status):
            """安全设置工具状态。"""
            if self._window is not None:
                try:
                    self._window.set_tool_status(status)
                except RuntimeError:
                    pass
        
        def safe_clear_tool_log():
            """安全清空工具日志。"""
            if self._window is not None:
                try:
                    self._window.clear_tool_log()
                except RuntimeError:
                    pass
        
        def safe_add_tool_log(entry):
            """安全添加工具日志。"""
            if self._window is not None:
                try:
                    self._window.add_tool_log(entry)
                except RuntimeError:
                    pass
        
        def safe_set_thinking_state(thinking):
            """安全设置思考状态。"""
            if self._window is not None:
                try:
                    self._window._set_thinking_state(thinking)
                except RuntimeError:
                    pass
        
        def safe_add_ai_message(text):
            """安全添加 AI 消息。"""
            if self._window is not None:
                try:
                    self._window.add_ai_message(text)
                except RuntimeError:
                    pass
        
        self._gui_agent.message_started.connect(
            lambda: (
                safe_set_tool_status("生成中..."),
                safe_clear_tool_log(),
            )
        )

        # 消息块信号：直接转发到UI
        self._gui_agent.message_chunk.connect(
            self._window.append_ai_message  # type: ignore
        )

        self._gui_agent.message_finished.connect(
            self._on_agent_message_finished
        )
        # 思考过程信号连接
        self._gui_agent.reasoning_started.connect(
            self._window.start_reasoning  # type: ignore
        )
        self._gui_agent.reasoning_chunk.connect(
            self._window.append_reasoning  # type: ignore
        )
        self._gui_agent.reasoning_finished.connect(
            self._window.finish_reasoning  # type: ignore
        )
        self._gui_agent.tool_call_started.connect(
            lambda name, action: (
                safe_set_tool_status(f"执行：{name}.{action}"),
                safe_add_tool_log(f"▶ {name}.{action}"),
            )
        )
        self._gui_agent.tool_call_finished.connect(
            lambda name, action, result: safe_add_tool_log(
                f"✔ {name}.{action} → {result[:150]}{'...' if len(result) > 150 else ''}"
            )
        )
        # 录音工具被 agent 调用时，弹出录音可视化窗口
        self._gui_agent.tool_call_started.connect(self._on_agent_tool_call_started)
        self._gui_agent.tool_call_finished.connect(self._on_agent_tool_call_finished)

        self._gui_agent.error_occurred.connect(
            lambda msg: (
                safe_add_ai_message(f"抱歉，AI 模型调用失败：{msg}"),
                safe_set_thinking_state(False),
            )
        )
        self._gui_agent.usage_updated.connect(
            self._window.update_usage  # type: ignore
        )
        
        # 定时任务状态更新
        self._gui_agent.cron_job_status.connect(
            lambda job_id, status, desc: self._on_cron_job_status(job_id, status, desc)
        )
        
        # 陪伴消息显示
        self._gui_agent.companion_care_message.connect(self._on_companion_care)
        
        # TTS 朗读
        self._gui_agent.tts_requested.connect(self._on_tts_speak)

        # 设置对话框
        self._window.settings_requested.connect(self._open_settings)

        # 显示菜单 - 主题切换
        self._window.theme_changed.connect(self._on_theme_changed)

        # 显示菜单 - 语言切换
        self._window.language_changed.connect(self._on_language_changed_from_menu)

        # 图片附件选择 -> OCR 识别
        self._window.image_selected.connect(self._on_image_selected)

        # 语音功能
        self._window.voice_record_requested.connect(self._on_voice_record)
        self._window.voice_stop_requested.connect(self._on_voice_stop)
        self._window.tts_toggle_requested.connect(self._on_tts_toggle)

        # 生成空间
        self._window.generated_space_requested.connect(self._on_open_generated_space)
        self._window.generated_space_clear_requested.connect(self._on_clear_generated_space)
        self._window.generated_space_file_delete_requested.connect(self._on_delete_gen_file)

        # 知识库
        self._window.knowledge_rag_requested.connect(self._on_open_knowledge_rag)
        self._window.knowledge_add_file_requested.connect(self._on_add_knowledge_file)
        self._window.knowledge_add_url_requested.connect(self._on_add_knowledge_url)
        self._window.knowledge_search_requested.connect(self._on_knowledge_search_query)
        self._window.knowledge_doc_delete_requested.connect(self._on_delete_knowledge_doc)

        # 定时任务管理
        self._window.cron_job_requested.connect(self._on_open_cron_job)

        # 历史对话（兼容旧代码，保留对话框方式）
        self._window.history_requested.connect(self._on_open_history)
        # 历史对话TAB页面
        self._window.history_refresh_requested.connect(self._on_refresh_history_tab)
        self._window.history_session_selected.connect(self._restore_session)
        self._window.history_session_delete_requested.connect(self._on_delete_history_session)

        # 设置模型列表（只显示可用的模型）
        models = self._model_registry.list_available_models() if self._model_registry else []
        model_names = [m.name for m in models]
        self._window.set_models(model_names)

        # 设置当前模型
        if self._agent and self._model_registry:
            cfg = self._model_registry.get(self._agent.model_key)
            if cfg:
                self._window.set_current_model(cfg.name)
        
        # 工作流面板信号连接（暂时注释，等工作流功能启用时再打开）
        # self._window.workflow_panel.cancel_requested.connect(self._on_workflow_cancel)

        # 设置工作流事件订阅
        self._setup_workflow_events()

        # 设置文件生成事件订阅
        self._setup_file_generated_events()

        # 设置远程 PWA 请求事件订阅（工具状态面板同步）
        self._setup_remote_events()

        # 设置 CommandHandler 的 agent 引用（用于命令切换模型）
        if self._window._cmd_handler:
            self._window._cmd_handler.set_agent(self._agent)

    def _update_session_title(self) -> None:
        """根据第一条用户消息更新会话标题。"""
        if not self._agent or not self._window:
            return

        try:
            session = self._agent.session_manager.current_session
            # 如果标题是默认的"默认对话"或"新对话"，则更新为第一条用户消息
            if session.title in ("默认对话", "新对话"):
                # 调用 session_manager 的 generate_title 方法
                new_title = self._agent.session_manager.generate_title()
                if new_title:
                    # 更新 UI 显示
                    self._window.set_session_info(new_title)
                    logger.info("会话标题已更新: %s", new_title)
        except Exception as e:
            logger.warning("更新会话标题失败: %s", e)

    def _on_user_message(self, message: str) -> None:
        """处理用户消息。"""
        if not self._gui_agent or not self._task_runner:
            return

        # 内部命令
        if message == "/new_session":
            if self._agent:
                self._agent.reset()
            return
        
        # 检查是否是关怀请求（不阻塞消息发送，两者并行执行）
        if self._companion_engine and self._check_care_request(message):
            # 通过异步桥接触发关怀（不阻塞消息发送）
            if self._bridge and self._bridge._loop:
                asyncio.run_coroutine_threadsafe(
                    self._companion_engine.on_user_care_request(message),
                    self._bridge._loop
                )
                logger.info("检测到关怀请求，已触发陪伴关怀")
        
        # 检查是否触发工作流
        if self._workflow_loader:
            matched_workflow = self._workflow_loader.match_trigger(message)
            if matched_workflow:
                if self._window:
                    self._window.add_tool_log(f"📊 触发工作流: {matched_workflow}")
                self._task_runner.run(
                    "workflow",
                    self._execute_workflow(matched_workflow, message)
                )
                return

        # 运行 Agent chat 任务，并跟踪当前任务
        self._current_chat_task = self._task_runner.run("chat", self._gui_agent.chat(message))
    
    def _on_stop(self) -> None:
        """停止当前运行的任务。"""
        if self._current_chat_task and not self._current_chat_task.done():
            self._current_chat_task.cancel()
            logger.info("用户取消了当前任务")
            if self._window:
                self._window.add_ai_message("\n[已取消]")
                self._window._set_thinking_state(False)
                self._window.set_tool_status("已取消")
        self._current_chat_task = None
    
    def _check_care_request(self, message: str) -> bool:
        """检查用户消息是否包含关怀请求关键词。
        
        Args:
            message: 用户输入的消息
            
        Returns:
            True 如果消息包含关怀请求关键词
        """
        from src.core.companion_topics import USER_CARE_REQUEST_KEYWORDS
        msg_lower = message.lower().strip()
        return any(kw in msg_lower for kw in USER_CARE_REQUEST_KEYWORDS)
    
    def _setup_global_error_handler(self) -> None:
        """设置全局异常处理器。"""
        def on_error(error_info: ErrorInfo) -> None:
            """全局错误回调。"""
            logger.error("全局异常: %s - %s", error_info.category.value, error_info.message)
            # 在主线程中显示错误（通过 Qt 信号机制）
            if self._window:
                try:
                    QMessageBox.warning(
                        self._window,
                        "错误",
                        error_info.to_display(),
                    )
                except Exception:
                    pass  # Qt 可能还未准备好

        install_error_handler(on_error=on_error)
    
    async def _execute_workflow(self, workflow_name: str, user_input: str) -> None:
        """执行工作流。"""
        if not self._workflow_loader or not self._window:
            return
        
        try:
            template = self._workflow_loader.get_template(workflow_name)
            if template:
                # 启动工作流面板
                steps_info = [
                    {"id": s.id, "name": s.name}
                    for s in template.definition.steps
                ]
                self._window.workflow_panel.start_workflow(
                    workflow_name,
                    template.definition.description,
                    steps_info
                )
            
            # 执行工作流
            context = await self._workflow_loader.execute_template(workflow_name)
            
            # 显示结果
            if context.status.value == "completed":
                self._window.add_tool_log(f"✅ 工作流执行成功")
            else:
                self._window.add_tool_log(f"❌ 工作流执行失败: {context.error}")
        
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            self._window.add_tool_log(f"❌ 工作流错误: {e}")
        finally:
            self._window.workflow_panel.reset()

    def _on_user_message_with_attachments(self, message: str, attachments: list) -> None:
        """处理带附件的用户消息。"""
        if not self._gui_agent or not self._task_runner:
            return
        
        # 构建附件上下文
        attachment_context = self._build_attachment_context(attachments)
        
        # 将附件信息添加到消息前面
        full_message = f"{attachment_context}\n用户请求: {message}"
        
        # 显示附件信息
        if self._window:
            self._window.add_tool_log(f"📎 发送 {len(attachments)} 个附件")
        
        # 运行 Agent chat 任务
        self._task_runner.run("chat", self._gui_agent.chat(full_message))
    
    def _build_attachment_context(self, attachments: list) -> str:
        """构建附件上下文描述。"""
        if not attachments:
            return ""
        
        lines = ["[附件信息]"]
        for att in attachments:
            type_desc = {
                "image": "图片",
                "text": "文本",
                "code": "代码",
                "document": "文档",
                "other": "文件",
            }.get(att.file_type, "文件")
            
            lines.append(f"- {att.name} ({type_desc}, {att.size_display()}, 路径: {att.path})")
        
        lines.append("")
        return "\n".join(lines)

    def _on_model_changed(self, model_name: str) -> None:
        """处理模型切换。"""
        if not self._agent:
            return
        key = self._model_key_map.get(model_name)
        if key:
            self._agent.model_key = key
            logger.info("模型切换为: %s (%s)", model_name, key)

    def _toggle_window(self) -> None:
        """切换窗口显示/隐藏（全局快捷键触发）。"""
        if not self._window:
            return
        if self._window.isVisible():
            self._window.hide()
        else:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()

    def _open_settings(self) -> None:
        """打开设置对话框。"""
        models = [m.name for m in (self._model_registry.list_available_models() if self._model_registry else [])]
        current_model = ""
        if self._agent and self._model_registry:
            cfg = self._model_registry.get(self._agent.model_key)
            if cfg:
                current_model = cfg.name

        dlg = SettingsDialog(
            self._window,
            current_theme=self._current_theme.value,
            current_model=current_model,
            available_models=models,
            current_hotkey=self._hotkey.hotkey if self._hotkey else "Win+Shift+Space",
            current_whisper_model=self._whisper_model,
            mcp_manager=self._mcp_manager,
        )
        dlg.theme_changed.connect(self._on_theme_changed)
        dlg.model_changed.connect(self._on_model_changed)
        dlg.hotkey_changed.connect(self._on_hotkey_changed)
        dlg.keys_updated.connect(lambda: logger.info("API Key 已更新"))
        dlg.whisper_model_changed.connect(self._on_whisper_model_changed)
        dlg.language_changed.connect(self._on_language_changed)
        dlg.exec()

    def _on_language_changed(self, lang_code: str) -> None:
        """语言切换后刷新 UI。"""
        if self._window:
            self._window.reload_ui()
        # 刷新托盘菜单
        if self._tray:
            self._tray._setup_menu()

    def _on_language_changed_from_menu(self, lang_code: str) -> None:
        """从菜单切换语言。"""
        from src.i18n import get_i18n_manager

        i18n = get_i18n_manager()
        if i18n.load_language(lang_code):
            logger.info("语言已切换为: %s", lang_code)
            # 保存语言设置到配置文件
            self._save_language_setting(lang_code)
            # 刷新 UI
            self._on_language_changed(lang_code)

    def _save_language_setting(self, lang_code: str) -> None:
        """保存语言设置到配置文件。"""
        try:
            import tomli as tomllib
            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                if "app" not in config:
                    config["app"] = {}
                config["app"]["language"] = lang_code

                # 手动写入 TOML 文件
                self._write_toml(config_path, config)
                logger.info("语言设置已保存: %s", lang_code)
        except Exception as e:
            logger.warning("保存语言设置失败: %s", e)

    def _save_theme_setting(self, theme_str: str) -> None:
        """保存主题设置到配置文件。"""
        try:
            # Python 3.11+ 内置 tomllib，否则使用 tomli
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            
            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                if "app" not in config:
                    config["app"] = {}
                config["app"]["theme"] = theme_str

                # 手动写入 TOML 文件
                self._write_toml(config_path, config)
                logger.info("主题设置已保存: %s", theme_str)
        except Exception as e:
            logger.warning("保存主题设置失败: %s", e)

    def _write_toml(self, path: Path, config: dict) -> None:
        """手动写入 TOML 配置文件，保留其他节。"""
        # 读取现有文件内容，保留注释
        existing_lines: list[str] = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

        # 找到 [app] 节的位置
        app_start = -1
        app_end = -1
        for i, line in enumerate(existing_lines):
            stripped = line.strip()
            if stripped == "[app]":
                app_start = i
            elif app_start >= 0 and stripped.startswith("[") and stripped.endswith("]"):
                app_end = i
                break

        # 构建新的 [app] 节
        app_lines = ["[app]\n"]
        for key, value in config.get("app", {}).items():
            if isinstance(value, str):
                app_lines.append(f'{key} = "{value}"\n')
            else:
                app_lines.append(f"{key} = {value}\n")
        app_lines.append("\n")

        # 重建文件内容
        if app_start >= 0 and app_end > app_start:
            # 替换现有 [app] 节
            new_lines = existing_lines[:app_start] + app_lines + existing_lines[app_end:]
        else:
            # 添加新的 [app] 节（在文件开头之后）
            new_lines = app_lines + existing_lines

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def _on_theme_changed(self, theme_str: str) -> None:
        """切换主题。"""
        theme = Theme(theme_str)
        self._current_theme = theme
        if self._app:
            apply_theme(self._app, theme)
        self._apply_chat_theme(theme)
        # 保存主题设置
        self._save_theme_setting(theme_str)

    def _apply_chat_theme(self, theme: Theme) -> None:
        """同步聊天区域主题颜色。"""
        if self._window:
            colors = get_theme_colors(theme)
            self._window._chat_widget.apply_theme(colors)

    def _on_hotkey_changed(self, hotkey: str) -> None:
        """更新快捷键。"""
        # 将显示格式转为 pynput 格式
        hk = hotkey.lower().replace("win", "<cmd>").replace("+", "+")
        for part in ["shift", "ctrl", "alt", "space"]:
            hk = hk.replace(part, f"<{part}>")
        # 防止重复尖括号
        import re
        hk = re.sub(r"<(<[^>]+>)>", r"\1", hk)
        if self._hotkey:
            self._hotkey.set_hotkey(hk)

    def _on_image_selected(self, image_path: str) -> None:
        """处理图片选择，进行 OCR 识别。"""
        if not self._task_runner or not self._window:
            return
        
        # 更新状态
        self._window.set_tool_status("图片 OCR 识别中...")
        self._window.add_tool_log(f"📷 开始识别: {image_path.split('/')[-1].split(chr(92))[-1]}")
        
        # 启动 OCR 任务
        self._task_runner.run(
            "ocr_recognize",
            self._recognize_image(image_path)
        )

    async def _recognize_image(self, image_path: str) -> None:
        """OCR 识别图片。"""
        try:
            from src.tools.ocr import OCRTool
            
            tool = OCRTool()
            
            # 识别图片
            result = await tool.execute(
                "recognize_file",
                {"image_path": image_path, "merge_lines": True}
            )
            
            if result.status == ToolResultStatus.SUCCESS and self._window:
                text = result.data.get("text", "") if result.data else ""
                line_count = result.data.get("line_count", 0) if result.data else 0
                
                if text.strip():
                    # 将识别结果填入输入框
                    self._window.set_input_text(text)
                    self._window.set_tool_status(f"OCR 完成: {line_count} 行文字")
                    self._window.add_tool_log(f"✅ OCR 识别成功: {len(text)} 字符")
                    
                    # 在聊天区显示识别结果预览
                    preview_text = text[:200] + ("..." if len(text) > 200 else "")
                    self._window._chat_widget.add_ai_message(
                        f"📝 OCR 识别结果 ({line_count} 行):\n```\n{preview_text}\n```\n"
                        f"\nℹ️ 识别文字已填入输入框，可以进行编辑或直接发送。"
                    )
                else:
                    self._window.set_tool_status("未识别到文字")
                    self._window.add_tool_log("⚠️ 图片中未识别到文字")
            else:
                if self._window:
                    error_msg = result.error or "OCR 识别失败"
                    self._window.set_tool_status(f"OCR 失败: {error_msg}")
                    self._window.add_tool_log(f"❌ {error_msg}")
        
        except ImportError as e:
            logger.error("OCR 工具不可用: %s", e)
            if self._window:
                self._window.set_tool_status("OCR 功能不可用")
                self._window.add_tool_log("❌ OCR 功能需要安装: pip install rapidocr-onnxruntime pillow")
                QMessageBox.warning(
                    self._window,
                    "OCR 功能不可用",
                    "OCR 功能需要安装额外依赖\n\n请运行: pip install rapidocr-onnxruntime pillow",
                )
        except Exception as e:
            logger.exception("OCR 识别错误")
            if self._window:
                self._window.set_tool_status(f"OCR 错误: {e}")
                self._window.add_tool_log(f"❌ OCR 错误: {e}")
        finally:
            if self._window:
                self._window.set_tool_status("空闲")

    def _cleanup(self) -> None:
        """清理资源。"""
        # 停止陪伴调度器
        if self._companion_engine:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._companion_engine.stop_scheduler(),
                        loop
                    ).result(timeout=5)
                else:
                    loop.run_until_complete(self._companion_engine.stop_scheduler())
                logger.info("CompanionEngine 调度器已停止")
            except Exception as e:
                logger.warning(f"停止陪伴调度器失败: {e}")
        
        # Phase 6: 清理意识系统
        if self._agent and hasattr(self._agent, 'cleanup'):
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._agent.cleanup())
                else:
                    loop.run_until_complete(self._agent.cleanup())
                logger.info("Agent 意识系统已清理")
            except Exception as e:
                logger.error(f"Agent 清理失败：{e}")
        
        # 取消当前任务
        if self._current_chat_task and not self._current_chat_task.done():
            self._current_chat_task.cancel()
            self._current_chat_task = None
        
        # 清理所有工具
        if self._tool_registry:
            for tool in self._tool_registry.list_tools():
                try:
                    if hasattr(tool, 'close'):
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(tool.close())
                        else:
                            loop.run_until_complete(tool.close())
                except Exception as e:
                    logger.warning("工具 %s 清理失败: %s", tool.name, e)
        
        if self._hotkey:
            self._hotkey.stop()
        if self._tray:
            self._tray.hide()
        if self._task_runner:
            self._task_runner.cancel_all()

    # ===== 语音配置读取 =====

    def _load_voice_config(self) -> dict:
        """读取 voice 配置节，返回配置字典。"""
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                voice = config.get("voice", {})
                return {
                    "max_duration": voice.get("max_duration", 30),
                    "auto_stop": voice.get("auto_stop", True),
                    "silence_threshold": voice.get("silence_threshold", 0.01),
                    "silence_duration": voice.get("silence_duration", 1.5),
                }
        except Exception as e:
            logger.debug("读取 voice 配置失败，使用默认值: %s", e)
        return {"max_duration": 30, "auto_stop": True, "silence_threshold": 0.01, "silence_duration": 1.5}

    # ===== 历史对话相关 =====

    def _get_storage(self):
        """获取 ChatStorage 实例（从 Agent 的 SessionManager 中取）。"""
        if self._agent and self._agent.session_manager._storage:
            return self._agent.session_manager._storage
        return None

    def _preload_history_sessions(self) -> None:
        """预加载历史会话列表（应用启动后调用，同步快速读取）。"""
        storage = self._get_storage()
        if not storage:
            return
        try:
            self._cached_history = storage.list_sessions_sync(limit=100)
            logger.info("预加载了 %d 个历史会话", len(self._cached_history))
        except Exception as e:
            logger.warning("预加载历史会话失败: %s", e)
            self._cached_history = []

    def _on_open_history(self) -> None:
        """打开历史对话对话框（纯同步，不阻塞事件循环）。"""
        if not self._window or not self._agent:
            return

        from .history_dialog import HistoryDialog

        storage = self._get_storage()
        sessions_data: list[dict] = []

        if storage:
            try:
                # 同步读取全部历史会话（直接用 sqlite3，无死锁）
                stored_sessions = storage.list_sessions_sync(limit=100)
                for st in stored_sessions:
                    msg_count = storage.get_message_count_sync(st.id)
                    sessions_data.append({
                        "id": st.id,
                        "title": st.title,
                        "updated_at": st.updated_at.isoformat(),
                        "message_count": msg_count,
                    })
            except Exception as e:
                logger.warning("读取历史会话列表失败: %s", e, exc_info=True)
        else:
            # 无持久化存储，只显示内存中的会话
            session_mgr = self._agent.session_manager
            for s in session_mgr.list_sessions():
                msg_count = sum(
                    1 for m in s.messages if m.get("role") != "system"
                )
                sessions_data.append({
                    "id": s.id,
                    "title": s.title,
                    "updated_at": s.created_at.isoformat(),
                    "message_count": msg_count,
                })

        dlg = HistoryDialog(sessions_data, self._window)
        dlg.session_selected.connect(self._restore_session)
        dlg.exec()

    def _restore_session(self, session_id: str) -> None:
        """恢复指定会话到聊天区域（纯同步，不阻塞事件循环）。"""
        if not self._agent or not self._window:
            return

        session_mgr = self._agent.session_manager
        storage = self._get_storage()

        # 如果会话不在内存中，从 SQLite 同步加载
        if session_id not in session_mgr._sessions:
            if not storage:
                QMessageBox.warning(
                    self._window, "加载失败",
                    "该会话已不在内存中，且未启用持久化存储。",
                )
                return

            try:
                # 同步加载会话元数据
                stored = storage.load_session_sync(session_id)
                if stored is None:
                    QMessageBox.warning(
                        self._window, "加载失败",
                        f"未找到会话 {session_id}，可能已被删除。",
                    )
                    return

                # 创建 Session 对象并注册到内存
                from src.core.session import Session
                session = Session(
                    id=stored.id,
                    title=stored.title,
                    model_key=stored.model_key,
                    created_at=stored.created_at,
                    messages=[],
                    total_tokens=stored.total_tokens,
                    metadata=stored.metadata,
                )
                # 添加 system prompt
                if session_mgr._system_prompt:
                    session.messages.append({
                        "role": "system",
                        "content": session_mgr._system_prompt,
                    })

                # 同步加载所有消息
                stored_msgs = storage.load_messages_sync(session_id)
                for sm in stored_msgs:
                    msg = sm.to_dict()
                    if msg.get("role") == "system" and session.has_system_prompt:
                        continue
                    session.messages.append(msg)

                session_mgr._sessions[session_id] = session
                logger.info("从存储加载会话 %s: %d 条消息", session_id, len(stored_msgs))

            except Exception as e:
                logger.error("加载会话消息失败: %s", e, exc_info=True)
                QMessageBox.warning(
                    self._window, "加载失败",
                    f"无法加载历史会话消息:\n{e}",
                )
                return

        # 切换到该会话
        try:
            session = session_mgr.switch_session(session_id)
        except ValueError as e:
            logger.error("切换会话失败: %s", e)
            return

        # 清空聊天区域并填充历史消息
        self._window._chat_widget.clear()
        self._window.set_session_info(session.title)

        for msg in session.messages:
            role = msg.get("role", "")
            content = str(msg.get("content", ""))
            if role == "user":
                self._window._chat_widget.add_user_message(content)
            elif role == "assistant" and content:
                self._window._chat_widget.add_ai_message(content)
            # system / tool 消息不显示

        self._window.add_tool_log(f"📋 已恢复对话: {session.title}")

    # ===== 历史对话TAB相关 =====

    def _on_refresh_history_tab(self) -> None:
        """刷新历史对话TAB页面数据。"""
        if not self._window or not self._agent:
            return

        storage = self._get_storage()
        sessions_data: list[dict] = []

        if storage:
            try:
                # 同步读取全部历史会话
                stored_sessions = storage.list_sessions_sync(limit=100)
                for st in stored_sessions:
                    msg_count = storage.get_message_count_sync(st.id)
                    sessions_data.append({
                        "id": st.id,
                        "title": st.title,
                        "updated_at": st.updated_at.isoformat(),
                        "message_count": msg_count,
                    })
            except Exception as e:
                logger.warning("读取历史会话列表失败: %s", e, exc_info=True)
        else:
            # 无持久化存储，只显示内存中的会话
            session_mgr = self._agent.session_manager
            for s in session_mgr.list_sessions():
                msg_count = sum(
                    1 for m in s.messages if m.get("role") != "system"
                )
                sessions_data.append({
                    "id": s.id,
                    "title": s.title,
                    "updated_at": s.created_at.isoformat(),
                    "message_count": msg_count,
                })

        # 更新TAB页面
        self._window.update_history_sessions(sessions_data)

    def _on_delete_history_session(self, session_id: str) -> None:
        """删除历史会话。"""
        if not self._agent:
            return

        storage = self._get_storage()
        session_mgr = self._agent.session_manager

        # 从存储中删除
        if storage:
            try:
                storage.delete_session_sync(session_id)
                logger.info("已从存储删除会话: %s", session_id)
            except Exception as e:
                logger.warning("删除会话存储失败: %s", e)

        # 从内存中移除
        if session_id in session_mgr._sessions:
            del session_mgr._sessions[session_id]
            logger.info("已从内存移除会话: %s", session_id)

        self._window.add_tool_log(f"🗑️ 已删除对话: {session_id[:8]}...")

    # ===== 生成空间相关 =====

    def _setup_file_generated_events(self) -> None:
        """订阅文件生成事件。"""
        if not self._agent:
            return

        event_bus = self._agent.event_bus

        async def on_file_generated(event_type, data) -> None:
            """文件生成事件处理。"""
            file_path = data.file_path if hasattr(data, "file_path") else data.get("file_path", "")
            source_tool = data.source_tool if hasattr(data, "source_tool") else data.get("source_tool", "")
            source_action = data.source_action if hasattr(data, "source_action") else data.get("source_action", "")
            session_id = data.session_id if hasattr(data, "session_id") else data.get("session_id", "")

            if not file_path:
                return

            info = self._generated_files_manager.register_file(
                file_path=file_path,
                source_tool=source_tool,
                source_action=source_action,
                session_id=session_id,
            )

            if info and self._window:
                self._window.update_generated_space_count(
                    self._generated_files_manager.count
                )
                # 更新TAB页面的文件列表
                files = list(self._generated_files_manager.files)
                self._window.update_generated_space_files(files)
                self._window.add_tool_log(
                    f"📂 已记录生成文件: {info.name} ({info.size_display()})"
                )

        event_bus.on("file_generated", on_file_generated)

    def _on_open_generated_space(self) -> None:
        """打开生成空间TAB页面（懒加载）。"""
        if not self._window:
            return

        # 切换到生成空间TAB
        self._window.switch_to_generated_space_tab()

        # 懒加载：只在首次切换时扫描和加载
        if not hasattr(self, '_gen_space_loaded') or not self._gen_space_loaded:
            self._gen_space_loaded = True
            # 扫描已有文件
            try:
                scanned_count = self._generated_files_manager.scan_existing_files()
                if scanned_count > 0:
                    logger.info("生成空间扫描到 %d 个历史文件", scanned_count)
            except Exception as e:
                logger.warning("扫描生成空间失败: %s", e)
        
        # 更新TAB页面的文件列表
        try:
            files = list(self._generated_files_manager.files)
            self._window.update_generated_space_files(files)
            self._window.update_generated_space_count(self._generated_files_manager.count)
        except Exception as e:
            logger.warning("更新生成空间显示失败: %s", e)

    def _on_clear_generated_space(self) -> None:
        """清空生成空间记录。"""
        try:
            self._generated_files_manager.clear()
            if self._window:
                self._window.update_generated_space_count(0)
            logger.info("已清空生成空间记录")
        except Exception as e:
            logger.warning("清空生成空间失败: %s", e)

    def _on_delete_gen_file(self, file_path: str) -> None:
        """删除单个生成文件记录。"""
        try:
            self._generated_files_manager.remove_file(file_path)
            if self._window:
                self._window.update_generated_space_count(self._generated_files_manager.count)
            logger.info("已删除生成文件记录: %s", file_path)
        except Exception as e:
            logger.warning("删除生成文件记录失败: %s", e)

    def _on_open_knowledge_rag(self) -> None:
        """打开知识库TAB页面（懒加载）。"""
        if not self._window:
            return

        # 获取 knowledge_rag 工具
        tool = None
        if self._tool_registry:
            tool = self._tool_registry.get_tool("knowledge_rag")

        if not tool:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._window,
                "知识库未就绪",
                "知识库工具尚未加载，请重启应用后重试。"
            )
            return

        # 切换到知识库TAB
        self._window.switch_to_knowledge_tab()

        # 懒加载：异步获取文档列表并更新TAB页面
        self._refresh_knowledge_tab(tool)

    def _refresh_knowledge_tab(self, tool) -> None:
        """异步刷新知识库TAB页面。"""
        from .knowledge_rag_dialog import ListDocumentsWorker

        # 如果有正在运行的worker，等待它完成
        try:
            if self._knowledge_worker and hasattr(self._knowledge_worker, 'isRunning'):
                if self._knowledge_worker.isRunning():
                    self._knowledge_worker.wait(1000)  # 等待最多1秒
        except RuntimeError:
            # 对象已被删除，重置为None
            self._knowledge_worker = None

        def on_docs_loaded(docs):
            if self._window:
                self._window.update_knowledge_documents(docs)

        self._knowledge_worker = ListDocumentsWorker(tool)
        self._knowledge_worker.finished.connect(on_docs_loaded)
        # 线程完成后自动删除并重置引用
        def on_finished():
            self._knowledge_worker = None
        self._knowledge_worker.finished.connect(on_finished)
        self._knowledge_worker.start()

    def _on_add_knowledge_file(self, file_path: str) -> None:
        """添加文件到知识库。"""
        tool = self._tool_registry.get_tool("knowledge_rag") if self._tool_registry else None
        if not tool:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self._window, "知识库未就绪", "知识库工具尚未加载")
            return
        
        from .knowledge_rag_dialog import AddDocumentWorker
        
        # 显示进度
        if self._window:
            self._window.update_knowledge_progress(True, 0, "准备添加...")
        
        def on_progress(msg):
            if self._window:
                self._window.update_knowledge_progress(True, 50, msg)
        
        def on_finished(success, msg):
            if self._window:
                self._window.update_knowledge_progress(False)
            from PySide6.QtWidgets import QMessageBox
            if success:
                QMessageBox.information(self._window, "成功", msg)
                self._refresh_knowledge_tab(tool)
            else:
                QMessageBox.warning(self._window, "失败", msg)
        
        worker = AddDocumentWorker(tool, file_path=file_path)
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()
        # 保存worker引用防止被回收
        self._add_doc_worker = worker

    def _on_add_knowledge_url(self, url: str) -> None:
        """添加URL到知识库。"""
        tool = self._tool_registry.get_tool("knowledge_rag") if self._tool_registry else None
        if not tool:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self._window, "知识库未就绪", "知识库工具尚未加载")
            return
        
        from .knowledge_rag_dialog import AddDocumentWorker
        
        # 显示进度
        if self._window:
            self._window.update_knowledge_progress(True, 0, "准备抓取网页...")
        
        def on_progress(msg):
            if self._window:
                self._window.update_knowledge_progress(True, 50, msg)
        
        def on_finished(success, msg):
            if self._window:
                self._window.update_knowledge_progress(False)
            from PySide6.QtWidgets import QMessageBox
            if success:
                QMessageBox.information(self._window, "成功", msg)
                self._refresh_knowledge_tab(tool)
            else:
                QMessageBox.warning(self._window, "失败", msg)
        
        worker = AddDocumentWorker(tool, url=url)
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()
        self._add_doc_worker = worker

    def _on_knowledge_search_query(self, query: str) -> None:
        """搜索知识库。"""
        tool = self._tool_registry.get_tool("knowledge_rag") if self._tool_registry else None
        if not tool:
            if self._window:
                self._window.update_knowledge_search_result("知识库未就绪")
            return
        
        from .knowledge_rag_dialog import SearchWorker
        
        # 预加载模型（避免线程冲突）
        try:
            _ = tool.embedder.model
        except Exception:
            pass
        
        def on_search_finished(result):
            if self._window:
                self._window.update_knowledge_search_result(result)
        
        worker = SearchWorker(tool, query, top_k=3)
        worker.finished.connect(on_search_finished)
        worker.start()
        self._search_worker = worker

    def _on_delete_knowledge_doc(self, doc_id: int) -> None:
        """删除知识库文档。"""
        tool = self._tool_registry.get_tool("knowledge_rag") if self._tool_registry else None
        if not tool:
            return
        
        from .knowledge_rag_dialog import DeleteDocumentWorker
        
        def on_delete_finished(success, msg):
            from PySide6.QtWidgets import QMessageBox
            if success:
                QMessageBox.information(self._window, "成功", msg)
                self._refresh_knowledge_tab(tool)
            else:
                QMessageBox.warning(self._window, "失败", msg)
        
        worker = DeleteDocumentWorker(tool, doc_id)
        worker.finished.connect(on_delete_finished)
        worker.start()
        self._delete_doc_worker = worker

    def _on_open_cron_job(self) -> None:
        """打开定时任务管理对话框。"""
        if not self._window:
            return

        # 获取 cron 工具
        tool = None
        if self._tool_registry:
            tool = self._tool_registry.get_tool("cron")

        if not tool:
            QMessageBox.warning(
                self._window,
                "定时任务未就绪",
                "定时任务工具尚未加载，请重启应用后重试。"
            )
            return

        from .cron_job_dialog import CronJobDialog
        dlg = CronJobDialog(tool, self._window)
        dlg.exec()

    def _on_voice_record(self) -> None:
        """处理录音请求。"""
        if not self._task_runner or not self._window:
            logger.warning("录音请求被忽略: task_runner=%s, window=%s", self._task_runner, self._window)
            return
        
        # 检查语音工具是否可用
        try:
            from src.tools.voice_input import VoiceInputTool
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self._window,
                "语音功能不可用",
                "语音输入功能需要安装额外依赖\n\n请运行: pip install -e \".[voice]\"",
            )
            self._window.reset_voice_button()
            return
        
        # 更新状态
        self._window.set_tool_status("录音中... (说完自动停止)")
        
        # 读取配置
        voice_config = self._load_voice_config()
        max_duration = voice_config.get("max_duration", 30)
        auto_stop = voice_config.get("auto_stop", True)
        
        # 创建并显示录音弹窗
        try:
            from .voice_record_dialog import VoiceRecordDialog
            self._voice_dialog = VoiceRecordDialog(
                duration=max_duration, parent=self._window, vad_mode=auto_stop
            )
            self._voice_dialog.stop_requested.connect(self._on_voice_stop)
            self._voice_dialog.cancelled.connect(self._on_voice_dialog_cancelled)
            self._voice_dialog.start_recording()
        except Exception as e:
            logger.exception("创建录音弹窗失败: %s", e)
            # 弹窗创建失败不影响录音流程
        
        # 启动录音任务
        self._recording_task = self._task_runner.run(
            "voice_record",
            self._record_and_transcribe()
        )

    def _on_voice_stop(self) -> None:
        """处理停止录音请求（手动停止按钮）。"""
        # 通知 VoiceInputTool 停止录音
        try:
            from src.tools.voice_input import VoiceInputTool
            # 发送停止信号（如果有活跃的工具实例）
            if hasattr(self, '_active_voice_tool') and self._active_voice_tool:
                self._active_voice_tool.stop_recording()
        except Exception as e:
            logger.warning("停止录音失败: %s", e)

    def _on_voice_dialog_cancelled(self) -> None:
        """录音弹窗被取消。"""
        if self._window:
            self._window.reset_voice_button()
            self._window.set_tool_status("空闲")

    def _on_agent_tool_call_started(self, tool_name: str, action: str) -> None:
        """Agent 调用工具时的回调，检测录音工具并弹出弹窗。"""
        if tool_name != "voice_input" or action not in ("record_and_transcribe", "record_audio"):
            return
        if not self._window:
            return

        try:
            from .voice_record_dialog import VoiceRecordDialog
            # 从配置读取录音参数
            voice_config = self._load_voice_config()
            max_duration = voice_config.get("max_duration", 30)
            auto_stop = voice_config.get("auto_stop", True)
            self._voice_dialog = VoiceRecordDialog(
                duration=max_duration, parent=self._window, vad_mode=auto_stop
            )
            self._voice_dialog.cancelled.connect(self._on_voice_dialog_cancelled)
            self._voice_dialog.start_recording()
            logger.info("Agent 调用录音工具，已弹出录音弹窗 (VAD=%s)", auto_stop)
        except Exception as e:
            logger.exception("Agent 路径创建录音弹窗失败: %s", e)

    def _on_agent_tool_call_finished(self, tool_name: str, action: str, result_preview: str) -> None:
        """Agent 工具执行完毕的回调，更新录音弹窗状态。"""
        if tool_name != "voice_input" or action != "record_and_transcribe":
            return

        dialog = getattr(self, '_voice_dialog', None)
        if not dialog or not dialog.isVisible():
            return

        try:
            if "录音转录成功" in result_preview:
                dialog.set_success("语音已识别，AI 正在处理...")
            elif "未识别" in result_preview or not result_preview.strip():
                dialog.set_no_speech()
            else:
                dialog.set_error(result_preview[:100] if result_preview else "识别失败")
        except Exception as e:
            logger.exception("更新录音弹窗状态失败: %s", e)

    def _on_whisper_model_changed(self, model_name: str) -> None:
        """处理 Whisper 模型切换。"""
        self._whisper_model = model_name
        logger.info("Whisper 模型已切换为: %s", model_name)
        if self._window:
            self._window.add_tool_log(f"🎵 Whisper 模型已切换为: {model_name}")

    def _on_tts_toggle(self, enabled: bool) -> None:
        """处理 TTS 开关切换。"""
        self._tts_enabled = enabled
        # 同步到 GuiAgent
        if self._gui_agent:
            self._gui_agent.set_tts_enabled(enabled)
        
        logger.info("TTS 已%s", "开启" if enabled else "关闭")
        if self._window:
            status = "开启" if enabled else "关闭"
            self._window.add_tool_log(f"🔊 TTS 已{status}")

    def _on_cron_job_status(self, job_id: str, status: str, description: str) -> None:
        """处理定时任务状态更新。
        
        Args:
            job_id: 任务ID
            status: 状态 (started/finished/error)
            description: 任务描述
        """
        if not self._window:
            return
        
        # 更新状态栏
        if status == "started":
            self._window.update_cron_status("running", description)
            self._window.add_tool_log(f"⏰ 定时任务开始: {description}")
            # 任务开始时弹出系统通知
            self._show_cron_notification("定时任务开始执行", f"⏰ {description}")
        elif status == "finished":
            self._window.update_cron_status("success", description)
            self._window.add_tool_log(f"✓ 定时任务完成: {description}")
            # 任务完成后5秒清除状态显示
            QTimer.singleShot(5000, lambda: self._window.update_cron_status("idle"))
        elif status == "error":
            self._window.update_cron_status("error", description)
            self._window.add_tool_log(f"✗ 定时任务失败: {description}")
            # 任务失败后5秒清除状态显示
            QTimer.singleShot(5000, lambda: self._window.update_cron_status("idle"))
            # 任务失败时弹出系统通知
            self._show_cron_notification("定时任务执行失败", f"✗ {description}")
        # 注意：执行中状态不清除，等待完成/失败事件
    
    def _show_cron_notification(self, title: str, message: str) -> None:
        """显示定时任务系统通知。
        
        Args:
            title: 通知标题
            message: 通知内容
        """
        try:
            # 使用 winotify 显示系统通知
            from winotify import Notification, audio
            toast = Notification(
                app_id="WinClaw",
                title=title,
                msg=message,
                duration="short",
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
        except ImportError:
            logger.debug("winotify 未安装，跳过系统通知")
        except Exception as e:
            logger.debug(f"显示系统通知失败: {e}")

    def _on_companion_care(self, message: str, interaction_type: str) -> None:
        """处理陪伴消息显示。
        
        将 CompanionEngine 触发的主动关怀消息显示到聊天区域，
        并根据 interaction_type 和 TTS 状态决定是否播放语音。
        
        Args:
            message: 陪伴消息内容
            interaction_type: 交互类型 (text/voice)
        """
        if not self._window:
            return
        
        # 在聊天区域显示消息（带有陪伴标识）
        care_message = f"💝 {message}"
        self._window._chat_widget.add_ai_message(care_message)
        self._window.add_tool_log(f"💝 主动陪伴: {message[:50]}...")
        
        # 如果 TTS 开启且 interaction_type 是 voice，触发 TTS 播放
        if self._tts_enabled and interaction_type == "voice":
            self._on_tts_speak(message)
        
        logger.info("陪伴消息已显示: %s", message[:50])

    def _on_agent_message_finished(self, full_content: str) -> None:
        """Agent 消息生成完成回调。"""
        if not self._window:
            return

        self._window.set_tool_status("完成")
        self._window._set_thinking_state(False)
        self._update_session_title()

        # 对话模式下，如果 TTS 未开启，需要直接恢复监听
        # （TTS 开启时，由 _on_tts_speak 走 conversation TTS 路径，播放完毕自动恢复）
        if self._window._conversation_mode != "off":
            if not self._tts_enabled:
                logger.info("对话模式下 TTS 未开启，直接恢复监听")
                if self._window._conversation_mgr:
                    self._window._conversation_mgr.on_tts_finished()

    def _on_tts_speak(self, text: str) -> None:
        """处理 TTS 朗读请求。

        统一使用 TTSPlayer 播放（无论对话模式还是普通模式），
        消除 VoiceOutputTool 独立 pyttsx3 实例带来的 COM 冲突。
        """
        if not self._window or not self._tts_enabled:
            return
        
        # 统一走 TTSPlayer 路径（对话模式与普通模式均一致）
        if self._window._tts_player:
            self._window._on_conversation_play_tts(text)
        else:
            logger.warning("TTSPlayer 未初始化，TTS 请求被忽略")

    async def _speak_text(self, text: str) -> None:
        """朗读文本。"""
        from src.tools.voice_output import VoiceOutputTool
        
        try:
            tool = VoiceOutputTool()
            
            # 限制朗读长度 (避免过长)
            max_length = 500
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            # 朗读
            result = await tool.execute(
                "speak",
                {"text": text, "rate": 200, "volume": 0.8}
            )
            
            if result.status == ToolResultStatus.SUCCESS:
                logger.info("TTS 朗读完成: %d 字符", len(text))
            else:
                logger.warning("TTS 朗读失败: %s", result.error)
        
        except Exception as e:
            logger.exception("TTS 朗读错误")
            if self._window:
                self._window.add_tool_log(f"❌ TTS 错误: {e}")

    async def _record_and_transcribe(self) -> None:
        """录音并转为文字（使用 VAD 智能录音）。"""
        from src.tools.voice_input import VoiceInputTool
        
        try:
            tool = VoiceInputTool()
            self._active_voice_tool = tool  # 保存引用，供手动停止使用
            
            # 使用配置的 Whisper 模型和录音参数
            model = self._whisper_model
            voice_config = self._load_voice_config()
            max_duration = voice_config.get("max_duration", 30)
            auto_stop = voice_config.get("auto_stop", True)
            
            logger.info("录音使用 Whisper 模型: %s, max_duration=%s, auto_stop=%s",
                        model, max_duration, auto_stop)
            
            # 录音（VAD 模式）
            result = await tool.execute(
                "record_and_transcribe",
                {"duration": max_duration, "auto_stop": auto_stop,
                 "model": model, "language": "zh"}
            )
            
            # 更新弹窗为识别处理中
            if hasattr(self, '_voice_dialog') and self._voice_dialog and self._voice_dialog.isVisible():
                self._voice_dialog.set_processing()
            
            if result.status == ToolResultStatus.SUCCESS and self._window:
                text = result.data.get("text", "")
                if text.strip():
                    # 将识别结果填入输入框
                    self._window.set_input_text(text)
                    self._window.set_tool_status(f"录音识别完成: {len(text)} 字")
                    self._window.add_tool_log(f"🎤 识别: {text[:50]}...")
                    # 弹窗显示成功
                    if hasattr(self, '_voice_dialog') and self._voice_dialog and self._voice_dialog.isVisible():
                        self._voice_dialog.set_success(text)
                else:
                    self._window.set_tool_status("未识别到语音")
                    self._window.add_tool_log("⚠️ 未识别到有效语音")
                    # 弹窗显示无语音
                    if hasattr(self, '_voice_dialog') and self._voice_dialog and self._voice_dialog.isVisible():
                        self._voice_dialog.set_no_speech()
            else:
                if self._window:
                    error_msg = result.error or "识别失败"
                    self._window.set_tool_status(f"录音失败: {error_msg}")
                    self._window.add_tool_log(f"❌ {error_msg}")
                    # 弹窗显示错误
                    if hasattr(self, '_voice_dialog') and self._voice_dialog and self._voice_dialog.isVisible():
                        self._voice_dialog.set_error(error_msg)
        
        except Exception as e:
            logger.exception("录音转文字失败")
            if self._window:
                self._window.set_tool_status(f"录音错误: {e}")
                self._window.add_tool_log(f"❌ 录音错误: {e}")
            # 弹窗显示错误
            if hasattr(self, '_voice_dialog') and self._voice_dialog and self._voice_dialog.isVisible():
                self._voice_dialog.set_error(str(e))
        
        finally:
            # 重置按钮状态
            if self._window:
                self._window.reset_voice_button()
                self._window.set_tool_status("空闲")
    
    # ===== 工作流相关 =====
    
    def _setup_workflow_events(self) -> None:
        """设置工作流事件订阅。"""
        if not self._agent:
            return
        
        # 订阅工作流事件
        event_bus = self._agent.event_bus
        
        async def on_workflow_started(data: dict) -> None:
            """工作流开始事件。"""
            if self._window:
                # 简化处理：记录日志
                self._window.add_tool_log(f"📊 工作流开始: {data.get('name', '')}")
        
        async def on_workflow_finished(data: dict) -> None:
            """工作流完成事件。"""
            if self._window:
                status = data.get('status', 'unknown')
                elapsed = data.get('elapsed', 0)
                self._window.add_tool_log(f"✅ 工作流完成: {status} ({elapsed:.1f}s)")
        
        async def on_step_started(data: dict) -> None:
            """步骤开始事件。"""
            if self._window:
                step_name = data.get('step_name', '')
                self._window.add_tool_log(f"  ▶ {step_name}")
        
        async def on_step_finished(data: dict) -> None:
            """步骤完成事件。"""
            if self._window:
                status = data.get('status', 'unknown')
                elapsed = data.get('elapsed', 0)
                icons = {'completed': '✔', 'failed': '✖', 'skipped': '⋆'}
                icon = icons.get(status, '●')
                self._window.add_tool_log(f"  {icon} ({elapsed:.1f}s)")
        
        event_bus.on("workflow_started", on_workflow_started)
        event_bus.on("workflow_finished", on_workflow_finished)
        event_bus.on("workflow_step_started", on_step_started)
        event_bus.on("workflow_step_finished", on_step_finished)
    
    def _on_workflow_cancel(self) -> None:
        """取消工作流。"""
        # TODO: 实现工作流取消逻辑
        if self._window:
            self._window.add_tool_log("⚠️ 工作流取消功能待实现")
            self._window.workflow_panel.reset()

    def _setup_remote_events(self) -> None:
        """订阅远程 PWA 请求事件，实时更新工具执行面板并标注来源。
        
        远程 PWA 请求直接调用 agent.chat_stream() 而不经过 GuiAgent.chat()，
        因此需要在 agent.event_bus 上单独订阅，以驱动工具状态面板更新。
        工具日志条目将以 📱[PWA] 前缀标注，区别于本地请求。
        """
        if not self._agent:
            return

        event_bus = self._agent.event_bus

        def _safe_set_tool_status(status: str) -> None:
            if self._window is not None:
                try:
                    self._window.set_tool_status(status)
                except RuntimeError:
                    pass

        def _safe_add_tool_log(entry: str) -> None:
            if self._window is not None:
                try:
                    self._window.add_tool_log(entry)
                except RuntimeError:
                    pass

        def _safe_clear_tool_log() -> None:
            if self._window is not None:
                try:
                    self._window.clear_tool_log()
                except RuntimeError:
                    pass

        async def on_remote_request_started(event_type, data):
            """远程请求开始：清空日志、设置来源标识。"""
            username = "远程用户"
            if isinstance(data, dict):
                username = data.get("username") or data.get("user_id", "远程用户")
                if len(username) > 12:
                    username = username[:12]
            self._remote_request_active = True
            self._remote_username = username
            _safe_set_tool_status(f"📱[PWA:{username}] 生成中...")
            _safe_clear_tool_log()
            _safe_add_tool_log(f"📱 [PWA 远程请求] 用户: {username}")

        async def on_remote_request_ended(event_type, data):
            """远程请求结束：标记完成状态。"""
            username = self._remote_username or "远程用户"
            self._remote_request_active = False
            self._remote_username = ""
            _safe_set_tool_status(f"📱[PWA:{username}] 完成")

        async def on_tool_call_remote(event_type, data):
            """工具调用开始（仅在远程请求期间生效）。"""
            if not self._remote_request_active:
                return
            _safe_set_tool_status(f"📱[PWA] 执行：{data.tool_name}.{data.action_name}")
            _safe_add_tool_log(f"📱 ▶ {data.tool_name}.{data.action_name}")

        async def on_tool_result_remote(event_type, data):
            """工具调用完成（仅在远程请求期间生效）。"""
            if not self._remote_request_active:
                return
            output = data.output or ""
            preview = output[:150] + ("..." if len(output) > 150 else "")
            _safe_add_tool_log(f"📱 ✔ {data.tool_name}.{data.action_name} → {preview}")

        event_bus.on("remote_request_started", on_remote_request_started)
        event_bus.on("remote_request_ended", on_remote_request_ended)
        event_bus.on("tool_call", on_tool_call_remote)
        event_bus.on("tool_result", on_tool_result_remote)


def main() -> int:
    """GUI 应用程序入口。"""
    from pathlib import Path
    from src.core.logging_config import setup_logging_from_config
    
    # 加载配置文件
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    
    config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
    config_dict = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config_dict = tomllib.load(f)
    
    # 设置统一日志
    setup_logging_from_config(config_dict)
    
    logger = logging.getLogger(__name__)
    logger.info("WeClaw GUI 启动...")
    
    app = WinClawGuiApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
