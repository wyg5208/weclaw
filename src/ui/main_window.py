"""WinClaw 主窗口。

布局：
- 顶部：标题栏（窗口控制 + 模型选择）
- 中部：聊天区域（消息气泡列表）
- 底部：输入区域（多行输入框 + 发送按钮 + 附件面板）
- 底部状态栏：模型、Token用量（输入/输出）、活跃任务、PWA连接、定时任务状态
- 右侧：状态面板（工具执行状态）
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QEvent, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.i18n import tr
from src.core.command_handler import CommandHandler
from src.conversation import (
    ConversationManager,
    AskParser,
    AskWidget,
    TimeoutManager,
    TaskNotificationHandler,
    get_scheduler,
    TaskPriority,
    TTSPlayer,
    TTSEngine,
    VoiceRecognizer,
    WakeWordDetector,
    SimpleWakeWordDetector,
)

from .attachment_manager import AttachmentManager
from .attachment_panel import AttachmentPanel
from .workflow_panel import WorkflowPanel
from .commands_data import get_commands_data
from .commands_dialog import CommandsDialog

if TYPE_CHECKING:
    from .async_bridge import AsyncBridge

logger = logging.getLogger(__name__)


class ChatInputEdit(QTextEdit):
    """自定义输入框：Enter 发送，Shift+Enter 换行。"""

    send_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置高度策略为 Fixed，以便 setFixedHeight 正常工作
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def keyPressEvent(self, event) -> None:
        """拦截回车键。"""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter → 换行
                super().keyPressEvent(event)
            else:
                # Enter → 发送
                self.send_requested.emit()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """WinClaw 主窗口。"""

    # 信号
    message_sent = Signal(str)  # 用户发送的消息
    voice_message_sent = Signal(str)  # CFTA: 语音模式发送的消息（走快速聊天路径）
    message_with_attachments = Signal(str, list)  # 用户发送的消息 + 附件列表
    attachment_requested = Signal()  # 请求添加附件
    image_selected = Signal(str)  # 图片文件路径被选择 (兼容旧版)
    model_changed = Signal(str)  # 模型切换
    settings_requested = Signal()  # 打开设置
    close_to_tray = Signal()  # 关闭到托盘
    voice_record_requested = Signal()  # 请求录音
    voice_stop_requested = Signal()  # 请求停止录音
    tts_toggle_requested = Signal(bool)  # 请求切换 TTS
    generated_space_requested = Signal()  # 打开生成空间
    generated_space_clear_requested = Signal()  # 清空生成空间记录
    generated_space_file_delete_requested = Signal(str)  # 删除单个生成文件记录(路径)
    knowledge_rag_requested = Signal()  # 打开知识库
    knowledge_add_file_requested = Signal(str)  # 添加文件到知识库
    knowledge_add_url_requested = Signal(str)  # 添加URL到知识库
    knowledge_search_requested = Signal(str)  # 搜索知识库
    knowledge_doc_delete_requested = Signal(int)  # 删除知识库文档(doc_id)
    cron_job_requested = Signal()  # 打开定时任务管理
    stop_requested = Signal()  # 请求停止当前任务
    history_requested = Signal()  # 打开历史对话（兼容旧代码）
    history_refresh_requested = Signal()  # 刷新历史对话列表
    history_session_selected = Signal(str)  # 选择历史会话(session_id)
    history_session_delete_requested = Signal(str)  # 删除历史会话(session_id)
    conversation_mode_changed = Signal(str)  # 对话模式切换 (off/continuous/wake_word)
    conversation_state_changed = Signal(str)  # 对话状态变化 (idle/listening/chatting/thinking/speaking)
    theme_changed = Signal(str)  # 主题切换 (light/dark/system)
    language_changed = Signal(str)  # 语言切换 (zh_CN/en_US)

    def __init__(
        self,
        bridge: AsyncBridge | None = None,
        tool_registry=None,
        model_registry=None,
        *,
        minimize_to_tray: bool = True
    ) -> None:
        super().__init__()
        self._bridge = bridge
        self._tool_registry = tool_registry
        self._model_registry = model_registry
        self._minimize_to_tray = minimize_to_tray
        self._force_quit = False
        self._tool_log_entries: list[str] = []
        self._is_recording = False  # 录音状态
        self._tts_enabled = False  # TTS 开启状态

        # 对话模式状态
        self._conversation_mode = "off"  # off/continuous/wake_word
        self._conversation_state = "idle"  # idle/listening/chatting/thinking/speaking

        # 对话模式管理器
        self._conversation_mgr: ConversationManager | None = None
        self._ask_parser: AskParser | None = None
        self._timeout_mgr: TimeoutManager | None = None

        # 附件管理器
        self._attachment_manager = AttachmentManager(self)

        # 初始化命令处理器
        self._init_command_handler()

        self._setup_window()
        self._setup_menu_bar()
        self._setup_tool_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._setup_conversation()
        self._setup_remote_bridge()  # 初始化远程桥接

    def _init_command_handler(self) -> None:
        """初始化命令处理器。"""
        self._cmd_handler = CommandHandler(
            tool_registry=self._tool_registry,
            model_registry=self._model_registry,
            attachment_manager=self._attachment_manager,
            agent=None,  # GUI模式下agent通过bridge访问，需后续设置
        )
        # 设置模型切换回调，用于同步更新下拉框
        self._cmd_handler.set_model_switched_callback(self._on_cmd_model_switched)

    def _on_cmd_model_switched(self, model_key: str, model_name: str) -> None:
        """处理命令切换模型后的UI同步。"""
        # 更新下拉框显示
        self.set_current_model(model_name)
        # 发出模型切换信号
        self.model_changed.emit(model_name)

    def _setup_conversation(self) -> None:
        """初始化对话模式相关组件。"""
        # 读取 conversation 配置
        thinking_timeout = 120
        speaking_timeout = 60
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                conv_cfg = config.get("conversation", {})
                thinking_timeout = conv_cfg.get("thinking_timeout", 120)
                speaking_timeout = conv_cfg.get("speaking_timeout", 60)
        except Exception as e:
            logger.debug("读取 conversation 配置失败，使用默认值: %s", e)

        # 初始化对话管理器
        self._conversation_mgr = ConversationManager(
            thinking_timeout=thinking_timeout,
            speaking_timeout=speaking_timeout,
        )
        self._conversation_mgr.set_callbacks(
            on_start_listening=self._on_conversation_start_listening,
            on_stop_listening=self._on_conversation_stop_listening,
            on_send_message=self._on_conversation_send_message,
            on_play_tts=self._on_conversation_play_tts,
        )

        # 连接信号
        self._conversation_mgr.mode_changed.connect(self._on_conversation_mgr_mode_changed)
        self._conversation_mgr.state_changed.connect(self._on_conversation_mgr_state_changed)
        self._conversation_mgr.wake_word_detected.connect(self._on_wake_word_detected)
        self._conversation_mgr.speech_recognized.connect(self._on_speech_recognized)
        self._conversation_mgr.speech_recognized_with_prompt.connect(self._on_speech_recognized_with_prompt)
        self._conversation_mgr.silence_warning.connect(self._on_silence_warning)
        self._conversation_mgr.silence_timeout.connect(self._on_silence_timeout)

        # 初始化TTS播放器（优先使用 Edge TTS，速度快质量高）
        self._tts_player: TTSPlayer | None = None
        try:
            self._tts_player = TTSPlayer(engine=TTSEngine.EDGE_TTS)
            self._tts_player.playback_finished.connect(self._on_tts_playback_finished)
            logger.info("TTS播放器初始化成功")
        except Exception as e:
            logger.warning(f"TTS播放器初始化失败: {e}")

        # 初始化语音识别器
        self._voice_recognizer: VoiceRecognizer | None = None
        try:
            self._voice_recognizer = VoiceRecognizer()
            self._voice_recognizer.speech_result.connect(self._on_voice_speech_result)
            self._voice_recognizer.speech_error.connect(self._on_voice_speech_error)
            logger.info("语音识别器初始化成功")
        except Exception as e:
            logger.warning(f"语音识别器初始化失败: {e}")

        # 初始化唤醒词检测器
        self._wake_word_detector: SimpleWakeWordDetector | None = None
        self._wake_word_detector = SimpleWakeWordDetector(wake_words=["小铃铛"])
        self._wake_word_detector.wake_word_detected.connect(self._on_wake_word_detected_from_recognizer)

        # 初始化追问解析器
        self._ask_parser = AskParser()

        # 初始化超时管理器
        self._timeout_mgr = TimeoutManager()

        # 初始化追问UI组件
        self._ask_widget = AskWidget()
        self._ask_widget.option_selected.connect(self._on_ask_option_selected)

        # 初始化任务通知处理器
        self._task_notification = TaskNotificationHandler(self)

    def _setup_remote_bridge(self) -> None:
        """初始化远程桥接客户端。"""
        # 远程桥接客户端
        self._remote_bridge = None
        self._remote_bridge_task = None
        
        # 读取远程配置
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            config_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                remote_cfg = config.get("remote", {})
                
                if remote_cfg.get("enabled", False):
                    self._init_remote_bridge(remote_cfg)
        except Exception as e:
            logger.warning(f"读取远程配置失败: {e}")

    def _init_remote_bridge(self, config: dict) -> None:
        """初始化并启动远程桥接客户端。
        
        Args:
            config: 远程配置字典
        """
        try:
            from src.remote_client import RemoteBridgeClient
            from src.remote_client.client import BridgeConfig
            
            # 获取 Agent 引用（通过 bridge）
            agent = None
            if self._bridge and hasattr(self._bridge, '_agent'):
                agent = self._bridge._agent
            
            if not agent:
                logger.warning("无法获取 Agent，远程桥接初始化失败")
                return
            
            # 创建桥接配置
            bridge_config = BridgeConfig(
                server_url=config.get("server_url", "wss://localhost:8000/ws/bridge"),
                token=config.get("token", ""),
                enabled=config.get("enabled", True),
                auto_connect=config.get("auto_connect", True),
                reconnect_interval=config.get("reconnect_interval", 5.0),
                max_reconnect_attempts=config.get("max_reconnect_attempts", 10),
                heartbeat_interval=config.get("heartbeat_interval", 30.0),
                connection_timeout=config.get("connection_timeout", 30.0)
            )
            
            # 创建客户端
            self._remote_bridge = RemoteBridgeClient(
                agent=agent,
                event_bus=getattr(agent, 'event_bus', None),
                session_manager=getattr(agent, 'session_manager', None),
                config=bridge_config,
                on_state_change=self._on_remote_bridge_state_change
            )
            
            # 启动客户端
            if bridge_config.auto_connect:
                self._start_remote_bridge()
                
            logger.info("远程桥接客户端初始化完成")
            
        except ImportError as e:
            logger.warning(f"远程桥接模块未安装: {e}")
        except Exception as e:
            logger.error(f"远程桥接初始化失败: {e}", exc_info=True)

    def _start_remote_bridge(self) -> None:
        """启动远程桥接客户端。"""
        if self._remote_bridge and not self._remote_bridge_task:
            # 使用 QTimer 延迟启动，等待事件循环开始运行
            from PySide6.QtCore import QTimer
            
            def do_start():
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        self._remote_bridge_task = asyncio.create_task(self._remote_bridge.start())
                        logger.info("远程桥接客户端已启动")
                    else:
                        logger.warning("事件循环仍未运行，再次延迟启动")
                        QTimer.singleShot(1000, do_start)
                except Exception as e:
                    logger.error(f"启动远程桥接失败: {e}")
            
            QTimer.singleShot(500, do_start)

    def _stop_remote_bridge(self) -> None:
        """停止远程桥接客户端。"""
        if self._remote_bridge:
            try:
                # 同步调用异步停止方法
                loop = asyncio.get_event_loop()
                if loop and loop.is_running():
                    asyncio.create_task(self._remote_bridge.stop())
                logger.info("远程桥接客户端已停止")
            except Exception as e:
                logger.error(f"停止远程桥接失败: {e}")
            
            if self._remote_bridge_task and not self._remote_bridge_task.done():
                self._remote_bridge_task.cancel()
            self._remote_bridge_task = None

    def _on_remote_bridge_state_change(self, state) -> None:
        """远程桥接状态变化回调。
        
        Args:
            state: ConnectionState 枚举值
        """
        from src.remote_client.client import ConnectionState
        
        state_text = {
            ConnectionState.DISCONNECTED: "未连接",
            ConnectionState.CONNECTING: "连接中",
            ConnectionState.CONNECTED: "已连接",
            ConnectionState.RECONNECTING: "重连中",
            ConnectionState.ERROR: "连接错误"
        }.get(state, "未知")
        
        logger.info(f"远程桥接状态: {state_text}")
        
        # 更新状态栏
        if hasattr(self, '_status_label'):
            self._status_label.setText(f"远程: {state_text}")


    def _on_conversation_start_listening(self) -> None:
        """对话模式开始监听回调。"""
        # 强制更新UI为录音状态
        self._is_recording = True
        self._voice_btn.setText("🔴 监听中...")
        self._voice_btn.setStyleSheet("background-color: #ff4444; color: white;")
        
        # 强制刷新UI
        self._voice_btn.repaint()
        self._voice_btn.update()

        # 启动语音识别器
        if self._voice_recognizer:
            self._voice_recognizer.start_listening()
            logger.info("语音识别器已启动")
        else:
            logger.warning("语音识别器未初始化")

        self.voice_record_requested.emit()

    def _on_conversation_stop_listening(self) -> None:
        """对话模式停止监听回调。"""
        # 停止语音识别器
        if self._voice_recognizer:
            self._voice_recognizer.stop_listening()
            logger.info("语音识别器已停止")

        # 更新UI为停止状态
        self._is_recording = False
        self._voice_btn.setText("🎤 录音")
        self._voice_btn.setStyleSheet("")
        
        # 强制刷新UI
        self._voice_btn.repaint()
        self._voice_btn.update()

        self.voice_stop_requested.emit()

    def _on_conversation_send_message(self, text: str) -> None:
        """对话模式发送消息回调。"""
        logger.info(f"对话模式发送消息: {text}")
        # 设置输入框内容
        self._input_edit.setPlainText(text)
        
        # 自动发送消息（模拟点击发送按钮）
        # 清空附件管理器
        self._attachment_manager.clear()
        
        # 触发发送信号
        self.message_sent.emit(text)
        
        # 显示思考状态
        self._set_thinking_state(True)

    def _on_conversation_mgr_mode_changed(self, mode: str) -> None:
        """对话模式切换回调。"""
        logger.info(f"对话模式切换: {mode}")

    def _on_conversation_mgr_state_changed(self, state: str) -> None:
        """对话状态变化回调。"""
        self._conversation_state = state
        self.conversation_state_changed.emit(state)
        logger.info(f"对话状态变化: {state}")

    def _on_wake_word_detected(self) -> None:
        """检测到唤醒词回调。"""
        logger.info("检测到唤醒词")
        self.add_tool_log("检测到唤醒词，已激活对话模式")

    def _on_speech_recognized(self, text: str, is_voice_mode: bool = False) -> None:
        """语音识别完成回调。

        Args:
            text: 识别的文本
            is_voice_mode: 是否是语音对话模式
        """
        logger.info(f"语音识别完成: {text}, 语音模式: {is_voice_mode}")
        # 添加到聊天显示
        self._chat_widget.add_user_message(text)

        # 清空输入框
        self._input_edit.clear()

        # 获取附件列表（对话模式通常没有附件）
        attachments = self._attachment_manager.attachments

        # 发出信号（包含附件信息）
        if attachments:
            self.message_with_attachments.emit(text, attachments)
            self._attachment_manager.clear()
        else:
            self.message_sent.emit(text)

        # 显示思考状态
        self._set_thinking_state(True)

    def _on_speech_recognized_with_prompt(self, text: str, is_voice_mode: bool = False) -> None:
        """带提示词的语音识别完成回调（用于发送给AI）。

        Args:
            text: 带提示词的文本
            is_voice_mode: 是否是语音对话模式
        """
        if is_voice_mode:
            logger.info(f"发送带提示词的文本给AI: {text[:50]}...")
            # CFTA: 语音模式使用专用信号，走快速聊天路径
            self.voice_message_sent.emit(text)

    def _on_silence_warning(self, remaining: int) -> None:
        """沉默警告回调。"""
        logger.info(f"沉默警告: {remaining}秒")
        self._conversation_status_label.setText(f"⚠️ {remaining}秒无输入将停止...")

    def _on_silence_timeout(self) -> None:
        """沉默超时回调。"""
        logger.info("沉默超时")
        if self._conversation_mode == "wake_word":
            self._conversation_status_label.setText("🔔 等待唤醒词...")
        else:
            self._conversation_status_label.setText("")

    def _on_tts_playback_finished(self) -> None:
        """TTS播放完成回调。"""
        logger.info("TTS播放完成")
        if self._conversation_mgr:
            self._conversation_mgr.on_tts_finished()

    def _on_voice_speech_result(self, text: str, is_final: bool) -> None:
        """语音识别结果回调。"""
        logger.info(f"语音识别结果: {text} (final={is_final})")

        # 检查唤醒词
        if self._conversation_mode == "wake_word" and self._wake_word_detector:
            if self._wake_word_detector.check(text):
                self.add_tool_log("检测到唤醒词，已激活对话模式")
                self._conversation_mgr.set_mode("continuous")

        # 发送到对话管理器
        if self._conversation_mgr:
            self._conversation_mgr.on_speech_result(text, is_final)

    def _on_voice_speech_error(self, error: str) -> None:
        """语音识别错误回调。"""
        logger.error(f"语音识别错误: {error}")
        self.add_tool_log(f"⚠️ 语音识别错误: {error}")

    def _on_wake_word_detected_from_recognizer(self) -> None:
        """从识别器检测到唤醒词回调。"""
        logger.info("唤醒词检测器检测到唤醒词")
        if self._conversation_mgr:
            self._conversation_mgr.on_speech_result("小铃铛", True)

    def _on_ask_option_selected(self, option: str) -> None:
        """追问选项选择回调。"""
        logger.info(f"用户选择选项: {option}")
        if option and option != "__done__":
            # 发送选择到AI
            self._chat_widget.add_user_message(f"[选择] {option}")
            self.message_sent.emit(option)
            self._set_thinking_state(True)
        self._timeout_mgr.cancel()

    def _on_conversation_play_tts(self, text: str) -> None:
        """对话模式播放TTS回调。"""
        if self._tts_player and self._tts_player.is_playing:
            self._tts_player.stop()

        if self._tts_player:
            # 解析文本，检查是否有追问
            cleaned_text, ask_intent = self._ask_parser.parse_without_markup(text) if self._ask_parser else (text, None)

            if ask_intent:
                # 有追问，显示选项UI
                self._ask_widget.show_choice(
                    ask_intent.question,
                    ask_intent.options,
                    ask_intent.recommended,
                    ask_intent.timeout_seconds,
                )
                # 启动超时管理器
                self._timeout_mgr.start(
                    ask_intent.timeout_strategy,
                    ask_intent.recommended,
                    ask_intent.timeout_seconds,
                )

            # 播放TTS
            if cleaned_text:
                self._tts_player.speak(cleaned_text)
                if self._conversation_mgr:
                    self._conversation_mgr.on_tts_start()

    def _setup_window(self) -> None:
        """设置窗口属性。"""
        self.setWindowTitle(f"WeClaw - {tr('AI 助手')}")
        self.setMinimumSize(900, 375)
        self.resize(1200, 600)
        self._setup_window_icon()
        self._center_on_screen()
    
    def _setup_window_icon(self) -> None:
        """设置窗口图标。"""
        # 尝试多种路径找到图标文件
        possible_paths = [
            Path(__file__).parent.parent.parent / "resources" / "icons" / "app_icon.ico",
            Path(__file__).parent.parent.parent / "resources" / "icons" / "app_icon_256.png",
            Path(__file__).parent.parent.parent / "resources" / "icons" / "logo1_bold_w.png",
            Path.cwd() / "resources" / "icons" / "app_icon.ico",
            Path.cwd() / "resources" / "icons" / "app_icon_256.png",
        ]
        
        for icon_path in possible_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                logging.getLogger(__name__).debug(f"窗口图标已设置: {icon_path}")
                return
        
        logging.getLogger(__name__).warning("未找到窗口图标文件")

    def _center_on_screen(self) -> None:
        """将窗口居中显示在屏幕上（稍微偏上，确保底部能完整显示）。"""
        screen = self.screen()
        if screen:
            screen_geometry = screen.geometry()
            window_geometry = self.geometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            # 稍微偏上显示，offset=50 可以根据需要调整，确保底部不被截断
            offset = 50
            y = (screen_geometry.height() - window_geometry.height()) // 2 - offset
            # 确保 y 不为负（窗体顶部不超过屏幕顶部）
            y = max(y, 10)
            self.move(x, y)

    def reload_ui(self) -> None:
        """重新加载 UI（语言切换后调用）。"""
        # 重新设置窗口标题
        self.setWindowTitle(f"WeClaw - {tr('AI 助手')}")

        # 重建菜单栏
        menubar = self.menuBar()
        menubar.clear()
        self._setup_menu_bar()

        # 重建工具栏
        toolbar = self.findChild(QToolBar, "MainToolBar")
        if toolbar:
            toolbar.setWindowTitle(tr("主工具栏"))
            # 刷新工具栏按钮文本
            self._refresh_toolbar()

        # 刷新状态栏
        self._status_model.setText(tr("模型") + ": " + tr("未选择"))
        self._status_connection.setText("● " + tr("未连接"))

    def _refresh_toolbar(self) -> None:
        """刷新工具栏按钮文本。"""
        # 重新查找并更新工具栏中的按钮
        toolbar = self.findChild(QToolBar)
        if not toolbar:
            return

        # 遍历工具栏 actions
        for action in toolbar.actions():
            widget = toolbar.widgetForAction(action)
            if isinstance(widget, QPushButton):
                text = action.text()
                # 根据原文本映射到新的翻译
                if "新建会话" in text or "New Session" in text:
                    widget.setText(tr("新建会话"))
                elif "历史对话" in text or "History" in text:
                    widget.setText(tr("📋 历史对话"))
                elif text == "清空" or text == "Clear":
                    widget.setText(tr("清空"))
                elif "录音" in text or "Record" in text:
                    widget.setText(tr("🎤 录音"))
                elif "TTS" in text:
                    widget.setText(tr("🔇 TTS"))
                elif "生成空间" in text or "Generated" in text:
                    widget.setText(tr("📂 生成空间"))
                elif "知识库" in text or "Knowledge" in text:
                    widget.setText(tr("🧠 知识库"))

    def _setup_menu_bar(self) -> None:
        """设置菜单栏。"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu(tr("文件"))

        new_session_action = QAction(tr("新建会话"), self)
        new_session_action.setShortcut(QKeySequence.StandardKey.New)
        new_session_action.triggered.connect(self._on_new_session)
        file_menu.addAction(new_session_action)

        history_action = QAction(tr("历史对话") + "...", self)
        history_action.setShortcut(QKeySequence("Ctrl+H"))
        history_action.triggered.connect(self._on_history)
        file_menu.addAction(history_action)

        file_menu.addSeparator()

        exit_action = QAction(tr("退出"), self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu(tr("编辑"))

        clear_action = QAction(tr("清空对话"), self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.triggered.connect(self._on_clear_chat)
        edit_menu.addAction(clear_action)

        # 显示菜单（主题 + 语言切换）
        view_menu = menubar.addMenu(tr("显示"))

        # 主题子菜单
        theme_menu = QMenu(tr("主题"), self)
        view_menu.addMenu(theme_menu)

        # 基础主题
        theme_light_action = QAction(tr("亮色"), self)
        theme_light_action.triggered.connect(lambda: self.theme_changed.emit("light"))
        theme_menu.addAction(theme_light_action)

        theme_dark_action = QAction(tr("暗色"), self)
        theme_dark_action.triggered.connect(lambda: self.theme_changed.emit("dark"))
        theme_menu.addAction(theme_dark_action)

        theme_system_action = QAction(tr("跟随系统"), self)
        theme_system_action.triggered.connect(lambda: self.theme_changed.emit("system"))
        theme_menu.addAction(theme_system_action)

        theme_menu.addSeparator()

        # 时尚渐变主题
        theme_ocean_action = QAction(tr("海洋蓝"), self)
        theme_ocean_action.triggered.connect(lambda: self.theme_changed.emit("ocean_blue"))
        theme_menu.addAction(theme_ocean_action)

        theme_forest_action = QAction(tr("森林绿"), self)
        theme_forest_action.triggered.connect(lambda: self.theme_changed.emit("forest_green"))
        theme_menu.addAction(theme_forest_action)

        theme_sunset_action = QAction(tr("日落橙"), self)
        theme_sunset_action.triggered.connect(lambda: self.theme_changed.emit("sunset_orange"))
        theme_menu.addAction(theme_sunset_action)

        theme_purple_action = QAction(tr("紫色梦幻"), self)
        theme_purple_action.triggered.connect(lambda: self.theme_changed.emit("purple_dream"))
        theme_menu.addAction(theme_purple_action)

        theme_pink_action = QAction(tr("玫瑰粉"), self)
        theme_pink_action.triggered.connect(lambda: self.theme_changed.emit("pink_rose"))
        theme_menu.addAction(theme_pink_action)

        theme_minimal_action = QAction(tr("极简白"), self)
        theme_minimal_action.triggered.connect(lambda: self.theme_changed.emit("minimal_white"))
        theme_menu.addAction(theme_minimal_action)

        theme_menu.addSeparator()

        # 深色系主题
        theme_deep_blue_action = QAction(tr("深蓝色"), self)
        theme_deep_blue_action.triggered.connect(lambda: self.theme_changed.emit("deep_blue"))
        theme_menu.addAction(theme_deep_blue_action)

        theme_deep_brown_action = QAction(tr("深棕色"), self)
        theme_deep_brown_action.triggered.connect(lambda: self.theme_changed.emit("deep_brown"))
        theme_menu.addAction(theme_deep_brown_action)

        theme_menu.addSeparator()

        # 赛博朋克风格主题
        theme_cyberpunk_action = QAction(tr("赛博朋克紫"), self)
        theme_cyberpunk_action.triggered.connect(lambda: self.theme_changed.emit("cyberpunk_purple"))
        theme_menu.addAction(theme_cyberpunk_action)

        theme_universe_blue_action = QAction(tr("赛博宇宙蓝"), self)
        theme_universe_blue_action.triggered.connect(lambda: self.theme_changed.emit("cyber_universe_blue"))
        theme_menu.addAction(theme_universe_blue_action)

        # 语言子菜单
        language_menu = QMenu(tr("语言"), self)
        view_menu.addMenu(language_menu)

        lang_zh_action = QAction("简体中文", self)
        lang_zh_action.triggered.connect(lambda: self.language_changed.emit("zh_CN"))
        language_menu.addAction(lang_zh_action)

        lang_en_action = QAction("English", self)
        lang_en_action.triggered.connect(lambda: self.language_changed.emit("en_US"))
        language_menu.addAction(lang_en_action)

        # 工具菜单
        tools_menu = menubar.addMenu(tr("工具"))

        gen_space_action = QAction(tr("📂 生成空间") + "...", self)
        gen_space_action.setShortcut(QKeySequence("Ctrl+G"))
        gen_space_action.triggered.connect(self._on_generated_space)
        tools_menu.addAction(gen_space_action)

        # 知识库管理
        knowledge_action = QAction(tr("🧠 知识库") + "...", self)
        knowledge_action.setShortcut(QKeySequence("Ctrl+K"))
        knowledge_action.triggered.connect(self._on_knowledge_rag)
        tools_menu.addAction(knowledge_action)

        # 定时任务管理
        cron_action = QAction(tr("⏰ 定时任务") + "...", self)
        cron_action.setShortcut(QKeySequence("Ctrl+T"))
        cron_action.triggered.connect(self._on_cron_job)
        tools_menu.addAction(cron_action)

        tools_menu.addSeparator()
        
        # Phase 6+: 工作流记录查看
        workflow_action = QAction(tr("📋 工作流记录"), self)
        workflow_action.setToolTip("查看所有工作流执行记录")
        workflow_action.triggered.connect(self._on_workflow_records)
        tools_menu.addAction(workflow_action)
        
        # Phase 6+: 意识流记录查看
        # 意识流记录功能已移除
        # consciousness_action = QAction(tr("🧠 意识流记录"), self)
        # consciousness_action.setToolTip("查看所有意识流行为和进化记录")
        # consciousness_action.triggered.connect(self._on_consciousness_records)
        # tools_menu.addAction(consciousness_action)

        tools_menu.addSeparator()

        settings_action = QAction(tr("设置") + "...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        tools_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu(tr("帮助"))

        about_action = QAction(tr("关于") + "...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_tool_bar(self) -> None:
        """设置工具栏。"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 模型选择下拉框
        model_label = QLabel(tr("模型") + ":")
        toolbar.addWidget(model_label)

        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(200)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        toolbar.addWidget(self._model_combo)

        toolbar.addSeparator()

        # 新建会话按钮
        new_btn = QPushButton(tr("新建会话"))
        new_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 60px; max-width: 70px;")
        new_btn.clicked.connect(self._on_new_session)
        toolbar.addWidget(new_btn)

        # 复制对话区按钮
        copy_chat_btn = QPushButton(tr("📋 复制对话"))
        copy_chat_btn.setToolTip(tr("复制所有对话内容"))
        copy_chat_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 80px; max-width: 90px;")
        copy_chat_btn.clicked.connect(self._on_copy_chat)
        toolbar.addWidget(copy_chat_btn)

        toolbar.addSeparator()

        # 清空按钮
        clear_btn = QPushButton(tr("清空"))
        clear_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 50px; max-width: 60px;")
        clear_btn.clicked.connect(self._on_clear_chat)
        toolbar.addWidget(clear_btn)
        
        toolbar.addSeparator()
        
        # 语音输入按钮 (麦克风)
        self._voice_btn = QPushButton(tr("🎤 录音"))
        self._voice_btn.setToolTip(tr("按住录音，松开发送") + " (Ctrl+R)")
        self._voice_btn.setCheckable(False)
        self._voice_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 70px; max-width: 80px;")
        self._voice_btn.clicked.connect(self._on_voice_record)
        toolbar.addWidget(self._voice_btn)
        
        # TTS 开关按钮
        self._tts_btn = QPushButton(tr("🔇 TTS"))
        self._tts_btn.setToolTip(tr("切换 AI 回复自动朗读"))
        self._tts_btn.setCheckable(True)
        self._tts_btn.setChecked(False)
        self._tts_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 60px; max-width: 70px;")
        self._tts_btn.clicked.connect(self._on_tts_toggle)
        toolbar.addWidget(self._tts_btn)

        # 对话模式开关（下拉菜单）
        self._conversation_mode_combo = QComboBox()
        self._conversation_mode_combo.setMinimumWidth(120)
        self._conversation_mode_combo.setStyleSheet("font-size: 11px; padding: 3px 6px;")
        self._conversation_mode_combo.addItems([
            tr("💬 对话模式"),
            tr("⚡ 持续对话"),
            tr("🔔 唤醒词模式"),
        ])
        self._conversation_mode_combo.setCurrentIndex(0)
        self._conversation_mode_combo.setToolTip(tr("选择对话模式，开启后实现语音交互"))
        self._conversation_mode_combo.currentIndexChanged.connect(self._on_conversation_mode_changed)
        toolbar.addWidget(self._conversation_mode_combo)

        # 对话状态标签
        self._conversation_status_label = QLabel("")
        self._conversation_status_label.setStyleSheet("color: #888; font-size: 11px;")
        self._conversation_status_label.setVisible(False)
        toolbar.addWidget(self._conversation_status_label)

        # 生成空间文件计数徽标（保留用于TAB页面更新）
        self._gen_space_count = 0

    def _setup_central_widget(self) -> None:
        """设置中央部件。"""
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局：水平分割器
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧：聊天区域
        left_widget = self._create_chat_area()
        splitter.addWidget(left_widget)

        # 右侧：状态面板
        right_widget = self._create_status_panel()
        splitter.addWidget(right_widget)

        # 设置分割比例：左侧600，右侧400（右侧宽度翻倍）
        splitter.setSizes([600, 400])

    def _create_chat_area(self) -> QWidget:
        """创建聊天区域。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 聊天显示区域
        from .chat import ChatWidget
        self._chat_widget = ChatWidget()
        layout.addWidget(self._chat_widget, stretch=1)

        # 输入区域
        input_widget = self._create_input_area()
        layout.addWidget(input_widget)

        return widget

    def _create_input_area(self) -> QWidget:
        """创建输入区域。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 附件面板
        self._attachment_panel = AttachmentPanel(self._attachment_manager)
        self._attachment_panel.add_files_requested.connect(self._on_attachment)
        self._attachment_panel.file_removed.connect(self._on_attachment_removed)
        self._attachment_panel.clear_requested.connect(self._on_attachments_clear)
        self._attachment_panel.files_dropped.connect(self._on_files_dropped)
        self._attachment_panel.quick_commands_requested.connect(self._on_show_quick_commands)
        self._attachment_panel.combo_commands_requested.connect(self._on_show_combo_commands)
        layout.addWidget(self._attachment_panel)

        # 输入框区域（展开按钮 + 输入框 + 操作按钮 + 发送按钮）
        input_container = QWidget()
        input_container_layout = QHBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(4)

        # 展开/收起按钮 - 输入框左侧，带边框的按钮样式
        self._expand_input_btn = QPushButton("展开")
        self._expand_input_btn.setToolTip("展开输入框")
        self._expand_input_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #333;
                border-radius: 4px;
                background: transparent;
                color: #333;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #333;
                color: white;
            }
        """)
        self._expand_input_btn.clicked.connect(self._toggle_input_expand)
        input_container_layout.addWidget(self._expand_input_btn)

        # 输入框（自定义键监听）
        self._input_edit = ChatInputEdit()
        self._input_edit.send_requested.connect(self._on_send)
        self._input_edit.setPlaceholderText("输入消息... (Enter发送，Shift+Enter换行)，/help 查看快捷工具指令清单，点击快捷命令、组合命令 获取100+示例")
        self._input_edit.setMinimumHeight(30)
        self._input_edit.setMaximumHeight(120)
        self._input_edit.setStyleSheet("""
            QTextEdit {
                padding: 0px 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                color: #333;
            }
            QTextEdit:focus {
                border: 1px solid #28a745;
            }
        """)
        input_container_layout.addWidget(self._input_edit, stretch=1)

        # 输入框操作按钮组 - 带边框的按钮样式
        btn_style = """
            QPushButton {
                border: 1px solid #333;
                border-radius: 4px;
                background: transparent;
                color: #333;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #333;
                color: white;
            }
        """

        # 复制按钮
        self._copy_input_btn = QPushButton("复制")
        self._copy_input_btn.setToolTip("复制输入框内容")
        self._copy_input_btn.setStyleSheet(btn_style)
        self._copy_input_btn.clicked.connect(self._on_copy_input)
        input_container_layout.addWidget(self._copy_input_btn)

        # 粘贴按钮
        self._paste_input_btn = QPushButton("粘贴")
        self._paste_input_btn.setToolTip("粘贴到输入框")
        self._paste_input_btn.setStyleSheet(btn_style)
        self._paste_input_btn.clicked.connect(self._on_paste_input)
        input_container_layout.addWidget(self._paste_input_btn)

        # 清空按钮
        self._clear_input_btn = QPushButton("清空")
        self._clear_input_btn.setToolTip("清空输入框")
        self._clear_input_btn.setStyleSheet(btn_style)
        self._clear_input_btn.clicked.connect(self._on_clear_input)
        input_container_layout.addWidget(self._clear_input_btn)

        # 发送按钮 - 确保文字完整显示
        self._send_btn = QPushButton("发送")
        self._send_btn.setDefault(True)
        self._send_btn.setMinimumSize(65, 30)
        self._send_btn.setStyleSheet("""
            QPushButton {
                border: none !important;
                border-radius: 6px !important;
                background: #28a745 !important;
                color: white !important;
                font-weight: bold !important;
                font-size: 14px !important;
                padding: 0px 12px !important;
            }
            QPushButton:hover {
                background: #218838 !important;
            }
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_container_layout.addWidget(self._send_btn)

        # 停止按钮（默认隐藏）
        self._stop_btn = QPushButton("停止")
        self._stop_btn.setMinimumSize(65, 30)
        self._stop_btn.setVisible(False)
        self._stop_btn.setStyleSheet("""
            QPushButton {
                border: none !important;
                border-radius: 6px !important;
                background: #dc3545 !important;
                color: white !important;
                font-weight: bold !important;
                font-size: 14px !important;
                padding: 0px 12px !important;
            }
            QPushButton:hover {
                background: #c82333 !important;
            }
        """)
        self._stop_btn.clicked.connect(self._on_stop)
        input_container_layout.addWidget(self._stop_btn)

        layout.addWidget(input_container)

        return widget

    def _create_status_panel(self) -> QWidget:
        """创建右侧状态面板（TAB页面模式）。"""
        widget = QWidget()
        widget.setMinimumWidth(300)  # 初始宽度
        widget.setMaximumWidth(500)  # 最大宽度
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        # 创建TAB控件
        self._right_tab_widget = QTabWidget()
        self._right_tab_widget.setDocumentMode(True)  # 更现代的TAB样式
        layout.addWidget(self._right_tab_widget)

        # TAB 1: 工具执行状态
        tools_tab = self._create_tools_status_tab()
        self._right_tab_widget.addTab(tools_tab, tr("🔧 工具状态"))

        # TAB 2: 生成空间
        gen_space_tab = self._create_generated_space_tab()
        self._right_tab_widget.addTab(gen_space_tab, tr("📂 生成空间"))

        # TAB 3: 知识库
        knowledge_tab = self._create_knowledge_tab()
        self._right_tab_widget.addTab(knowledge_tab, tr("🧠 知识库"))

        # TAB 4: 历史对话
        history_tab = self._create_history_tab()
        self._right_tab_widget.addTab(history_tab, tr("📋 历史"))

        # 保留 _session_info 用于兼容现有代码（隐藏的）
        self._session_info = QLabel("新会话")
        self._session_info.setVisible(False)

        # TAB切换事件（延迟连接，避免初始化时触发）
        QTimer.singleShot(100, lambda: self._right_tab_widget.currentChanged.connect(self._on_tab_changed))

        return widget

    def _on_tab_changed(self, index: int) -> None:
        """TAB切换事件处理（懒加载）。"""
        if index == 1:  # 生成空间TAB
            self.generated_space_requested.emit()
        elif index == 2:  # 知识库TAB
            self.knowledge_rag_requested.emit()
        elif index == 3:  # 历史对话TAB
            self.history_refresh_requested.emit()

    def _create_tools_status_tab(self) -> QWidget:
        """创建工具执行状态TAB页面。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 标题行：状态 + 复制按钮
        header_layout = QHBoxLayout()
        self._tool_status = QLabel("空闲")
        header_layout.addWidget(self._tool_status)
        header_layout.addStretch()
        copy_tools_btn = QPushButton("复制")
        copy_tools_btn.setToolTip("复制工具执行状态")
        copy_tools_btn.setFixedSize(45, 22)
        copy_tools_btn.setStyleSheet("font-size: 10px; border: none; padding: 2px;")
        copy_tools_btn.clicked.connect(self._copy_tool_status)
        header_layout.addWidget(copy_tools_btn)
        layout.addLayout(header_layout)

        # 进度条
        self._tool_progress = QProgressBar()
        self._tool_progress.setRange(0, 0)  # 不确定进度
        self._tool_progress.setMaximumHeight(6)
        self._tool_progress.setVisible(False)
        layout.addWidget(self._tool_progress)

        # 工具执行日志滚动区
        self._tool_log = QLabel("")
        self._tool_log.setWordWrap(True)
        self._tool_log.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._tool_log.setStyleSheet("font-size: 12px;")

        self._tool_log_scroll = QScrollArea()
        self._tool_log_scroll.setWidgetResizable(True)
        self._tool_log_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tool_log_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._tool_log_scroll.setMinimumHeight(80)
        self._tool_log_scroll.setWidget(self._tool_log)
        layout.addWidget(self._tool_log_scroll, stretch=1)

        return widget

    def _create_generated_space_tab(self) -> QWidget:
        """创建生成空间TAB页面（完整功能）。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题行
        header_layout = QHBoxLayout()
        title_label = QLabel(tr("📂 生成空间"))
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 打开文件夹按钮
        self._gen_open_folder_btn = QPushButton(tr("📁"))
        self._gen_open_folder_btn.setToolTip(tr("打开生成空间文件夹"))
        self._gen_open_folder_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 28px; max-width: 32px;")
        self._gen_open_folder_btn.clicked.connect(self._on_open_generated_space_folder)
        header_layout.addWidget(self._gen_open_folder_btn)
        layout.addLayout(header_layout)

        # 文件计数+摘要标签
        self._gen_space_count_label = QLabel(tr("0 个文件"))
        self._gen_space_count_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._gen_space_count_label)

        # 搜索+筛选+排序行（合并为一行）
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self._gen_search_input = QLineEdit()
        self._gen_search_input.setPlaceholderText(tr("搜索..."))
        self._gen_search_input.textChanged.connect(self._on_gen_filter_changed)
        search_layout.addWidget(self._gen_search_input, stretch=1)
        
        # 筛选器
        self._gen_filter_combo = QComboBox()
        self._gen_filter_combo.addItems([tr("全部"), tr("文档"), tr("图片"), tr("代码"), tr("其他")])
        self._gen_filter_combo.setFixedWidth(60)
        self._gen_filter_combo.currentTextChanged.connect(self._on_gen_filter_changed)
        search_layout.addWidget(self._gen_filter_combo)
        
        # 排序器
        self._gen_sort_combo = QComboBox()
        self._gen_sort_combo.addItems([
            tr("时间↓"), tr("时间↑"), tr("名称↓"), tr("名称↑"), tr("大小↓"), tr("大小↑")
        ])
        self._gen_sort_combo.setFixedWidth(60)
        self._gen_sort_combo.currentTextChanged.connect(self._on_gen_filter_changed)
        search_layout.addWidget(self._gen_sort_combo)
        
        layout.addLayout(search_layout)

        # 文件列表滚动区域
        self._gen_space_scroll = QScrollArea()
        self._gen_space_scroll.setWidgetResizable(True)
        self._gen_space_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._gen_space_list_widget = QWidget()
        self._gen_space_list_layout = QVBoxLayout(self._gen_space_list_widget)
        self._gen_space_list_layout.setContentsMargins(0, 0, 0, 0)
        self._gen_space_list_layout.setSpacing(4)

        self._gen_space_scroll.setWidget(self._gen_space_list_widget)
        layout.addWidget(self._gen_space_scroll, stretch=1)

        # 空状态提示
        self._gen_space_empty_label = QLabel(
            tr("🎉 尚未生成任何文件\n\n当 AI 创建文件时，\n会自动出现在这里。")
        )
        self._gen_space_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gen_space_empty_label.setStyleSheet("color: gray; font-size: 11px; padding: 15px;")
        self._gen_space_empty_label.setWordWrap(True)
        self._gen_space_list_layout.addWidget(self._gen_space_empty_label)
        self._gen_space_list_layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        refresh_gen_btn = QPushButton(tr("刷新"))
        refresh_gen_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 45px; max-width: 55px;")
        refresh_gen_btn.clicked.connect(self._on_refresh_generated_space)
        btn_layout.addWidget(refresh_gen_btn)
        
        btn_layout.addStretch()
        
        # 清空记录按钮
        self._gen_clear_btn = QPushButton(tr("清空"))
        self._gen_clear_btn.setToolTip(tr("清空所有生成记录（不删除文件）"))
        self._gen_clear_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 45px; max-width: 55px;")
        self._gen_clear_btn.clicked.connect(self._on_clear_generated_space)
        btn_layout.addWidget(self._gen_clear_btn)
        
        layout.addLayout(btn_layout)

        # 保存所有文件用于筛选排序
        self._gen_all_files: list = []

        return widget

    def _create_knowledge_tab(self) -> QWidget:
        """创建知识库TAB页面（完整功能）。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题行（含进度条）
        header_layout = QHBoxLayout()
        title_label = QLabel(tr("🧠 知识库"))
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title_label)
        
        # 进度条（放在标题右侧）
        self._knowledge_progress = QProgressBar()
        self._knowledge_progress.setVisible(False)
        self._knowledge_progress.setFixedHeight(16)
        self._knowledge_progress.setMinimumWidth(100)
        self._knowledge_progress.setMaximumWidth(150)
        header_layout.addWidget(self._knowledge_progress)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 文档统计标签
        self._knowledge_count_label = QLabel(tr("0 个文档"))
        self._knowledge_count_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._knowledge_count_label)

        # 添加文档区域
        add_layout = QHBoxLayout()
        add_layout.setSpacing(4)
        
        # 添加方式选择
        self._knowledge_add_type = QComboBox()
        self._knowledge_add_type.addItems([tr("文件"), tr("网址")])
        self._knowledge_add_type.setFixedWidth(55)
        self._knowledge_add_type.currentTextChanged.connect(self._on_knowledge_add_type_changed)
        add_layout.addWidget(self._knowledge_add_type)
        
        # 路径/URL输入
        self._knowledge_path_input = QLineEdit()
        self._knowledge_path_input.setPlaceholderText(tr("选择文件..."))
        add_layout.addWidget(self._knowledge_path_input, stretch=1)
        
        # 浏览按钮
        self._knowledge_browse_btn = QPushButton("...")
        self._knowledge_browse_btn.setStyleSheet("font-size: 11px; padding: 4px 6px; min-width: 25px; max-width: 30px;")
        self._knowledge_browse_btn.clicked.connect(self._on_knowledge_browse)
        add_layout.addWidget(self._knowledge_browse_btn)
        
        # 添加按钮
        self._knowledge_add_btn = QPushButton(tr("添加"))
        self._knowledge_add_btn.setToolTip(tr("添加到知识库"))
        self._knowledge_add_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 40px; max-width: 50px;")
        self._knowledge_add_btn.clicked.connect(self._on_knowledge_add_document)
        add_layout.addWidget(self._knowledge_add_btn)
        
        layout.addLayout(add_layout)

        # 搜索+筛选+排序行（合并为一行）
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self._knowledge_search_input = QLineEdit()
        self._knowledge_search_input.setPlaceholderText(tr("搜索..."))
        self._knowledge_search_input.returnPressed.connect(self._on_knowledge_search)
        search_layout.addWidget(self._knowledge_search_input, stretch=1)
        
        search_btn = QPushButton(tr("搜索"))
        search_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 40px; max-width: 50px;")
        search_btn.clicked.connect(self._on_knowledge_search)
        search_layout.addWidget(search_btn)
        
        # 筛选器
        self._knowledge_filter_combo = QComboBox()
        self._knowledge_filter_combo.addItems([tr("全部"), "PDF", "DOCX", "TXT", tr("图片"), tr("网页"), tr("其他")])
        self._knowledge_filter_combo.setFixedWidth(60)
        self._knowledge_filter_combo.currentTextChanged.connect(self._on_knowledge_filter_changed)
        search_layout.addWidget(self._knowledge_filter_combo)
        
        # 排序器
        self._knowledge_sort_combo = QComboBox()
        self._knowledge_sort_combo.addItems([
            tr("时间↓"), tr("时间↑"), tr("名称↓"), tr("名称↑"), tr("大小↓"), tr("大小↑")
        ])
        self._knowledge_sort_combo.setFixedWidth(60)
        self._knowledge_sort_combo.currentTextChanged.connect(self._on_knowledge_filter_changed)
        search_layout.addWidget(self._knowledge_sort_combo)
        
        layout.addLayout(search_layout)

        # 搜索结果区域（可折叠）
        self._knowledge_search_result = QLabel("")
        self._knowledge_search_result.setWordWrap(True)
        self._knowledge_search_result.setStyleSheet("font-size: 11px; background: rgba(0,0,0,0.05); padding: 4px; border-radius: 4px;")
        self._knowledge_search_result.setVisible(False)
        self._knowledge_search_result.setMaximumHeight(80)
        layout.addWidget(self._knowledge_search_result)

        # 文档列表滚动区域
        self._knowledge_scroll = QScrollArea()
        self._knowledge_scroll.setWidgetResizable(True)
        self._knowledge_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._knowledge_list_widget = QWidget()
        self._knowledge_list_layout = QVBoxLayout(self._knowledge_list_widget)
        self._knowledge_list_layout.setContentsMargins(0, 0, 0, 0)
        self._knowledge_list_layout.setSpacing(4)

        self._knowledge_scroll.setWidget(self._knowledge_list_widget)
        layout.addWidget(self._knowledge_scroll, stretch=1)

        # 空状态提示
        self._knowledge_empty_label = QLabel(
            tr("📭 知识库为空\n\n添加文档到知识库，\n支持PDF、DOCX、图片、网页。")
        )
        self._knowledge_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._knowledge_empty_label.setStyleSheet("color: gray; font-size: 11px; padding: 15px;")
        self._knowledge_empty_label.setWordWrap(True)
        self._knowledge_list_layout.addWidget(self._knowledge_empty_label)
        self._knowledge_list_layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        refresh_btn = QPushButton(tr("刷新"))
        refresh_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 45px; max-width: 55px;")
        refresh_btn.clicked.connect(self._on_refresh_knowledge)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 保存所有文档用于筛选排序
        self._knowledge_all_docs: list = []

        return widget

    def _create_history_tab(self) -> QWidget:
        """创建历史对话TAB页面（完整功能）。"""
        from datetime import datetime
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题行
        header_layout = QHBoxLayout()
        title_label = QLabel(tr("📋 历史对话"))
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title_label)
        
        # 会话数量
        self._history_count_label = QLabel("0 " + tr("个会话"))
        self._history_count_label.setStyleSheet("color: gray; font-size: 11px;")
        header_layout.addWidget(self._history_count_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 搜索行
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self._history_search_input = QLineEdit()
        self._history_search_input.setPlaceholderText(tr("搜索对话..."))
        self._history_search_input.textChanged.connect(self._on_history_filter_changed)
        search_layout.addWidget(self._history_search_input, stretch=1)
        
        # 排序器
        self._history_sort_combo = QComboBox()
        self._history_sort_combo.addItems([tr("时间↓"), tr("时间↑"), tr("消息数↓"), tr("消息数↑")])
        self._history_sort_combo.setFixedWidth(70)
        self._history_sort_combo.currentTextChanged.connect(self._on_history_filter_changed)
        search_layout.addWidget(self._history_sort_combo)
        
        layout.addLayout(search_layout)

        # 会话列表滚动区域
        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._history_list_widget = QWidget()
        self._history_list_layout = QVBoxLayout(self._history_list_widget)
        self._history_list_layout.setContentsMargins(0, 0, 0, 0)
        self._history_list_layout.setSpacing(4)

        self._history_scroll.setWidget(self._history_list_widget)
        layout.addWidget(self._history_scroll, stretch=1)

        # 空状态提示
        self._history_empty_label = QLabel(
            tr("📭 暂无历史对话\n\n开始新的对话后，\n会自动保存在这里。")
        )
        self._history_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._history_empty_label.setStyleSheet("color: gray; font-size: 11px; padding: 15px;")
        self._history_empty_label.setWordWrap(True)
        self._history_list_layout.addWidget(self._history_empty_label)
        self._history_list_layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        refresh_btn = QPushButton(tr("刷新"))
        refresh_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 45px; max-width: 55px;")
        refresh_btn.clicked.connect(self._on_refresh_history)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 保存所有会话用于筛选排序
        self._history_all_sessions: list = []

        return widget

    def _setup_status_bar(self) -> None:
        """设置状态栏（P2-12 增强版）。"""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        # 左侧：模型名
        self._status_model = QLabel(tr("模型") + ": " + tr("未选择"))
        self._status_bar.addWidget(self._status_model)

        # 当前会话（模型右侧）
        self._status_session = QLabel(tr("会话") + ": " + tr("新会话"))
        self._status_session.setStyleSheet("margin-left: 16px;")
        self._status_bar.addWidget(self._status_session)

        # 中间：Token 简报
        self._status_tokens = QLabel("")
        self._status_tokens.setStyleSheet("margin-left: 16px;")
        self._status_bar.addWidget(self._status_tokens)

        # 定时任务概览（活跃任务数量和最近任务）
        self._status_cron_overview = QLabel("")
        self._status_cron_overview.setStyleSheet("margin-left: 16px; color: #666;")
        self._status_bar.addWidget(self._status_cron_overview)

        # PWA 连接状态（活跃任务右侧）
        self._status_pwa = QLabel("")
        self._status_pwa.setStyleSheet("margin-left: 16px; color: #888;")
        self._status_bar.addWidget(self._status_pwa)

        # 定时任务执行状态（执行中/完成/失败）
        self._status_cron = QLabel("")
        self._status_cron.setStyleSheet("margin-left: 16px; padding: 2px 8px; border-radius: 4px;")
        self._status_cron.setMinimumWidth(50)  # 确保有最小宽度
        self._status_bar.addWidget(self._status_cron)

        # 右侧：连接状态
        self._status_connection = QLabel("● " + tr("未连接"))
        self._status_connection.setStyleSheet("color: #888;")
        self._status_bar.addPermanentWidget(self._status_connection)
        
        # 启动定时任务概览刷新定时器（每60秒刷新一次）
        self._cron_overview_timer = QTimer(self)
        self._cron_overview_timer.timeout.connect(self._refresh_cron_overview)
        self._cron_overview_timer.start(60000)  # 60秒
        # 初始刷新
        QTimer.singleShot(1000, self._refresh_cron_overview)
        
        # 启动 PWA 连接状态刷新定时器（每5秒刷新一次）
        self._pwa_status_timer = QTimer(self)
        self._pwa_status_timer.timeout.connect(self._refresh_pwa_status)
        self._pwa_status_timer.start(5000)  # 5秒
        # 初始刷新
        QTimer.singleShot(2000, self._refresh_pwa_status)
    
    def _refresh_cron_overview(self) -> None:
        """刷新定时任务概览信息。"""
        try:
            # 从工具注册表获取 CronTool
            if self._tool_registry:
                cron_tool = self._tool_registry.get_tool("cron")
                if cron_tool and hasattr(cron_tool, 'storage'):
                    jobs = cron_tool.storage.get_all_jobs()
                    active_jobs = [j for j in jobs if j.status.value == "active"]
                    count = len(active_jobs)
                    
                    if count == 0:
                        self._status_cron_overview.setText("")
                        return
                    
                    # 获取最近即将执行的任务
                    from datetime import datetime
                    now = datetime.now()
                    upcoming = None
                    upcoming_name = ""
                    
                    for job in active_jobs:
                        # 尝试从 trigger_config 获取下次执行时间
                        next_run = None
                        if hasattr(job, 'trigger_config') and job.trigger_config:
                            trigger_type = job.trigger_config.get('type', '')
                            if trigger_type == 'once' and 'run_date' in job.trigger_config:
                                try:
                                    next_run = datetime.fromisoformat(job.trigger_config['run_date'])
                                except:
                                    pass
                        
                        if next_run and next_run > now:
                            if upcoming is None or next_run < upcoming:
                                upcoming = next_run
                                upcoming_name = job.description or job.job_id
                    
                    if upcoming:
                        time_str = upcoming.strftime("%H:%M")
                        self._status_cron_overview.setText(
                            f"📅 {count}个任务 | 下次: {time_str} {upcoming_name[:12]}"
                        )
                    else:
                        self._status_cron_overview.setText(f"📅 {count}个活跃任务")
        except Exception as e:
            logger.debug(f"刷新定时任务概览失败: {e}")
    
    def _refresh_pwa_status(self) -> None:
        """刷新 PWA 连接状态显示。"""
        try:
            if not self._remote_bridge:
                return
            
            # 从 Bridge 统计中获取 PWA 连接信息
            stats = self._remote_bridge.stats
            connections = []
            
            # 将 PWAConnection 转换为字典
            for conn in stats.pwa_connections:
                connections.append({
                    "user_id": conn.user_id,
                    "username": conn.username,
                    "session_id": conn.session_id,
                    "connected_at": conn.connected_at,
                    "last_request_at": conn.last_request_at,
                    "request_count": conn.request_count
                })
            
            # 更新 UI
            self.update_pwa_status(connections)
            
        except Exception as e:
            logger.debug(f"刷新 PWA 状态失败: {e}")
    
    def update_cron_status(self, status: str, job_description: str = "") -> None:
        """更新定时任务状态显示。
        
        Args:
            status: 状态类型 (idle/running/success/error)
            job_description: 任务描述
        """
        if status == "idle" or not job_description:
            self._status_cron.setText("")
            self._status_cron.setStyleSheet("margin-left: 16px; padding: 2px 8px; border-radius: 4px;")
        elif status == "running":
            self._status_cron.setText(f"⏰ {job_description[:25]}...")
            # 橙色背景更醒目
            self._status_cron.setStyleSheet(
                "margin-left: 16px; padding: 2px 8px; border-radius: 4px; "
                "color: white; background-color: #FF9800; font-weight: bold;"
            )
        elif status == "success":
            self._status_cron.setText(f"✓ {job_description[:25]}")
            self._status_cron.setStyleSheet(
                "margin-left: 16px; padding: 2px 8px; border-radius: 4px; "
                "color: white; background-color: #4CAF50;"
            )
        elif status == "error":
            self._status_cron.setText(f"✗ {job_description[:25]}")
            self._status_cron.setStyleSheet(
                "margin-left: 16px; padding: 2px 8px; border-radius: 4px; "
                "color: white; background-color: #F44336;"
            )

    def _setup_shortcuts(self) -> None:
        """设置快捷键。"""
        # Ctrl+L 清空
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self._on_clear_chat)


    def closeEvent(self, event: QCloseEvent) -> None:
        """拦截关闭事件 → 最小化到托盘。"""
        # 停止远程桥接
        self._stop_remote_bridge()
        
        if self._minimize_to_tray and not self._force_quit:
            event.ignore()
            self.hide()
            self.close_to_tray.emit()
        else:
            event.accept()

    def force_quit(self) -> None:
        """强制退出（不最小化到托盘）。"""
        self._force_quit = True
        self.close()

    # ===== 事件处理 =====

    def _copy_tool_status(self) -> None:
        """复制工具执行状态到剪贴板。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_tool_status') or self._tool_status is None:
            return
        if not hasattr(self, '_tool_log') or self._tool_log is None:
            return
        try:
            # 构建要复制的文本
            status_text = f"状态：{self._tool_status.text()}\n"
            log_text = self._tool_log.text()
            if log_text:
                status_text += f"日志:\n{log_text}"
            else:
                status_text += "日志：(无)"
    
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(status_text)
    
            # 反馈复制成功
            self.statusBar().showMessage("已复制工具执行状态到剪贴板", 3000)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def _on_workflow_copy(self) -> None:
        """工作流复制成功时的回调。"""
        self.statusBar().showMessage("已复制工作流信息到剪贴板", 3000)

    def update_pwa_status(self, connections: list) -> None:
        """更新 PWA 连接状态显示（状态栏）。"""
        try:
            count = len(connections)
            
            if count == 0:
                status_text = "📱 PWA: 无连接"
            else:
                # 简化的状态栏显示：显示连接数和用户
                usernames = [conn.get("username", conn.get("user_id", "?")[:6]) for conn in connections[:3]]
                if count <= 3:
                    user_str = " ".join(f"@{u}" for u in usernames)
                else:
                    user_str = " ".join(f"@{u}" for u in usernames) + f" +{count - 3}"
                status_text = f"📱 PWA: {count}用户 {user_str}"
            
            if hasattr(self, '_status_pwa') and self._status_pwa is not None:
                self._status_pwa.setText(status_text)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def _toggle_input_expand(self) -> None:
        """切换输入框展开/收起状态。"""
        current_height = self._input_edit.height()
        if current_height < 100:
            # 展开到最大高度
            self._input_edit.setFixedHeight(120)
            self._expand_input_btn.setText("收起")
            self._expand_input_btn.setToolTip("收起输入框")
        else:
            # 收起到最小高度
            self._input_edit.setFixedHeight(30)
            self._expand_input_btn.setText("展开")
            self._expand_input_btn.setToolTip("展开输入框")

    def _on_copy_input(self) -> None:
        """复制输入框内容到剪贴板。"""
        text = self._input_edit.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.statusBar().showMessage("已复制输入框内容", 2000)

    def _on_paste_input(self) -> None:
        """粘贴剪贴板内容到输入框。"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            # 在当前光标位置插入文本
            cursor = self._input_edit.textCursor()
            cursor.insertText(text)
            self.statusBar().showMessage("已粘贴内容", 2000)

    def _on_clear_input(self) -> None:
        """清空输入框。"""
        text = self._input_edit.toPlainText()
        if text:
            self._input_edit.clear()
            self.statusBar().showMessage("已清空输入框", 2000)

    def _on_send(self) -> None:
        """发送消息。"""
        text = self._input_edit.toPlainText().strip()
        if not text:
            return

        # 添加到聊天显示
        self._chat_widget.add_user_message(text)

        # 清空输入框
        self._input_edit.clear()

        # 检查是否为命令
        if text.startswith("/"):
            # 异步执行命令
            asyncio.create_task(self._execute_command(text))
            return

        # 获取附件列表
        attachments = self._attachment_manager.attachments

        # 发出信号（包含附件信息）
        if attachments:
            self.message_with_attachments.emit(text, attachments)
            # 清空附件
            self._attachment_manager.clear()
        else:
            self.message_sent.emit(text)

        # 显示思考中状态
        self._set_thinking_state(True)

    async def _execute_command(self, text: str) -> None:
        """执行快捷命令。"""
        # 显示思考中状态
        self._set_thinking_state(True)

        try:
            result = await self._cmd_handler.execute(text)

            # 移除思考状态
            self._set_thinking_state(False)

            # 显示命令执行结果
            if result.is_quit:
                self.close()
            elif result.success:
                self._chat_widget.add_ai_message(result.output)
            else:
                self._chat_widget.add_ai_message(f"❌ {result.output}")
        except Exception as e:
            self._set_thinking_state(False)
            self._chat_widget.add_ai_message(f"❌ 命令执行错误: {e}")

    def _on_stop(self) -> None:
        """停止生成。"""
        self.stop_requested.emit()

    def _on_show_commands_menu(self) -> None:
        """显示常用命令菜单"""
        # 获取命令数据
        commands_data = get_commands_data()

        # 创建菜单
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555;
                margin: 5px 0px;
            }
        """)

        # 遍历分类和子分组
        for category_key, category_value in commands_data.items():
            # 创建分类菜单（快捷命令 / 组合命令）
            category_menu = QMenu(category_value["name"], menu)
            category_menu.setIcon(QIcon(""))

            for subgroup_key, subgroup_value in category_value["subgroups"].items():
                # 创建子分组菜单
                subgroup_menu = QMenu(subgroup_value["name"], category_menu)

                for cmd in subgroup_value["commands"]:
                    # 创建命令项
                    action = QAction(cmd, subgroup_menu)
                    action.triggered.connect(lambda checked, c=cmd: self._on_command_selected(c))
                    subgroup_menu.addAction(action)

                category_menu.addMenu(subgroup_menu)

            menu.addMenu(category_menu)

        # 显示菜单（位于按钮下方）
        menu.exec(self._commands_btn.mapToGlobal(self._commands_btn.rect().bottomLeft()))

    def _on_show_quick_commands(self) -> None:
        """显示快捷命令对话框"""
        dialog = CommandsDialog(self, "快捷命令", get_commands_data()["快捷命令"])
        dialog.command_selected.connect(self._on_command_selected)
        dialog.exec()

    def _on_show_combo_commands(self) -> None:
        """显示组合命令对话框"""
        dialog = CommandsDialog(self, "组合命令", get_commands_data()["组合命令"])
        dialog.command_selected.connect(self._on_command_selected)
        dialog.exec()

    def _on_command_selected(self, command: str) -> None:
        """当用户选择一个命令时"""
        # 将命令填入输入框
        self._input_edit.setPlainText(command)
        # 聚焦到输入框
        self._input_edit.setFocus()

    def _on_attachment(self) -> None:
        """添加附件 - 打开多选文件对话框。"""
        file_filter = (
            "所有支持的文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.txt *.md *.csv *.log "
            "*.json *.xml *.yaml *.yml *.py *.js *.java *.cpp *.c *.html *.css);;"
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;"
            "文本文件 (*.txt *.md *.csv *.log *.json *.xml *.yaml *.yml);;"
            "代码文件 (*.py *.js *.java *.cpp *.c *.html *.css);;"
            "所有文件 (*.*)"
        )
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要添加的文件",
            "",
            file_filter
        )
        
        if file_paths:
            success, errors = self._attachment_manager.add_files(file_paths)
            if errors:
                # 显示错误信息
                self.add_tool_log(f"⚠️ 部分文件添加失败: {len(errors)} 个")
            if success > 0:
                self.add_tool_log(f"📎 已添加 {success} 个文件")
    
    def _on_attachment_removed(self, file_path: str) -> None:
        """附件被移除。"""
        self._attachment_manager.remove_file(file_path)
    
    def _on_attachments_clear(self) -> None:
        """清空所有附件。"""
        self._attachment_manager.clear()
    
    def _on_files_dropped(self, file_paths: List[str]) -> None:
        """文件被拖放到附件面板。"""
        success, errors = self._attachment_manager.add_files(file_paths)
        if success > 0:
            self.add_tool_log(f"📎 已添加 {success} 个文件")

    def _on_new_session(self) -> None:
        """新建会话。"""
        self._chat_widget.clear()
        self._session_info.setText("新会话")
        self._status_session.setText(tr("会话") + ": " + tr("新会话"))
        self.message_sent.emit("/new_session")

    def _on_copy_chat(self) -> None:
        """复制所有对话内容到剪贴板。"""
        from PySide6.QtWidgets import QApplication
        conversation_text = self._chat_widget.copy_all_conversation()
        if conversation_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(conversation_text)

    def _on_clear_chat(self) -> None:
        """清空对话。"""
        self._chat_widget.clear()

    def _on_settings(self) -> None:
        """打开设置。"""
        self.settings_requested.emit()

    def _on_about(self) -> None:
        """关于对话框。"""
        from src import __version__
        QMessageBox.about(
            self,
            "关于 WeClaw",
            f"<h2>WeClaw v{__version__}</h2>"
            "<p>你的 AI 桌面管家 - 38+ 工具 + 移动端远程控制</p>"
            "<p>基于 PySide6 + LiteLLM 构建</p>"
            "<hr>"
            "<p><b>功能特性:</b></p>"
            "<ul>"
            "<li>多模型支持 (OpenAI/DeepSeek/Claude/Gemini/智谱 GLM/Kimi/通义千问等)</li>"
            "<li>38+ 实用工具 (Shell/文件管理/截图/浏览器自动化/语音交互/OCR 等)</li>"
            "<li>工作流引擎 - 自动化复杂任务</li>"
            "<li>定时任务系统 - 计划任务管理</li>"
            "<li>MCP 协议扩展支持</li>"
            "<li>移动端 PWA 远程控制</li>"
            "<li>对话历史持久化</li>"
            "<li>主动陪伴智能系统</li>"
            "</ul>"
            "<hr>"
            "<p><b>版本:</b> v2.12.0 (2026-03-22)</p>"
            "<p><a href='https://github.com/wyg5208/weclaw'>GitHub 项目主页</a></p>"
        )

    def _on_model_changed(self, model_name: str) -> None:
        """模型切换。"""
        self._status_model.setText(f"模型: {model_name}")
        self.model_changed.emit(model_name)

    def _set_thinking_state(self, thinking: bool) -> None:
        """设置思考状态。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_send_btn') or self._send_btn is None:
            return
        if not hasattr(self, '_stop_btn') or self._stop_btn is None:
            return
        if not hasattr(self, '_input_edit') or self._input_edit is None:
            return
        if not hasattr(self, '_tool_status') or self._tool_status is None:
            return
            
        try:
            self._send_btn.setVisible(not thinking)
            self._stop_btn.setVisible(thinking)
            self._input_edit.setEnabled(not thinking)
            
            if thinking:
                self._tool_status.setText("思考中...")
            else:
                self._tool_status.setText("空闲")
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    # ===== 公共 API =====

    def add_ai_message(self, text: str) -> None:
        """添加 AI 消息。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_chat_widget') or self._chat_widget is None:
            return
        try:
            self._chat_widget.add_ai_message(text)
            self._set_thinking_state(False)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def append_ai_message(self, text: str) -> None:
        """追加 AI 消息（流式输出）。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_chat_widget') or self._chat_widget is None:
            return
        try:
            self._chat_widget.append_ai_message(text)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def start_reasoning(self) -> None:
        """开始显示思考过程。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_chat_widget') or self._chat_widget is None:
            return
        try:
            self._chat_widget.start_reasoning()
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def append_reasoning(self, text: str) -> None:
        """追加思考内容。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_chat_widget') or self._chat_widget is None:
            return
        try:
            self._chat_widget.append_reasoning(text)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def finish_reasoning(self) -> None:
        """完成思考过程。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_chat_widget') or self._chat_widget is None:
            return
        try:
            self._chat_widget.finish_reasoning()
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def set_models(self, models: list[str]) -> None:
        """设置可用模型列表。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_model_combo') or self._model_combo is None:
            return
        try:
            current = self._model_combo.currentText()
            self._model_combo.clear()
            self._model_combo.addItems(models)
                
            # 恢复之前的选择
            if current in models:
                self._model_combo.setCurrentText(current)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass
    
    def set_current_model(self, model: str) -> None:
        """设置当前模型。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_model_combo') or self._model_combo is None:
            return
        try:
            index = self._model_combo.findText(model)
            if index >= 0:
                self._model_combo.setCurrentIndex(index)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass
    
    def update_usage(self, input_tokens: int, output_tokens: int, cost: float) -> None:
        """更新用量显示（状态栏，拆分为输入和输出）。"""
        try:
            total = input_tokens + output_tokens
            if total > 0:
                if hasattr(self, '_status_tokens') and self._status_tokens is not None:
                    self._status_tokens.setText(f"输入: {input_tokens} 输出: {output_tokens} | ${cost:.4f}")
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def set_connection_status(self, connected: bool) -> None:
        """设置连接状态。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_status_connection') or self._status_connection is None:
            return
        try:
            if connected:
                self._status_connection.setText("● 已连接")
                self._status_connection.setStyleSheet("color: #28a745;")
            else:
                self._status_connection.setText("● 未连接")
                self._status_connection.setStyleSheet("color: #888;")
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def set_tool_status(self, status: str) -> None:
        """设置工具状态。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_tool_status') or self._tool_status is None:
            return
        try:
            self._tool_status.setText(status)
            # 控制进度条可见性
            is_busy = status not in ("空闲", "完成")
            if hasattr(self, '_tool_progress') and self._tool_progress is not None:
                self._tool_progress.setVisible(is_busy)
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def add_tool_log(self, entry: str) -> None:
        """追加一条工具执行日志。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_tool_log') or self._tool_log is None:
            return
        if not hasattr(self, '_tool_log_entries') or self._tool_log_entries is None:
            return
        if not hasattr(self, '_tool_log_scroll') or self._tool_log_scroll is None:
            return
            
        try:
            self._tool_log_entries.append(entry)
            # 只保留最近 10 条
            if len(self._tool_log_entries) > 10:
                self._tool_log_entries = self._tool_log_entries[-10:]
            self._tool_log.setText("\n".join(self._tool_log_entries))
            # 自动滚动到底部
            v_bar = self._tool_log_scroll.verticalScrollBar()
            if v_bar:
                v_bar.setValue(v_bar.maximum())
        except RuntimeError:
            # 组件已被销毁，忽略
            pass

    def clear_tool_log(self) -> None:
        """清空工具日志。"""
        # 检查组件是否仍然有效
        if not hasattr(self, '_tool_log_entries') or self._tool_log_entries is None:
            return
        if not hasattr(self, '_tool_log') or self._tool_log is None:
            return
        try:
            self._tool_log_entries.clear()
            self._tool_log.setText("")
        except RuntimeError:
            # 组件已被销毁，忽略
            pass
    
    def _on_voice_record(self) -> None:
        """处理录音按钮点击。"""
        if not self._is_recording:
            # 开始录音
            self._is_recording = True
            self._voice_btn.setText("🔴 录音中...")
            self._voice_btn.setStyleSheet("background-color: #ff4444; color: white;")
            self.voice_record_requested.emit()
        else:
            # 停止录音
            self._is_recording = False
            self._voice_btn.setText("🎤 录音")
            self._voice_btn.setStyleSheet("")
            self.voice_stop_requested.emit()
    
    def _on_tts_toggle(self, checked: bool) -> None:
        """处理 TTS 开关切换。"""
        self._tts_enabled = checked
        if checked:
            self._tts_btn.setText("🔊 TTS")
        else:
            self._tts_btn.setText("🔇 TTS")
        self.tts_toggle_requested.emit(checked)

    def _on_conversation_mode_changed(self, index: int) -> None:
        """处理对话模式切换。"""
        mode_map = {
            0: "off",
            1: "continuous",
            2: "wake_word",
        }
        mode = mode_map.get(index, "off")
        self._conversation_mode = mode

        # 调用ConversationManager设置模式
        if self._conversation_mgr:
            self._conversation_mgr.set_mode(mode)

        self._update_conversation_status()
        self.conversation_mode_changed.emit(mode)

    def _update_conversation_status(self) -> None:
        """更新对话模式状态显示。"""
        mode_texts = {
            "off": ("", False),
            "continuous": (tr("⚡ 持续对话中..."), True),
            "wake_word": (tr("🔔 等待唤醒词..."), True),
        }
        text, visible = mode_texts.get(self._conversation_mode, ("", False))
        self._conversation_status_label.setText(text)
        self._conversation_status_label.setVisible(visible)

        # 根据模式设置颜色
        color_map = {
            "off": "#888",
            "continuous": "#28a745",  # 绿色
            "wake_word": "#0078d4",  # 蓝色
        }
        color = color_map.get(self._conversation_mode, "#888")
        self._conversation_status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_conversation_state(self, state: str) -> None:
        """设置对话状态（供外部调用）。"""
        self._conversation_state = state
        self.conversation_state_changed.emit(state)

    def reset_voice_button(self) -> None:
        """重置录音按钮状态（录音完成后调用）。"""
        self._is_recording = False
        self._voice_btn.setText("🎤 录音")
        self._voice_btn.setStyleSheet("")
    
    def set_input_text(self, text: str) -> None:
        """设置输入框文字。"""
        self._input_edit.setPlainText(text)
        self._input_edit.setFocus()  # 聚焦到输入框
    
    @property
    def attachment_manager(self) -> AttachmentManager:
        """获取附件管理器。"""
        return self._attachment_manager
    
    @property
    def workflow_panel(self) -> WorkflowPanel | None:
        """获取工作流面板（暂时返回 None，等工作流功能启用时再恢复）。"""
        # return self._workflow_panel
        return None

    def _on_generated_space(self) -> None:
        """打开生成空间。"""
        self.generated_space_requested.emit()

    def _on_knowledge_rag(self) -> None:
        """打开知识库管理。"""
        self.knowledge_rag_requested.emit()

    def _on_cron_job(self) -> None:
        """打开定时任务管理。"""
        self.cron_job_requested.emit()
    
    def _on_workflow_records(self) -> None:
        """打开工作流记录查看器。"""
        # TODO: 实现工作流记录查看对话框
        QMessageBox.information(
            self,
            "📋 工作流记录",
            "工作流记录查看器开发中...\n\n功能规划：\n- 显示所有工作流执行历史\n- 按时间/状态筛选\n- 查看执行详情和日志\n- 导出记录报告"
        )
    
    # 意识流记录功能已移除
    # def _on_consciousness_records(self) -> None:
    #     """打开意识流记录查看器。"""
    #     QMessageBox.information(
    #         self,
    #         "🧠 意识流记录",
    #         "意识流记录查看器开发中..."
    #     )

    def _on_history(self) -> None:
        """打开历史对话。"""
        self.history_requested.emit()

    def update_generated_space_count(self, count: int) -> None:
        """更新生成空间TAB页面的文件数量显示。"""
        self._gen_space_count = count
        self._gen_space_count_label.setText(f"{count} " + tr("个文件"))
        if count > 0:
            self._gen_space_count_label.setStyleSheet("color: #0078d4; font-size: 12px; font-weight: bold;")
        else:
            self._gen_space_count_label.setStyleSheet("color: gray; font-size: 12px;")

    def set_session_info(self, text: str) -> None:
        """设置会话信息（同时更新底栏和隐藏的兼容标签）。"""
        self._session_info.setText(text)
        # 截断过长的标题
        display_text = text if len(text) <= 20 else text[:17] + "..."
        self._status_session.setText(tr("会话") + ": " + display_text)

    # ===== 生成空间TAB页面事件处理 =====

    def _on_open_generated_space_folder(self) -> None:
        """打开生成空间文件夹。"""
        self.generated_space_requested.emit()

    def _on_refresh_generated_space(self) -> None:
        """刷新生成空间TAB页面。"""
        self.generated_space_requested.emit()

    def _on_gen_filter_changed(self) -> None:
        """生成空间筛选或排序条件变化。"""
        self._refresh_gen_space_display()

    def _on_clear_generated_space(self) -> None:
        """清空生成空间记录。"""
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, '_gen_all_files') or not self._gen_all_files:
            QMessageBox.information(self, tr("提示"), tr("没有可清空的记录"))
            return
        
        reply = QMessageBox.question(
            self,
            tr("清空生成记录"),
            tr("确定清空所有生成文件记录？\n\n注意：仅清空追踪记录，不会删除实际文件。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 发出清空信号由gui_app处理
            self._gen_all_files = []
            self._refresh_gen_space_display()
            # 通知gui_app清空
            self.generated_space_clear_requested.emit()

    def _get_gen_file_category(self, file_info) -> str:
        """获取生成文件的类别。"""
        name = file_info.name.lower() if hasattr(file_info, 'name') else str(file_info).lower()
        ext = file_info.extension.lower() if hasattr(file_info, 'extension') and file_info.extension else ''
        
        doc_exts = ('.pdf', '.doc', '.docx', '.txt', '.md', '.rtf', '.ppt', '.pptx', '.xls', '.xlsx', '.csv')
        img_exts = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico')
        code_exts = ('.py', '.js', '.ts', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.java', '.c', '.cpp', '.go', '.rs')
        
        if ext in doc_exts or any(name.endswith(e) for e in doc_exts):
            return tr("文档")
        elif ext in img_exts or any(name.endswith(e) for e in img_exts):
            return tr("图片")
        elif ext in code_exts or any(name.endswith(e) for e in code_exts):
            return tr("代码")
        else:
            return tr("其他")

    def _apply_gen_filter_and_sort(self) -> list:
        """应用生成空间筛选和排序。"""
        if not hasattr(self, '_gen_all_files') or not self._gen_all_files:
            return []
        
        search_text = self._gen_search_input.text().strip().lower()
        filter_type = self._gen_filter_combo.currentText()
        sort_type = self._gen_sort_combo.currentText()
        
        # 筛选
        filtered = []
        for f in self._gen_all_files:
            name = f.name.lower() if hasattr(f, 'name') else str(f).lower()
            if search_text and search_text not in name:
                continue
            
            if filter_type != tr("全部"):
                category = self._get_gen_file_category(f)
                if category != filter_type:
                    continue
            
            filtered.append(f)
        
        # 排序
        if sort_type == tr("时间↓"):
            filtered.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') and x.created_at else "", reverse=True)
        elif sort_type == tr("时间↑"):
            filtered.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') and x.created_at else "")
        elif sort_type == tr("名称↓"):
            filtered.sort(key=lambda x: x.name.lower() if hasattr(x, 'name') else "", reverse=True)
        elif sort_type == tr("名称↑"):
            filtered.sort(key=lambda x: x.name.lower() if hasattr(x, 'name') else "")
        elif sort_type == tr("大小↓"):
            filtered.sort(key=lambda x: x.size if hasattr(x, 'size') else 0, reverse=True)
        elif sort_type == tr("大小↑"):
            filtered.sort(key=lambda x: x.size if hasattr(x, 'size') else 0)
        
        return filtered

    def _refresh_gen_space_display(self) -> None:
        """刷新生成空间显示（应用筛选排序）。"""
        try:
            # 清空现有卡片
            items_to_remove = []
            for i in range(self._gen_space_list_layout.count()):
                item = self._gen_space_list_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget and widget != self._gen_space_empty_label:
                        items_to_remove.append(widget)
            
            for widget in items_to_remove:
                self._gen_space_list_layout.removeWidget(widget)
                widget.deleteLater()
            
            # 应用筛选和排序
            filtered_files = self._apply_gen_filter_and_sort()
            
            if not filtered_files:
                self._gen_space_empty_label.show()
                total_count = len(self._gen_all_files) if hasattr(self, '_gen_all_files') else 0
                if total_count > 0:
                    self._gen_space_count_label.setText(f"0 / {total_count} " + tr("个文件"))
                else:
                    self._gen_space_count_label.setText(tr("0 个文件"))
                return
            
            self._gen_space_empty_label.hide()
            total_count = len(self._gen_all_files) if hasattr(self, '_gen_all_files') else 0
            if len(filtered_files) < total_count:
                self._gen_space_count_label.setText(f"{len(filtered_files)} / {total_count} " + tr("个文件"))
            else:
                self._gen_space_count_label.setText(f"{len(filtered_files)} " + tr("个文件"))
            
            # 添加文件卡片（最多显示20个）
            for file_info in filtered_files[:20]:
                try:
                    card = self._create_file_card(file_info)
                    self._gen_space_list_layout.insertWidget(self._gen_space_list_layout.count() - 1, card)
                except Exception as e:
                    logger.warning(f"创建文件卡片失败: {e}")
                    
        except Exception as e:
            logger.error(f"刷新生成空间显示失败: {e}")

    def update_generated_space_files(self, files: list) -> None:
        """更新生成空间TAB页面的文件列表。"""
        try:
            # 保存所有文件用于筛选排序
            self._gen_all_files = list(files) if files else []
            # 刷新显示
            self._refresh_gen_space_display()
        except Exception as e:
            logger.error(f"更新生成空间文件列表失败: {e}")
            self._gen_space_empty_label.show()
            self._gen_space_count_label.setText(tr("加载失败"))

    def _create_file_card(self, file_info) -> QWidget:
        """创建文件卡片组件（含打开和删除按钮）。"""
        from PySide6.QtGui import QFont, QCursor

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        card.setObjectName("fileCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # 图标
        icon_label = QLabel(file_info.get_icon() if hasattr(file_info, 'get_icon') else "📄")
        icon_label.setFont(QFont("", 14))
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 文件信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)

        name_label = QLabel(file_info.name if hasattr(file_info, 'name') else str(file_info))
        name_label.setFont(QFont("", 9))
        name_label.setWordWrap(True)
        name_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if hasattr(file_info, 'path'):
            name_label.mousePressEvent = lambda event, p=file_info.path: self._open_file_path(p)
            name_label.setToolTip(tr("点击打开: ") + file_info.path)
        info_layout.addWidget(name_label)

        # 详细信息
        size_str = file_info.size_display() if hasattr(file_info, 'size_display') else ""
        detail_label = QLabel(size_str)
        detail_label.setStyleSheet("font-size: 9px; color: #888;")
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, stretch=1)

        # 打开按钮
        open_btn = QPushButton(tr("打开"))
        open_btn.setToolTip(tr("打开文件"))
        open_btn.setStyleSheet("font-size: 11px; padding: 3px 6px; min-width: 38px; max-width: 45px;")
        open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if hasattr(file_info, 'path'):
            open_btn.clicked.connect(lambda checked, p=file_info.path: self._open_file_path(p))
        layout.addWidget(open_btn)

        # 删除按钮
        delete_btn = QPushButton(tr("删除"))
        delete_btn.setToolTip(tr("删除此记录"))
        delete_btn.setStyleSheet("font-size: 11px; padding: 3px 6px; min-width: 38px; max-width: 45px;")
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if hasattr(file_info, 'path'):
            delete_btn.clicked.connect(lambda checked, f=file_info: self._on_delete_gen_file(f))
        layout.addWidget(delete_btn)

        return card

    def _on_delete_gen_file(self, file_info) -> None:
        """删除单个生成文件记录。"""
        from PySide6.QtWidgets import QMessageBox
        
        name = file_info.name if hasattr(file_info, 'name') else str(file_info)
        reply = QMessageBox.question(
            self,
            tr("删除文件记录"),
            tr("确定删除此文件记录？\n") + f"{name}\n\n" + tr("注意：仅删除追踪记录，不会删除实际文件。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 从列表中移除
            if hasattr(self, '_gen_all_files') and file_info in self._gen_all_files:
                self._gen_all_files.remove(file_info)
                self._refresh_gen_space_display()
            # 通知gui_app删除
            if hasattr(file_info, 'path'):
                self.generated_space_file_delete_requested.emit(file_info.path)

    def _open_file_path(self, path: str) -> None:
        """打开文件路径。"""
        import subprocess
        import sys
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            logger.warning(f"打开文件失败: {e}")

    # ===== 知识库TAB页面事件处理 =====

    def _on_knowledge_add_type_changed(self, text: str) -> None:
        """添加类型变化。"""
        if text == tr("文件"):
            self._knowledge_path_input.setPlaceholderText(tr("选择文件..."))
            self._knowledge_browse_btn.setVisible(True)
        else:
            self._knowledge_path_input.setPlaceholderText(tr("输入网页URL..."))
            self._knowledge_browse_btn.setVisible(False)

    def _on_knowledge_browse(self) -> None:
        """浏览文件。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("选择文档"),
            "",
            tr("所有支持的文件") + " (*.pdf *.docx *.doc *.txt *.md *.json *.csv *.jpg *.jpeg *.png);;" +
            "PDF (*.pdf);;" +
            "Word (*.docx *.doc);;" +
            tr("文本文件") + " (*.txt *.md);;" +
            tr("所有文件") + " (*.*)",
        )
        if file_path:
            self._knowledge_path_input.setText(file_path)

    def _on_knowledge_add_document(self) -> None:
        """添加知识库文档。"""
        add_type = self._knowledge_add_type.currentText()
        path_or_url = self._knowledge_path_input.text().strip()
        
        if not path_or_url:
            QMessageBox.warning(self, tr("提示"), tr("请输入文件路径或网址"))
            return
        
        if add_type == tr("文件"):
            import os
            if not os.path.exists(path_or_url):
                QMessageBox.warning(self, tr("提示"), tr("文件不存在"))
                return
            # 发出添加文件信号
            self.knowledge_add_file_requested.emit(path_or_url)
        else:
            if not path_or_url.startswith(("http://", "https://")):
                QMessageBox.warning(self, tr("提示"), tr("请输入有效的URL（以 http:// 或 https:// 开头）"))
                return
            # 发出添加URL信号
            self.knowledge_add_url_requested.emit(path_or_url)
        
        # 清空输入
        self._knowledge_path_input.clear()

    def _on_knowledge_search(self) -> None:
        """搜索知识库。"""
        query = self._knowledge_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, tr("提示"), tr("请输入搜索内容"))
            return
        # 发出搜索信号
        self.knowledge_search_requested.emit(query)

    def _on_knowledge_filter_changed(self) -> None:
        """知识库筛选或排序条件变化。"""
        self._refresh_knowledge_display()

    def _on_refresh_knowledge(self) -> None:
        """刷新知识库TAB页面。"""
        self.knowledge_rag_requested.emit()

    def _get_knowledge_doc_category(self, doc_info: dict) -> str:
        """获取知识库文档的类别。"""
        file_type = doc_info.get("file_type", "")
        
        if file_type == "pdf":
            return "PDF"
        elif file_type in ("docx", "doc"):
            return "DOCX"
        elif file_type in ("txt", "md", "text", "markdown"):
            return "TXT"
        elif file_type in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "image"):
            return tr("图片")
        elif file_type == "url":
            return tr("网页")
        else:
            return tr("其他")

    def _apply_knowledge_filter_and_sort(self) -> list:
        """应用知识库筛选和排序。"""
        if not hasattr(self, '_knowledge_all_docs') or not self._knowledge_all_docs:
            return []
        
        filter_type = self._knowledge_filter_combo.currentText()
        sort_type = self._knowledge_sort_combo.currentText()
        
        # 筛选
        filtered = []
        for doc in self._knowledge_all_docs:
            if filter_type == tr("全部"):
                filtered.append(doc)
            else:
                category = self._get_knowledge_doc_category(doc)
                if category == filter_type:
                    filtered.append(doc)
        
        # 排序
        if sort_type == tr("时间↓"):
            filtered.sort(key=lambda x: x.get("indexed_at", ""), reverse=True)
        elif sort_type == tr("时间↑"):
            filtered.sort(key=lambda x: x.get("indexed_at", ""))
        elif sort_type == tr("名称↓"):
            filtered.sort(key=lambda x: x.get("filename", "").lower(), reverse=True)
        elif sort_type == tr("名称↑"):
            filtered.sort(key=lambda x: x.get("filename", "").lower())
        elif sort_type == tr("大小↓"):
            filtered.sort(key=lambda x: x.get("size", 0), reverse=True)
        elif sort_type == tr("大小↑"):
            filtered.sort(key=lambda x: x.get("size", 0))
        
        return filtered

    def _refresh_knowledge_display(self) -> None:
        """刷新知识库显示（应用筛选排序）。"""
        try:
            # 清空现有卡片
            items_to_remove = []
            for i in range(self._knowledge_list_layout.count()):
                item = self._knowledge_list_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget and widget != self._knowledge_empty_label:
                        items_to_remove.append(widget)
            
            for widget in items_to_remove:
                self._knowledge_list_layout.removeWidget(widget)
                widget.deleteLater()
            
            # 应用筛选和排序
            filtered_docs = self._apply_knowledge_filter_and_sort()
            
            if not filtered_docs:
                self._knowledge_empty_label.show()
                total_count = len(self._knowledge_all_docs) if hasattr(self, '_knowledge_all_docs') else 0
                if total_count > 0:
                    self._knowledge_count_label.setText(f"0 / {total_count} " + tr("个文档"))
                else:
                    self._knowledge_count_label.setText(tr("0 个文档"))
                return
            
            self._knowledge_empty_label.hide()
            total_count = len(self._knowledge_all_docs) if hasattr(self, '_knowledge_all_docs') else 0
            if len(filtered_docs) < total_count:
                self._knowledge_count_label.setText(f"{len(filtered_docs)} / {total_count} " + tr("个文档"))
            else:
                self._knowledge_count_label.setText(f"{len(filtered_docs)} " + tr("个文档"))
            
            # 添加文档卡片（最多显示20个）
            for doc_info in filtered_docs[:20]:
                try:
                    card = self._create_doc_card(doc_info)
                    self._knowledge_list_layout.insertWidget(self._knowledge_list_layout.count() - 1, card)
                except Exception as e:
                    logger.warning(f"创建文档卡片失败: {e}")
                    
        except Exception as e:
            logger.error(f"刷新知识库显示失败: {e}")

    def update_knowledge_search_result(self, result: str) -> None:
        """更新知识库搜索结果。"""
        if result:
            self._knowledge_search_result.setText(result)
            self._knowledge_search_result.setVisible(True)
        else:
            self._knowledge_search_result.setVisible(False)

    def update_knowledge_progress(self, visible: bool, value: int = 0, text: str = "") -> None:
        """更新知识库添加进度。"""
        self._knowledge_progress.setVisible(visible)
        if visible:
            self._knowledge_progress.setValue(value)
            if text:
                self._knowledge_progress.setFormat(text)

    def update_knowledge_documents(self, docs: list) -> None:
        """更新知识库TAB页面的文档列表。"""
        try:
            # 保存所有文档用于筛选排序
            self._knowledge_all_docs = list(docs) if docs else []
            # 刷新显示
            self._refresh_knowledge_display()
        except Exception as e:
            logger.error(f"更新知识库文档列表失败: {e}")
            self._knowledge_empty_label.show()
            self._knowledge_count_label.setText(tr("加载失败"))

    def _create_doc_card(self, doc_info: dict) -> QWidget:
        """创建文档卡片组件（含查看和删除按钮）。"""
        from PySide6.QtGui import QFont, QCursor

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        card.setObjectName("documentCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # 图标
        file_type = doc_info.get("file_type", "unknown")
        icon_map = {
            "pdf": "📕", "docx": "📘", "doc": "📘", "url": "🌐",
            "image": "🖼️", "text": "📄", "txt": "📄", "md": "📄",
            "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "gif": "🖼️",
        }
        icon_label = QLabel(icon_map.get(file_type, "📄"))
        icon_label.setFont(QFont("", 14))
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 文档信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)

        filename = doc_info.get("filename", tr("未知"))
        name_label = QLabel(filename)
        name_label.setFont(QFont("", 9))
        name_label.setWordWrap(True)
        name_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        name_label.setToolTip(doc_info.get("source_path", filename))
        name_label.mousePressEvent = lambda event, d=doc_info: self._on_view_knowledge_doc(d)
        info_layout.addWidget(name_label)

        # 详细信息
        size = doc_info.get("size", 0)
        size_kb = size / 1024 if size else 0
        chunks = doc_info.get("chunk_count", 0)
        detail_text = f"{file_type.upper()} · {size_kb:.0f}KB · {chunks}" + tr("段")
        detail_label = QLabel(detail_text)
        detail_label.setStyleSheet("font-size: 9px; color: #888;")
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, stretch=1)

        # 查看按钮
        view_btn = QPushButton(tr("查看"))
        view_btn.setToolTip(tr("查看详情"))
        view_btn.setStyleSheet("font-size: 11px; padding: 3px 6px; min-width: 38px; max-width: 45px;")
        view_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        view_btn.clicked.connect(lambda checked, d=doc_info: self._on_view_knowledge_doc(d))
        layout.addWidget(view_btn)

        # 删除按钮
        delete_btn = QPushButton(tr("删除"))
        delete_btn.setToolTip(tr("从知识库删除"))
        delete_btn.setStyleSheet("font-size: 11px; padding: 3px 6px; min-width: 38px; max-width: 45px;")
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        doc_id = doc_info.get("id")
        if doc_id is not None:
            delete_btn.clicked.connect(lambda checked, did=doc_id: self._on_delete_knowledge_doc(did))
        layout.addWidget(delete_btn)

        return card

    def _on_view_knowledge_doc(self, doc_info: dict) -> None:
        """查看知识库文档详情。"""
        try:
            from .document_detail_dialog import DocumentDetailDialog
            dlg = DocumentDetailDialog(doc_info, self)
            dlg.exec()
        except Exception as e:
            logger.warning(f"查看文档详情失败: {e}")
            QMessageBox.information(
                self,
                tr("文档信息"),
                f"{tr('文件名')}: {doc_info.get('filename', tr('未知'))}\n"
                f"{tr('类型')}: {doc_info.get('file_type', tr('未知'))}\n"
                f"{tr('片段数')}: {doc_info.get('chunk_count', 0)}"
            )

    def _on_delete_knowledge_doc(self, doc_id: int) -> None:
        """删除知识库文档。"""
        reply = QMessageBox.question(
            self,
            tr("确认删除"),
            tr("确定要从知识库中删除此文档吗？"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 发出删除信号
            self.knowledge_doc_delete_requested.emit(doc_id)

    def switch_to_tools_tab(self) -> None:
        """切换到工具状态TAB。"""
        self._right_tab_widget.setCurrentIndex(0)

    def switch_to_generated_space_tab(self) -> None:
        """切换到生成空间TAB。"""
        self._right_tab_widget.setCurrentIndex(1)

    def switch_to_knowledge_tab(self) -> None:
        """切换到知识库TAB。"""
        self._right_tab_widget.setCurrentIndex(2)

    def switch_to_history_tab(self) -> None:
        """切换到历史对话TAB。"""
        self._right_tab_widget.setCurrentIndex(3)

    # ============ 历史对话TAB相关方法 ============

    def _on_history_filter_changed(self) -> None:
        """历史对话筛选或排序条件变化。"""
        self._refresh_history_display()

    def _on_refresh_history(self) -> None:
        """刷新历史对话TAB页面。"""
        self.history_refresh_requested.emit()

    def _apply_history_filter_and_sort(self) -> list:
        """应用历史对话筛选和排序。"""
        if not hasattr(self, '_history_all_sessions') or not self._history_all_sessions:
            return []
        
        search_text = self._history_search_input.text().strip().lower()
        sort_type = self._history_sort_combo.currentText()
        
        # 搜索过滤
        filtered = []
        for session in self._history_all_sessions:
            if search_text:
                title = session.get("title", "").lower()
                if search_text in title:
                    filtered.append(session)
            else:
                filtered.append(session)
        
        # 排序
        if sort_type == tr("时间↓"):
            filtered.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_type == tr("时间↑"):
            filtered.sort(key=lambda x: x.get("updated_at", ""))
        elif sort_type == tr("消息数↓"):
            filtered.sort(key=lambda x: x.get("message_count", 0), reverse=True)
        elif sort_type == tr("消息数↑"):
            filtered.sort(key=lambda x: x.get("message_count", 0))
        
        return filtered

    def _refresh_history_display(self) -> None:
        """根据当前筛选排序条件刷新历史对话显示。"""
        try:
            # 清空现有卡片（保留空状态标签）
            items_to_remove = []
            for i in range(self._history_list_layout.count()):
                item = self._history_list_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget and widget != self._history_empty_label:
                        items_to_remove.append(widget)
            
            for widget in items_to_remove:
                self._history_list_layout.removeWidget(widget)
                widget.deleteLater()
            
            # 应用筛选排序
            filtered_sessions = self._apply_history_filter_and_sort()
            
            # 重新添加卡片
            if not filtered_sessions:
                self._history_empty_label.show()
                total_count = len(self._history_all_sessions) if hasattr(self, '_history_all_sessions') else 0
                if total_count > 0:
                    self._history_count_label.setText(f"0 / {total_count} " + tr("个会话"))
                else:
                    self._history_count_label.setText(tr("0 个会话"))
                return
            
            self._history_empty_label.hide()
            total_count = len(self._history_all_sessions) if hasattr(self, '_history_all_sessions') else 0
            if len(filtered_sessions) < total_count:
                self._history_count_label.setText(f"{len(filtered_sessions)} / {total_count} " + tr("个会话"))
            else:
                self._history_count_label.setText(f"{len(filtered_sessions)} " + tr("个会话"))
            
            # 添加会话卡片（最多显示50个）
            for session_info in filtered_sessions[:50]:
                try:
                    card = self._create_session_card(session_info)
                    self._history_list_layout.insertWidget(self._history_list_layout.count() - 1, card)
                except Exception as e:
                    logger.warning(f"创建会话卡片失败: {e}")
                    
        except Exception as e:
            logger.error(f"刷新历史对话显示失败: {e}")

    def update_history_sessions(self, sessions: list) -> None:
        """更新历史对话TAB页面的会话列表。"""
        try:
            # 保存所有会话用于筛选排序
            self._history_all_sessions = list(sessions) if sessions else []
            # 刷新显示
            self._refresh_history_display()
        except Exception as e:
            logger.error(f"更新历史会话列表失败: {e}")
            self._history_empty_label.show()
            self._history_count_label.setText(tr("加载失败"))

    def _create_session_card(self, session_info: dict) -> QWidget:
        """创建会话卡片组件（含打开和删除按钮）。"""
        from PySide6.QtGui import QFont, QCursor
        from datetime import datetime

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        card.setObjectName("sessionCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # 图标
        icon_label = QLabel("💬")
        icon_label.setFont(QFont("", 14))
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 会话信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)

        title = session_info.get("title", tr("未命名对话"))
        name_label = QLabel(title)
        name_label.setFont(QFont("", 9))
        name_label.setWordWrap(True)
        name_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        session_id = session_info.get("id", "")
        name_label.mousePressEvent = lambda event, sid=session_id: self._on_select_history_session(sid)
        info_layout.addWidget(name_label)

        # 详细信息：时间 + 消息数
        updated_at = session_info.get("updated_at", "")
        message_count = session_info.get("message_count", 0)
        time_str = ""
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = updated_at[:16] if len(updated_at) >= 16 else updated_at
        
        detail_text = f"{time_str} · {message_count}" + tr("条消息")
        detail_label = QLabel(detail_text)
        detail_label.setStyleSheet("font-size: 9px; color: #888;")
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, stretch=1)

        # 打开按钮
        open_btn = QPushButton(tr("打开"))
        open_btn.setToolTip(tr("恢复此对话"))
        open_btn.setStyleSheet("font-size: 11px; padding: 3px 6px; min-width: 38px; max-width: 45px;")
        open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_btn.clicked.connect(lambda checked, sid=session_id: self._on_select_history_session(sid))
        layout.addWidget(open_btn)

        # 删除按钮
        delete_btn = QPushButton(tr("删除"))
        delete_btn.setToolTip(tr("删除此对话"))
        delete_btn.setStyleSheet("font-size: 11px; padding: 3px 6px; min-width: 38px; max-width: 45px;")
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        delete_btn.clicked.connect(lambda checked, sid=session_id: self._on_delete_history_session(sid))
        layout.addWidget(delete_btn)

        return card

    def _on_select_history_session(self, session_id: str) -> None:
        """选择历史会话。"""
        if session_id:
            self.history_session_selected.emit(session_id)

    def _on_delete_history_session(self, session_id: str) -> None:
        """删除历史会话。"""
        reply = QMessageBox.question(
            self,
            tr("确认删除"),
            tr("确定要删除此历史对话吗？删除后无法恢复。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 发出删除信号
            self.history_session_delete_requested.emit(session_id)
            # 从本地列表中移除
            self._history_all_sessions = [
                s for s in self._history_all_sessions if s.get("id") != session_id
            ]
            # 刷新显示
            self._refresh_history_display()
