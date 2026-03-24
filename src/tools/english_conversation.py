"""英语口语对话练习工具 - 多主题场景英语口语练习系统。

提供完整的英语口语对话练习功能：
- 多种主题场景（餐厅、机场、酒店、购物、旅行等）
- 语音识别和语音合成集成
- AI 角色扮演对话
- 实时语音反馈
- 简单的语法和发音建议

依赖:
- VoiceInputTool: 语音识别 (GLM ASR/Whisper)
- VoiceOutputTool: 语音合成 (Edge-TTS/Qwen3-TTS)
- LLM: 对话内容生成
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


# ========== 主题场景配置 ==========

@dataclass
class TopicConfig:
    """主题场景配置。"""
    topic_id: str
    title_zh: str
    title_en: str
    ai_role: str
    scenario_zh: str
    scenario_en: str
    opening_line: str
    vocabulary: list[str]
    difficulty_suggestions: list[str] = field(default_factory=lambda: ["beginner", "intermediate", "advanced"])


# 预定义主题场景库
TOPIC_LIBRARY = {
    "restaurant": TopicConfig(
        topic_id="restaurant",
        title_zh="餐厅点餐",
        title_en="Restaurant Dining",
        ai_role="Waiter/Waitress",
        scenario_zh="您在餐厅用餐，服务员为您点餐。",
        scenario_en="You are dining at a restaurant. The waiter will take your order.",
        opening_line="Good evening! Welcome to our restaurant. Here's the menu. Are you ready to order, or would you like a few more minutes?",
        vocabulary=["menu", "order", "appetizer", "main course", "dessert", "bill", "water", "wine"],
    ),
    "airport": TopicConfig(
        topic_id="airport",
        title_zh="机场值机",
        title_en="Airport Check-in",
        ai_role="Check-in Agent",
        scenario_zh="您在机场办理登机手续。",
        scenario_en="You are at the airport checking in for your flight.",
        opening_line="Good morning! May I see your passport and ticket, please? Where are you flying to today?",
        vocabulary=["passport", "boarding pass", "luggage", "seat", "flight number", "gate", "departure"],
    ),
    "hotel": TopicConfig(
        topic_id="hotel",
        title_zh="酒店入住",
        title_en="Hotel Check-in",
        ai_role="Hotel Receptionist",
        scenario_zh="您在酒店办理入住手续。",
        scenario_en="You are checking into a hotel.",
        opening_line="Good afternoon! Welcome to our hotel. Do you have a reservation?",
        vocabulary=["reservation", "check-in", "room key", "breakfast", "elevator", "floor"],
    ),
    "shopping": TopicConfig(
        topic_id="shopping",
        title_zh="购物",
        title_en="Shopping",
        ai_role="Shop Assistant",
        scenario_zh="您在商店购物，店员为您提供帮助。",
        scenario_en="You are shopping at a store. The assistant will help you.",
        opening_line="Hello! How can I help you today? Are you looking for anything specific?",
        vocabulary=["size", "color", "try on", "price", "discount", "cashier", "fitting room"],
    ),
    "travel": TopicConfig(
        topic_id="travel",
        title_zh="旅行问路",
        title_en="Travel Directions",
        ai_role="Local Guide",
        scenario_zh="您在旅行中向当地人问路。",
        scenario_en="You are traveling and asking a local for directions.",
        opening_line="Hi there! Are you looking for something? I'd be happy to help you find your way.",
        vocabulary=["directions", "map", "station", "turn left", "turn right", "straight", "landmark"],
    ),
    "daily_chat": TopicConfig(
        topic_id="daily_chat",
        title_zh="日常聊天",
        title_en="Daily Conversation",
        ai_role="Friend",
        scenario_zh="与朋友进行日常英语聊天。",
        scenario_en="Having a casual English conversation with a friend.",
        opening_line="Hey! How's it going? Anything interesting happening lately?",
        vocabulary=["weekend", "hobbies", "work", "family", "movies", "music"],
    ),
    "business": TopicConfig(
        topic_id="business",
        title_zh="商务会议",
        title_en="Business Meeting",
        ai_role="Business Partner",
        scenario_zh="参加商务英语会议。",
        scenario_en="Participating in a business meeting.",
        opening_line="Good morning! Thank you for joining the meeting. Shall we start with the agenda?",
        vocabulary=["agenda", "proposal", "budget", "deadline", "presentation", "feedback"],
    ),
}


@dataclass
class ConversationSession:
    """对话会话数据类。"""
    session_id: str
    topic: str
    difficulty: str
    ai_role: str
    scenario_description: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    user_evaluations: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    total_turns: int = 0
    
    def add_message(self, role: str, content: str, metadata: Optional[dict] = None):
        """添加消息到对话历史。"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            message["metadata"] = metadata
        self.messages.append(message)
        self.last_active = datetime.now()
        self.total_turns += 1
    
    def get_context_messages(self, max_turns: int = 20) -> list[dict]:
        """获取上下文消息（保留最近 N 轮）。"""
        # 保留 system prompt + 最近的消息
        system_msg = next((m for m in self.messages if m["role"] == "system"), None)
        other_msgs = [m for m in self.messages if m["role"] != "system"]
        
        # 限制长度
        recent_msgs = other_msgs[-max_turns:] if len(other_msgs) > max_turns else other_msgs
        
        return ([system_msg] if system_msg else []) + recent_msgs


class EnglishConversationTool(BaseTool):
    """英语口语对话练习工具。"""
    
    name = "english_conversation"
    emoji = "🗣️"
    title = "英语口语对话练习"
    description = "多主题场景英语口语对话练习，支持语音识别和语音合成，随时随地练习口语"
    
    def __init__(self):
        super().__init__()
        self._sessions: dict[str, ConversationSession] = {}
        self._current_session_id: Optional[str] = None  # 当前活跃会话 ID
        self._voice_input = None
        self._voice_output = None
        self._dialog: Optional[Any] = None  # EnglishConversationDialog 实例
        self._image_generator = None
        logger.info("EnglishConversationTool 初始化完成")
    
    def _get_topic_config(self, topic: str) -> TopicConfig:
        """获取主题配置。"""
        if topic not in TOPIC_LIBRARY:
            raise ValueError(f"不支持的主题：{topic}。可用主题：{', '.join(TOPIC_LIBRARY.keys())}")
        return TOPIC_LIBRARY[topic]
    
    def _create_session(
        self,
        topic: str,
        difficulty: str,
        ai_role: str,
        scenario: str,
    ) -> ConversationSession:
        """创建新的对话会话。"""
        session_id = str(uuid.uuid4())[:8]
        session = ConversationSession(
            session_id=session_id,
            topic=topic,
            difficulty=difficulty,
            ai_role=ai_role,
            scenario_description=scenario,
        )
        self._sessions[session_id] = session
        logger.info(f"创建对话会话：{session_id}, 主题：{topic}")
        return session
    
    async def _speak_text(self, text: str) -> ToolResult:
        """使用 TTS 朗读文本。"""
        try:
            if self._voice_output is None:
                from src.tools.voice_output import VoiceOutputTool
                self._voice_output = VoiceOutputTool()
            
            result = await self._voice_output.execute("speak", {"text": text})
            return result
        except Exception as e:
            logger.error(f"TTS 失败：{e}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"语音合成失败：{e}"
            )
    
    async def _generate_scene_images(self, topic: str, ai_role: str) -> tuple[Optional[str], Optional[str]]:
        """生成场景图片和角色图片。
        
        Args:
            topic: 主题 ID
            ai_role: AI 扮演的角色
            
        Returns:
            (scene_image_path, character_image_path)
        """
        try:
            # 延迟导入图像生成工具
            if self._image_generator is None:
                from src.tools.image_generator import ImageGeneratorTool
                self._image_generator = ImageGeneratorTool()
            
            # 预定义的场景 prompt
            scene_prompts = {
                "restaurant": "A cozy restaurant interior with tables, chairs, waiter holding menu, warm lighting, realistic style, high quality",
                "airport": "Modern airport check-in counter, passengers with luggage, airline staff in uniform, bright daylight, professional photography",
                "hotel": "Elegant hotel reception desk, bellboy with luggage, luxury lobby interior, chandelier, 5-star hotel, photorealistic",
                "shopping": "Fashionable retail store interior, clothing racks, shopping assistant helping customer, modern boutique, bright lighting",
                "travel": "City street with landmarks, tourist asking for directions, friendly local guide, sunny day, travel photography style",
                "daily_chat": "Cozy cafe interior, two friends chatting at table, coffee cups, relaxed atmosphere, natural lighting, lifestyle photography",
                "business": "Modern office meeting room, business people in suits, conference table, laptop and documents, corporate environment, professional",
            }
            
            # 角色 prompt
            character_prompts = {
                "Waiter/Waitress": "Professional waiter in formal uniform, holding notepad and pen, friendly smile, restaurant background, portrait photo",
                "Check-in Agent": "Airline check-in counter staff in blue uniform, name tag, computer screen behind, airport terminal, professional headshot",
                "Hotel Receptionist": "Hotel front desk receptionist in business attire, welcoming gesture, luxury hotel lobby background, corporate portrait",
                "Shop Assistant": "Friendly shop assistant in casual uniform, helping customer, retail store background, customer service portrait",
                "Local Guide": "Friendly local tour guide with map, casual outdoor clothing, city landmark background, travel guide portrait",
                "Friend": "Casual friend in everyday clothes, coffee shop setting, relaxed pose, natural smile, lifestyle portrait",
                "Business Partner": "Business professional in suit, office environment, confident expression, corporate headshot, professional photography",
            }
            
            logger.info(f"开始生成图片：topic={topic}, ai_role={ai_role}")
            
            # 生成场景图片
            scene_prompt = scene_prompts.get(topic, scene_prompts["restaurant"])
            logger.debug(f"场景 prompt: {scene_prompt[:100]}...")
            
            scene_result = await self._image_generator.execute("generate_image", {
                "prompt": scene_prompt,
                "size": "1024x768",
                "model": "cogview-4-250304"
            })
            
            if scene_result.is_success:
                scene_path = scene_result.data.get("image_path")
                logger.info(f"✅ 场景图片生成成功：{scene_path}")
            else:
                logger.warning(f"⚠️ 场景图片生成失败：{scene_result.error}")
                scene_path = None
            
            # 生成角色图片
            char_key = next((k for k in character_prompts.keys() if k.lower() in ai_role.lower()), None)
            char_prompt = character_prompts.get(char_key, list(character_prompts.values())[0])
            logger.debug(f"角色 prompt: {char_prompt[:100]}...")
            
            char_result = await self._image_generator.execute("generate_image", {
                "prompt": char_prompt,
                "size": "512x512",
                "model": "cogview-4-250304"
            })
            
            if char_result.is_success:
                char_path = char_result.data.get("image_path")
                logger.info(f"✅ 角色图片生成成功：{char_path}")
            else:
                logger.warning(f"⚠️ 角色图片生成失败：{char_result.error}")
                char_path = None
            
            return scene_path, char_path
            
        except Exception as e:
            logger.error(f"图片生成异常：{e}", exc_info=True)
            return None, None
    
    async def _transcribe_audio(self, audio_data: Any = None) -> ToolResult:
        """转录音频为文字。"""
        try:
            if self._voice_input is None:
                from src.tools.voice_input import VoiceInputTool
                self._voice_input = VoiceInputTool()
            
            # 如果没有提供音频数据，则录制一段音频
            if audio_data is None:
                result = await self._voice_input.execute(
                    "transcribe",
                    {"duration": 30, "auto_stop": True}
                )
            else:
                result = await self._voice_input.execute(
                    "transcribe_from_data",
                    {"audio_data": audio_data}
                )
            return result
        except Exception as e:
            logger.error(f"语音识别失败：{e}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"语音识别失败：{e}"
            )
    
    def _build_system_prompt(self, session: ConversationSession) -> str:
        """构建 System Prompt。"""
        topic_config = TOPIC_LIBRARY.get(session.topic)
        
        difficulty_instructions = {
            "beginner": "Use simple vocabulary and short sentences.",
            "intermediate": "Use moderate vocabulary and natural sentences.",
            "advanced": "Use rich vocabulary and complex sentences.",
        }
        
        return f"""You are an English conversation partner. Be CONCISE.

Your Role: {session.ai_role}
Scenario: {topic_config.scenario_en if topic_config else session.scenario_description}

CRITICAL RULES:
1. Be BRIEF - Maximum 1-2 sentences per response
2. NEVER repeat yourself or summarize what you said
3. NEVER list options or suggestions
4. Stay in character - respond naturally to move the dialogue forward
5. {difficulty_instructions.get(session.difficulty, difficulty_instructions['intermediate'])}
6. Only provide Chinese translation if the learner seems confused

GOOD: "What would you like to order today?"
BAD: "I can help you order. Here are some options: 1. steak 2. fish 3. salad. What would you like?"

Remember: Less is more. Keep it natural."""
    
    async def start_conversation(
        self,
        topic: str,
        difficulty: str = "intermediate",
        role: Optional[str] = None,
        custom_scenario: Optional[str] = None,
        enable_voice: bool = True,
        enable_ui: bool = True,
    ) -> ToolResult:
        """开始一个英语对话练习。
        
        Args:
            topic: 对话主题（restaurant/airport/hotel/shopping/travel/daily_chat/business/custom）
            difficulty: 难度级别（beginner/intermediate/advanced）
            role: AI 扮演的角色（可选，默认根据主题自动设定）
            custom_scenario: 自定义场景描述（当 topic="custom" 时使用）
            enable_voice: 是否启用语音播放（默认 True）
            enable_ui: 是否显示 UI 窗口（默认 True）
        
        Returns:
            对话开场白和场景信息
        """
        try:
            # 验证主题
            if topic == "custom":
                if not custom_scenario:
                    return ToolResult(
                        status=ToolResultStatus.ERROR,
                        error="使用自定义主题时，必须提供 custom_scenario 参数"
                    )
                topic_config = TopicConfig(
                    topic_id="custom",
                    title_zh="自定义场景",
                    title_en="Custom Scenario",
                    ai_role=role or "Conversation Partner",
                    scenario_zh=custom_scenario,
                    scenario_en=custom_scenario,
                    opening_line=f"Let's start our conversation about: {custom_scenario}",
                    vocabulary=[],
                )
            else:
                topic_config = self._get_topic_config(topic)
            
            # 确定 AI 角色
            ai_role = role or topic_config.ai_role
            
            # 验证难度级别
            if difficulty not in ["beginner", "intermediate", "advanced"]:
                difficulty = "intermediate"
            
            # 创建会话
            session = self._create_session(
                topic=topic,
                difficulty=difficulty,
                ai_role=ai_role,
                scenario=topic_config.scenario_zh,
            )
            
            # 保存为当前活跃会话
            self._current_session_id = session.session_id
            
            # 添加 System Prompt
            system_prompt = self._build_system_prompt(session)
            session.add_message("system", system_prompt)
            
            # 显示 UI 对话框
            if enable_ui:
                # 注意：已改为主窗体模式，不再弹独立窗口
                # 场景信息会通过返回消息显示在主对话区
                logger.info("英语口语对话模式：使用主窗体对话区")
                # 已禁用独立窗口，改为在主对话区显示
                # self._show_dialog()
            
            # 准备返回结果（纯英语，无中文提示）
            output_lines = [
                f"**{topic_config.title_en}** - {topic_config.opening_line}",
            ]
            
            # 词汇提示（英文）
            if topic_config.vocabulary:
                vocab = topic_config.vocabulary[:5]
                output_lines.append(f"Key vocabulary: {', '.join(vocab)}")
            
            # 朗读开场白
            if enable_voice:
                await self._speak_text(topic_config.opening_line)
            
            # 自动激活持续对话模式（CFTA）
            logger.info("英语对话：自动激活持续对话模式")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={
                    "session_id": session.session_id,
                    "topic": topic,
                    "title_zh": topic_config.title_zh,
                    "title_en": topic_config.title_en,
                    "ai_role": ai_role,
                    "difficulty": difficulty,
                    "opening_line": topic_config.opening_line,
                    "vocabulary": topic_config.vocabulary,
                    "activate_cfta": True,  # 自动激活持续对话模式
                },
            )
            
        except Exception as e:
            logger.exception("开始对话失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"开始对话失败：{e}"
            )
    
    async def _generate_and_update_ui(self, topic: str, ai_role: str, topic_config):
        """异步生成图片并更新 UI。"""
        try:
            # 生成图片
            scene_path, char_path = await self._generate_scene_images(topic, ai_role)
            
            # 更新 UI
            self._update_ui_scene(topic_config, ai_role, scene_path, char_path)
            
        except Exception as e:
            logger.error(f"异步生成图片失败：{e}")
    
    async def respond(
        self,
        session_id: Optional[str] = None,
        user_input: str = "",
        input_type: str = "voice",
        enable_voice: bool = True,
        enable_ui: bool = True,
    ) -> ToolResult:
        """回应用户的输入，继续对话。
        
        Args:
            session_id: 对话会话 ID（可选，默认使用当前活跃会话）
            user_input: 用户输入（文字或语音识别结果）
            input_type: 输入类型（voice/text），默认 voice
            enable_voice: 是否启用语音播放
            enable_ui: 是否更新 UI 显示
        
        Returns:
            AI 的回复和学习建议
        """
        try:
            # 如果没有提供 session_id，使用当前活跃会话
            if not session_id:
                session_id = self._current_session_id
                logger.info(f"使用当前活跃会话：{session_id}")
            
            if not session_id:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="没有活跃的对话会话，请先调用 start_conversation 开始对话"
                )
            
            
            # 查找会话
            if session_id not in self._sessions:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"会话不存在：{session_id}"
                )
            
            session = self._sessions[session_id]
            
            # 如果是语音输入但没有提供文本，先进行语音识别
            if input_type == "voice" and not user_input.strip():
                transcribe_result = await self._transcribe_audio()
                if not transcribe_result.is_success:
                    return transcribe_result
                user_input = transcribe_result.data.get("text", "")
                logger.info(f"语音识别结果：{user_input}")
            
            if not user_input.strip():
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="用户输入为空"
                )
            
            # 添加用户消息到上下文
            session.add_message("user", user_input)
            
            # 注意：已禁用独立窗口，用户输入通过主对话区显示
            # if enable_ui:
            #     self._update_ui_dialogue(
            #         role="user",
            #         speaker="You",
            #         english=user_input,
            #         chinese=None
            #     )
            
            # 构建对话上下文
            context_messages = session.get_context_messages(max_turns=20)
            
            # 调用 LLM 生成回复（这里简化处理，实际需要调用 Agent）
            ai_response = await self._generate_ai_response(context_messages, session)
            
            # 解析 AI 回复（分离英文和中文提示）
            main_response, chinese_tip = self._parse_ai_response(ai_response)
            
            # 添加 AI 回复到上下文
            session.add_message("assistant", ai_response)
            
            # 注意：已禁用独立窗口，AI 回复通过主对话区显示
            # if enable_ui:
            #     self._update_ui_dialogue(
            #         role="ai",
            #         speaker=session.ai_role,
            #         english=main_response,
            #         chinese=chinese_tip
            #     )
            
            # 准备返回结果（纯英语对话）
            output_lines = [f"**{main_response}**"]
                        
            # 朗读 AI 回复
            if enable_voice:
                await self._speak_text(main_response)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={
                    "session_id": session_id,
                    "ai_response": main_response,
                    "chinese_tip": chinese_tip,
                    "total_turns": session.total_turns,
                },
            )
            
        except Exception as e:
            logger.exception("回应失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"回应失败：{e}"
            )
    
    async def _generate_ai_response(
        self,
        context_messages: list[dict],
        session: ConversationSession,
    ) -> str:
        """生成 AI 回复（使用 LiteLLM 调用 LLM）。"""
        try:
            import litellm
            from litellm import acompletion
            
            # 构建完整的消息列表
            messages = context_messages.copy()
            
            # 调用 LLM（使用正确的 provider 前缀）
            # LiteLLM 需要完整的模型名称，格式：<provider>/<model>
            # 常见选项：deepseek/deepseek-chat, openai/gpt-4, zhipuai/glm-4
            response = await acompletion(
                model="deepseek/deepseek-chat",  # 已修复：添加 provider 前缀
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"LLM 回复：{ai_response[:100]}")
            return ai_response
            
        except Exception as e:
            logger.error(f"LLM 调用失败：{e}")
            # 降级到简化回复
            return await self._fallback_response(context_messages)
    
    async def _fallback_response(
        self,
        context_messages: list[dict],
    ) -> str:
        """降级回复策略（当 LLM 不可用时）。"""
        last_user_msg = next(
            (m["content"] for m in reversed(context_messages) if m["role"] == "user"),
            ""
        )
        
        # 简单的关键词回复
        responses = {
            "hello": "Hello! How are you doing today?",
            "thank": "You're welcome! Is there anything else I can help you with?",
            "yes": "Great! Please go ahead.",
            "no": "No problem. Take your time.",
            "order": "Excellent choice! How would you like that prepared?",
            "bill": "Sure! Let me get the bill for you.",
            "how much": "The total is... Let me calculate that for you.",
            "where": "It's located nearby. Would you like me to show you on a map?",
        }
        
        # 匹配关键词
        lower_msg = last_user_msg.lower()
        for key, response in responses.items():
            if key in lower_msg:
                return response
        
        # 默认回复
        return "I see. Could you tell me more about that?"
    
    def _parse_ai_response(self, response: str) -> tuple[str, Optional[str]]:
        """解析 AI 回复，分离英文内容和中文提示。"""
        # 查找括号中的中文提示
        import re
        match = re.search(r'\(([^)]+)\)', response)
        
        if match:
            chinese_tip = match.group(1)
            main_response = response[:match.start()].strip()
            return main_response, chinese_tip
        else:
            return response, None
    
    def _show_dialog(self):
        """显示 UI 对话框。"""
        try:
            from PySide6.QtWidgets import QApplication
            from src.ui.english_conversation_dialog import EnglishConversationDialog
            
            # 获取现有的 QApplication 实例（优先复用）
            app = QApplication.instance()
            if app is None:
                # 如果没有现有实例，才创建新的（ standalone 模式）
                import sys
                app = QApplication(sys.argv)
                app.setApplicationName("WinClaw")
                logger.info("创建新的 QApplication 实例（standalone 模式）")
            else:
                logger.info("复用现有的 QApplication 实例")
            
            # 检查是否已经显示了对话框
            if self._dialog is not None:
                # 如果已存在，将其提到前台
                self._dialog.raise_()
                self._dialog.activateWindow()
                logger.info("对话框已存在，激活窗口")
                return
            
            # 创建对话框
            self._dialog = EnglishConversationDialog()
            self._dialog.close_requested.connect(self._on_dialog_closed)
            
            # 显示对话框
            self._dialog.show()
            self._dialog.raise_()
            self._dialog.activateWindow()
            
            logger.info("UI 对话框已显示")
            
        except Exception as e:
            logger.error(f"显示 UI 失败：{e}")
            self._dialog = None
    
    def _on_dialog_closed(self):
        """对话框关闭处理。"""
        logger.info("UI 对话框已关闭")
        self._dialog = None
    
    def _update_ui_scene(self, topic_config, ai_role: str, scene_path: Optional[str], char_path: Optional[str]):
        """更新 UI 场景显示。"""
        if self._dialog is None:
            return
        
        try:
            # 准备词汇数据
            vocabulary = [
                {"en": word, "cn": self._translate_word(word)}
                for word in topic_config.vocabulary[:8]
            ]
            
            # 更新 UI
            self._dialog.update_scene(
                topic=topic_config.topic_id,
                title_zh=topic_config.title_zh,
                title_en=topic_config.title_en,
                scene_image=scene_path,
                character_image=char_path,
                vocabulary=vocabulary
            )
            
            logger.info("UI 场景已更新")
            
        except Exception as e:
            logger.error(f"更新 UI 场景失败：{e}")
    
    def _update_ui_dialogue(self, role: str, speaker: str, english: str, chinese: Optional[str] = None):
        """更新 UI 对话内容。"""
        if self._dialog is None:
            return
        
        try:
            self._dialog.add_dialogue_line(
                role=role,
                speaker=speaker,
                english=english,
                chinese=chinese
            )
            logger.debug("UI 对话已更新")
            
        except Exception as e:
            logger.error(f"更新 UI 对话失败：{e}")
    
    def _update_ui_status(self, status_message: str):
        """更新 UI 状态提示。"""
        if self._dialog is None:
            return
        
        try:
            self._dialog.update_status(status_message)
            logger.debug(f"UI 状态已更新：{status_message}")
            
        except Exception as e:
            logger.error(f"更新 UI 状态失败：{e}")
    
    def _translate_word(self, word: str) -> str:
        """简单的单词翻译（硬编码常用词）。"""
        translations = {
            "menu": "菜单",
            "order": "点餐",
            "appetizer": "开胃菜",
            "main course": "主菜",
            "dessert": "甜点",
            "bill": "账单",
            "water": "水",
            "wine": "葡萄酒",
            "passport": "护照",
            "boarding pass": "登机牌",
            "luggage": "行李",
            "seat": "座位",
            "flight number": "航班号",
            "gate": "登机口",
            "departure": "出发",
            "reservation": "预订",
            "check-in": "入住",
            "room key": "房卡",
            "breakfast": "早餐",
            "elevator": "电梯",
            "floor": "楼层",
            "size": "尺寸",
            "color": "颜色",
            "try on": "试穿",
            "price": "价格",
            "discount": "折扣",
            "cashier": "收银台",
            "fitting room": "试衣间",
            "directions": "方向",
            "map": "地图",
            "station": "车站",
            "turn left": "左转",
            "turn right": "右转",
            "straight": "直走",
            "landmark": "地标",
            "weekend": "周末",
            "hobbies": "爱好",
            "work": "工作",
            "family": "家庭",
            "movies": "电影",
            "music": "音乐",
            "agenda": "议程",
            "proposal": "提案",
            "budget": "预算",
            "deadline": "截止日期",
            "presentation": "演示",
            "feedback": "反馈",
        }
        return translations.get(word.lower(), "未知")
    
    async def end_conversation(
        self,
        session_id: Optional[str] = None,
        save_recording: bool = False,
    ) -> ToolResult:
        """结束对话并提供总结。
        
        Args:
            session_id: 对话会话 ID（可选，默认使用当前活跃会话）
            save_recording: 是否保存对话录音
        
        Returns:
            对话总结和学习建议
        """
        try:
            # 如果没有提供 session_id，使用当前活跃会话
            if not session_id:
                session_id = self._current_session_id
            
            if not session_id:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="没有活跃的对话会话"
                )
            
            if session_id not in self._sessions:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"会话不存在：{session_id}"
                )
            
            session = self._sessions[session_id]
            
            # 收集对话记录
            dialogue_history = session.get_context_messages(max_turns=50)
            user_messages = [m["content"] for m in dialogue_history if m["role"] == "user"]
            
            # 生成总结（纯英语，鼓励为主）
            total_turns = len(user_messages)
            duration_minutes = (datetime.now() - session.started_at).seconds // 60
            
            # 根据表现生成鼓励性反馈
            feedback_lines = []
            
            if total_turns >= 5:
                feedback_lines.append("Excellent dedication! You completed multiple conversation rounds.")
            elif total_turns >= 3:
                feedback_lines.append("Great effort! You maintained a good conversation flow.")
            else:
                feedback_lines.append("Good start! Every conversation helps improve your English.")
            
            # 根据用户输入内容分析
            if user_messages:
                avg_length = sum(len(m.split()) for m in user_messages) / len(user_messages)
                if avg_length >= 8:
                    feedback_lines.append("Your sentences are well-developed and expressive!")
                elif avg_length >= 5:
                    feedback_lines.append("You're building confidence in expressing yourself.")
                else:
                    feedback_lines.append("Keep practicing to express more complex ideas!")
            
            # 添加建议
            feedback_lines.extend([
                "",
                "Tips for improvement:",
                "- Try using new vocabulary from the conversation",
                "- Practice speaking with different intonations",
                "- Listen to native speakers and mimic their pronunciation",
            ])
            
            output_lines = [
                "🎉 **Conversation Complete!**",
                "",
                f"📊 Statistics: {total_turns} exchanges, {duration_minutes} minutes",
                "",
                "🌟 **Your Performance:**",
            ]
            output_lines.extend(feedback_lines)
            
            output_lines.extend([
                "",
                "💡 Ready for another round? Say \"Let's practice again\" or choose a new topic!",
            ])
            
            # 清理会话
            del self._sessions[session_id]
            
            # 如果清理的是当前活跃会话，重置活跃会话 ID
            if self._current_session_id == session_id:
                self._current_session_id = None
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={
                    "session_id": session_id,
                    "topic": session.topic,
                    "total_turns": total_turns,
                    "duration_minutes": duration_minutes,
                },
            )
            
        except Exception as e:
            logger.exception("结束对话失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"结束对话失败：{e}"
            )
    
    def list_topics(self) -> ToolResult:
        """列出所有可用的对话主题。
        
        Returns:
            主题列表
        """
        try:
            topics_info = []
            for topic_id, config in TOPIC_LIBRARY.items():
                topics_info.append({
                    "id": topic_id,
                    "title_zh": config.title_zh,
                    "title_en": config.title_en,
                    "ai_role": config.ai_role,
                    "scenario_zh": config.scenario_zh,
                    "difficulty": ", ".join(config.difficulty_suggestions),
                })
            
            output_lines = [
                f"{self.emoji} 可用的对话主题:",
                "",
            ]
            
            for info in topics_info:
                output_lines.append(f"📍 {info['id']}: {info['title_zh']} ({info['title_en']})")
                output_lines.append(f"   角色：{info['ai_role']}")
                output_lines.append(f"   场景：{info['scenario_zh']}")
                output_lines.append(f"   难度：{info['difficulty']}")
                output_lines.append("")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(output_lines),
                data={"topics": topics_info},
            )
            
        except Exception as e:
            logger.exception("列出主题失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列出主题失败：{e}"
            )
    
    def get_actions(self) -> list[ActionDef]:
        """获取工具支持的动作列表。"""
        return [
            ActionDef(
                name="start_conversation",
                description="开始一个英语对话练习场景",
                parameters={
                    "topic": {
                        "type": "string",
                        "description": "对话主题：restaurant/airport/hotel/shopping/travel/daily_chat/business/custom",
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "难度级别：beginner/intermediate/advanced",
                        "default": "intermediate",
                    },
                    "role": {
                        "type": "string",
                        "description": "AI 扮演的角色（可选，默认根据主题自动设定）",
                    },
                    "custom_scenario": {
                        "type": "string",
                        "description": "自定义场景描述（当 topic=custom 时必须）",
                    },
                    "enable_voice": {
                        "type": "boolean",
                        "description": "是否启用语音播放",
                        "default": True,
                    },
                },
                required_params=["topic"],
            ),
            ActionDef(
                name="respond",
                description="回应用户输入，继续对话（session_id 可选，默认使用当前会话）",
                parameters={
                    "session_id": {
                        "type": "string",
                        "description": "对话会话 ID（可选，默认使用最近创建的会话）",
                    },
                    "user_input": {
                        "type": "string",
                        "description": "用户输入（文字或语音识别结果）",
                    },
                    "input_type": {
                        "type": "string",
                        "description": "输入类型：voice/text",
                        "default": "voice",
                    },
                    "enable_voice": {
                        "type": "boolean",
                        "description": "是否启用语音播放",
                        "default": True,
                    },
                },
                required_params=["user_input"],  # session_id 变为可选
            ),
            ActionDef(
                name="end_conversation",
                description="结束对话并提供总结（session_id 可选）",
                parameters={
                    "session_id": {
                        "type": "string",
                        "description": "对话会话 ID（可选，默认使用最近创建的会话）",
                    },
                    "save_recording": {
                        "type": "boolean",
                        "description": "是否保存对话录音",
                        "default": False,
                    },
                },
                required_params=[],  # session_id 变为可选
            ),
            ActionDef(
                name="list_topics",
                description="列出所有可用的对话主题",
                parameters={},
            ),
        ]
    
    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行工具动作。"""
        if action == "start_conversation":
            return await self.start_conversation(**params)
        elif action == "respond":
            return await self.respond(**params)
        elif action == "end_conversation":
            return await self.end_conversation(**params)
        elif action == "list_topics":
            return self.list_topics()
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知动作：{action}"
            )
