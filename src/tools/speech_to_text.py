"""语音转文字工具 - 音频语音识别与转录

支持:
- faster-whisper (主引擎) — 更快、更省内存
- openai-whisper (备用引擎)
- 降级方案: ffprobe 或 Python wave 模块提取音频元数据

功能:
- transcribe_audio: 转录音频文件为文字
- transcribe_file: 转录并保存到文件 (txt/srt/vtt/json)
- batch_transcribe: 批量转录多个音频文件

降级策略:
- 无 ffmpeg 时: 使用 Python wave 模块读取 .wav 文件
- 无 whisper 时: 仅提取音频元信息，提示安装建议
"""

import asyncio
import json
import logging
import os
import shutil
import struct
import subprocess
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# ========== 双引擎条件导入 ==========

# 主引擎: GLM ASR (云端，推荐)
GLM_ASR_AVAILABLE: bool | None = None
_glm_asr_client = None

# 备用引擎: faster-whisper
FASTER_WHISPER_AVAILABLE: bool | None = None
_faster_whisper_model = None

# 备用引擎: openai-whisper
OPENAI_WHISPER_AVAILABLE: bool | None = None
_whisper = None

# ffmpeg 检测
FFMPEG_AVAILABLE: bool | None = None


def _check_glm_asr() -> bool:
    """检查 GLM ASR 云端引擎是否可用。"""
    global GLM_ASR_AVAILABLE, _glm_asr_client
    if GLM_ASR_AVAILABLE is not None:
        return GLM_ASR_AVAILABLE
    
    try:
        from src.core.glm_asr_client import GLMASRClient
        api_key = os.getenv("GLM_ASR_API_KEY")
        if api_key:
            _glm_asr_client = GLMASRClient
            GLM_ASR_AVAILABLE = True
            logger.debug("GLM ASR 云端引擎可用")
        else:
            GLM_ASR_AVAILABLE = False
            logger.debug("GLM_ASR_API_KEY 未配置")
    except (ImportError, Exception):
        GLM_ASR_AVAILABLE = False
        logger.debug("GLM ASR 不可用")
    
    return GLM_ASR_AVAILABLE


def _check_faster_whisper() -> bool:
    """检查 faster-whisper 是否可用。"""
    global FASTER_WHISPER_AVAILABLE
    if FASTER_WHISPER_AVAILABLE is not None:
        return FASTER_WHISPER_AVAILABLE
    try:
        from faster_whisper import WhisperModel
        FASTER_WHISPER_AVAILABLE = True
        logger.debug("faster-whisper 可用")
    except (ImportError, TypeError, OSError, Exception):
        FASTER_WHISPER_AVAILABLE = False
        logger.debug("faster-whisper 不可用")
    return FASTER_WHISPER_AVAILABLE


def _check_openai_whisper() -> bool:
    """检查 openai-whisper 是否可用。"""
    global OPENAI_WHISPER_AVAILABLE, _whisper
    if OPENAI_WHISPER_AVAILABLE is not None:
        return OPENAI_WHISPER_AVAILABLE
    try:
        import whisper
        _whisper = whisper
        OPENAI_WHISPER_AVAILABLE = True
        logger.debug("openai-whisper 可用")
    except (ImportError, TypeError, OSError, Exception):
        OPENAI_WHISPER_AVAILABLE = False
        logger.debug("openai-whisper 不可用")
    return OPENAI_WHISPER_AVAILABLE


def _check_ffmpeg() -> bool:
    """检测 ffmpeg 是否可用。"""
    global FFMPEG_AVAILABLE
    if FFMPEG_AVAILABLE is None:
        FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
    return FFMPEG_AVAILABLE


def _get_whisper_engine() -> str:
    """检测可用的语音识别引擎。

    Returns:
        "glm-asr", "faster-whisper", "openai-whisper", 或 "none"
    """
    # 优先使用 GLM ASR 云端引擎
    if _check_glm_asr():
        return "glm-asr"
    if _check_faster_whisper():
        return "faster-whisper"
    if _check_openai_whisper():
        return "openai-whisper"
    return "none"


class SpeechToTextTool(BaseTool):
    """语音转文字工具 - 音频语音识别与转录"""

    name = "speech_to_text"
    emoji = "🎙️"
    title = "语音转文字"
    description = "音频语音识别与转录工具"
    timeout = 300  # 语音处理可能较慢

    # 支持的音频格式
    SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aac", ".wma"}

    # 模型大小选项
    MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]

    def __init__(self, output_dir: str = None):
        """初始化语音转文字工具。

        Args:
            output_dir: 输出目录，默认为 generated/YYYY-MM-DD/
        """
        super().__init__()
        self._model = None
        self._model_name: str = ""
        self._engine: str = ""

        # 设置输出目录
        if output_dir:
            self._output_dir = Path(output_dir)
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            self._output_dir = Path.cwd() / "generated" / today
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="transcribe_audio",
                description="转录音频文件为文字",
                parameters={
                    "audio_file": {
                        "type": "string",
                        "description": "音频文件路径，支持 wav/mp3/m4a/flac/ogg 等格式",
                    },
                    "language": {
                        "type": "string",
                        "description": "语言代码（如 zh/en/ja），留空自动检测",
                        "default": None,
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Whisper 模型大小",
                        "default": "base",
                        "enum": ["tiny", "base", "small", "medium", "large"],
                    },
                    "timestamps": {
                        "type": "boolean",
                        "description": "是否输出时间戳",
                        "default": False,
                    },
                },
                required_params=["audio_file"],
            ),
            ActionDef(
                name="transcribe_file",
                description="转录音频并保存到文件",
                parameters={
                    "audio_file": {
                        "type": "string",
                        "description": "音频文件路径",
                    },
                    "output_format": {
                        "type": "string",
                        "description": "输出格式",
                        "default": "txt",
                        "enum": ["txt", "srt", "vtt", "json"],
                    },
                    "language": {
                        "type": "string",
                        "description": "语言代码，留空自动检测",
                        "default": None,
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Whisper 模型大小",
                        "default": "base",
                        "enum": ["tiny", "base", "small", "medium", "large"],
                    },
                },
                required_params=["audio_file"],
            ),
            ActionDef(
                name="batch_transcribe",
                description="批量转录多个音频文件",
                parameters={
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "音频文件路径列表",
                    },
                    "output_format": {
                        "type": "string",
                        "description": "输出格式",
                        "default": "txt",
                        "enum": ["txt", "srt", "vtt", "json"],
                    },
                    "language": {
                        "type": "string",
                        "description": "语言代码，留空自动检测",
                        "default": None,
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Whisper 模型大小",
                        "default": "base",
                        "enum": ["tiny", "base", "small", "medium", "large"],
                    },
                },
                required_params=["audio_files"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行语音转文字操作。"""
        if action == "transcribe_audio":
            return await self._transcribe_audio(**params)
        elif action == "transcribe_file":
            return await self._transcribe_file(**params)
        elif action == "batch_transcribe":
            return await self._batch_transcribe(**params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知动作: {action}",
                output=f"可用动作: {[a.name for a in self.get_actions()]}",
            )

    # ==================== 核心方法 ====================

    def _load_faster_whisper_model(self, model_size: str = "base"):
        """加载 faster-whisper 模型。"""
        from faster_whisper import WhisperModel

        if self._model is None or self._model_name != model_size or self._engine != "faster-whisper":
            logger.info(f"加载 faster-whisper 模型: {model_size}")
            # 使用 CPU，int8 量化以节省内存
            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
            self._model_name = model_size
            self._engine = "faster-whisper"
        return self._model

    def _load_openai_whisper_model(self, model_size: str = "base"):
        """加载 openai-whisper 模型。"""
        if self._model is None or self._model_name != model_size or self._engine != "openai-whisper":
            logger.info(f"加载 openai-whisper 模型: {model_size}")
            self._model = _whisper.load_model(model_size)
            self._model_name = model_size
            self._engine = "openai-whisper"
        return self._model

    def _preprocess_audio(self, audio_path: Path) -> Path:
        """使用 ffmpeg 预处理音频文件（转为 16kHz mono WAV）。

        如果 ffmpeg 不可用，对于 WAV 文件使用 Python wave 模块处理。

        Args:
            audio_path: 原始音频路径

        Returns:
            处理后的 WAV 文件路径
        """
        is_wav = audio_path.suffix.lower() in (".wav", ".wave")

        if _check_ffmpeg():
            # ffmpeg 可用，使用 ffmpeg 转换
            temp_wav = Path(tempfile.gettempdir()) / f"stt_{audio_path.stem}_{datetime.now().strftime('%H%M%S')}.wav"

            cmd = [
                "ffmpeg", "-y",
                "-i", str(audio_path),
                "-ar", "16000",  # 采样率 16kHz
                "-ac", "1",      # 单声道
                "-f", "wav",
                str(temp_wav),
            ]

            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    check=True,
                    timeout=60,
                )
                logger.debug(f"音频预处理完成: {audio_path} -> {temp_wav}")
                return temp_wav
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"ffmpeg 转换失败: {e.stderr.decode()}")

        # ffmpeg 不可用
        if not is_wav:
            raise RuntimeError(
                f"ffmpeg 不可用，无法处理 {audio_path.suffix} 格式音频。\n"
                f"请安装 ffmpeg: winget install Gyan.FFmpeg\n"
                f"或将音频转为 WAV 格式后重试。"
            )

        # 对于 WAV 文件，使用 Python wave 模块检查/转换
        return self._preprocess_wav_with_python(audio_path)

    def _preprocess_wav_with_python(self, audio_path: Path) -> Path:
        """使用 Python wave 模块预处理 WAV 文件。

        如果已经是 16kHz mono，直接返回；否则进行转换。

        Args:
            audio_path: WAV 文件路径

        Returns:
            处理后的 WAV 文件路径
        """
        try:
            with wave.open(str(audio_path), "rb") as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                sample_width = wf.getsampwidth()
                n_frames = wf.getnframes()

                # 如果已经是 16kHz mono，直接返回
                if sample_rate == 16000 and channels == 1:
                    logger.debug(f"WAV 文件已是 16kHz mono: {audio_path}")
                    return audio_path

                # 读取原始数据
                raw_data = wf.readframes(n_frames)

            # 需要转换
            logger.debug(f"转换 WAV: {sample_rate}Hz {channels}ch -> 16000Hz 1ch")

            # 转换为 numpy 风格处理（使用 struct 模块）
            if sample_width == 2:  # 16-bit
                fmt = f"<{n_frames * channels}h"
                samples = list(struct.unpack(fmt, raw_data))
            elif sample_width == 1:  # 8-bit
                samples = [((b - 128) * 256) for b in raw_data]
            else:
                # 不支持的采样位深，返回原文件
                logger.warning(f"不支持的采样位深: {sample_width * 8}bit")
                return audio_path

            # 转单声道（取平均）
            if channels > 1:
                mono_samples = []
                for i in range(0, len(samples), channels):
                    avg = sum(samples[i:i + channels]) // channels
                    mono_samples.append(avg)
                samples = mono_samples

            # 简单重采样到 16kHz（线性插值）
            if sample_rate != 16000:
                duration = len(samples) / sample_rate
                target_len = int(duration * 16000)
                if target_len > 0:
                    resampled = []
                    for i in range(target_len):
                        src_idx = i * (len(samples) - 1) / (target_len - 1) if target_len > 1 else 0
                        idx_low = int(src_idx)
                        idx_high = min(idx_low + 1, len(samples) - 1)
                        frac = src_idx - idx_low
                        val = int(samples[idx_low] * (1 - frac) + samples[idx_high] * frac)
                        resampled.append(val)
                    samples = resampled

            # 写入临时文件
            temp_wav = Path(tempfile.gettempdir()) / f"stt_{audio_path.stem}_{datetime.now().strftime('%H%M%S')}.wav"
            with wave.open(str(temp_wav), "wb") as wf_out:
                wf_out.setnchannels(1)
                wf_out.setsampwidth(2)  # 16-bit
                wf_out.setframerate(16000)
                # 打包为 16-bit PCM
                packed = struct.pack(f"<{len(samples)}h", *[max(-32768, min(32767, s)) for s in samples])
                wf_out.writeframes(packed)

            logger.debug(f"WAV 转换完成: {audio_path} -> {temp_wav}")
            return temp_wav

        except Exception as e:
            logger.warning(f"Python wave 处理失败: {e}，使用原文件")
            return audio_path

    def _get_audio_info_wave(self, audio_path: Path) -> dict[str, Any]:
        """使用 Python wave 模块获取 WAV 文件元数据（无需 ffmpeg）。

        Args:
            audio_path: WAV 音频文件路径

        Returns:
            包含 duration, sample_rate, channels 等的字典
        """
        try:
            with wave.open(str(audio_path), "rb") as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                sample_width = wf.getsampwidth()
                duration = n_frames / sample_rate if sample_rate > 0 else 0

                return {
                    "duration": duration,
                    "format": "wav",
                    "size_bytes": audio_path.stat().st_size,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "sample_width": sample_width,
                    "n_frames": n_frames,
                    "codec": "pcm",
                }
        except Exception as e:
            logger.warning(f"wave 模块读取失败: {e}")
            return {}

    def _get_audio_info_basic(self, audio_path: Path) -> dict[str, Any]:
        """获取基本音频文件信息（仅文件元数据，无需任何外部依赖）。

        Args:
            audio_path: 音频文件路径

        Returns:
            基本文件信息字典
        """
        stat = audio_path.stat()
        return {
            "file_name": audio_path.name,
            "format": audio_path.suffix.lstrip(".").lower(),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def _get_audio_info_ffprobe(self, audio_path: Path) -> dict[str, Any]:
        """使用 ffprobe 获取音频元数据。

        Args:
            audio_path: 音频文件路径

        Returns:
            包含 duration, format, sample_rate 等的字典
        """
        if not _check_ffmpeg():
            # 降级：对于 WAV 文件使用 wave 模块
            if audio_path.suffix.lower() in (".wav", ".wave"):
                return self._get_audio_info_wave(audio_path)
            # 其他格式只能返回基本信息
            return self._get_audio_info_basic(audio_path)

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(audio_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            data = json.loads(result.stdout.decode())

            # 提取音频流信息
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break

            format_info = data.get("format", {})

            return {
                "duration": float(format_info.get("duration", 0)),
                "format": format_info.get("format_name", "unknown"),
                "size_bytes": int(format_info.get("size", 0)),
                "bit_rate": int(format_info.get("bit_rate", 0)),
                "codec": audio_stream.get("codec_name", "unknown") if audio_stream else "unknown",
                "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
                "channels": audio_stream.get("channels", 0) if audio_stream else 0,
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.warning(f"ffprobe 获取音频信息失败: {e}")
            # 降级处理
            if audio_path.suffix.lower() in (".wav", ".wave"):
                return self._get_audio_info_wave(audio_path)
            return self._get_audio_info_basic(audio_path)

    def _transcribe_with_faster_whisper(
        self, audio_path: Path, language: Optional[str] = None, timestamps: bool = False
    ) -> dict[str, Any]:
        """使用 faster-whisper 转录。"""
        model = self._load_faster_whisper_model(self._model_name or "base")

        # 预处理音频
        wav_path = self._preprocess_audio(audio_path)

        try:
            # 转录
            transcribe_kwargs = {}
            if language:
                transcribe_kwargs["language"] = language

            segments, info = model.transcribe(str(wav_path), **transcribe_kwargs)

            # 收集结果
            segments_list = []
            full_text = []
            for segment in segments:
                segments_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                })
                full_text.append(segment.text.strip())

            return {
                "text": " ".join(full_text),
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": segments_list if timestamps else [],
                "engine": "faster-whisper",
            }
        finally:
            # 清理临时文件
            if wav_path != audio_path and wav_path.exists():
                wav_path.unlink()

    def _transcribe_with_openai_whisper(
        self, audio_path: Path, language: Optional[str] = None, timestamps: bool = False
    ) -> dict[str, Any]:
        """使用 openai-whisper 转录。"""
        model = self._load_openai_whisper_model(self._model_name or "base")

        # 预处理音频
        wav_path = self._preprocess_audio(audio_path)

        try:
            transcribe_kwargs = {"fp16": False}
            if language:
                transcribe_kwargs["language"] = language

            result = model.transcribe(str(wav_path), **transcribe_kwargs)

            segments_list = []
            if timestamps and "segments" in result:
                for seg in result["segments"]:
                    segments_list.append({
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip(),
                    })

            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": segments_list,
                "engine": "openai-whisper",
            }
        finally:
            # 清理临时文件
            if wav_path != audio_path and wav_path.exists():
                wav_path.unlink()

    def _transcribe_with_glm_asr(
        self, audio_path: Path, language: Optional[str] = None
    ) -> dict[str, Any]:
        """使用 GLM ASR 云端引擎转录。
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码（GLM ASR 会自动检测）
        
        Returns:
            转录结果字典
        """
        import asyncio
        
        # 预处理音频（确保是 16kHz WAV）
        wav_path = self._preprocess_audio(audio_path)
        
        try:
            # 创建新的事件循环（在线程池中运行）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                client = _glm_asr_client()
                result = loop.run_until_complete(
                    client.transcribe_async(
                        file_path=str(wav_path),
                        request_id=f"stt_{datetime.now().strftime('%H%M%S')}",
                    )
                )
                
                return {
                    "text": result.text.strip(),
                    "language": language or "zh",
                    "engine": "glm-asr",
                    "request_id": result.request_id,
                }
            finally:
                loop.close()
        
        except Exception as e:
            logger.error(f"GLM ASR 转录失败: {e}")
            return {
                "text": "",
                "error": f"GLM ASR 转录失败: {e}",
                "engine": "glm-asr",
            }
        finally:
            # 清理临时文件
            if wav_path != audio_path and wav_path.exists():
                wav_path.unlink()

    def _transcribe_audio_sync(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model_size: str = "base",
        timestamps: bool = False,
    ) -> dict[str, Any]:
        """同步执行音频转录。"""
        self._model_name = model_size
        engine = _get_whisper_engine()

        # 优先使用 GLM ASR 云端引擎
        if engine == "glm-asr":
            return self._transcribe_with_glm_asr(audio_path, language)
        elif engine == "faster-whisper":
            return self._transcribe_with_faster_whisper(audio_path, language, timestamps)
        elif engine == "openai-whisper":
            return self._transcribe_with_openai_whisper(audio_path, language, timestamps)
        else:
            # 降级方案：提取音频元信息并给出安装建议
            return self._fallback_audio_info(audio_path)

    def _fallback_audio_info(self, audio_path: Path) -> dict[str, Any]:
        """降级方案：无 Whisper 时提取音频元信息并给出安装建议。

        Args:
            audio_path: 音频文件路径

        Returns:
            包含音频信息和安装建议的字典
        """
        # 获取音频信息（优先使用 ffprobe，降级到 wave 或基本信息）
        audio_info = self._get_audio_info_ffprobe(audio_path)

        # 构建安装建议
        install_suggestions = [
            "语音转文字引擎未安装，无法进行转录。",
            "",
            "请安装以下任一语音识别引擎：",
            "",
            "【推荐】GLM ASR 云端引擎（无需本地模型）：",
            "  1. 在 .env 中配置 GLM_ASR_API_KEY",
            "  2. pip install httpx tenacity",
            "",
            "【备选】faster-whisper（本地）：",
            "  pip install faster-whisper",
            "",
            "【备选】openai-whisper（本地）：",
            "  pip install openai-whisper",
            "",
        ]

        # 根据 ffmpeg 状态添加额外提示
        if not _check_ffmpeg():
            install_suggestions.extend([
                "【可选】安装 ffmpeg 以支持更多音频格式：",
                "  winget install Gyan.FFmpeg",
                "",
            ])

        # 添加音频信息摘要
        info_lines = ["音频文件信息："]
        if audio_info.get("duration"):
            info_lines.append(f"  时长: {audio_info['duration']:.1f} 秒")
        if audio_info.get("sample_rate"):
            info_lines.append(f"  采样率: {audio_info['sample_rate']} Hz")
        if audio_info.get("channels"):
            info_lines.append(f"  声道: {audio_info['channels']}")
        if audio_info.get("codec"):
            info_lines.append(f"  编码: {audio_info['codec']}")
        if audio_info.get("size_bytes"):
            size_mb = audio_info["size_bytes"] / (1024 * 1024)
            info_lines.append(f"  大小: {size_mb:.2f} MB")

        return {
            "text": "",
            "error": "\n".join(install_suggestions),
            "audio_info": audio_info,
            "audio_summary": "\n".join(info_lines),
            "engine": "info-only",
            "whisper_available": False,
            "ffmpeg_available": _check_ffmpeg(),
        }

    # ==================== 动作实现 ====================

    async def _transcribe_audio(
        self,
        audio_file: str,
        language: Optional[str] = None,
        model_size: str = "base",
        timestamps: bool = False,
    ) -> ToolResult:
        """转录音频文件为文字。"""
        try:
            audio_path = Path(audio_file).expanduser().resolve()

            # 验证文件
            if not audio_path.exists():
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"文件不存在: {audio_file}",
                )

            if audio_path.suffix.lower() not in self.SUPPORTED_FORMATS:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"不支持的音频格式: {audio_path.suffix}。支持: {', '.join(self.SUPPORTED_FORMATS)}",
                )

            # 检查文件大小（限制 100MB）
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 100:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"文件过大: {file_size_mb:.1f}MB（限制 100MB）",
                )

            # 在线程池中执行转录
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._transcribe_audio_sync(audio_path, language, model_size, timestamps),
            )

            # 处理降级情况（无 Whisper 引擎）
            if result.get("engine") == "info-only":
                # 返回部分成功：提供音频信息但无法转录
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=result.get("error", "语音转文字引擎不可用"),
                    output=result.get("audio_summary", ""),
                    data={
                        "audio_info": result.get("audio_info", {}),
                        "whisper_available": False,
                        "ffmpeg_available": result.get("ffmpeg_available", False),
                        "file_path": str(audio_path),
                    },
                )

            # 处理其他错误情况
            if "error" in result and not result.get("text"):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=result["error"],
                    data={"audio_info": result.get("audio_info", {})},
                )

            # 构建输出
            output_parts = [f"转录成功 ({result.get('engine', 'unknown')})"]
            if result.get("language"):
                output_parts.append(f"语言: {result['language']}")
            if result.get("duration"):
                output_parts.append(f"时长: {result['duration']:.1f}s")

            data = {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "engine": result.get("engine"),
                "model_size": model_size,
                "file_path": str(audio_path),
            }

            if timestamps and result.get("segments"):
                data["segments"] = result["segments"]
                # 格式化带时间戳的文本
                timestamped_text = []
                for seg in result["segments"]:
                    start = self._format_timestamp(seg["start"])
                    end = self._format_timestamp(seg["end"])
                    timestamped_text.append(f"[{start} --> {end}] {seg['text']}")
                data["timestamped_text"] = "\n".join(timestamped_text)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=" | ".join(output_parts),
                data=data,
            )

        except Exception as e:
            logger.exception("音频转录失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"转录失败: {e}")

    async def _transcribe_file(
        self,
        audio_file: str,
        output_format: str = "txt",
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> ToolResult:
        """转录音频并保存到文件。"""
        try:
            audio_path = Path(audio_file).expanduser().resolve()

            # 先执行转录
            timestamps = output_format in ("srt", "vtt", "json")
            transcribe_result = await self._transcribe_audio(
                audio_file=audio_file,
                language=language,
                model_size=model_size,
                timestamps=timestamps,
            )

            if not transcribe_result.is_success:
                return transcribe_result

            # 生成输出文件
            output_filename = f"{audio_path.stem}_transcript.{output_format}"
            output_path = self._output_dir / output_filename

            text = transcribe_result.data.get("text", "")
            segments = transcribe_result.data.get("segments", [])

            if output_format == "txt":
                content = text
            elif output_format == "srt":
                content = self._generate_srt(segments)
            elif output_format == "vtt":
                content = self._generate_vtt(segments)
            elif output_format == "json":
                content = json.dumps({
                    "text": text,
                    "language": transcribe_result.data.get("language"),
                    "segments": segments,
                    "source_file": str(audio_path),
                    "model_size": model_size,
                }, ensure_ascii=False, indent=2)
            else:
                content = text

            output_path.write_text(content, encoding="utf-8")
            logger.info(f"转录结果已保存: {output_path}")

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"转录完成，已保存到: {output_path.name}",
                data={
                    **transcribe_result.data,
                    "output_file": str(output_path),
                    "output_format": output_format,
                },
            )

        except Exception as e:
            logger.exception("转录文件保存失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"转录保存失败: {e}")

    async def _batch_transcribe(
        self,
        audio_files: list[str],
        output_format: str = "txt",
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> ToolResult:
        """批量转录多个音频文件。"""
        try:
            if not audio_files:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="音频文件列表为空",
                )

            results = []
            success_count = 0
            error_count = 0

            for audio_file in audio_files:
                result = await self._transcribe_file(
                    audio_file=audio_file,
                    output_format=output_format,
                    language=language,
                    model_size=model_size,
                )

                file_result = {
                    "file": audio_file,
                    "success": result.is_success,
                }

                if result.is_success:
                    success_count += 1
                    file_result["output_file"] = result.data.get("output_file")
                    file_result["text"] = result.data.get("text", "")[:200]  # 截断预览
                else:
                    error_count += 1
                    file_result["error"] = result.error

                results.append(file_result)

            return ToolResult(
                status=ToolResultStatus.SUCCESS if error_count == 0 else ToolResultStatus.ERROR,
                output=f"批量转录完成: {success_count} 成功, {error_count} 失败",
                data={
                    "total": len(audio_files),
                    "success_count": success_count,
                    "error_count": error_count,
                    "results": results,
                },
            )

        except Exception as e:
            logger.exception("批量转录失败")
            return ToolResult(status=ToolResultStatus.ERROR, error=f"批量转录失败: {e}")

    # ==================== 辅助方法 ====================

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为 HH:MM:SS,mmm 格式。"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        """格式化时间戳为 VTT 格式 HH:MM:SS.mmm。"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _generate_srt(self, segments: list[dict]) -> str:
        """生成 SRT 字幕格式。"""
        if not segments:
            return ""

        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._format_timestamp(seg["start"])
            end = self._format_timestamp(seg["end"])
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(seg["text"])
            lines.append("")

        return "\n".join(lines)

    def _generate_vtt(self, segments: list[dict]) -> str:
        """生成 WebVTT 字幕格式。"""
        if not segments:
            return "WEBVTT\n"

        lines = ["WEBVTT", ""]
        for seg in segments:
            start = self._format_timestamp_vtt(seg["start"])
            end = self._format_timestamp_vtt(seg["end"])
            lines.append(f"{start} --> {end}")
            lines.append(seg["text"])
            lines.append("")

        return "\n".join(lines)

    async def close(self) -> None:
        """清理资源。"""
        self._model = None
        self._model_name = ""
        self._engine = ""
