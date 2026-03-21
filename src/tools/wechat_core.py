"""微信核心功能模块 - 从 skills 重构的 WeChatBot 类。

基于 .qoder/skills/we_chat_examples 中的代码重构，提供：
- 窗口激活与控制
- 消息发送与接收
- OCR 识别（GLM 视觉模型）
- 智能回复生成
- 消息监听循环
"""

from __future__ import annotations

import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pyautogui
import yaml

# 延迟导入，避免初始化时失败
pyperclip = None
try:
    import pyperclip
except ImportError:
    pass


def pyperclip_copy(text: str) -> bool:
    """安全地复制文本到剪贴板。
    
    Args:
        text: 要复制的文本
    
    Returns:
        是否成功
    """
    if pyperclip is None:
        logger.warning("pyperclip 未安装，无法使用剪贴板")
        return False
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.error("复制到剪贴板失败：%s", e)
        return False

logger = logging.getLogger(__name__)


class WeChatBot:
    """微信机器人核心类
    
    功能：
    - 窗口管理：激活、最小化、切换
    - 消息收发：发送文本、读取消息
    - OCR 识别：使用 GLM 视觉模型提取聊天消息
    - 智能回复：基于 LLM 生成自然回复
    - 消息监听：定时检测新消息并触发回调
    """
    
    def __init__(self, config_path: str | None = None):
        """初始化微信机器人
        
        Args:
            config_path: 配置文件路径，默认 config/wechat_config.yaml
        """
        self.config_path = Path(config_path) if config_path else Path("config/wechat_config.yaml")
        self.config = self._load_config()
        
        # 状态标记
        self._window_handle = None
        self._message_monitor_active = False
        self._auto_reply_enabled = False
        self._last_message_hash = None
        self._context_history = {}  # 每个聊天的上下文历史
        
        # 回调函数
        self._on_new_message: Callable | None = None
        self._on_reply_sent: Callable | None = None
        
        # 目标聊天列表（用于过滤）
        self._target_chats: list[str] = []
        
        logger.info("WeChatBot 已初始化，配置：%s", self.config_path)
    
    def _load_config(self) -> dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning("配置文件不存在：%s，使用默认配置", self.config_path)
            return self._default_config()
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.debug("成功加载配置文件")
            return config
        except Exception as e:
            logger.error("加载配置文件失败：%s", e)
            return self._default_config()
    
    def _default_config(self) -> dict[str, Any]:
        """默认配置"""
        return {
            "process_name": "Weixin.exe,WeChat.exe",
            "window": {
                "activate_hotkey": "Ctrl+Alt+W",
                "check_interval": 10.0
            },
            "message_monitor": {
                "enabled": True,
                "check_interval": 10.0,
                "ocr_engine": "glm"
            },
            "llm": {
                "enabled": True,
                "delay_min": 3.0,
                "delay_max": 8.0,
                "max_context_length": 10,
                "exclude_chats": [
                    "文件传输助手",
                    "信用卡",
                    "银行",
                    "微信支付",
                    "服务通知",
                    "订阅号消息"
                ],
                "glm": {
                    "vision_model": "glm-4.6v",
                    "chat_model": "glm-4-flash"
                }
            }
        }
    
    def _ocr_chat_list_with_glm(self, img_base64: str, limit: int = 50, chat_type: str = "all") -> list[dict[str, Any]]:
        """使用 GLM-4.6V 识别聊天列表
        
        Args:
            img_base64: Base64 编码的图片
            limit: 返回数量限制
            chat_type: 聊天类型 (all/individual/group)
        
        Returns:
            聊天列表
        """
        try:
            # 导入 ZhipuAI SDK
            from zai import ZhipuAiClient
            import os
            from dotenv import load_dotenv
            
            # 加载 .env 文件
            load_dotenv()
            
            # 获取 API Key
            api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
            if not api_key:
                logger.warning("未找到 GLM API Key，返回空列表")
                return []
            
            # 创建客户端
            client = ZhipuAiClient(api_key=api_key)
            
            # 构建提示词
            prompt = """请分析这张微信聊天列表截图，提取所有可见的聊天对象信息。

对于每个聊天对象，请提取：
1. 名称（个人或群聊名称）
2. 最后一条消息的简要内容（如果是图片、表情等，请用文字描述如"[图片]"、"[表情]"）
3. 时间戳（如"刚刚"、"10 分钟前"、"昨天"等）
4. 是否是群聊（根据名称或图标判断）

请以 JSON 数组格式返回，每个对象包含以下字段：
- name: 聊天对象名称
- last_message: 最后一条消息内容
- timestamp: 时间戳
- is_group: 是否群聊（true/false）

只返回聊天对象信息，不要有其他说明文字。直接返回 JSON 数组。"""
            
            # 调用 GLM-4.6V
            response = client.chat.completions.create(
                model="glm-4.6v",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                thinking={"type": "enabled"}
            )
            
            # 解析结果
            result_text = response.choices[0].message.content.strip()
            
            # 尝试从文本中提取 JSON
            import json
            import re
            
            # 查找 JSON 数组
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                chat_list = json.loads(json_match.group())
                
                # 根据类型过滤
                if chat_type == "individual":
                    chat_list = [c for c in chat_list if not c.get("is_group", False)]
                elif chat_type == "group":
                    chat_list = [c for c in chat_list if c.get("is_group", False)]
                
                # 限制数量
                chat_list = chat_list[:limit]
                
                logger.info("GLM-4.6V 识别到 %d 个聊天对象", len(chat_list))
                return chat_list
            else:
                logger.warning("GLM 返回格式不正确：%s", result_text[:200])
                return []
                
        except ImportError:
            logger.error("zai-sdk 未安装，无法使用 GLM-4.6V")
            return []
        except Exception as e:
            logger.error("GLM-4.6V OCR 识别失败：%s", e)
            return []
    
    def _ocr_messages_with_glm(self, img_base64: str, limit: int = 20) -> list[dict[str, Any]]:
        """使用 GLM-4.6V 识别聊天消息
        
        Args:
            img_base64: Base64 编码的图片
            limit: 返回数量限制
        
        Returns:
            消息列表
        """
        try:
            # 导入 ZhipuAI SDK
            from zai import ZhipuAiClient
            import os
            from dotenv import load_dotenv
            
            # 加载 .env 文件
            load_dotenv()
            
            # 获取 API Key
            api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
            if not api_key:
                logger.warning("未找到 GLM API Key，返回空列表")
                return []
            
            # 创建客户端
            client = ZhipuAiClient(api_key=api_key)
            
            # 构建提示词
            prompt = """请分析这张微信聊天对话截图，提取所有可见的消息。

对于每条消息，请提取：
1. 发送者（"我"表示自己发送的消息，或其他人的昵称）
2. 消息内容（文字、表情、图片等，如果是图片请用"[图片]"描述）
3. 时间戳（如"10:30"、"昨天"等，如果没有显示时间可以留空）
4. 是否是自己发送的（is_self: true/false）

请以 JSON 数组格式返回，每个对象包含以下字段：
- sender: 发送者名称（"我"表示自己）
- content: 消息内容
- timestamp: 时间戳
- is_self: 是否自己发送（true/false）

只返回消息列表，不要有其他说明文字。直接返回 JSON 数组。按时间从旧到新排序。"""
            
            # 调用 GLM-4.6V
            response = client.chat.completions.create(
                model="glm-4.6v",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                thinking={"type": "enabled"}
            )
            
            # 解析结果
            result_text = response.choices[0].message.content.strip()
            
            # 尝试从文本中提取 JSON
            import json
            import re
            
            # 查找 JSON 数组
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                messages = json.loads(json_match.group())
                
                # 限制数量
                messages = messages[:limit]
                
                logger.info("GLM-4.6V 识别到 %d 条消息", len(messages))
                return messages
            else:
                logger.warning("GLM 返回格式不正确：%s", result_text[:200])
                return []
                
        except ImportError:
            logger.error("zai-sdk 未安装，无法使用 GLM-4.6V")
            return []
        except Exception as e:
            logger.error("GLM-4.6V OCR 识别失败：%s", e)
            return []
    
    # ----------------------------------------------------------------
    # 窗口管理
    # ----------------------------------------------------------------
    
    def activate_window(self) -> bool:
        """激活微信窗口到前台
        
        Returns:
            是否成功
        """
        try:
            # 使用快捷键激活（最可靠的方式）
            hotkey = self.config.get("window", {}).get("activate_hotkey", "Ctrl+Alt+W")
            key_parts = hotkey.replace("+", " ").split()
            
            # 转换为 pyautogui 格式
            keys = [k.lower().replace("ctrl", "command" if sys.platform == "darwin" else "ctrl") 
                   for k in key_parts]
            
            pyautogui.hotkey(*keys)
            time.sleep(0.5)
            
            logger.debug("微信窗口已激活")
            return True
            
        except Exception as e:
            logger.error("激活窗口失败：%s", e)
            return False
    
    def launch_wechat(self) -> bool:
        """启动微信客户端
        
        Returns:
            bool: 是否成功启动
        """
        try:
            import subprocess
            import os
            
            # 常见的微信安装路径（优先 Weixin.exe）
            possible_paths = [
                os.path.expandvars(r"%ProgramFiles(x86)%\Tencent\WeChat\WeChat.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tencent\WeChat\WeChat.exe"),
                r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
                r"D:\Program Files\Tencent\WeChat\WeChat.exe",
                os.path.expandvars(r"%ProgramW6432%\Tencent\WeChat\WeChat.exe"),
                "Weixin.exe",  # 微软商店版本（优先，首字母大写）
                "WeChat.exe",  # 桌面版
            ]
            
            for wechat_path in possible_paths:
                if os.path.exists(wechat_path):
                    logger.info("从 %s 启动微信", wechat_path)
                    subprocess.Popen([wechat_path])
                    return True
            
            # 尝试使用 start 命令（优先 Weixin）
            logger.info("尝试使用 start 命令启动微信")
            subprocess.Popen(["start", "Weixin"], shell=True)
            return True
            
        except Exception as e:
            logger.error("启动微信失败：%s", e)
            return False
    
    def find_wechat_window(self) -> int | None:
        """查找微信窗口句柄
        
        Returns:
            窗口句柄，找不到返回 None
        """
        try:
            import win32gui
            import win32con
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    # 严格匹配微信窗口名称，避免误选其他应用窗口
                    # 微信窗口通常包含以下特征：
                    # 1. 窗口标题就是"微信"或"WeChat"
                    # 2. 窗口类名包含 WeChatMainWndForPC
                    # 排除包含其他关键词的窗口（如 weclaw、winclaw 等）
                    if any(keyword in window_text for keyword in ["微信", "WeChat", "Weixin"]):
                        # 排除非微信窗口（如 weclaw 助手窗口）
                        if any(exclude in window_text.lower() for exclude in ["weclaw", "winclaw", "助手"]):
                            logger.debug("排除非微信窗口：%s", window_text)
                            return True
                        
                        # 进一步验证窗口类名（微信 PC 版主窗口类名通常为 WeChatMainWndForPC 或 Qt 框架）
                        try:
                            class_name = win32gui.GetClassName(hwnd)
                            # 如果类名包含 WeChat、Weixin、微信或 Qt（微信使用 Qt 框架），确认是微信窗口
                            if any(kw in class_name for kw in ["WeChat", "Weixin", "微信"]):
                                windows.append(hwnd)
                                logger.debug("确认微信窗口：hwnd=%d, title=%s, class=%s", hwnd, window_text, class_name)
                            elif "Qt" in class_name:
                                # Qt 框架窗口，结合标题判断是否为微信
                                # 微信的 Qt 窗口通常没有明显的类名特征，但标题包含"微信"
                                windows.append(hwnd)
                                logger.debug("确认为 Qt 版微信窗口：hwnd=%d, title=%s, class=%s", hwnd, window_text, class_name)
                            else:
                                # 类名不匹配，跳过
                                logger.debug("窗口类名不匹配：%s (类名：%s)", window_text, class_name)
                        except Exception as e:
                            # 无法获取类名时，使用标题匹配作为备选
                            logger.warning("无法获取窗口类名，使用标题匹配：%s, 错误：%s", window_text, e)
                            windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                self._window_handle = windows[0]
                logger.debug("找到微信窗口：%d, 标题：%s", self._window_handle, win32gui.GetWindowText(self._window_handle))
                return self._window_handle
            
            logger.warning("未找到微信窗口")
            return None
            
        except Exception as e:
            logger.error("查找窗口失败：%s", e)
            return None
    
    # ----------------------------------------------------------------
    # 消息发送
    # ----------------------------------------------------------------
    
    def send_message(self, message: str, chat_name: str | None = None, delay: float = 2.0) -> bool:
        """发送消息到指定聊天
        
        Args:
            message: 消息内容
            chat_name: 聊天对象名称，None 则使用当前聊天
            delay: 延迟发送时间（秒）
        
        Returns:
            是否成功
        """
        try:
            # 1. 确保窗口在前台
            if not self._ensure_window_active():
                return False
            
            # 2. 切换到指定聊天（如果需要）
            if chat_name and chat_name != self._get_current_chat_name():
                if not self.switch_to_chat(chat_name):
                    logger.warning("切换聊天失败，使用当前聊天")
            
            # 3. 等待延迟
            if delay > 0:
                time.sleep(delay)
            
            # 4. 清空输入框
            self._clear_input()
            
            # 5. 复制消息到剪贴板并粘贴
            if not self._input_message(message):
                return False
            
            # 6. 发送消息（按 Enter）
            pyautogui.press('enter')
            time.sleep(0.3)
            
            logger.info("消息已发送：%s", message[:50])
            return True
            
        except Exception as e:
            logger.error("发送消息失败：%s", e)
            return False
    
    def _ensure_window_active(self) -> bool:
        """确保微信窗口在前台且聊天区域激活
        
        Returns:
            是否成功
        """
        try:
            # 检查窗口是否存在
            if not self.find_wechat_window():
                logger.warning("微信窗口未找到")
                return False
            
            # 激活窗口
            if not self.activate_window():
                return False
            
            # 双击输入框确保聚焦
            self._focus_input()
            
            return True
            
        except Exception as e:
            logger.error("确保窗口激活失败：%s", e)
            return False
    
    def _clear_input(self) -> bool:
        """清空输入框
        
        Returns:
            是否成功
        """
        try:
            # Ctrl+A 全选
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            # Delete 删除
            pyautogui.press('delete')
            time.sleep(0.2)
            
            return True
        except Exception as e:
            logger.error("清空输入框失败：%s", e)
            return False
    
    def _focus_input(self) -> bool:
        """聚焦到输入框
        
        Returns:
            是否成功
        """
        try:
            # 双击输入框区域（需要图像定位，这里简化处理）
            # 实际使用时可能需要屏幕坐标或图像匹配
            logger.debug("输入框已聚焦（通过窗口激活自动完成）")
            return True
        except Exception as e:
            logger.error("聚焦输入框失败：%s", e)
            return False
    
    def _input_message(self, message: str) -> bool:
        """输入消息到剪贴板并粘贴
        
        Args:
            message: 消息内容
        
        Returns:
            是否成功
        """
        try:
            # 使用剪贴板方式（支持中文）
            if pyperclip is None:
                logger.error("pyperclip 未安装，无法输入中文")
                return False
            
            pyperclip.copy(message)
            time.sleep(0.2)
            
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            
            return True
            
        except Exception as e:
            logger.error("输入消息失败：%s", e)
            return False
    
    # ----------------------------------------------------------------
    # 聊天管理
    # ----------------------------------------------------------------
    
    def switch_to_chat(self, chat_name: str) -> bool:
        """切换到指定聊天
        
        Args:
            chat_name: 聊天对象名称
        
        Returns:
            是否成功
        """
        try:
            # 确保窗口激活
            if not self._ensure_window_active():
                return False
            
            import pyautogui
            import time
            
            # 步骤 1: 点击微信左侧聊天列表区域（确保聚焦）
            screen_width, screen_height = pyautogui.size()
            click_x = int(screen_width * 0.1)
            click_y = int(screen_height * 0.3)
            
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            
            # 步骤 2: 直接输入聊天名称进行搜索
            # 微信支持在当前聊天界面直接输入名称搜索联系人
            pyperclip_copy(chat_name)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            
            # 步骤 3: 按 Enter 确认（如果有搜索结果弹出）
            # pyautogui.press('enter')
            
            logger.info("已尝试切换到聊天：%s", chat_name)
            return True
            
        except Exception as e:
            logger.error("切换聊天失败：%s", e)
            return False
    
    def _get_current_chat_name(self) -> str | None:
        """获取当前聊天对象名称
        
        Returns:
            聊天对象名称
        """
        # TODO: 实现当前聊天检测
        # 可以通过 OCR 识别聊天标题区域
        return None
    
    def get_chat_list(self, limit: int = 50, chat_type: str = "all") -> list[dict[str, Any]]:
        """获取最近聊天列表
        
        Args:
            limit: 返回数量限制
            chat_type: 聊天类型 (all/individual/group)
        
        Returns:
            聊天列表，每项包含 {name, last_message, timestamp, is_group}
        """
        try:
            # 确保窗口激活
            if not self._ensure_window_active():
                logger.warning("微信窗口未激活，无法获取聊天列表")
                return []
            
            # 使用 pyautogui 截取屏幕
            import pyautogui
            from PIL import ImageGrab
            import time
            import base64
            import io
            
            # 等待窗口稳定
            time.sleep(0.5)
            
            # 获取屏幕尺寸
            screen_width, screen_height = pyautogui.size()
            
            # 微信聊天列表通常在左侧，大约占屏幕宽度的 1/4
            # 截取左侧区域（用于 OCR 识别聊天名称）
            left_x = 0
            top_y = int(screen_height * 0.15)  # 避开顶部搜索栏
            right_x = int(screen_width * 0.28)
            bottom_y = int(screen_height * 0.9)
            
            # 截取屏幕区域
            screenshot = ImageGrab.grab(bbox=(left_x, top_y, right_x, bottom_y))
            
            # 将图片转换为 base64
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # 调用 GLM-4.6V 进行 OCR 识别
            chat_list = self._ocr_chat_list_with_glm(img_base64, limit, chat_type)
            
            logger.info("获取到 %d 个聊天对象", len(chat_list))
            return chat_list
            
        except Exception as e:
            logger.error("获取聊天列表失败：%s", e)
            return []
    
    # ----------------------------------------------------------------
    # 消息监听与 OCR
    # ----------------------------------------------------------------
    
    def start_message_monitor(self, auto_reply: bool = False, callback: Callable | None = None):
        """启动消息监听
        
        Args:
            auto_reply: 是否启用自动回复
            callback: 新消息回调函数
        """
        self._message_monitor_active = True
        self._auto_reply_enabled = auto_reply
        self._on_new_message = callback
        
        logger.info("消息监听已启动，自动回复：%s", auto_reply)
        
        check_interval = self.config.get("message_monitor", {}).get("check_interval", 10.0)
        
        while self._message_monitor_active:
            try:
                # 检测消息变化
                if self._check_message_changes():
                    # 有新消息
                    messages = self._get_current_messages()
                    
                    if callback:
                        callback(messages)
                    
                    # 自动回复
                    if auto_reply:
                        self._handle_auto_reply(messages)
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("用户中断监听")
                break
            except Exception as e:
                logger.error("监听过程出错：%s", e)
                time.sleep(check_interval)
        
        logger.info("消息监听已停止")
    
    def stop_message_monitor(self):
        """停止消息监听"""
        self._message_monitor_active = False
        logger.info("消息监听标志已重置")
    
    def _check_message_changes(self) -> bool:
        """检查聊天内容是否变化（使用图像 Hash）
        
        Returns:
            是否有变化
        """
        try:
            # TODO: 截取聊天区域并计算 Hash
            # 对比上一次 Hash 判断是否变化
            
            # 临时实现：始终返回 False
            return False
            
        except Exception as e:
            logger.error("检查消息变化失败：%s", e)
            return False
    
    def _get_current_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取当前聊天的消息列表
        
        Args:
            limit: 返回数量限制
        
        Returns:
            消息列表，每项包含 {sender, content, timestamp, is_self}
        """
        try:
            # 确保窗口激活
            if not self._ensure_window_active():
                return []
            
            import time
            import pyautogui
            from PIL import ImageGrab
            import base64
            import io
            
            # 等待窗口稳定
            time.sleep(0.5)
            
            # 获取屏幕尺寸
            screen_width, screen_height = pyautogui.size()
            
            # 截取聊天对话区域（右侧主要区域）
            left_x = int(screen_width * 0.3)
            top_y = int(screen_height * 0.15)
            right_x = int(screen_width * 0.95)
            bottom_y = int(screen_height * 0.85)
            
            # 截取屏幕区域
            screenshot = ImageGrab.grab(bbox=(left_x, top_y, right_x, bottom_y))
            
            # 将图片转换为 base64
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # 调用 GLM-4.6V 进行 OCR 识别
            messages = self._ocr_messages_with_glm(img_base64, limit)
            
            logger.info("获取到 %d 条消息", len(messages))
            return messages
            
        except Exception as e:
            logger.error("获取消息失败：%s", e)
            return []
    
    def _handle_auto_reply(self, messages: list[dict[str, Any]]):
        """处理自动回复逻辑
        
        Args:
            messages: 消息列表
        """
        if not messages:
            return
        
        last_message = messages[-1]
        
        # 排除规则检查
        exclude_chats = self.config.get("llm", {}).get("exclude_chats", [])
        chat_name = last_message.get("chat_name", "")
        
        for keyword in exclude_chats:
            if keyword in chat_name:
                logger.debug("排除聊天：%s", chat_name)
                return
        
        # 生成回复
        reply = self._generate_reply(last_message)
        
        if reply:
            # 随机延迟
            delay_min = self.config.get("llm", {}).get("delay_min", 3.0)
            delay_max = self.config.get("llm", {}).get("delay_max", 8.0)
            delay = random.uniform(delay_min, delay_max)
            
            time.sleep(delay)
            
            # 发送回复
            if self.send_message(reply, delay=0):
                logger.info("自动回复已发送：%s", reply[:50])
                
                if self._on_reply_sent:
                    self._on_reply_sent(reply)
    
    # ----------------------------------------------------------------
    # 智能回复生成
    # ----------------------------------------------------------------
    
    def _generate_reply(self, message: dict[str, Any]) -> str | None:
        """生成智能回复
        
        Args:
            message: 消息内容
        
        Returns:
            回复内容
        """
        try:
            # TODO: 调用 LLM 生成回复
            # 可以使用 knowledge_rag 或直接调用 LLM
            
            content = message.get("content", "")
            chat_name = message.get("chat_name", "")
            
            logger.debug("为 %s 生成回复：%s", chat_name, content[:50])
            
            # 临时返回
            return "收到，稍后回复你~"
            
        except Exception as e:
            logger.error("生成回复失败：%s", e)
            return None
    
    def ocr_chat_screenshot(self, screenshot_path: str) -> str:
        """对聊天截图进行 OCR 识别
        
        Args:
            screenshot_path: 截图路径
        
        Returns:
            识别的文字内容
        """
        try:
            # TODO: 调用 GLM 视觉模型进行 OCR
            logger.debug("OCR 识别截图：%s", screenshot_path)
            
            return ""
            
        except Exception as e:
            logger.error("OCR 识别失败：%s", e)
            return ""
    
    # ----------------------------------------------------------------
    # 配置管理
    # ----------------------------------------------------------------
    
    def set_target_chats(self, chat_names: list[str]):
        """设置目标聊天列表（只监听这些聊天）
        
        Args:
            chat_names: 聊天名称列表
        """
        self._target_chats = chat_names
        logger.info("已设置目标聊天：%s", chat_names)
    
    def enable_smart_reply(self, enabled: bool = True):
        """启用/禁用智能回复
        
        Args:
            enabled: 是否启用
        """
        self._auto_reply_enabled = enabled
        logger.info("智能回复已%s", "启用" if enabled else "禁用")
    
    def update_config(self, key: str, value: Any):
        """更新配置项
        
        Args:
            key: 配置键（支持点号，如 llm.delay_min）
            value: 配置值
        """
        keys = key.split(".")
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.debug("配置已更新：%s = %s", key, value)
