"""语音输入工具 - 支持 Whisper 和 GLM ASR 双引擎

支持:
- 实时录音（直接传 numpy 数组给 Whisper，无需 ffmpeg）
- 音频文件转文字（WAV 可用 scipy 读取，其他格式需 ffmpeg）
- 纯录音并保存文件（record_audio）
- VAD 语音活动检测，说完自动停止
- 多语言识别
- 可选模型大小 (tiny/base/small/medium/large)
- GLM ASR 云端识别（高精度、免依赖）

Phase 4.6 优化：
- 延迟导入：whisper/sounddevice/numpy/scipy 仅在实际使用时导入
- 启动速度大幅提升

Phase 7.0 优化：
- 新增 record_audio 动作：纯录音生成 WAV 文件
- VAD（Voice Activity Detection）智能停止：说完自动停止录音
- 移除固定 5 秒限制，支持灵活时长

v2.15.0 新增：
- GLM ASR 云端识别引擎
- 支持 engine 参数选择 whisper/glm-asr
"""
import asyncio
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 延迟导入标记
VOICE_AVAILABLE: bool | None = None  # Whisper 识别引擎
RECORD_AVAILABLE: bool | None = None  # 录音功能（sounddevice 等）
FFMPEG_AVAILABLE: bool | None = None
GLM_ASR_AVAILABLE: bool | None = None

# 模块引用（延迟加载后赋值）
_whisper = None
_sd = None
_np = None
_read_wav = None
_write_wav = None
_glm_asr_client = None


def _check_record_dependencies() -> bool:
    """检查录音依赖是否可用（sounddevice, numpy, scipy）。"""
    global RECORD_AVAILABLE, _sd, _np, _read_wav, _write_wav
    if RECORD_AVAILABLE is not None:
        return RECORD_AVAILABLE
    
    try:
        import sounddevice as sd
        import numpy as np
        from scipy.io.wavfile import read as read_wav
        from scipy.io.wavfile import write as write_wav
        
        _sd = sd
        _np = np
        _read_wav = read_wav
        _write_wav = write_wav
        RECORD_AVAILABLE = True
        logger.debug("录音依赖加载成功")
    except (ImportError, TypeError, OSError) as e:
        RECORD_AVAILABLE = False
        logger.error(f"录音依赖加载失败：{e}")
    except Exception as e:
        RECORD_AVAILABLE = False
        logger.error(f"录音依赖加载异常：{e}")
    
    return RECORD_AVAILABLE


def _check_voice_dependencies() -> bool:
    """检查语音依赖是否可用，延迟导入。"""
    global VOICE_AVAILABLE, _whisper, _sd, _np, _read_wav, _write_wav
    if VOICE_AVAILABLE is not None:
        return VOICE_AVAILABLE
    
    try:
        import whisper
        import sounddevice as sd
        import numpy as np
        from scipy.io.wavfile import read as read_wav
        from scipy.io.wavfile import write as write_wav
        
        _whisper = whisper
        _sd = sd
        _np = np
        _read_wav = read_wav
        _write_wav = write_wav
        VOICE_AVAILABLE = True
        logger.debug("语音依赖加载成功")
    except (ImportError, TypeError, OSError) as e:
        # Whisper 在某些 Windows 环境下可能因为 ctypes 问题加载失败
        # 这是已知问题，建议用户使用 GLM ASR 引擎
        VOICE_AVAILABLE = False
        logger.warning(f"Whisper 加载失败：{e}")
        logger.warning("建议使用 GLM ASR 云端引擎（设置 VOICE_RECOGNITION_ENGINE=glm-asr）")
        logger.debug("语音依赖不可用")
    except Exception as e:
        VOICE_AVAILABLE = False
        logger.error(f"语音依赖加载异常：{e}")
    
    return VOICE_AVAILABLE


def _check_ffmpeg() -> bool:
    """检测 ffmpeg 是否可用。"""
    global FFMPEG_AVAILABLE
    if FFMPEG_AVAILABLE is None:
        FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
    return FFMPEG_AVAILABLE


def _check_glm_asr() -> bool:
    """检查 GLM ASR 是否可用。"""
    global GLM_ASR_AVAILABLE, _glm_asr_client
    if GLM_ASR_AVAILABLE is not None:
        return GLM_ASR_AVAILABLE
    
    try:
        from src.core.glm_asr_client import GLMASRClient
        api_key = os.getenv("GLM_ASR_API_KEY")
        if not api_key:
            logger.warning("GLM_ASR_API_KEY 未配置，GLM ASR 不可用")
            GLM_ASR_AVAILABLE = False
            return False
        
        _glm_asr_client = GLMASRClient
        GLM_ASR_AVAILABLE = True
        logger.debug("GLM ASR 引擎可用")
    except ImportError:
        logger.debug("GLM ASR 客户端未安装")
        GLM_ASR_AVAILABLE = False
    except Exception as e:
        logger.debug(f"GLM ASR 初始化失败：{e}")
        GLM_ASR_AVAILABLE = False
    
    return GLM_ASR_AVAILABLE


from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus
from .text_utils import to_simplified_chinese


class VoiceInputTool(BaseTool):
    """语音输入工具 - 使用 Whisper 将语音转为文字"""

    name = "voice_input"
    emoji = "🎤"
    title = "语音输入"
    description = "语音转文字工具,支持实时录音、VAD智能录音、纯录音保存文件或从音频文件识别"

    # VAD（语音活动检测）默认参数
    VAD_SILENCE_THRESHOLD = 0.01    # 静音能量阈值
    VAD_SILENCE_DURATION = 1.5      # 静音持续时间(秒)触发停止
    VAD_MIN_RECORDING = 1.0         # 最短录音时长(秒)
    VAD_MAX_RECORDING = 30.0        # 最大录音时长(秒)
    VAD_CHUNK_DURATION = 0.1        # 每次检测块时长(秒)

    def __init__(self):
        super().__init__()
        self._model: Optional[Any] = None
        self._model_name: str = "base"
        self._sample_rate: int = 16000
        # 录音中止标志（供外部停止录音）
        self._stop_recording = False
        # 默认使用 GLM ASR 云端引擎（无需本地依赖），可配置切换到 Whisper
        self._engine = os.getenv("VOICE_RECOGNITION_ENGINE", "glm-asr").lower()
        # 不在初始化时检查依赖，延迟到实际使用时

    def _check_available(self) -> bool:
        """检查语音功能是否可用。"""
        if not _check_record_dependencies():
            raise ImportError(
                "录音功能不可用。请安装依赖：pip install sounddevice scipy"
            )
        return True

    def _load_model(self, model_name: str = "base") -> Any:
        """延迟加载 Whisper 模型"""
        self._check_available()
        if self._model is None or self._model_name != model_name:
            self._model_name = model_name
            self._model = _whisper.load_model(model_name)
        return self._model

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="record_and_transcribe",
                description="录制音频并转为文字（支持VAD自动停止：说完自动停止录音）",
                parameters={
                    "duration": {
                        "type": "number",
                        "description": "最大录音时长(秒),VAD模式下为上限,默认30秒",
                        "default": 30,
                    },
                    "auto_stop": {
                        "type": "boolean",
                        "description": "是否启用 VAD 自动检测说话结束，默认 True",
                        "default": True,
                    },
                    "engine": {
                        "type": "string",
                        "description": "识别引擎：glm-asr(云端，推荐) 或 whisper(本地)",
                        "default": "glm-asr",
                        "enum": ["glm-asr", "whisper"],
                    },
                    "model": {
                        "type": "string",
                        "description": "Whisper 模型 (tiny/base/small/medium/large),默认 base (仅 whisper 引擎)",
                        "default": "base",
                        "enum": ["tiny", "base", "small", "medium", "large"],
                    },
                    "language": {
                        "type": "string",
                        "description": "语言代码(如 zh/en),留空自动检测",
                        "default": None,
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="record_audio",
                description="录制音频并保存为WAV文件（支持VAD自动停止）",
                parameters={
                    "duration": {
                        "type": "number",
                        "description": "最大录音时长(秒),默认30秒",
                        "default": 30,
                    },
                    "auto_stop": {
                        "type": "boolean",
                        "description": "是否启用VAD自动检测说话结束,默认True",
                        "default": True,
                    },
                    "save_path": {
                        "type": "string",
                        "description": "保存路径(留空自动生成到 generated/audio/ 目录)",
                        "default": None,
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="transcribe_file",
                description="将音频文件转为文字",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "音频文件路径(支持 wav/mp3/m4a 等)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Whisper 模型",
                        "default": "base",
                        "enum": ["tiny", "base", "small", "medium", "large"],
                    },
                    "language": {
                        "type": "string",
                        "description": "语言代码,留空自动检测",
                        "default": None,
                    },
                },
                required_params=["file_path"],
            ),
            ActionDef(
                name="list_devices",
                description="列出可用的音频输入设备",
                parameters={},
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行语音输入操作"""
        if action == "record_and_transcribe":
            return await self._record_and_transcribe(**params)
        elif action == "record_audio":
            return await self._record_audio(**params)
        elif action == "transcribe_file":
            return await self._transcribe_file(**params)
        elif action == "list_devices":
            return self._list_devices()
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知动作: {action}",
                output=f"可用动作: {[a.name for a in self.get_actions()]}",
            )

    def stop_recording(self) -> None:
        """外部请求停止当前录音（手动停止按钮调用）。"""
        self._stop_recording = True

    def _record_with_vad(
        self,
        max_duration: float = 30.0,
        auto_stop: bool = True,
        silence_threshold: float = VAD_SILENCE_THRESHOLD,
        silence_duration: float = VAD_SILENCE_DURATION,
    ) -> tuple:
        """使用 VAD（语音活动检测）录音。

        在后台线程中同步执行。持续录音直到检测到说完（静音超过阈值），
        或达到最大时长，或外部调用 stop_recording()。

        Args:
            max_duration: 最大录音时长(秒)
            auto_stop: 是否启用VAD自动停止
            silence_threshold: 静音能量阈值
            silence_duration: 静音持续多少秒停止

        Returns:
            (audio_data: numpy float32 array, actual_duration: float)
        """
        self._stop_recording = False
        chunk_samples = int(self.VAD_CHUNK_DURATION * self._sample_rate)
        max_samples = int(max_duration * self._sample_rate)
        min_samples = int(self.VAD_MIN_RECORDING * self._sample_rate)
        silence_samples_needed = int(silence_duration / self.VAD_CHUNK_DURATION)

        all_chunks = []
        total_samples = 0
        silence_count = 0
        has_speech = False

        logger.info(
            "开始VAD录音: max=%.1fs, auto_stop=%s, threshold=%.4f, silence=%.1fs",
            max_duration, auto_stop, silence_threshold, silence_duration,
        )

        # 打开音频流
        stream = _sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_samples,
        )
        stream.start()

        try:
            while total_samples < max_samples and not self._stop_recording:
                chunk, overflowed = stream.read(chunk_samples)
                all_chunks.append(chunk.copy())
                total_samples += len(chunk)

                # 计算 RMS 能量
                energy = float(_np.sqrt(_np.mean(chunk ** 2)))

                if energy > silence_threshold:
                    silence_count = 0
                    has_speech = True
                else:
                    silence_count += 1

                # VAD 自动停止：已经有语音输入，且连续静音超过阈值
                if auto_stop and has_speech and total_samples >= min_samples:
                    if silence_count >= silence_samples_needed:
                        logger.info("VAD 检测到说话结束（静音 %.1f 秒）", silence_count * self.VAD_CHUNK_DURATION)
                        break
        finally:
            stream.stop()
            stream.close()

        if not all_chunks:
            return _np.array([], dtype=_np.float32), 0.0

        audio_data = _np.concatenate(all_chunks, axis=0).flatten().astype(_np.float32)
        actual_duration = len(audio_data) / self._sample_rate
        logger.info("录音完成: 实际时长=%.1fs, 数据长度=%d", actual_duration, len(audio_data))
        return audio_data, actual_duration

    async def _record_and_transcribe(
        self, duration: float = 30.0, auto_stop: bool = True,
        engine: Optional[str] = None, model: str = "base", language: Optional[str] = None
    ) -> ToolResult:
        """录制音频并转文字（支持 VAD 自动停止）。
    
        Args:
            duration: 最大录音时长 (秒), VAD 模式下为上限
            auto_stop: 是否启用 VAD 自动检测说话结束
            engine: 识别引擎 whisper/glm-asr，默认 glm-asr（云端）
            model: Whisper 模型 (仅 whisper 引擎)
            language: 语言代码
        """
        # 如果未指定引擎，使用实例默认值（可通过环境变量配置）
        if engine is None:
            engine = self._engine
        
        try:
            # 检查录音依赖（任何引擎都需要录音功能）
            self._check_available()
            
            # 根据引擎检查识别依赖
            if engine == "glm-asr":
                if not _check_glm_asr():
                    logger.warning("GLM ASR 不可用，降级到 Whisper")
                    engine = "whisper"
    
            # 限制时长
            duration = max(1, min(duration, 120))
    
            logger.info("开始录音：max=%.1fs, auto_stop=%s, engine=%s, 采样率=%d",
                        duration, auto_stop, engine, self._sample_rate)

            # 在线程池中使用 VAD 录音
            loop = asyncio.get_event_loop()
            audio_data, actual_duration = await loop.run_in_executor(
                None,
                lambda: self._record_with_vad(
                    max_duration=duration,
                    auto_stop=auto_stop,
                )
            )

            if len(audio_data) == 0 or actual_duration < 0.3:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="未检测到有效语音",
                    data={"text": "", "language": "unknown", "duration": actual_duration},
                )

            #新代码
            logger.info("录音完成，实际时长：%.1fs, 数据长度：%d, 范围：[%.4f, %.4f]",
                        actual_duration, len(audio_data), audio_data.min(), audio_data.max())

            # 根据引擎选择转录方式
            if engine == "glm-asr":
                # 使用 GLM ASR 云端识别
                return await self._transcribe_with_glm_asr(
                    audio_data=audio_data,
                    actual_duration=actual_duration,
                    loop=loop,
                )
            else:
                # 使用 Whisper 本地识别
                model_obj = await loop.run_in_executor(None, self._load_model, model)
                
                # 直接将 numpy 数组传给 Whisper（无需 ffmpeg）
                transcribe_kwargs = {"fp16": False}
                if language:
                    transcribe_kwargs["language"] = language
                
                result = await loop.run_in_executor(
                    None, lambda: model_obj.transcribe(audio_data, **transcribe_kwargs)
                )
                
                text = result["text"].strip()
                detected_language = result.get("language", "unknown")
                
                # 转换为简体中文
                text = to_simplified_chinese(text)
                
                logger.info("转录完成：语言=%s, 文字=%s", detected_language, text[:50])
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=f"录音转录成功 (时长：{actual_duration:.1f}s, 语言：{detected_language})",
                    data={
                        "text": text,
                        "language": detected_language,
                        "duration": actual_duration,
                        "model": model,
                        "auto_stopped": auto_stop,
                    },
                )
            ### 旧
            '''
            logger.info("录音完成, 实际时长: %.1fs, 数据长度: %d, 范围: [%.4f, %.4f]",
                        actual_duration, len(audio_data), audio_data.min(), audio_data.max())

            # 加载模型
            model_obj = await loop.run_in_executor(None, self._load_model, model)

            # 直接将 numpy 数组传给 Whisper（无需 ffmpeg）
            transcribe_kwargs = {"fp16": False}
            if language:
                transcribe_kwargs["language"] = language

            result = await loop.run_in_executor(
                None, lambda: model_obj.transcribe(audio_data, **transcribe_kwargs)
            )

            text = result["text"].strip()
            detected_language = result.get("language", "unknown")

            # 转换为简体中文
            text = to_simplified_chinese(text)

            logger.info("转录完成: 语言=%s, 文字=%s", detected_language, text[:50])

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"录音转录成功 (时长: {actual_duration:.1f}s, 语言: {detected_language})",
                data={
                    "text": text,
                    "language": detected_language,
                    "duration": actual_duration,
                    "model": model,
                    "auto_stopped": auto_stop,
                },
            )
            '''
        except Exception as e:
            logger.exception("录音转录失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"录音转录失败: {e}")

    async def _record_audio(
        self, duration: float = 30.0, auto_stop: bool = True,
        save_path: Optional[str] = None,
    ) -> ToolResult:
        """纯录音并保存为 WAV 文件。

        Args:
            duration: 最大录音时长(秒)
            auto_stop: 是否启用 VAD 自动停止
            save_path: 保存路径(None 则自动生成)
        """
        try:
            self._check_available()

            duration = max(1, min(duration, 120))

            # 确定保存路径
            if save_path:
                out_path = Path(save_path).expanduser().resolve()
            else:
                # 自动生成到 generated/audio/ 目录
                audio_dir = Path.cwd() / "generated" / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = audio_dir / f"recording_{timestamp}.wav"

            logger.info("开始纯录音: max=%.1fs, auto_stop=%s, 保存到=%s",
                        duration, auto_stop, out_path)

            # VAD 录音
            loop = asyncio.get_event_loop()
            audio_data, actual_duration = await loop.run_in_executor(
                None,
                lambda: self._record_with_vad(
                    max_duration=duration,
                    auto_stop=auto_stop,
                )
            )

            if len(audio_data) == 0 or actual_duration < 0.3:
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="未检测到有效语音，未保存文件",
                    data={"file_path": None, "duration": 0},
                )

            # 保存为 WAV 文件（int16 格式）
            out_path.parent.mkdir(parents=True, exist_ok=True)
            audio_int16 = (_np.clip(audio_data, -1.0, 1.0) * 32767).astype(_np.int16)
            await loop.run_in_executor(
                None,
                lambda: _write_wav(str(out_path), self._sample_rate, audio_int16)
            )

            file_size_mb = out_path.stat().st_size / (1024 * 1024)
            logger.info("录音文件已保存: %s (%.2f MB, %.1fs)", out_path, file_size_mb, actual_duration)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"录音已保存: {out_path.name} ({actual_duration:.1f}s, {file_size_mb:.2f}MB)",
                data={
                    "file_path": str(out_path),
                    "duration": actual_duration,
                    "file_size_mb": file_size_mb,
                    "sample_rate": self._sample_rate,
                    "format": "wav",
                },
            )

        except Exception as e:
            logger.exception("录音保存失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"录音保存失败: {e}")

    def _load_audio_file(self, file_path: str):
        """加载音频文件为 Whisper 要求的 float32 numpy 数组。

        优先使用 ffmpeg（支持所有格式），若不可用则用 scipy 读取 WAV。
        """
        self._check_available()

        if _check_ffmpeg():
            # ffmpeg 可用时，使用 whisper 内置加载（支持所有格式）
            return _whisper.load_audio(file_path)

        # ffmpeg 不可用，用 scipy 读取 WAV 文件
        ext = Path(file_path).suffix.lower()
        if ext not in (".wav", ".wave"):
            raise RuntimeError(
                f"不支持 {ext} 格式（需要 ffmpeg）。"
                f"请安装 ffmpeg 或将文件转为 WAV 格式。\n"
                f"安装方法: winget install Gyan.FFmpeg"
            )

        sample_rate, data = _read_wav(file_path)

        # 转为 float32
        if data.dtype == _np.int16:
            audio = data.astype(_np.float32) / 32768.0
        elif data.dtype == _np.int32:
            audio = data.astype(_np.float32) / 2147483648.0
        elif data.dtype == _np.float32:
            audio = data
        else:
            audio = data.astype(_np.float32)

        # 多声道转单声道
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # 重采样到 16kHz (Whisper 要求)
        if sample_rate != 16000:
            # 简单线性重采样
            duration = len(audio) / sample_rate
            target_len = int(duration * 16000)
            indices = _np.linspace(0, len(audio) - 1, target_len)
            audio = _np.interp(indices, _np.arange(len(audio)), audio).astype(_np.float32)

        return audio

    async def _transcribe_file(
        self, file_path: str, model: str = "base", language: Optional[str] = None
    ) -> ToolResult:
        """将音频文件转为文字"""
        try:
            path = Path(file_path).expanduser().resolve()
            if not path.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

            # 检查文件大小 (限制 50MB)
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:
                return ToolResult(
                    status=ToolResultStatus.ERROR, error=f"文件过大: {file_size_mb:.1f}MB (限制 50MB)"
                )

            # 加载模型
            loop = asyncio.get_event_loop()
            model_obj = await loop.run_in_executor(None, self._load_model, model)

            # 加载音频文件为 numpy 数组
            audio_data = await loop.run_in_executor(None, self._load_audio_file, str(path))

            # 转录（传入 numpy 数组，无需 ffmpeg）
            transcribe_kwargs = {"fp16": False}
            if language:
                transcribe_kwargs["language"] = language

            result = await loop.run_in_executor(
                None, lambda: model_obj.transcribe(audio_data, **transcribe_kwargs)
            )

            text = result["text"].strip()
            detected_language = result.get("language", "unknown")

            # 转换为简体中文
            text = to_simplified_chinese(text)

            ffmpeg_note = "" if _check_ffmpeg() else " (无 ffmpeg, 仅支持 WAV)"
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"文件转录成功: {path.name}{ffmpeg_note}",
                data={
                    "text": text,
                    "language": detected_language,
                    "file_path": str(path),
                    "file_size_mb": file_size_mb,
                    "model": model,
                },
            )

        except Exception as e:
            logger.exception("文件转录失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件转录失败: {e}")

    def _list_devices(self) -> ToolResult:
        """列出可用的音频输入设备"""
        try:
            self._check_available()
    
            devices = _sd.query_devices()
            input_devices = []
    
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    input_devices.append(
                        {
                            "index": i,
                            "name": dev["name"],
                            "channels": dev["max_input_channels"],
                            "sample_rate": dev["default_samplerate"],
                        }
                    )
    
            default_device = _sd.query_devices(kind="input")
    
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"找到 {len(input_devices)} 个音频输入设备",
                data={"devices": input_devices, "default": default_device["name"]},
            )
    
        except Exception as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"查询设备失败：{e}")
    
    # ========== GLM ASR 云端识别支持 ==========
    
    async def _transcribe_with_glm_asr(
        self,
        audio_data,
        actual_duration: float,
        loop: asyncio.AbstractEventLoop,
    ) -> ToolResult:
        """使用 GLM ASR 云端引擎转录。"""
        import tempfile
            
        try:
            # 临时保存为 WAV 文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_path = Path(temp_wav.name)
                
            # 保存 WAV 文件
            audio_int16 = (_np.clip(audio_data, -1.0, 1.0) * 32767).astype(_np.int16)
            await loop.run_in_executor(
                None,
                lambda: _write_wav(str(temp_path), self._sample_rate, audio_int16)
            )
                
            logger.info("临时 WAV 文件已保存：%s (%.1f KB)", temp_path, temp_path.stat().st_size / 1024)
                
            # 调用 GLM ASR API
            client = _glm_asr_client()
            result = await client.transcribe_async(
                file_path=str(temp_path),
                request_id=f"weclaw_{time.time()}",
            )
                
            logger.info("GLM ASR 转录完成：text=%s", result.text[:50])
                
            # 清理临时文件
            try:
                temp_path.unlink()
                logger.debug("已清理临时 WAV 文件")
            except Exception as e:
                logger.warning(f"清理临时文件失败：{e}")
                
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"录音转录成功 (GLM ASR, 时长：{actual_duration:.1f}s)",
                data={
                    "text": result.text,
                    "language": "zh",
                    "duration": actual_duration,
                    "engine": "glm-asr-2512",
                    "request_id": result.request_id,
                },
            )
                
        except Exception as e:
            logger.exception("GLM ASR 转录失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"GLM ASR 转录失败：{e}",
                data={"engine": "glm-asr"},
            )
