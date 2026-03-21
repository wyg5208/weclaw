"""
语音输出工具 - 基于 pyttsx3 的文字转语音 (TTS)

支持:
- 文字转语音朗读
- 保存语音到文件
- 调节语速和音量
- 多音色选择
"""
import asyncio
from pathlib import Path
from typing import Any, Optional

try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    pyttsx3 = None

from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus


class VoiceOutputTool(BaseTool):
    """语音输出工具 - 文字转语音 (TTS)"""

    name = "voice_output"
    emoji = "🔊"
    title = "语音输出"
    description = "文字转语音工具,支持朗读和保存音频文件"

    def __init__(self):
        super().__init__()
        self._engine: Optional[Any] = None

        if not TTS_AVAILABLE:
            raise ImportError("TTS 功能不可用。请安装依赖: pip install pyttsx3")

    def _get_engine(self):
        """获取 TTS 引擎实例"""
        if self._engine is None:
            self._engine = pyttsx3.init()
        return self._engine

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

            engine = self._get_engine()

            # 设置语速和音量
            engine.setProperty("rate", max(100, min(rate, 300)))
            engine.setProperty("volume", max(0.0, min(volume, 1.0)))

            # 设置音色
            voices = engine.getProperty("voices")
            if voices and 0 <= voice_index < len(voices):
                engine.setProperty("voice", voices[voice_index].id)

            # 在线程池中执行阻塞的朗读操作
            # 注意：pyttsx3 在 Windows 上有已知问题，需要先 stop() 清理状态
            # 否则第二次调用 runAndWait() 可能立即返回而不播放
            def _do_speak():
                try:
                    engine.stop()  # 清理之前的播放状态（关键修复）
                except Exception:
                    pass  # 忽略 stop 失败
                engine.say(text)
                engine.runAndWait()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _do_speak)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"朗读完成 ({len(text)} 字符)",
                data={"text": text[:50] + "..." if len(text) > 50 else text, "length": len(text)},
            )

        except Exception as e:
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

            engine = self._get_engine()

            # 设置参数
            engine.setProperty("rate", max(100, min(rate, 300)))
            engine.setProperty("volume", max(0.0, min(volume, 1.0)))

            voices = engine.getProperty("voices")
            if voices and 0 <= voice_index < len(voices):
                engine.setProperty("voice", voices[voice_index].id)

            # 保存到文件
            # 注意：与 speak 相同，需要先 stop() 清理引擎状态
            def _do_save():
                try:
                    engine.stop()  # 清理之前的状态
                except Exception:
                    pass
                engine.save_to_file(text, str(path))
                engine.runAndWait()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _do_save)

            file_size_kb = path.stat().st_size / 1024

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"语音已保存: {path.name} ({file_size_kb:.1f} KB)",
                data={"output_path": str(path), "file_size_kb": file_size_kb, "text_length": len(text)},
            )

        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"保存失败: {e}")

    def _list_voices(self) -> ToolResult:
        """列出可用的音色"""
        try:
            engine = self._get_engine()
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

    def _stop(self) -> ToolResult:
        """停止朗读"""
        try:
            if self._engine:
                self._engine.stop()

            return ToolResult(status=ToolResultStatus.SUCCESS, output="已停止朗读")

        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"停止失败: {e}")
