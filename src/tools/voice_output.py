""" 
语音输出工具 - 支持多种 TTS 引擎

支持引擎:
- edge-tts: Edge 在线引擎，音质好（实时对话主引擎）
- pyttsx3: Windows SAPI5 本地引擎（降级备选）
- Qwen3-TTS: 本地大模型，高质量多语言语音合成（仅用于异步任务如故事生成、保存文件）
- gtts: Google 在线引擎

实时对话优先级: edge_tts > pyttsx3 > gtts
Qwen3-TTS 绝不用于实时对话，仅用于 save_to_file 等异步任务。
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# ========== TTS 引擎可用性检测 ==========

TTS_ENGINE_PRIORITY = ["edge_tts", "pyttsx3", "qwen_tts", "gtts"]

# Qwen3-TTS 可用性
QWEN_TTS_AVAILABLE = None
try:
    from src.core.qwen_tts_client import QwenTTSClient, PRESET_VOICES
    QWEN_TTS_AVAILABLE = True
except ImportError:
    QWEN_TTS_AVAILABLE = False
    PRESET_VOICES = {}

# pyttsx3 可用性
PYTTSX3_AVAILABLE = None
_pyttsx3 = None
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
    _pyttsx3 = pyttsx3
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

# Windows COM 支持
try:
    import pythoncom
    COM_AVAILABLE = True
except ImportError:
    pythoncom = None
    COM_AVAILABLE = False


def _get_available_engine() -> str:
    """获取可用的 TTS 引擎，按优先级返回第一个可用的。
    
    优先级: edge_tts > pyttsx3 > qwen_tts > gtts
    """
    # 1. 优先尝试 Edge TTS
    try:
        import edge_tts
        return "edge_tts"
    except ImportError:
        pass
    
    # 2. pyttsx3
    if PYTTSX3_AVAILABLE:
        return "pyttsx3"
    
    # 3. Qwen3-TTS
    if QWEN_TTS_AVAILABLE:
        try:
            from src.core.qwen_tts_client import QwenTTSClient
            client = QwenTTSClient(preload=False)
            if client.is_available:
                return "qwen_tts"
        except Exception:
            pass
    
    # 默认回退到 pyttsx3
    return "pyttsx3"


class VoiceOutputTool(BaseTool):
    """语音输出工具 - 多引擎文字转语音 (TTS)"""

    name = "voice_output"
    emoji = "🔊"
    title = "语音输出"
    description = "文字转语音工具,支持朗读和保存音频文件 (Qwen3-TTS/pyttsx3/edge-tts)"

    def __init__(self):
        super().__init__()
        self._engine = _get_available_engine()
        logger.info(f"VoiceOutputTool 初始化，引擎: {self._engine}")
        
        # 预加载 Qwen3-TTS 客户端
        self._qwen_client = None
        if self._engine == "qwen_tts":
            self._init_qwen_client()
    
    def _init_qwen_client(self) -> bool:
        """初始化 Qwen3-TTS 客户端"""
        if not QWEN_TTS_AVAILABLE:
            return False
        
        try:
            from src.core.qwen_tts_client import QwenTTSClient
            self._qwen_client = QwenTTSClient(preload=True)
            return self._qwen_client.is_available
        except Exception as e:
            logger.warning(f"Qwen3-TTS 初始化失败: {e}")
            return False

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="speak",
                description="朗读文本 (支持 Qwen3-TTS / pyttsx3)",
                parameters={
                    "text": {
                        "type": "string",
                        "description": "要朗读的文本内容",
                    },
                    "rate": {
                        "type": "number",
                        "description": "语速 (pyttsx3: 100-300 词/分钟, Qwen3-TTS: 0.5-2.0 倍速)",
                        "default": 200,
                    },
                    "volume": {
                        "type": "number",
                        "description": "音量 (0.0-1.0), 默认 1.0",
                        "default": 1.0,
                    },
                    "voice": {
                        "type": "string",
                        "description": "Qwen3-TTS 音色 (vivian/alice/ryan/emma/lucas/anna/james/mia/david), 或 pyttsx3 音色索引",
                        "default": "vivian",
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
                    "voice": {
                        "type": "string",
                        "description": "音色名称或索引",
                        "default": "vivian",
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
        self, text: str, rate: int = 200, volume: float = 1.0, voice: str = "vivian"
    ) -> ToolResult:
        """朗读文本
        
        引擎优先级: edge_tts > pyttsx3
        Qwen3-TTS 不用于实时朗读，仅用于 save_to_file。
        """
        try:
            if not text.strip():
                return ToolResult(status=ToolResultStatus.ERROR, error="文本内容为空")

            # 实时朗读优先用 Edge TTS，降级用 pyttsx3
            if self._engine == "edge_tts":
                return await self._speak_edge_tts(text)
            elif self._engine == "pyttsx3":
                return await self._speak_pyttsx3(text, rate, volume, voice)
            elif self._engine == "qwen_tts":
                # Qwen3-TTS 降级为 pyttsx3 来朗读（不用于实时）
                return await self._speak_pyttsx3(text, rate, volume, voice)
            else:
                return await self._speak_pyttsx3(text, rate, volume, voice)

        except Exception as e:
            logger.error("TTS 朗读失败: %s", e)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"朗读失败: {e}")

    async def _speak_edge_tts(self, text: str) -> ToolResult:
        """使用 Edge TTS 朗读（内存处理，无临时文件）。"""
        def _do_speak():
            import io
            import subprocess
            import numpy as np
            import simpleaudio as sa

            try:
                import edge_tts
                import asyncio

                # 收集 MP3 数据到内存
                mp3_buffer = io.BytesIO()

                async def _gather_audio():
                    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            mp3_buffer.write(chunk["data"])

                loop = asyncio.new_event_loop()
                loop.run_until_complete(_gather_audio())
                loop.close()

                mp3_data = mp3_buffer.getvalue()
                if not mp3_data:
                    raise RuntimeError("Edge TTS 未返回音频数据")

                # ffmpeg pipe 转码
                from src.conversation.tts_player import _find_ffmpeg
                ffmpeg_path = _find_ffmpeg()
                process = subprocess.Popen(
                    [ffmpeg_path, '-i', 'pipe:0', '-f', 's16le',
                     '-acodec', 'pcm_s16le', '-ar', '24000', '-ac', '1', 'pipe:1'],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                pcm_data, _ = process.communicate(input=mp3_data)

                if not pcm_data:
                    raise RuntimeError("ffmpeg 转码失败")

                # 播放
                audio_np = np.frombuffer(pcm_data, dtype=np.int16)
                play_obj = sa.play_buffer(audio_np, 1, 2, 24000)
                play_obj.wait_done()

            except Exception as e:
                logger.error(f"Edge TTS 朗读失败: {e}")
                raise

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_speak)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"朗读完成 ({len(text)} 字符) [Edge TTS]",
            data={"text": text[:50] + "..." if len(text) > 50 else text, "length": len(text), "engine": "edge_tts"},
        )

    async def _speak_qwen_tts(
        self, text: str, rate: float = 1.0, voice: str = "vivian"
    ) -> ToolResult:
        """使用 Qwen3-TTS 朗读"""
        def _do_speak():
            import numpy as np
            import soundfile as sf
            import winsound
            
            try:
                # 确保客户端已初始化
                if not self._qwen_client:
                    self._init_qwen_client()
                
                if not self._qwen_client or not self._qwen_client.is_available:
                    raise RuntimeError("Qwen3-TTS 不可用")
                
                # 转换语速
                speed = rate / 200.0 if rate <= 2.0 else 1.0
                speed = max(0.5, min(2.0, speed))
                
                # 生成语音
                from src.core.qwen_tts_client import QwenTTSLanguage
                wavs, sr = self._qwen_client.speak(
                    text=text,
                    language=QwenTTSLanguage.CHINESE,
                    voice=voice,
                    speed=speed
                )
                
                # 转换为 numpy 数组
                audio_data = wavs[0] if isinstance(wavs, list) else wavs
                
                # 归一化到 int16 范围
                if audio_data.dtype != np.int16:
                    audio_data = (audio_data * 32767).astype(np.int16)
                
                # 保存到临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
                    temp_file = Path(f.name)
                    sf.write(str(temp_file), audio_data, sr)
                
                # 播放
                winsound.PlaySound(str(temp_file), winsound.SND_FILENAME)
                
                # 删除临时文件
                try:
                    temp_file.unlink()
                except Exception:
                    pass
                    
            except Exception as e:
                logger.error(f"Qwen3-TTS 朗读失败: {e}")
                raise

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_speak)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"朗读完成 ({len(text)} 字符) [Qwen3-TTS]",
            data={"text": text[:50] + "..." if len(text) > 50 else text, "length": len(text), "engine": "qwen_tts"},
        )

    async def _speak_pyttsx3(
        self, text: str, rate: int = 200, volume: float = 1.0, voice: str = "0"
    ) -> ToolResult:
        """使用 pyttsx3 朗读（兼容旧参数）"""
        # 解析音色
        try:
            voice_index = int(voice) if voice.isdigit() else 0
        except (ValueError, TypeError):
            voice_index = 0

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
            output=f"朗读完成 ({len(text)} 字符) [pyttsx3]",
            data={"text": text[:50] + "..." if len(text) > 50 else text, "length": len(text), "engine": "pyttsx3"},
        )

    async def _save_to_file(
        self,
        text: str,
        output_path: str,
        rate: int = 200,
        volume: float = 1.0,
        voice: str = "vivian",
    ) -> ToolResult:
        """将文本转为语音并保存为文件"""
        try:
            if not text.strip():
                return ToolResult(status=ToolResultStatus.ERROR, error="文本内容为空")

            path = Path(output_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)

            # 根据引擎选择实现
            if self._engine == "qwen_tts":
                return await self._save_to_file_qwen_tts(text, path, rate, voice)
            else:
                # 解析音色
                try:
                    voice_index = int(voice) if voice.isdigit() else 0
                except (ValueError, TypeError):
                    voice_index = 0
                return await self._save_to_file_pyttsx3(text, path, rate, volume, voice_index)

        except Exception as e:
            logger.error("TTS 保存失败: %s", e)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"保存失败: {e}")

    async def _save_to_file_qwen_tts(
        self, text: str, path: Path, rate: float = 1.0, voice: str = "vivian"
    ) -> ToolResult:
        """使用 Qwen3-TTS 保存到文件"""
        def _do_save():
            try:
                if not self._qwen_client:
                    self._init_qwen_client()
                
                if not self._qwen_client or not self._qwen_client.is_available:
                    raise RuntimeError("Qwen3-TTS 不可用")
                
                # 转换语速
                speed = rate / 200.0 if rate <= 2.0 else 1.0
                speed = max(0.5, min(2.0, speed))
                
                # 生成并保存
                from src.core.qwen_tts_client import QwenTTSLanguage
                self._qwen_client.speak_to_file(
                    text=text,
                    output_path=str(path),
                    language=QwenTTSLanguage.CHINESE,
                    voice=voice,
                    speed=speed
                )
                    
            except Exception as e:
                logger.error(f"Qwen3-TTS 保存失败: {e}")
                raise

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_save)

        file_size_kb = path.stat().st_size / 1024
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"语音已保存: {path.name} ({file_size_kb:.1f} KB) [Qwen3-TTS]",
            data={"output_path": str(path), "file_size_kb": file_size_kb, "text_length": len(text), "engine": "qwen_tts"},
        )

    async def _save_to_file_pyttsx3(
        self, text: str, path: Path, rate: int = 200, volume: float = 1.0, voice_index: int = 0
    ) -> ToolResult:
        """使用 pyttsx3 保存到文件"""
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
            output=f"语音已保存: {path.name} ({file_size_kb:.1f} KB) [pyttsx3]",
            data={"output_path": str(path), "file_size_kb": file_size_kb, "text_length": len(text), "engine": "pyttsx3"},
        )

    def _list_voices(self) -> ToolResult:
        """列出可用的音色"""
        # 根据引擎返回音色列表
        if self._engine == "qwen_tts" and QWEN_TTS_AVAILABLE:
            # Qwen3-TTS 预设音色
            voice_list = [
                {"id": "vivian", "name": "Vivian", "description": "年轻女性声音，温柔亲切"},
                {"id": "alice", "name": "Alice", "description": "成熟女性声音，专业播报"},
                {"id": "ryan", "name": "Ryan", "description": "年轻男性声音，活力充沛"},
                {"id": "emma", "name": "Emma", "description": "童声女孩，活泼可爱"},
                {"id": "lucas", "name": "Lucas", "description": "童声男孩，阳光开朗"},
                {"id": "anna", "name": "Anna", "description": "成年女性声音，知性优雅"},
                {"id": "james", "name": "James", "description": "成年男性声音，沉稳有力"},
                {"id": "mia", "name": "Mia", "description": "年轻女性声音，清新甜美"},
                {"id": "david", "name": "David", "description": "中年男性声音，成熟稳重"},
            ]
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"Qwen3-TTS: 找到 {len(voice_list)} 个预设音色",
                data={"voices": voice_list, "engine": "qwen_tts"},
            )
        else:
            # pyttsx3 系统音色
            return self._list_voices_pyttsx3()

    def _list_voices_pyttsx3(self) -> ToolResult:
        """列出 pyttsx3 可用的音色"""
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
                output=f"pyttsx3: 找到 {len(voice_list)} 个系统音色",
                data={"voices": voice_list, "engine": "pyttsx3"},
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
