"""TTS语音播放器。

支持多种TTS引擎：pyttsx3、edge-tts、gtts等。

重构说明（v1.3.0 - TTS 架构重构）：
- Edge TTS 作为实时对话主引擎，pyttsx3 降级备选
- Qwen3-TTS 仅用于 VoiceOutputTool 异步任务，不在此模块中使用
- 新增播放队列（enqueue）支持流式模式连续播放多个句子
- Edge TTS 全内存处理：MP3 数据通过 ffmpeg pipe 转 PCM，零临时文件
- 停止机制适配 simpleaudio（替代 winsound.SND_PURGE）
- 复用 asyncio 事件循环，避免每次 asyncio.run() 的开销
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import shutil
import subprocess
import tempfile
import threading
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import simpleaudio as sa
from PySide6.QtCore import QObject, Signal, Slot, QThread

logger = logging.getLogger(__name__)


# ============================================================
# ffmpeg 路径自动检测
# ============================================================

_ffmpeg_path: str | None = None


def _find_ffmpeg() -> str:
    """自动检测 ffmpeg 路径。"""
    global _ffmpeg_path
    if _ffmpeg_path is not None:
        return _ffmpeg_path

    # 1. 系统 PATH
    path = shutil.which('ffmpeg')
    if path:
        _ffmpeg_path = path
        logger.info("找到 ffmpeg (PATH): %s", path)
        return _ffmpeg_path

    # 2. Windows 常见 fallback 路径
    fallback_paths = [
        r'E:\ffmpeg2024-05-15\bin\ffmpeg.exe',
        r'C:\ffmpeg\bin\ffmpeg.exe',
    ]
    for fb in fallback_paths:
        if Path(fb).exists():
            _ffmpeg_path = fb
            logger.info("找到 ffmpeg (fallback): %s", fb)
            return _ffmpeg_path

    raise FileNotFoundError(
        "ffmpeg not found. 请安装 ffmpeg 并添加到 PATH，"
        "或将其放置在常见路径下。"
    )


class TTSEngine(Enum):
    """TTS引擎枚举。"""
    PYTTSX3 = "pyttsx3"     # 本地TTS，无需网络 (Windows SAPI5)
    EDGE_TTS = "edge_tts"   # Edge在线TTS，音质好
    GTTS = "gtts"           # Google TTS，需联网
    QWEN_TTS = "qwen_tts"   # Qwen3-TTS 本地大模型（仅 VoiceOutputTool 使用）


# ============================================================
# Worker（运行在独立 QThread 中）
# ============================================================

class _TTSWorker(QObject):
    """TTS 工作器 - 在独立 QThread 事件循环中执行阻塞 TTS 操作。

    所有 Signal 从此对象所在线程（工作线程）发射，
    连接到主线程 slot 时自动使用 QueuedConnection，线程安全。
    """

    work_started = Signal()     # TTS 开始播放
    work_finished = Signal()    # TTS 播放完成
    work_error = Signal(str)    # TTS 播放错误

    def __init__(
        self,
        engine_type: TTSEngine,
        voice_rate: int,
        voice_volume: float,
        voice_name: str,
    ):
        super().__init__()
        self._engine_type = engine_type
        self._voice_rate = voice_rate
        self._voice_volume = voice_volume
        self._voice_name = voice_name

        # 引擎实例（在工作线程中初始化）
        self._active_engine: TTSEngine | None = None
        self._pyttsx3_engine = None
        self._edge_tts_module = None
        self._gtts_class = None
        self._engine_initialized = False

        # 持久 asyncio 事件循环（避免每次 asyncio.run() 的开销）
        self._loop: asyncio.AbstractEventLoop | None = None

        # 跨线程停止标志
        self._stop_requested = False
        # 停止完成事件（用于同步等待旧任务停止）
        self._stop_event = threading.Event()
        self._stop_event.set()  # 初始状态为"已停止"

        # 当前 simpleaudio 播放对象（用于停止）
        self._current_play_obj: sa.PlayObject | None = None

        # 临时文件
        self._temp_files: list[Path] = []

        # 缓存可用语音列表（pyttsx3）
        self._available_voices: list[str] = []

    # ---------- 引擎初始化（在工作线程中调用） ----------

    @Slot()
    def init_engine(self) -> None:
        """在工作线程中初始化 TTS 引擎（保证 COM 线程亲和性）。"""
        if self._engine_initialized:
            return

        # 创建持久事件循环（用于 Edge TTS 异步操作）
        self._loop = asyncio.new_event_loop()

        if self._engine_type == TTSEngine.PYTTSX3:
            self._try_init_pyttsx3()
        elif self._engine_type == TTSEngine.EDGE_TTS:
            self._try_init_edge_tts()
        elif self._engine_type == TTSEngine.GTTS:
            self._try_init_gtts()
        else:
            # QWEN_TTS 不在实时路径中，默认走 Edge TTS
            self._try_init_edge_tts()

        self._engine_initialized = True
        logger.info("TTS Worker 引擎初始化完成: %s", self._active_engine)

    def _try_init_pyttsx3(self) -> None:
        """尝试初始化 pyttsx3 引擎。"""
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            if self._voice_rate != 0:
                self._pyttsx3_engine.setProperty('rate', 200 + self._voice_rate * 2)
            if self._voice_volume != 1.0:
                self._pyttsx3_engine.setProperty('volume', self._voice_volume)
            if self._voice_name:
                voices = self._pyttsx3_engine.getProperty('voices')
                for voice in voices:
                    if self._voice_name in voice.name:
                        self._pyttsx3_engine.setProperty('voice', voice.id)
                        break
            # 缓存语音列表
            try:
                voices = self._pyttsx3_engine.getProperty('voices')
                self._available_voices = [v.name for v in voices]
            except Exception:
                pass
            self._active_engine = TTSEngine.PYTTSX3
            logger.info("TTS引擎初始化成功: pyttsx3")
        except ImportError:
            logger.warning("pyttsx3未安装，尝试其他引擎")
            self._try_init_edge_tts()
        except Exception as e:
            logger.error("pyttsx3初始化失败: %s", e)
            self._try_init_edge_tts()

    def _try_init_edge_tts(self) -> None:
        """尝试初始化 Edge TTS 引擎。"""
        try:
            import edge_tts
            self._edge_tts_module = edge_tts
            self._active_engine = TTSEngine.EDGE_TTS
            logger.info("TTS引擎初始化成功: edge-tts")
        except ImportError:
            logger.warning("edge-tts未安装，尝试gtts")
            self._try_init_gtts()
        except Exception as e:
            logger.error("edge-tts初始化失败: %s", e)
            self._try_init_gtts()

    def _try_init_gtts(self) -> None:
        """尝试初始化 Google TTS 引擎。"""
        try:
            from gtts import gTTS
            self._gtts_class = gTTS
            self._active_engine = TTSEngine.GTTS
            logger.info("TTS引擎初始化成功: gTTS")
        except ImportError:
            logger.error("所有TTS引擎都不可用")
            self._active_engine = None

    # ---------- 播放（在工作线程事件循环中执行） ----------

    @Slot(str)
    def do_speak(self, text: str) -> None:
        """在工作线程中执行 TTS 播放（阻塞直到播放完成或被中断）。"""
        if not self._engine_initialized:
            self.init_engine()

        self._stop_requested = False
        # 通知旧任务停止（如果有的话在等待）
        if self._stop_event.is_set():
            self._stop_event.clear()

        try:
            self.work_started.emit()

            if self._active_engine == TTSEngine.PYTTSX3:
                self._speak_pyttsx3(text)
            elif self._active_engine == TTSEngine.EDGE_TTS:
                self._loop.run_until_complete(self._speak_edge_tts(text))
            elif self._active_engine == TTSEngine.GTTS:
                self._speak_gtts(text)
            else:
                self.work_error.emit("没有可用的TTS引擎")
                return

            # 正常播放完成（未被中断）
            if not self._stop_requested:
                self.work_finished.emit()

        except Exception as e:
            logger.error("TTS播放错误: %s", e)
            if not self._stop_requested:
                self.work_error.emit(str(e))
        finally:
            self._cleanup_temp_files()
            # 标记停止完成，通知等待中的新任务
            self._stop_event.set()

    def _speak_pyttsx3(self, text: str) -> None:
        """使用 pyttsx3 播放（阻塞）。

        按照 v2.9.4 经验：每次播放都需要清理 _activeEngines 缓存，
        否则 pyttsx3 会复用已损坏的缓存实例。
        """
        import pyttsx3
        engine = None
        com_initialized = False

        try:
            # 1. Windows COM 初始化（qasync 线程池中必需）
            try:
                import pythoncom
                pythoncom.CoInitialize()
                com_initialized = True
            except Exception:
                pass

            # 2. 关键：清理 pyttsx3 内部的全局引擎缓存
            if hasattr(pyttsx3, '_activeEngines'):
                pyttsx3._activeEngines.clear()

            # 3. 显式指定驱动创建引擎
            engine = pyttsx3.init(driverName='sapi5')

            # 4. 设置参数
            engine.setProperty('rate', 200 + self._voice_rate * 2)
            engine.setProperty('volume', self._voice_volume)
            if self._voice_name:
                voices = engine.getProperty('voices')
                for voice in voices:
                    if self._voice_name in voice.name:
                        engine.setProperty('voice', voice.id)
                        break

            # 5. 播放
            engine.say(text)
            engine.runAndWait()

        finally:
            # 6. 清理引擎
            if engine:
                try:
                    engine.stop()
                except Exception:
                    pass
                # 关键：使用后再次清理缓存
                if hasattr(pyttsx3, '_activeEngines'):
                    pyttsx3._activeEngines.clear()
                del engine

            # 7. 反初始化 COM
            if com_initialized:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    async def _speak_edge_tts(self, text: str) -> None:
        """使用 Edge TTS 播放（全内存处理，零临时文件）。

        流程：edge-tts stream → 内存 MP3 → ffmpeg pipe 转 PCM → simpleaudio 播放
        """
        try:
            # 1. 收集 MP3 数据到内存（不写磁盘）
            mp3_buffer = io.BytesIO()
            communicate = self._edge_tts_module.Communicate(text, "zh-CN-XiaoxiaoNeural")
            async for chunk in communicate.stream():
                if self._stop_requested:
                    return
                if chunk["type"] == "audio":
                    mp3_buffer.write(chunk["data"])

            if self._stop_requested:
                return

            mp3_data = mp3_buffer.getvalue()
            if not mp3_data:
                logger.warning("Edge TTS 未返回音频数据")
                return

            # 2. ffmpeg pipe 内存转码 MP3 → PCM（无临时文件）
            ffmpeg_path = _find_ffmpeg()
            process = subprocess.Popen(
                [ffmpeg_path, '-i', 'pipe:0', '-f', 's16le',
                 '-acodec', 'pcm_s16le', '-ar', '24000', '-ac', '1', 'pipe:1'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            pcm_data, stderr = process.communicate(input=mp3_data)

            if self._stop_requested:
                return

            if not pcm_data:
                logger.error("ffmpeg 转码失败: %s", stderr.decode(errors='replace')[-200:])
                return

            # 3. 直接播放 PCM 数据
            audio_np = np.frombuffer(pcm_data, dtype=np.int16)
            self._current_play_obj = sa.play_buffer(audio_np, 1, 2, 24000)
            self._current_play_obj.wait_done()
            self._current_play_obj = None

        except Exception as e:
            logger.error("Edge TTS 播放失败: %s", e)
            self._current_play_obj = None

    def _speak_gtts(self, text: str) -> None:
        """使用 gTTS 播放。"""
        try:
            tts = self._gtts_class(text=text, lang='zh-cn')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                temp_file = Path(f.name)
                self._temp_files.append(temp_file)
                tts.save(str(temp_file))

            if self._stop_requested:
                return
            try:
                import winsound
                winsound.PlaySound(str(temp_file), winsound.SND_FILENAME)
            except Exception as e:
                logger.error("播放音频失败: %s", e)
        except Exception as e:
            logger.error("gTTS生成失败: %s", e)

    # ---------- 停止（可从任意线程调用） ----------

    def request_stop(self) -> None:
        """请求停止播放（跨线程安全）。

        不依赖 QThread 事件循环（因为 do_speak 阻塞时事件循环不响应），
        而是直接设置标志并中断底层播放操作，然后等待旧任务真正停止。
        """
        self._stop_requested = True
        # 中断 pyttsx3
        if self._pyttsx3_engine:
            try:
                self._pyttsx3_engine.stop()
            except Exception:
                pass
        # 中断 simpleaudio 播放（适用于 Edge TTS / gTTS）
        if self._current_play_obj:
            try:
                self._current_play_obj.stop()
            except Exception:
                pass
        # 等待旧任务真正停止（最多等待1秒避免永久阻塞）
        if not self._stop_event.wait(timeout=1.0):
            logger.warning("TTS停止等待超时")

    # ---------- 清理 ----------

    def _cleanup_temp_files(self) -> None:
        """清理临时音频文件。"""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning("删除临时文件失败: %s", e)
        self._temp_files.clear()


# ============================================================
# TTSPlayer（主线程 API）
# ============================================================

class TTSPlayer(QObject):
    """TTS 语音播放器。

    使用 Worker + QThread 标准模式：
    - _TTSWorker 运行在独立 QThread 中，执行阻塞 TTS 操作
    - 所有 Signal 通过 QueuedConnection 安全传递到主线程
    - 支持播放队列（enqueue），用于流式模式连续播放多个句子
    """

    # 公共信号（在主线程中触发 slot）
    playback_started = Signal()     # 开始播放
    playback_finished = Signal()    # 播放完成（队列也全部播完）
    playback_error = Signal(str)    # 播放错误
    progress_changed = Signal(int)  # 播放进度（0-100）

    # 内部信号：从主线程触发工作线程执行
    _request_speak = Signal(str)

    def __init__(
        self,
        engine: TTSEngine = TTSEngine.PYTTSX3,
        voice_rate: int = 0,
        voice_volume: float = 1.0,
        voice_name: str = "",
    ):
        super().__init__()
        self._is_playing = False
        self._is_paused = False
        self._current_text = ""

        # 流式 TTS 模式标志：为 True 时 speak() 降级为 enqueue()，防止打断流式播放
        self._is_streaming_active = False

        # 播放队列（流式模式用）
        self._sentence_queue: list[str] = []

        # 创建 Worker + QThread
        self._worker = _TTSWorker(engine, voice_rate, voice_volume, voice_name)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)

        # 主线程 -> 工作线程
        self._request_speak.connect(self._worker.do_speak)
        self._worker_thread.started.connect(self._worker.init_engine)

        # 工作线程 -> 主线程
        self._worker.work_started.connect(self._on_worker_started)
        self._worker.work_finished.connect(self._on_worker_finished)
        self._worker.work_error.connect(self._on_worker_error)

        # 启动工作线程
        self._worker_thread.start()

    # ========== 公共API ==========

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def engine(self) -> TTSEngine:
        return self._worker._active_engine or TTSEngine.PYTTSX3

    @property
    def is_streaming_active(self) -> bool:
        """是否处于流式 TTS 模式（流式模式下 speak 降级为 enqueue）。"""
        return self._is_streaming_active

    @is_streaming_active.setter
    def is_streaming_active(self, value: bool) -> None:
        self._is_streaming_active = value

    def speak(self, text: str) -> None:
        """播放文本语音（非流式）。

        清空队列，停止当前播放，立即播放新文本。
        用于手动点击播放、非流式场景。

        注意：当流式 TTS 模式激活时（is_streaming_active=True），
        自动降级为 enqueue()，避免打断正在进行的流式播放。
        """
        if not text:
            return

        # 流式模式激活时，降级为 enqueue 防止打断
        if self._is_streaming_active:
            logger.info("TTS speak() 降级为 enqueue()（流式模式激活中）")
            self.enqueue(text)
            return

        # 清空队列并停止当前播放
        self._sentence_queue.clear()
        if self._is_playing:
            self._worker.request_stop()

        cleaned_text = self._preprocess_text(text)
        if not cleaned_text:
            return

        self._current_text = cleaned_text
        self._is_playing = True
        self._request_speak.emit(cleaned_text)

    def enqueue(self, text: str) -> None:
        """将文本加入播放队列（流式模式）。

        如果当前无播放，自动开始播放；否则加入队列等待。
        用于流式 TTS，句子按顺序连续播放，不互相打断。
        """
        if not text:
            return
        cleaned_text = self._preprocess_text(text)
        if not cleaned_text:
            return

        self._sentence_queue.append(cleaned_text)
        if not self._is_playing:
            self._play_next()

    def clear_queue(self) -> None:
        """清空播放队列。"""
        self._sentence_queue.clear()

    def stop(self) -> None:
        """停止播放并清空队列。"""
        self._sentence_queue.clear()
        self._is_playing = False
        self._is_paused = False
        self._worker.request_stop()
        logger.info("TTS播放已停止（队列已清空）")

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def set_voice(self, voice_name: str) -> None:
        self._worker._voice_name = voice_name

    def get_available_voices(self) -> list[str]:
        return list(self._worker._available_voices)

    def cleanup(self) -> None:
        """清理资源（应用退出时调用）。"""
        self._sentence_queue.clear()
        self._worker.request_stop()
        # 关闭持久事件循环
        if self._worker._loop and not self._worker._loop.is_closed():
            self._worker._loop.close()
        self._worker_thread.quit()
        if not self._worker_thread.wait(2000):
            logger.warning("TTS工作线程未能在2秒内退出")
            self._worker_thread.terminate()

    # ========== 内部方法 ==========

    def _play_next(self) -> None:
        """从队列取下一个句子播放，队列为空则发射 playback_finished。"""
        if not self._sentence_queue:
            self._is_playing = False
            self.playback_finished.emit()
            return
        text = self._sentence_queue.pop(0)
        self._current_text = text
        self._is_playing = True
        self._request_speak.emit(text)

    # ========== 内部 Slot ==========

    def _on_worker_started(self) -> None:
        self.playback_started.emit()

    def _on_worker_finished(self) -> None:
        """单句播放完成，自动播放队列中的下一句。"""
        self._play_next()

    def _on_worker_error(self, error_msg: str) -> None:
        logger.error("TTS 播放错误: %s", error_msg)
        # 出错后继续播放队列中的下一句（不因一句失败而停止所有）
        self.playback_error.emit(error_msg)
        self._play_next()

    # ========== 文本预处理 ==========

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """预处理文本，移除无法朗读的字符（标点符号、Emoji、特殊符号）。"""
        # 移除特殊标记
        text = re.sub(r'<\|.*?\|>', '', text)
        text = re.sub(r'\[.*?\]', '', text)
    
        # 移除所有标点符号（中英文）
        # 中文标点：，。！？；：、""''``……—～《》【】（）〔〕〈〉「」『』〖〗〘〙〚〛⸨⸩
        # 英文标点：,.!?;:'"`~…–—·•
        # 其他符号：@#$%^&*()_+-=[]{}|;':",./<>?\\等
        punctuation_pattern = re.compile(
            r'[，。！？；：、""\'\'``……—～《》【】（）〔〕〈〉「」『』〖〗〘〙〚〛⸨⸩'
            r',.!?;:\'"`…–—·•'
            r'@#$%^&*()_+\-=\[\]{}|;\':",./<>?\\'
            r']+', 
            flags=re.UNICODE
        )
        text = punctuation_pattern.sub(' ', text)
    
        # 移除 Emoji（只匹配真正的 emoji 范围，避免误删 CJK 字符）
        # 注意：不要使用大的 Unicode 范围如 \U000024C2-\U0001F251，
        # 因为它会错误地包含 CJK 汉字范围 (U+4E00-U+9FFF)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"   # dingbats
            "\U000024C2"              # only circled M, not a range
            "\U0001F251"              # only positive face, not a range
            "]+", flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
    
        # 清理多余空白（多个空格合并为一个，去除首尾空格）
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
    
        return text
