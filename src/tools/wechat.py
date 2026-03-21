"""微信消息管理工具。

提供完整的微信消息管理能力：
- 消息收发（查看、回复、发送）
- 聊天管理（切换对象、搜索联系人）
- 消息监听（新消息检测、OCR 识别）
- 智能客服（知识库问答、自动回复）
- 定时任务集成
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class WeChatTool(BaseTool):
    """微信消息管理工具
    
    功能：
    - 消息收发：查看消息、发送消息
    - 聊天管理：切换聊天对象、获取聊天列表
    - 消息检索：搜索历史消息
    - 智能回复：AI 自动回复、知识库客服
    - 定时任务：定时检查消息、定期发送
    """
    
    name = "wechat"
    emoji = "💬"
    title = "微信消息管理"
    description = "管理电脑端微信消息，支持查看、回复、切换聊天对象和智能客服问答"
    
    def __init__(
        self, 
        config_path: str | None = None,
        knowledge_base_path: str | None = None,
        tool_registry=None,
        model_registry=None
    ):
        """初始化微信工具
        
        Args:
            config_path: 配置文件路径
            knowledge_base_path: 知识库路径
            tool_registry: 工具注册表（用于调用其他工具）
            model_registry: 模型注册表（用于 LLM 调用）
        """
        super().__init__()
        
        self.config_path = Path(config_path) if config_path else Path("config/wechat_config.yaml")
        self.knowledge_base_path = Path(knowledge_base_path) if knowledge_base_path else Path("data/wechat_knowledge.db")
        self._tool_registry = tool_registry
        self._model_registry = model_registry
        
        # 懒加载核心组件
        self._bot = None
        self._knowledge_base = None
        
        # 状态标记
        self._customer_service_enabled = False
        self._auto_reply_config = {}
        
        logger.info("WeChatTool 已初始化")
    
    def _get_bot(self):
        """懒加载 WeChatBot"""
        if self._bot is None:
            from .wechat_core import WeChatBot
            self._bot = WeChatBot(str(self.config_path))
            logger.debug("WeChatBot 已懒加载")
        return self._bot
    
    async def _get_knowledge_base(self):
        """异步懒加载知识库"""
        if self._knowledge_base is None:
            from .wechat_knowledge import WeChatKnowledgeBase
            self._knowledge_base = WeChatKnowledgeBase(
                db_path=str(self.knowledge_base_path)
            )
            await self._knowledge_base.initialize()
            logger.debug("WeChatKnowledgeBase 已懒加载")
        return self._knowledge_base
    
    def get_actions(self) -> list[ActionDef]:
        """返回此工具支持的所有动作定义"""
        return [
            ActionDef(
                name="check_window",
                description="检查微信客户端是否运行并激活窗口，确保微信可见且在前台",
                parameters={},
                required_params=[]
            ),
            ActionDef(
                name="launch",
                description="启动微信客户端，如果微信未运行则自动启动",
                parameters={},
                required_params=[]
            ),
            ActionDef(
                name="view_messages",
                description="查看当前聊天对象的消息列表，支持 OCR 识别截图中的消息",
                parameters={
                    "chat_name": {
                        "type": "string", 
                        "description": "聊天对象名称，留空使用当前聊天"
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "返回最近 N 条消息，默认 20", 
                        "default": 20
                    },
                    "include_images": {
                        "type": "boolean", 
                        "description": "是否包含图片消息的 OCR 识别结果", 
                        "default": True
                    }
                },
                required_params=[]
            ),
            ActionDef(
                name="send_message",
                description="向指定聊天对象发送消息，支持文本和表情",
                parameters={
                    "chat_name": {
                        "type": "string", 
                        "description": "聊天对象名称，留空使用当前聊天"
                    },
                    "message": {
                        "type": "string", 
                        "description": "要发送的消息内容"
                    },
                    "delay": {
                        "type": "number", 
                        "description": "延迟发送时间（秒），模拟真人输入", 
                        "default": 2.0
                    }
                },
                required_params=["message"]
            ),
            ActionDef(
                name="switch_chat",
                description="切换到指定聊天对象，或列出所有最近聊天",
                parameters={
                    "chat_name": {
                        "type": "string", 
                        "description": "聊天对象名称，支持模糊匹配"
                    }
                },
                required_params=[]
            ),
            ActionDef(
                name="search_messages",
                description="搜索特定用户或群聊的历史消息",
                parameters={
                    "chat_name": {
                        "type": "string", 
                        "description": "聊天对象名称"
                    },
                    "keyword": {
                        "type": "string", 
                        "description": "搜索关键词"
                    },
                    "date_range": {
                        "type": "string", 
                        "description": "日期范围，格式：'2026-03-01,2026-03-12'", 
                        "default": "last_7_days"
                    }
                },
                required_params=["keyword"]
            ),
            ActionDef(
                name="enable_auto_reply",
                description="启用 AI 智能自动回复，支持自定义回复策略",
                parameters={
                    "enabled": {
                        "type": "boolean", 
                        "description": "是否启用"
                    },
                    "target_chats": {
                        "type": "array", 
                        "items": {"type": "string"}, 
                        "description": "只回复特定聊天列表，留空回复所有"
                    },
                    "reply_delay_min": {
                        "type": "number", 
                        "description": "最小回复延迟（秒）", 
                        "default": 3.0
                    },
                    "reply_delay_max": {
                        "type": "number", 
                        "description": "最大回复延迟（秒）", 
                        "default": 8.0
                    },
                    "exclude_keywords": {
                        "type": "array", 
                        "items": {"type": "string"}, 
                        "description": "排除包含这些关键词的聊天"
                    }
                },
                required_params=["enabled"]
            ),
            ActionDef(
                name="get_chat_list",
                description="获取最近聊天列表，可选择按类型过滤",
                parameters={
                    "chat_type": {
                        "type": "string", 
                        "enum": ["all", "individual", "group"], 
                        "default": "all"
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "返回数量", 
                        "default": 50
                    }
                },
                required_params=[]
            ),
            ActionDef(
                name="customer_service",
                description="启用微信客服模式，基于知识库自动回答客户咨询",
                parameters={
                    "enabled": {
                        "type": "boolean", 
                        "description": "是否启用客服模式"
                    },
                    "knowledge_base": {
                        "type": "string", 
                        "description": "知识库路径或 ID"
                    },
                    "confidence_threshold": {
                        "type": "number", 
                        "description": "最低置信度阈值（0-1）", 
                        "default": 0.7
                    },
                    "fallback_to_llm": {
                        "type": "boolean", 
                        "description": "知识库无匹配时使用 LLM 生成", 
                        "default": True
                    },
                    "working_hours": {
                        "type": "string", 
                        "description": "工作时间，格式：'09:00-18:00'", 
                        "default": "00:00-23:59"
                    }
                },
                required_params=["enabled"]
            ),
            ActionDef(
                name="add_to_knowledge",
                description="将当前对话添加到知识库，用于未来自动回复",
                parameters={
                    "question": {
                        "type": "string", 
                        "description": "客户问题"
                    },
                    "answer": {
                        "type": "string", 
                        "description": "标准答案"
                    },
                    "category": {
                        "type": "string", 
                        "description": "分类标签"
                    }
                },
                required_params=["question", "answer"]
            )
        ]
    
    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作
        
        Args:
            action: 动作名称
            params: 动作参数
        
        Returns:
            ToolResult 执行结果
        """
        try:
            # 路由到具体处理方法
            actions_map = {
                "check_window": self._check_window,
                "launch": self._launch_wechat,
                "view_messages": self._view_messages,
                "send_message": self._send_message,
                "switch_chat": self._switch_chat,
                "search_messages": self._search_messages,
                "enable_auto_reply": self._enable_auto_reply,
                "get_chat_list": self._get_chat_list,
                "customer_service": self._customer_service,
                "add_to_knowledge": self._add_to_knowledge,
            }
            
            handler = actions_map.get(action)
            if not handler:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未知动作：{action}"
                )
            
            return await handler(params)
            
        except Exception as e:
            logger.error(f"WeChatTool 执行失败：{e}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e)
            )
    
    async def _check_window(self, params: dict[str, Any]) -> ToolResult:
        """检查并激活微信窗口"""
        bot = self._get_bot()
        
        # 查找窗口
        hwnd = bot.find_wechat_window()
        
        if not hwnd:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="微信客户端未运行，请先打开微信并登录"
            )
        
        # 激活窗口
        success = bot.activate_window()
        
        if success:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="微信窗口已激活并置于前台",
                data={"window_handle": hwnd, "activated": True}
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="微信窗口激活失败，请手动切换到微信"
            )
    
    async def _launch_wechat(self, params: dict[str, Any]) -> ToolResult:
        """启动微信客户端"""
        import time
        bot = self._get_bot()
        
        # 先检查是否已在运行
        hwnd = bot.find_wechat_window()
        if hwnd:
            logger.info("微信已在运行")
            bot.activate_window()
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="微信已在运行，窗口已激活",
                data={"window_handle": hwnd}
            )
        
        # 尝试启动
        success = bot.launch_wechat()
        
        if success:
            # 等待微信启动（最多等待 10 秒）
            logger.info("等待微信启动...")
            for i in range(10):
                time.sleep(1.0)
                hwnd = bot.find_wechat_window()
                if hwnd:
                    logger.info("微信启动成功，耗时 %d 秒", i + 1)
                    bot.activate_window()
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        output=f"微信已启动并激活（耗时{i+1}秒）",
                        data={"window_handle": hwnd, "startup_time_sec": i + 1}
                    )
            
            # 超时未找到窗口
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="微信已启动但未检测到窗口，请手动检查微信是否正常打开",
                data={"launched": True, "timeout": True}
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="无法启动微信，请确认微信已安装"
            )
    
    async def _view_messages(self, params: dict[str, Any]) -> ToolResult:
        """查看消息"""
        chat_name = params.get("chat_name", "")
        limit = params.get("limit", 20)
        include_images = params.get("include_images", True)
        
        bot = self._get_bot()
        
        # 先检查并激活窗口
        hwnd = bot.find_wechat_window()
        if not hwnd:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="微信客户端未运行，请先打开微信并登录",
                data={"window_found": False}
            )
        
        # 激活窗口
        bot.activate_window()
        
        # 获取消息
        messages = bot._get_current_messages(limit=limit)
        
        if not messages:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="未检测到消息（可能是因为没有打开聊天窗口或 OCR 识别失败）",
                data={
                    "messages": [],
                    "chat_name": chat_name or "当前聊天",
                    "count": 0,
                    "window_handle": hwnd
                }
            )
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已获取{len(messages)}条消息",
            data={
                "messages": messages,
                "chat_name": chat_name or "当前聊天",
                "count": len(messages),
                "window_handle": hwnd
            }
        )
    
    async def _send_message(self, params: dict[str, Any]) -> ToolResult:
        """发送消息"""
        message = params.get("message", "")
        chat_name = params.get("chat_name", "")
        delay = params.get("delay", 2.0)
        
        if not message:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="消息内容不能为空"
            )
        
        bot = self._get_bot()
        success = bot.send_message(message, chat_name, delay)
        
        if success:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="消息已发送",
                data={"sent": True, "message": message[:100]}
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="消息发送失败，请检查微信是否正常运行"
            )
    
    async def _switch_chat(self, params: dict[str, Any]) -> ToolResult:
        """切换聊天"""
        chat_name = params.get("chat_name", "")
        
        bot = self._get_bot()
        
        if not chat_name:
            # 返回聊天列表
            chat_list = bot.get_chat_list(limit=20)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"已获取{len(chat_list)}个聊天对象",
                data={"chat_list": chat_list}
            )
        
        # 切换到指定聊天
        success = bot.switch_to_chat(chat_name)
        
        if success:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"已切换到聊天：{chat_name}",
                data={"switched": True, "chat_name": chat_name}
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"切换聊天失败：{chat_name}"
            )
    
    async def _search_messages(self, params: dict[str, Any]) -> ToolResult:
        """搜索消息"""
        keyword = params.get("keyword", "")
        chat_name = params.get("chat_name", "")
        date_range = params.get("date_range", "last_7_days")
        
        if not keyword:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="搜索关键词不能为空"
            )
        
        # TODO: 实现消息搜索
        results = []
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"搜索到{len(results)}条相关消息",
            data={
                "results": results,
                "keyword": keyword,
                "chat_name": chat_name,
                "count": len(results)
            }
        )
    
    async def _enable_auto_reply(self, params: dict[str, Any]) -> ToolResult:
        """启用自动回复"""
        enabled = params.get("enabled", False)
        target_chats = params.get("target_chats", [])
        reply_delay_min = params.get("reply_delay_min", 3.0)
        reply_delay_max = params.get("reply_delay_max", 8.0)
        exclude_keywords = params.get("exclude_keywords", [])
        
        bot = self._get_bot()
        
        if enabled:
            # 更新配置
            bot.update_config("llm.delay_min", reply_delay_min)
            bot.update_config("llm.delay_max", reply_delay_max)
            
            if exclude_keywords:
                bot.update_config("llm.exclude_chats", exclude_keywords)
            
            if target_chats:
                bot.set_target_chats(target_chats)
            
            bot.enable_smart_reply(True)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="自动回复已启用",
                data={
                    "enabled": True,
                    "target_chats": target_chats,
                    "delay_range": f"{reply_delay_min}-{reply_delay_max}s"
                }
            )
        else:
            bot.enable_smart_reply(False)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="自动回复已禁用",
                data={"enabled": False}
            )
    
    async def _get_chat_list(self, params: dict[str, Any]) -> ToolResult:
        """获取聊天列表"""
        chat_type = params.get("chat_type", "all")
        limit = params.get("limit", 50)
        
        bot = self._get_bot()
        
        # 先检查并激活窗口
        hwnd = bot.find_wechat_window()
        if not hwnd:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="微信客户端未运行，请先打开微信并登录"
            )
        
        # 激活窗口
        bot.activate_window()
        
        # 获取聊天列表
        chat_list = bot.get_chat_list(limit=limit, chat_type=chat_type)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已获取{len(chat_list)}个聊天对象",
            data={
                "chat_list": chat_list,
                "type": chat_type,
                "count": len(chat_list)
            }
        )
    
    async def _customer_service(self, params: dict[str, Any]) -> ToolResult:
        """客服模式"""
        enabled = params.get("enabled", False)
        knowledge_base = params.get("knowledge_base", "")
        confidence_threshold = params.get("confidence_threshold", 0.7)
        fallback_to_llm = params.get("fallback_to_llm", True)
        working_hours = params.get("working_hours", "00:00-23:59")
        
        if enabled:
            # 初始化知识库
            kb = await self._get_knowledge_base()
            
            self._customer_service_enabled = True
            self._auto_reply_config = {
                "knowledge_base": knowledge_base,
                "confidence_threshold": confidence_threshold,
                "fallback_to_llm": fallback_to_llm,
                "working_hours": working_hours
            }
            
            # 启用自动回复
            bot = self._get_bot()
            bot.enable_smart_reply(True)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="客服模式已启用",
                data={
                    "enabled": True,
                    "knowledge_base": knowledge_base or str(self.knowledge_base_path),
                    "confidence_threshold": confidence_threshold,
                    "working_hours": working_hours
                }
            )
        else:
            self._customer_service_enabled = False
            self._auto_reply_config = {}
            
            bot = self._get_bot()
            bot.enable_smart_reply(False)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="客服模式已禁用",
                data={"enabled": False}
            )
    
    async def _add_to_knowledge(self, params: dict[str, Any]) -> ToolResult:
        """添加到知识库"""
        question = params.get("question", "")
        answer = params.get("answer", "")
        category = params.get("category", "general")
        
        if not question or not answer:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="问题和答案都不能为空"
            )
        
        kb = await self._get_knowledge_base()
        success = await kb.add_faq(question, answer, category)
        
        if success:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="已成功添加到知识库",
                data={
                    "added": True,
                    "question": question[:100],
                    "category": category
                }
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="添加 FAQ 失败"
            )
    
    async def close(self) -> None:
        """清理资源"""
        try:
            if self._bot:
                self._bot.stop_message_monitor()
            logger.info("WeChatTool 资源已清理")
        except Exception as e:
            logger.error(f"清理资源失败：{e}")
