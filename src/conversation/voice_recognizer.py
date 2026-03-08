"""语音识别器。

支持多种语音识别引擎：SpeechRecognition、Whisper等。

重构说明（v1.2.2）：
- 线程安全信号发射：后台线程通过内部信号 + QueuedConnection 安全传递到主线程
- 统一音频后端：Whisper 路径从 pyaudio 替换为 sounddevice（与 VoiceInputTool 一致）
- 消除设备冲突：不再有两套不同的音频采集库
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, Qt

logger = logging.getLogger(__name__)

# 简繁转换工具
try:
    from src.tools.text_utils import to_simplified_chinese
except ImportError:
    # 如果导入失败，定义一个空实现
    def to_simplified_chinese(text: str) -> str:
        return text


class RecognizerEngine(Enum):
    """语音识别引擎枚举。"""
    SPEECH_RECOGNITION = "speech_recognition"  # 使用Google Web Speech API
    WHISPER = "whisper"                        # OpenAI Whisper本地识别


class VoiceRecognizer(QObject):
    """语音识别器。

    支持持续监听、语音转文本、实时识别。

    线程安全：后台监听线程通过内部信号（_bg_speech_result / _bg_speech_error）
    将结果传递到主线程，再由主线程 slot 发射公共信号。连接类型显式指定为
    QueuedConnection，确保 slot 始终在主线程执行。
    """

    # 公共信号（在主线程中发射）
    speech_started = Signal()        # 开始识别
    speech_result = Signal(str, bool)  # 识别结果 (text, is_final)
    speech_error = Signal(str)       # 识别错误
    audio_level = Signal(float)      # 音频级别（0.0-1.0）

    # 内部信号：从后台线程安全传递数据到主线程
    _bg_speech_result = Signal(str, bool)
    _bg_speech_error = Signal(str)

    def __init__(
        self,
        engine: RecognizerEngine = RecognizerEngine.SPEECH_RECOGNITION,
        language: str = "zh-CN",
        continuous: bool = True,
        interim_results: bool = True,
    ):
        """初始化语音识别器。

        Args:
            engine: 识别引擎类型
            language: 识别语言
            continuous: 是否持续识别
            interim_results: 是否返回临时结果
        """
        super().__init__()
        self._engine = engine
        self._language = language
        # Whisper使用"zh"，而不是"zh-CN"等格式
        self._language_for_whisper = self._convert_language_for_whisper(language)
        self._continuous = continuous
        self._interim_results = interim_results
        self._is_listening = False
        self._is_paused = False

        self._recognizer = None
        self._microphone = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # 线程安全信号连接（显式 QueuedConnection，确保 slot 在主线程执行）
        self._bg_speech_result.connect(
            self._on_bg_speech_result, Qt.ConnectionType.QueuedConnection
        )
        self._bg_speech_error.connect(
            self._on_bg_speech_error, Qt.ConnectionType.QueuedConnection
        )

        self._engine_init()

    # ========== 线程安全信号桥接 ==========

    @Slot(str, bool)
    def _on_bg_speech_result(self, text: str, is_final: bool) -> None:
        """在主线程中发射 speech_result 信号。"""
        self.speech_result.emit(text, is_final)

    @Slot(str)
    def _on_bg_speech_error(self, error: str) -> None:
        """在主线程中发射 speech_error 信号。"""
        self.speech_error.emit(error)

    # ========== 引擎初始化 ==========

    @staticmethod
    def _convert_language_for_whisper(language: str) -> str:
        """将语言代码转换为Whisper格式。

        Whisper支持的语言代码格式与Google Speech不同：
        - "zh-CN" / "zh-cn" -> "zh"
        - "en-US" -> "en"
        - 其他保持不变
        """
        lang_map = {
            "zh-CN": "zh",
            "zh-cn": "zh",
            "zh-TW": "zh",
            "zh-tw": "zh",
            "en-US": "en",
            "en-us": "en",
            "en-GB": "en",
            "en-gb": "en",
        }
        return lang_map.get(language, language)

    def _engine_init(self) -> None:
        """初始化识别引擎。"""
        # 优先尝试使用whisper
        try:
            import whisper
            self._whisper_model = whisper.load_model("base", device="cpu")
            self._whisper_available = True
            self._active_engine = RecognizerEngine.WHISPER
            logger.info("语音识别引擎初始化成功: Whisper (CPU)")
            return
        except ImportError:
            logger.warning("whisper未安装")
        except Exception as e:
            logger.warning(f"whisper加载失败: {e}")

        # 尝试使用speech_recognition
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 200
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()

            with self._microphone as source:
                logger.info("正在校准麦克风...")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("麦克风校准完成")

            self._active_engine = RecognizerEngine.SPEECH_RECOGNITION
            logger.info("语音识别引擎初始化成功: SpeechRecognition")

        except ImportError:
            logger.error("speech_recognition库和whisper都未安装")
            self._active_engine = None
        except Exception as e:
            logger.error(f"语音识别初始化失败: {e}")
            self._active_engine = None

    # ========== 公共API ==========

    @property
    def is_listening(self) -> bool:
        """是否正在监听。"""
        return self._is_listening

    @property
    def is_paused(self) -> bool:
        """是否暂停。"""
        return self._is_paused

    def start_listening(self) -> bool:
        """开始持续监听。

        Returns:
            是否成功开始
        """
        if self._is_listening:
            return True

        if not self._active_engine:
            logger.error("没有可用的语音识别引擎")
            return False

        if self._active_engine == RecognizerEngine.SPEECH_RECOGNITION:
            if not self._recognizer or not self._microphone:
                logger.error("SpeechRecognition组件未初始化")
                return False

        logger.info(f"开始语音监听，当前引擎: {self._active_engine}")

        self._is_listening = True
        self._is_paused = False
        self._stop_event.clear()

        # 在后台线程中运行
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

        self.speech_started.emit()
        logger.info("开始语音监听")
        return True

    def stop_listening(self) -> None:
        """停止监听。"""
        if not self._is_listening:
            return

        self._is_listening = False
        self._is_paused = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        logger.info("停止语音监听")

    def pause_listening(self) -> None:
        """暂停监听。"""
        self._is_paused = True

    def resume_listening(self) -> None:
        """恢复监听。"""
        self._is_paused = False

    def recognize_once(self) -> Optional[str]:
        """识别一次语音。

        Returns:
            识别结果文本，失败返回None
        """
        if not self._active_engine or not self._microphone:
            return None

        try:
            import speech_recognition as sr

            with self._microphone as source:
                logger.info("正在识别...")
                audio = self._recognizer.listen(source, timeout=5)

            text = self._recognizer.recognize_google(audio, language=self._language)
            logger.info(f"识别结果: {text}")
            return text

        except Exception as e:
            logger.error(f"识别错误: {e}")
            return None

    # ========== 后台监听线程 ==========

    def _listen_loop(self) -> None:
        """监听循环（在后台线程中运行）。

        注意：此方法中 **不直接** 调用 self.speech_result.emit()，
        而是通过 self._bg_speech_result.emit() 安全地将结果传递到主线程。
        """
        # 根据不同引擎检查必要组件
        if self._active_engine == RecognizerEngine.SPEECH_RECOGNITION:
            if not self._recognizer or not self._microphone:
                logger.error("SpeechRecognition组件未正确初始化")
                return
        elif self._active_engine == RecognizerEngine.WHISPER:
            if not self._whisper_model:
                logger.error("Whisper模型未正确初始化")
                return
        else:
            logger.error("没有可用的语音识别引擎")
            return

        try:
            while not self._stop_event.is_set():
                if self._is_paused:
                    self._stop_event.wait(0.1)
                    continue

                try:
                    if self._active_engine == RecognizerEngine.SPEECH_RECOGNITION:
                        self._listen_speech_recognition()
                    elif self._active_engine == RecognizerEngine.WHISPER:
                        self._listen_whisper()
                        # Whisper 路径内部自己循环，退出时跳出外层循环
                        break

                except Exception as e:
                    if "WaitTimeoutError" in type(e).__name__:
                        continue
                    logger.error(f"监听错误: {e}")
                    continue

        except Exception as e:
            logger.error(f"监听循环错误: {e}")
            # 通过安全信号通知主线程
            self._bg_speech_error.emit(str(e))
        finally:
            self._is_listening = False

    def _listen_speech_recognition(self) -> None:
        """SpeechRecognition 引擎监听（单次，在外层循环中反复调用）。"""
        import speech_recognition as sr

        with self._microphone as source:
            audio = self._recognizer.listen(
                source,
                timeout=1,
                phrase_time_limit=20
            )

        if self._stop_event.is_set():
            return

        # 识别
        self._recognize_audio(audio)

    def _listen_whisper(self) -> None:
        """Whisper 引擎监听（使用 sounddevice，统一音频后端）。

        使用 sounddevice.InputStream 替代 pyaudio，
        与 VoiceInputTool 使用同一音频后端，消除设备冲突。
        """
        import sounddevice as sd
        import numpy as np

        RATE = 16000
        CHANNELS = 1
        CHUNK = 1024
        SILENCE_THRESHOLD = 100   # 静音能量阈值（int16 范围）
        MAX_SILENCE_FRAMES = 20   # 连续静音帧数触发识别

        logger.info("开始Whisper实时监听 (sounddevice)...")

        stream = sd.InputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK,
        )
        stream.start()

        audio_buffer = np.array([], dtype=np.int16)
        silence_frames = 0

        try:
            while not self._stop_event.is_set():
                if self._is_paused:
                    self._stop_event.wait(0.1)
                    continue

                # 读取音频数据
                data, overflowed = stream.read(CHUNK)
                audio_chunk = data.flatten()  # (CHUNK, 1) -> (CHUNK,)
                audio_buffer = np.concatenate([audio_buffer, audio_chunk])

                # 能量检测
                energy = np.mean(np.abs(audio_chunk.astype(np.float32)))

                if energy < SILENCE_THRESHOLD:
                    silence_frames += 1
                else:
                    silence_frames = 0

                # 连续静音超过阈值且有足够音频 -> 执行识别
                if silence_frames > MAX_SILENCE_FRAMES and len(audio_buffer) > RATE:
                    # 归一化到 [-1, 1] 范围（Whisper 要求 float32）
                    audio_float32 = audio_buffer.astype(np.float32) / 32768.0

                    try:
                        result = self._whisper_model.transcribe(
                            audio_float32,
                            language=self._language_for_whisper,
                            fp16=False
                        )
                        text = result["text"].strip()
                        if text:
                            text = to_simplified_chinese(text)
                            logger.info(f"Whisper识别结果: {text}")
                            # 安全发射（通过 QueuedConnection 到主线程）
                            self._bg_speech_result.emit(text, True)
                    except Exception as e:
                        logger.error(f"Whisper识别错误: {e}")

                    # 重置缓冲区
                    audio_buffer = np.array([], dtype=np.int16)
                    silence_frames = 0

                # 短暂等待
                self._stop_event.wait(0.05)

        finally:
            stream.stop()
            stream.close()
            logger.info("Whisper监听已停止 (sounddevice)")

    def _recognize_audio(self, audio) -> None:
        """识别音频（在后台线程中调用，使用安全信号发射结果）。"""
        import speech_recognition as sr

        try:
            text = self._recognizer.recognize_google(
                audio,
                language=self._language,
                show_all=False
            )
            if text:
                text = to_simplified_chinese(text)
                logger.info(f"识别结果: {text}")
                # 安全发射（通过 QueuedConnection 到主线程）
                self._bg_speech_result.emit(text, True)

        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            logger.error(f"识别请求失败: {e}")
            self._bg_speech_error.emit(f"识别请求失败: {e}")
        except Exception as e:
            logger.error(f"识别错误: {e}")
            self._bg_speech_error.emit(str(e))


class WhisperRecognizer(VoiceRecognizer):
    """Whisper语音识别器（可选实现）。"""

    def __init__(
        self,
        model_name: str = "base",
        language: str = "zh",
        device: str = "cpu",
    ):
        """初始化Whisper识别器。

        Args:
            model_name: 模型名称 (tiny, base, small, medium, large)
            language: 识别语言
            device: 运行设备 (cpu, cuda)
        """
        super().__init__(engine=RecognizerEngine.WHISPER)
        self._model_name = model_name
        self._device = device
        self._whisper_model = None
        self._whisper_init()

    def _whisper_init(self) -> None:
        """初始化Whisper模型。"""
        try:
            import whisper
            logger.info(f"正在加载Whisper模型: {self._model_name}")
            self._whisper_model = whisper.load_model(
                self._model_name,
                device=self._device
            )
            logger.info("Whisper模型加载完成")
        except ImportError:
            logger.error("whisper库未安装")
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {e}")

    def recognize_audio_file(self, audio_path: str) -> Optional[str]:
        """识别音频文件。

        Args:
            audio_path: 音频文件路径

        Returns:
            识别结果
        """
        if not self._whisper_model:
            return None

        try:
            result = self._whisper_model.transcribe(
                audio_path,
                language=self._language_for_whisper,
                fp16=False
            )
            text = result["text"].strip()
            text = to_simplified_chinese(text)
            return text
        except Exception as e:
            logger.error(f"Whisper识别失败: {e}")
            return None
