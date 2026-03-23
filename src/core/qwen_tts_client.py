"""
Qwen3-TTS 客户端封装模块

提供基于 Qwen3-TTS-12Hz-1.7B-CustomVoice 的语音合成功能

功能:
- 文字转语音 (TTS)
- 支持 10 种语言 (中、英、日、韩、法、德、西、意、葡、俄)
- 支持多种预设音色
- 支持语速调节
- 生成高质量 WAV 音频

依赖:
    pip install qwen-tts soundfile torch

模型下载:
    python -m src.core.qwen_tts_download
"""

import logging
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import soundfile as sf
import torch

logger = logging.getLogger(__name__)

# 全局模型单例
_qwen_tts_model = None
_model_path = None


class QwenTTSLanguage(Enum):
    """Qwen3-TTS 支持的语言"""
    CHINESE = "Chinese"
    ENGLISH = "English"
    JAPANESE = "Japanese"
    KOREAN = "Korean"
    FRENCH = "French"
    GERMAN = "German"
    SPANISH = "Spanish"
    ITALIAN = "Italian"
    PORTUGUESE = "Portuguese"
    RUSSIAN = "Russian"


@dataclass
class VoiceProfile:
    """语音配置文件"""
    name: str
    speaker_id: str
    description: str


# Qwen3-TTS-CustomVoice 内置的预设音色
# 注意: 这些是实际支持的音色名称
PRESET_VOICES = {
    "vivian": VoiceProfile(
        name="Vivian",
        speaker_id="vivian",
        description="年轻女性声音，温柔亲切"
    ),
    "serena": VoiceProfile(
        name="Serena",
        speaker_id="serena", 
        description="成熟女性声音，专业播报"
    ),
    "ryan": VoiceProfile(
        name="Ryan",
        speaker_id="ryan",
        description="年轻男性声音，活力充沛"
    ),
    "aiden": VoiceProfile(
        name="Aiden",
        speaker_id="aiden",
        description="年轻男性声音，沉稳有力"
    ),
    "dylan": VoiceProfile(
        name="Dylan",
        speaker_id="dylan",
        description="成年男性声音，磁性低沉"
    ),
    "eric": VoiceProfile(
        name="Eric",
        speaker_id="eric",
        description="中年男性声音，成熟稳重"
    ),
    "sohee": VoiceProfile(
        name="Sohee",
        speaker_id="sohee",
        description="年轻女性声音，清新甜美"
    ),
    "ono_anna": VoiceProfile(
        name="On Anna",
        speaker_id="ono_anna",
        description="日式女性声音，温柔典雅"
    ),
    "uncle_fu": VoiceProfile(
        name="Uncle Fu",
        speaker_id="uncle_fu",
        description="年长男性声音，慈祥温和"
    ),
}


def _check_cuda_available() -> bool:
    """检查 CUDA 是否可用"""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def _get_model_path() -> Optional[Path]:
    """获取模型路径
    
    优先从以下位置查找:
    1. 环境变量 QWEN_TTS_MODEL_PATH
    2. resources/qwen_tts_models/0.6B 模型
    3. resources/qwen_tts_models/1.7B 模型
    4. ~/.cache/huggingface/hub/ (HuggingFace 缓存)
    """
    import os
    
    # 1. 环境变量
    env_path = os.getenv("QWEN_TTS_MODEL_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    
    # 2. resources 目录 - 优先 0.6B 模型（更小更快）
    project_root = Path(__file__).parent.parent.parent
    model_06b = project_root / "resources" / "qwen_tts_models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
    model_17b = project_root / "resources" / "qwen_tts_models" / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
    
    if model_06b.exists():
        logger.info("使用 Qwen3-TTS 0.6B 模型（轻量快速）")
        return model_06b
    elif model_17b.exists():
        logger.info("使用 Qwen3-TTS 1.7B 模型（高质量）")
        return model_17b
    
    # 3. HuggingFace 缓存
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        # 查找实际的模型目录
        for d in hf_cache.iterdir():
            if d.is_dir() and "Qwen3-TTS" in d.name:
                return d
    
    return None


def _load_model(model_path: Optional[Path] = None) -> Optional[Any]:
    """加载 Qwen3-TTS 模型
    
    Args:
        model_path: 模型路径，为 None 则自动查找或从网络下载
    
    Returns:
        加载的模型，未找到返回 None
    """
    global _qwen_tts_model, _model_path
    
    if _qwen_tts_model is not None:
        return _qwen_tts_model
    
    try:
        from qwen_tts import Qwen3TTSModel
        import torch
        
        # 确定模型路径
        resolved_model_path = model_path or _get_model_path()
        
        # 构建加载参数
        load_kwargs = {}
        
        # 确定设备
        if _check_cuda_available():
            load_kwargs["device_map"] = "cuda:0"
            logger.info("使用 CUDA 加速")
        else:
            load_kwargs["device_map"] = "cpu"
            logger.warning("CUDA 不可用，将在 CPU 上运行（非常慢）")
        
        # 根据 torch 版本选择 dtype
        if hasattr(torch, 'bfloat16'):
            load_kwargs["dtype"] = torch.bfloat16
        else:
            load_kwargs["dtype"] = torch.float32  # CPU fallback
        
        # 确定模型 ID
        if resolved_model_path and Path(resolved_model_path).exists():
            model_id = str(resolved_model_path)
            logger.info(f"从本地加载模型: {model_id}")
        else:
            # 从网络加载
            model_id = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
            logger.info(f"从网络加载模型: {model_id} (首次可能需要下载)")
        
        # 加载模型
        _qwen_tts_model = Qwen3TTSModel.from_pretrained(
            model_id,
            **load_kwargs
        )
        
        _model_path = resolved_model_path
        logger.info("Qwen3-TTS 模型加载成功！")
        return _qwen_tts_model
        
    except ImportError as e:
        logger.error(f"qwen-tts 包未安装: {e}")
        logger.info("请运行: pip install qwen-tts")
        return None
    except Exception as e:
        logger.error(f"Qwen3-TTS 模型加载失败: {e}")
        return None


def _unload_model() -> None:
    """卸载模型，释放显存"""
    global _qwen_tts_model, _model_path
    
    if _qwen_tts_model is not None:
        del _qwen_tts_model
        _qwen_tts_model = None
        _model_path = None
        
        # 清理 CUDA 缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Qwen3-TTS 模型已卸载")


class QwenTTSClient:
    """Qwen3-TTS 客户端
    
    提供文字转语音功能，支持多种语言和预设音色。
    
    使用示例:
        client = QwenTTSClient()
        
        # 使用预设音色生成语音
        audio, sr = client.speak(
            text="你好，这是一段测试语音。",
            language=QwenTTSLanguage.CHINESE,
            voice="vivian"
        )
        
        # 保存到文件
        client.speak_to_file(
            text="你好，世界！",
            output_path="output.wav",
            language=QwenTTSLanguage.CHINESE,
            voice="ryan"
        )
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        preload: bool = False,
        device: Optional[str] = None
    ):
        """初始化 Qwen3-TTS 客户端
        
        Args:
            model_path: 模型路径，为 None 则自动查找
            preload: 是否预加载模型
            device: 设备，None 则自动选择 (cuda/cpu)
        """
        self._model_path = Path(model_path) if model_path else None
        self._model = None
        self._device = device
        
        if preload:
            self._ensure_model()
    
    def _ensure_model(self) -> bool:
        """确保模型已加载
        
        Returns:
            模型是否加载成功
        """
        if self._model is not None:
            return True
        
        self._model = _load_model(self._model_path)
        return self._model is not None
    
    @property
    def is_available(self) -> bool:
        """检查 TTS 引擎是否可用"""
        return self._ensure_model()
    
    @property
    def available_voices(self) -> dict[str, VoiceProfile]:
        """获取可用的语音列表"""
        return PRESET_VOICES.copy()
    
    def speak(
        self,
        text: str,
        language: QwenTTSLanguage = QwenTTSLanguage.CHINESE,
        voice: str = "vivian",
        speed: float = 1.0,
        instruction: Optional[str] = None
    ) -> tuple[list, int]:
        """生成语音
        
        Args:
            text: 要转换的文本
            language: 语言
            voice: 预设音色名称 (如 "vivian", "ryan")
            speed: 语速 (0.5-2.0, 1.0 为正常)
            instruction: 额外的语音指令 (如 "用温柔的语调")
        
        Returns:
            tuple: (音频数据, 采样率)
        
        Raises:
            RuntimeError: 模型加载失败或生成失败
        """
        if not self._ensure_model():
            raise RuntimeError("Qwen3-TTS 模型不可用")
        
        if not text or not text.strip():
            raise ValueError("文本内容不能为空")
        
        try:
            logger.debug(f"正在生成语音: {text[:50]}...")
            
            # 调用 CustomVoice 生成
            wavs, sr = self._model.generate_custom_voice(
                text=text,
                language=language.value,
                speaker=voice,
                speed=speed,
                instruct=instruction
            )
            
            return wavs, sr
            
        except Exception as e:
            logger.error(f"语音生成失败: {e}")
            raise RuntimeError(f"语音生成失败: {e}")
    
    def speak_to_file(
        self,
        text: str,
        output_path: str,
        language: QwenTTSLanguage = QwenTTSLanguage.CHINESE,
        voice: str = "vivian",
        speed: float = 1.0,
        instruction: Optional[str] = None,
        sample_rate: int = 24000
    ) -> str:
        """生成语音并保存到文件
        
        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            language: 语言
            voice: 预设音色名称
            speed: 语速
            instruction: 额外的语音指令
            sample_rate: 输出采样率
        
        Returns:
            实际保存的文件路径
        """
        wavs, sr = self.speak(
            text=text,
            language=language,
            voice=voice,
            speed=speed,
            instruction=instruction
        )
        
        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存音频
        audio_data = wavs[0] if isinstance(wavs, list) else wavs
        
        # 重采样到指定采样率（如果需要）
        if sr != sample_rate:
            import numpy as np
            from scipy import signal
            # 计算重采样比例
            num_samples = int(len(audio_data) * sample_rate / sr)
            audio_data = signal.resample(audio_data, num_samples)
        
        sf.write(str(output_path), audio_data, sample_rate)
        logger.info(f"语音已保存到: {output_path}")
        
        return str(output_path)
    
    def speak_to_bytes(
        self,
        text: str,
        language: QwenTTSLanguage = QwenTTSLanguage.CHINESE,
        voice: str = "vivian",
        speed: float = 1.0,
        instruction: Optional[str] = None,
        sample_rate: int = 24000
    ) -> tuple[bytes, int]:
        """生成语音并返回字节数据
        
        Args:
            text: 要转换的文本
            language: 语言
            voice: 预设音色名称
            speed: 语速
            instruction: 额外的语音指令
            sample_rate: 输出采样率
        
        Returns:
            tuple: (WAV 格式的字节数据, 采样率)
        """
        import io
        import numpy as np
        
        wavs, sr = self.speak(
            text=text,
            language=language,
            voice=voice,
            speed=speed,
            instruction=instruction
        )
        
        audio_data = wavs[0] if isinstance(wavs, list) else wavs
        
        # 重采样（如果需要）
        if sr != sample_rate:
            from scipy import signal
            num_samples = int(len(audio_data) * sample_rate / sr)
            audio_data = signal.resample(audio_data, num_samples)
        
        # 写入 BytesIO
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)
        
        return buffer.read(), sample_rate
    
    def generate_streaming(
        self,
        text: str,
        language: QwenTTSLanguage = QwenTTSLanguage.CHINESE,
        voice: str = "vivian",
        speed: float = 1.0,
        instruction: Optional[str] = None
    ):
        """生成流式语音（生成器）
        
        Args:
            text: 要转换的文本
            language: 语言
            voice: 预设音色名称
            speed: 语速
            instruction: 额外的语音指令
        
        Yields:
            音频数据片段
        """
        if not self._ensure_model():
            raise RuntimeError("Qwen3-TTS 模型不可用")
        
        try:
            # CustomVoice 不支持流式，这里返回完整音频
            wavs, sr = self.speak(
                text=text,
                language=language,
                voice=voice,
                speed=speed,
                instruction=instruction
            )
            
            audio_data = wavs[0] if isinstance(wavs, list) else wavs
            
            # 分段 yield
            chunk_size = sr * 0.5  # 0.5秒一块
            for i in range(0, len(audio_data), int(chunk_size)):
                yield audio_data[i:i + int(chunk_size)]
                
        except Exception as e:
            logger.error(f"流式语音生成失败: {e}")
            raise RuntimeError(f"流式语音生成失败: {e}")
    
    def close(self) -> None:
        """关闭客户端，释放资源"""
        self._model = None
        logger.debug("QwenTTSClient 已关闭")


# 全局客户端单例
_qwen_tts_client: Optional[QwenTTSClient] = None


def get_qwen_tts_client() -> QwenTTSClient:
    """获取全局 QwenTTSClient 单例
    
    Returns:
        QwenTTSClient 实例
    """
    global _qwen_tts_client
    
    if _qwen_tts_client is None:
        _qwen_tts_client = QwenTTSClient(preload=False)
    
    return _qwen_tts_client


def unload_qwen_tts() -> None:
    """卸载全局模型"""
    global _qwen_tts_client, _qwen_tts_model
    
    if _qwen_tts_client:
        _qwen_tts_client.close()
        _qwen_tts_client = None
    
    _unload_model()


# ========== 便捷函数 ==========

def speak(
    text: str,
    language: QwenTTSLanguage = QwenTTSLanguage.CHINESE,
    voice: str = "vivian",
    speed: float = 1.0
) -> tuple[list, int]:
    """便捷函数：生成语音
    
    Args:
        text: 要转换的文本
        language: 语言
        voice: 预设音色名称
        speed: 语速
    
    Returns:
        tuple: (音频数据, 采样率)
    """
    client = get_qwen_tts_client()
    return client.speak(text, language, voice, speed)


def speak_to_file(
    text: str,
    output_path: str,
    language: QwenTTSLanguage = QwenTTSLanguage.CHINESE,
    voice: str = "vivian",
    speed: float = 1.0
) -> str:
    """便捷函数：生成语音并保存到文件
    
    Args:
        text: 要转换的文本
        output_path: 输出文件路径
        language: 语言
        voice: 预设音色名称
        speed: 语速
    
    Returns:
        实际保存的文件路径
    """
    client = get_qwen_tts_client()
    return client.speak_to_file(text, output_path, language, voice, speed)


# 需要 os 模块
import os
