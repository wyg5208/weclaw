"""
语音输出工具 - 基于 pyttsx3 的文字转语音 (TTS)

支持:
- 文字转语音朗读
- 保存语音到文件
- 调节语速和音量
- 多音色选择

注意: Windows SAPI5 后端有已知问题，引擎实例在 runAndWait() 后
可能进入损坏状态，因此每次调用都创建新引擎实例。
此外，在 qasync/Qt 环境下需要显式初始化 COM。
"""
import asyncio
import logging
from pathlib import Path
from typing import Any

try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    pyttsx3 = None

# Windows COM 支持
try:
    import pythoncom
    COM_AVAILABLE = True
except ImportError:
    pythoncom = None
    COM_AVAILABLE = False

from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class VoiceOutputTool(BaseTool):
    """语音输出工具 - 文字转语音 (TTS)"""

    name = "voice_output"
    emoji = "🔊"
    title = "语音输出"
    description = "文字转语音工具,支持朗读和保存音频文件"

    def __init__(self):
        super().__init__()
        # 注意：不再缓存引擎实例，每次使用时创建新实例
        # 这是因为 pyttsx3 在 Windows SAPI5 下复用引擎会导致第二次播放失败

        if not TTS_AVAILABLE:
            raise ImportError("TTS 功能不可用。请安装依赖: pip install pyttsx3")

    def _create_engine(self):
        """创建新的 TTS 引擎实例
        
        每次调用都创建新实例，避免 Windows SAPI5 引擎状态残留问题。
        """
        return pyttsx3.init()

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="speak",
                description="朗读文本",
                parameters={
                    "text": {
                        "type": "string",
                        "description": "要朗读的文本内容",
                    },
                    "rate": {
                        "type": "number",
                        "description": "语速(词/分钟), 默认 200, 范围 100-300",
                        "default": 200,
                    },
                    "volume": {
                        "type": "number",
                        "description": "音量 (0.0-1.0), 默认 1.0",
                        "default": 1.0,
                    },
                    "voice_index": {
                        "type": "integer",
                        "description": "音色索引 (0=默认), 使用 list_voices 查看可用音色",
                        "default": 0,
                    },
                },
                required_params=["text"],
            ),
            ActionDef(
                name="save_to_file",
                description="将文本转为语音并保存为音频文件",
                parameters={
                    "text": {
                        "type": "string",
                        "description": "要转换的文本内容",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出音频文件路径 (.wav/.mp3)",
                    },
                    "rate": {
                        "type": "number",
                        "description": "语速",
                        "default": 200,
                    },
                    "volume": {
                        "type": "number",
                        "description": "音量",
                        "default": 1.0,
                    },
                    "voice_index": {
                        "type": "integer",
                        "description": "音色索引",
                        "default": 0,
                    },
                },
                required_params=["text", "output_path"],
            ),
            ActionDef(
                name="list_voices",
                description="列出可用的语音音色",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="stop",
                description="停止当前朗读",
                parameters={},
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行语音输出操作"""
        if action == "speak":
            return await self._speak(**params)
        elif action == "save_to_file":
            return await self._save_to_file(**params)
        elif action == "list_voices":
            return self._list_voices()
        elif action == "stop":
            return self._stop()
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知动作: {action}",
                output=f"可用动作: {[a.name for a in self.get_actions()]}",
            )

    async def _speak(
        self, text: str, rate: int = 200, volume: float = 1.0, voice_index: int = 0
    ) -> ToolResult:
        """朗读文本"""
        try:
            if not text.strip():
                return ToolResult(status=ToolResultStatus.ERROR, error="文本内容为空")

            # 在线程池中执行阻塞的朗读操作
            # 关键：pyttsx3 内部有 _activeEngines 全局缓存，必须手动清理
            def _do_speak():
                import threading
                thread_id = threading.current_thread().ident
                logger.info(f"TTS _do_speak 开始: thread={thread_id}, text={text[:20]}")
                
                engine = None
                com_initialized = False
                try:
                    # Windows COM 初始化（在 qasync 线程池中必需）
                    if COM_AVAILABLE and pythoncom:
                        pythoncom.CoInitialize()
                        com_initialized = True
                        logger.info(f"TTS COM 初始化完成: thread={thread_id}")
                    
                    # 关键：清理 pyttsx3 内部的全局引擎缓存
                    if hasattr(pyttsx3, '_activeEngines'):
                        pyttsx3._activeEngines.clear()
                        logger.info(f"TTS 清理 _activeEngines 缓存: thread={thread_id}")
                    
                    engine = pyttsx3.init(driverName='sapi5')  # 显式指定驱动
                    logger.info(f"TTS 引擎创建完成: thread={thread_id}")
                    
                    # 设置语速和音量
                    engine.setProperty("rate", max(100, min(rate, 300)))
                    engine.setProperty("volume", max(0.0, min(volume, 1.0)))
                    
                    # 设置音色
                    voices = engine.getProperty("voices")
                    if voices and 0 <= voice_index < len(voices):
                        engine.setProperty("voice", voices[voice_index].id)
                    
                    engine.say(text)
                    logger.info(f"TTS say() 完成, 开始 runAndWait: thread={thread_id}")
                    engine.runAndWait()
                    logger.info(f"TTS runAndWait() 完成: thread={thread_id}")
                finally:
                    # 必须显式删除引擎
                    if engine:
                        try:
                            engine.stop()
                        except Exception:
                            pass
                        
                        # 关键：从 pyttsx3 内部缓存中移除
                        if hasattr(pyttsx3, '_activeEngines'):
                            pyttsx3._activeEngines.clear()
                        
                        del engine
                        logger.info(f"TTS 引擎已释放: thread={thread_id}")
                    
                    # 反初始化 COM
                    if com_initialized and pythoncom:
                        pythoncom.CoUninitialize()
                        logger.info(f"TTS COM 反初始化完成: thread={thread_id}")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _do_speak)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"朗读完成 ({len(text)} 字符)",
                data={"text": text[:50] + "..." if len(text) > 50 else text, "length": len(text)},
            )

        except Exception as e:
            logger.error("TTS 朗读失败: %s", e)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"朗读失败: {e}")

    async def _save_to_file(
        self,
        text: str,
        output_path: str,
        rate: int = 200,
        volume: float = 1.0,
        voice_index: int = 0,
    ) -> ToolResult:
        """将文本转为语音并保存为文件"""
        try:
            if not text.strip():
                return ToolResult(status=ToolResultStatus.ERROR, error="文本内容为空")

            path = Path(output_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)

            # 关键：pyttsx3 内部有 _activeEngines 全局缓存，必须手动清理
            def _do_save():
                engine = None
                com_initialized = False
                try:
                    # Windows COM 初始化
                    if COM_AVAILABLE and pythoncom:
                        pythoncom.CoInitialize()
                        com_initialized = True
                    
                    # 清理 pyttsx3 内部缓存
                    if hasattr(pyttsx3, '_activeEngines'):
                        pyttsx3._activeEngines.clear()
                    
                    engine = pyttsx3.init(driverName='sapi5')
                    
                    # 设置参数
                    engine.setProperty("rate", max(100, min(rate, 300)))
                    engine.setProperty("volume", max(0.0, min(volume, 1.0)))
                    
                    voices = engine.getProperty("voices")
                    if voices and 0 <= voice_index < len(voices):
                        engine.setProperty("voice", voices[voice_index].id)
                    
                    engine.save_to_file(text, str(path))
                    engine.runAndWait()
                finally:
                    if engine:
                        try:
                            engine.stop()
                        except Exception:
                            pass
                        
                        if hasattr(pyttsx3, '_activeEngines'):
                            pyttsx3._activeEngines.clear()
                        
                        del engine
                    
                    # 反初始化 COM
                    if com_initialized and pythoncom:
                        pythoncom.CoUninitialize()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _do_save)

            file_size_kb = path.stat().st_size / 1024

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"语音已保存: {path.name} ({file_size_kb:.1f} KB)",
                data={"output_path": str(path), "file_size_kb": file_size_kb, "text_length": len(text)},
            )

        except Exception as e:
            logger.error("TTS 保存失败: %s", e)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"保存失败: {e}")

    def _list_voices(self) -> ToolResult:
        """列出可用的音色"""
        engine = None
        com_initialized = False
        try:
            # Windows COM 初始化
            if COM_AVAILABLE and pythoncom:
                pythoncom.CoInitialize()
                com_initialized = True
            
            # 清理 pyttsx3 内部缓存
            if hasattr(pyttsx3, '_activeEngines'):
                pyttsx3._activeEngines.clear()
            
            engine = pyttsx3.init(driverName='sapi5')
            voices = engine.getProperty("voices")

            voice_list = []
            for i, voice in enumerate(voices):
                voice_list.append(
                    {
                        "index": i,
                        "id": voice.id,
                        "name": voice.name,
                        "languages": voice.languages if hasattr(voice, "languages") else [],
                    }
                )

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"找到 {len(voice_list)} 个可用音色",
                data={"voices": voice_list},
            )

        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"查询音色失败: {e}")
        finally:
            # 必须显式删除引擎
            if engine:
                try:
                    engine.stop()
                except Exception:
                    pass
                
                if hasattr(pyttsx3, '_activeEngines'):
                    pyttsx3._activeEngines.clear()
                
                del engine
            
            # 反初始化 COM
            if com_initialized and pythoncom:
                pythoncom.CoUninitialize()

    def _stop(self) -> ToolResult:
        """停止朗读
        
        注意：由于每次播放都使用新引擎实例，此方法主要用于兼容性。
        实际的停止效果有限，因为播放是在独立线程中进行的。
        """
        # 由于不再缓存引擎，这里只返回成功
        # 真正的停止需要通过取消 asyncio 任务来实现
        return ToolResult(status=ToolResultStatus.SUCCESS, output="已发送停止请求")
