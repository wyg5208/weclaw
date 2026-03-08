"""TTS语音播放器。

支持多种TTS引擎：pyttsx3、edge-tts、gtts等。

重构说明（v1.2.2）：
- 使用标准 Worker + QThread 模式，替代覆盖 QThread.run() 的反模式
- 所有 Signal 从工作线程事件循环安全发射，通过 QueuedConnection 到主线程
- pyttsx3 引擎在工作线程中初始化，保证 COM 线程亲和性
- 停止机制使用跨线程标志 + 直接中断，不依赖阻塞中的事件循环
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from enum import Enum
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QThread

logger = logging.getLogger(__name__)


class TTSEngine(Enum):
    """TTS引擎枚举。"""
    PYTTSX3 = "pyttsx3"     # 本地TTS，无需网络
    EDGE_TTS = "edge_tts"   # Edge在线TTS，音质好
    GTTS = "gtts"           # Google TTS，需联网


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

        # 跨线程停止标志
        self._stop_requested = False

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

        if self._engine_type == TTSEngine.PYTTSX3:
            self._try_init_pyttsx3()
        elif self._engine_type == TTSEngine.EDGE_TTS:
            self._try_init_edge_tts()
        elif self._engine_type == TTSEngine.GTTS:
            self._try_init_gtts()
        else:
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

        try:
            self.work_started.emit()

            if self._active_engine == TTSEngine.PYTTSX3:
                self._speak_pyttsx3(text)
            elif self._active_engine == TTSEngine.EDGE_TTS:
                asyncio.run(self._speak_edge_tts(text))
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

    def _speak_pyttsx3(self, text: str) -> None:
        """使用 pyttsx3 播放（阻塞）。"""
        if not self._pyttsx3_engine:
            return
        try:
            self._pyttsx3_engine.stop()
        except Exception:
            pass
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()

    async def _speak_edge_tts(self, text: str) -> None:
        """使用 Edge TTS 播放。"""
        communicate = self._edge_tts_module.Communicate(text, "zh-CN-XiaoxiaoNeural")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_file = Path(f.name)
            self._temp_files.append(temp_file)
            await communicate.save(temp_file)

        if self._stop_requested:
            return
        try:
            import winsound
            winsound.PlaySound(str(temp_file), winsound.SND_FILENAME)
        except Exception as e:
            logger.error("播放音频失败: %s", e)

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
        而是直接设置标志并中断底层播放操作。
        """
        self._stop_requested = True
        # 中断 pyttsx3
        if self._pyttsx3_engine:
            try:
                self._pyttsx3_engine.stop()
            except Exception:
                pass
        # 中断 winsound（适用于 edge-tts / gtts 播放阶段）
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

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
    - pyttsx3 COM 对象在工作线程中创建和使用，保证线程亲和性
    """

    # 公共信号（在主线程中触发 slot）
    playback_started = Signal()     # 开始播放
    playback_finished = Signal()    # 播放完成
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
        """初始化TTS播放器。

        Args:
            engine: TTS引擎类型
            voice_rate: 语速（-100到100，默认0）
            voice_volume: 音量（0.0到1.0，默认1.0）
            voice_name: 指定语音名称
        """
        super().__init__()
        self._is_playing = False
        self._is_paused = False
        self._current_text = ""

        # 创建 Worker + QThread
        self._worker = _TTSWorker(engine, voice_rate, voice_volume, voice_name)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)

        # 主线程 -> 工作线程（QueuedConnection，在工作线程事件循环中执行 slot）
        self._request_speak.connect(self._worker.do_speak)
        self._worker_thread.started.connect(self._worker.init_engine)

        # 工作线程 -> 主线程（QueuedConnection，signal 安全到达主线程）
        self._worker.work_started.connect(self._on_worker_started)
        self._worker.work_finished.connect(self._on_worker_finished)
        self._worker.work_error.connect(self._on_worker_error)

        # 启动工作线程（触发 init_engine）
        self._worker_thread.start()

    # ========== 公共API ==========

    @property
    def is_playing(self) -> bool:
        """是否正在播放。"""
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        """是否暂停。"""
        return self._is_paused

    @property
    def engine(self) -> TTSEngine:
        """当前使用的引擎。"""
        return self._worker._active_engine or TTSEngine.PYTTSX3

    def speak(self, text: str) -> None:
        """播放文本语音。

        Args:
            text: 要播放的文本
        """
        if not text:
            return

        # 如果正在播放，先停止
        if self._is_playing:
            self.stop()

        # 预处理文本
        cleaned_text = self._preprocess_text(text)
        if not cleaned_text:
            return

        self._current_text = cleaned_text
        self._is_playing = True

        # 通过信号触发工作线程执行（QueuedConnection -> 工作线程事件循环）
        self._request_speak.emit(cleaned_text)

    def stop(self) -> None:
        """停止播放。

        使用跨线程标志 + 直接中断，不依赖工作线程事件循环
        （因为 do_speak 阻塞时事件循环不响应信号）。
        """
        self._is_playing = False
        self._is_paused = False
        # 直接跨线程中断（不走 Signal）
        self._worker.request_stop()
        logger.info("TTS播放已停止")

    def pause(self) -> None:
        """暂停播放。"""
        self._is_paused = True

    def resume(self) -> None:
        """恢复播放。"""
        self._is_paused = False

    def set_voice(self, voice_name: str) -> None:
        """设置语音（在下次 speak 时生效）。

        Args:
            voice_name: 语音名称
        """
        self._worker._voice_name = voice_name

    def get_available_voices(self) -> list[str]:
        """获取可用的语音列表（从缓存读取，线程安全）。"""
        return list(self._worker._available_voices)

    def cleanup(self) -> None:
        """清理资源（应用退出时调用）。"""
        self._worker.request_stop()
        self._worker_thread.quit()
        if not self._worker_thread.wait(2000):
            logger.warning("TTS工作线程未能在2秒内退出")
            self._worker_thread.terminate()

    # ========== 内部 Slot ==========

    def _on_worker_started(self) -> None:
        """Worker 开始播放（在主线程中执行）。"""
        self.playback_started.emit()

    def _on_worker_finished(self) -> None:
        """Worker 播放完成（在主线程中执行）。"""
        self._is_playing = False
        self._is_paused = False
        self.playback_finished.emit()

    def _on_worker_error(self, error_msg: str) -> None:
        """Worker 播放错误（在主线程中执行）。"""
        self._is_playing = False
        self._is_paused = False
        self.playback_error.emit(error_msg)

    # ========== 文本预处理 ==========

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """预处理文本，移除无法朗读的字符。"""
        # 移除特殊标记
        text = re.sub(r'<\|.*?\|>', '', text)
        text = re.sub(r'\[.*?\]', '', text)

        # 移除Emoji（保留基本标点）
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)

        # 清理多余空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text
