"""智谱 GLM-ASR 语音识别客户端。

封装智谱 GLM-ASR-2512 模型的语音转文本 API，提供同步/异步转录功能。

特性:
- HTTP multipart/form-data 音频上传
- JWT Bearer Token 认证
- 同步/异步转录接口
- 流式响应支持 (可选)
- 完善的错误处理 (网络/超时/鉴权/格式)
- 自动重试机制
- 热词支持
- 请求追踪

API 文档参考：
https://docs.bigmodel.cn/llms.txt
"""
import asyncio
import base64
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


@dataclass
class ASRResult:
    """语音识别结果。
    
    Attributes:
        text: 转录的文本内容
        language: 检测的语言 (自动检测)
        duration: 音频时长 (秒)
        request_id: 请求 ID
        model: 使用的模型名称
    """
    text: str
    language: str = "zh"
    duration: float = 0.0
    request_id: str = ""
    model: str = "glm-asr-2512"


@dataclass
class ASRError:
    """语音识别错误信息。
    
    Attributes:
        code: 错误码
        message: 错误消息
        request_id: 请求 ID
    """
    code: str
    message: str
    request_id: str = ""


class GLMASRError(Exception):
    """GLM ASR API 异常。"""
    def __init__(self, error: ASRError):
        self.error = error
        super().__init__(f"GLM ASR Error {error.code}: {error.message}")


class GLMASRClient:
    """智谱 GLM-ASR 语音识别客户端。
    
    使用示例:
        ```python
        client = GLMASRClient()
        result = await client.transcribe_async("audio.wav")
        print(result.text)
        ```
    """
    
    # API 端点
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    TRANSCRIBE_ENDPOINT = "/audio/transcriptions"
    
    # 默认配置
    DEFAULT_MODEL = "glm-asr-2512"
    DEFAULT_TIMEOUT = 60.0  # 秒
    DEFAULT_MAX_RETRIES = 3
    
    # 音频限制 (根据 API 文档)
    MAX_FILE_SIZE_MB = 25
    MAX_DURATION_SECONDS = 30
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """初始化 GLM ASR 客户端。
        
        Args:
            api_key: API Key，默认为环境变量 GLM_ASR_API_KEY
            base_url: API 基础 URL，可自定义
            timeout: HTTP 请求超时 (秒)
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("GLM_ASR_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GLM ASR API Key 未提供。\n"
                "请设置环境变量 GLM_ASR_API_KEY 或在构造函数中传入。\n"
                "获取地址：https://open.bigmodel.cn/"
            )
        
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        logger.debug(
            f"GLM ASR 客户端初始化完成：base_url={self.base_url}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )
    
    def _get_headers(self) -> dict:
        """获取 HTTP 请求头。
        
        Returns:
            包含认证信息的 headers 字典
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Weclaw-GLM-ASR-Client/1.0",
        }
    
    def _validate_audio_file(self, file_path: Path) -> None:
        """验证音频文件。
        
        Args:
            file_path: 音频文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或文件过大
        """
        if not file_path.exists():
            raise FileNotFoundError(f"音频文件不存在：{file_path}")
        
        # 检查格式
        supported_formats = {".wav", ".mp3"}
        if file_path.suffix.lower() not in supported_formats:
            raise ValueError(
                f"不支持的音频格式：{file_path.suffix}。\n"
                f"支持的格式：{', '.join(supported_formats)}"
            )
        
        # 检查大小
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"音频文件过大：{file_size_mb:.2f}MB (限制 {self.MAX_FILE_SIZE_MB}MB)"
            )
    
    async def _upload_audio_multipart(
        self,
        client: httpx.AsyncClient,
        file_path: Path,
        model: str,
        hotwords: Optional[List[str]] = None,
        prompt: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ASRResult:
        """通过 multipart/form-data 上传音频文件。
        
        Args:
            client: HTTP 客户端
            file_path: 音频文件路径
            model: 模型名称
            hotwords: 热词表
            prompt: 上下文提示
            request_id: 请求 ID
            user_id: 终端用户 ID
            
        Returns:
            识别结果
            
        Raises:
            GLMASRError: API 调用失败
        """
        url = f"{self.base_url}{self.TRANSCRIBE_ENDPOINT}"
        
        # 准备表单数据
        files = {
            "file": (file_path.name, open(file_path, "rb"), "audio/wav"),
        }
        
        data = {
            "model": model,
            "stream": "false",
        }
        
        if hotwords:
            import json
            data["hotwords"] = json.dumps(hotwords)
        
        if prompt:
            data["prompt"] = prompt
        
        if request_id:
            data["request_id"] = request_id
        
        if user_id:
            data["user_id"] = user_id
        
        try:
            response = await client.post(
                url,
                files=files,
                data=data,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            # 解析结果
            return ASRResult(
                text=result_data.get("text", ""),
                language="zh",  # GLM 自动检测中文
                duration=0.0,  # API 未返回时长
                request_id=result_data.get("request_id", ""),
                model=result_data.get("model", model),
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 状态错误：{e.response.status_code}")
            error_data = e.response.json() if e.response.content else {}
            raise GLMASRError(ASRError(
                code=str(e.response.status_code),
                message=error_data.get("error", {}).get("message", str(e)),
                request_id=error_data.get("request_id", ""),
            ))
        except httpx.RequestError as e:
            logger.error(f"请求错误：{e}")
            raise GLMASRError(ASRError(
                code="REQUEST_ERROR",
                message=f"网络请求失败：{str(e)}",
            ))
        finally:
            # 确保文件句柄关闭
            files["file"][1].close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GLMASRError),
        reraise=True,
    )
    async def transcribe_async(
        self,
        file_path: str,
        model: str = DEFAULT_MODEL,
        hotwords: Optional[List[str]] = None,
        prompt: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ASRResult:
        """异步转录音频文件为文本。
        
        Args:
            file_path: 音频文件路径 (.wav/.mp3)
            model: 模型名称，默认 glm-asr-2512
            hotwords: 热词表，如 ["人名", "地名"]
            prompt: 上下文提示 (长文本场景)
            request_id: 请求追踪 ID (自动生成)
            user_id: 终端用户 ID (用于风控)
            
        Returns:
            识别结果
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或过大
            GLMASRError: API 调用失败
        """
        path = Path(file_path).expanduser().resolve()
        self._validate_audio_file(path)
        
        logger.info(
            f"开始 GLM ASR 转录：file={path.name}, "
            f"size={path.stat().st_size/1024:.1f}KB, model={model}"
        )
        
        async with httpx.AsyncClient() as client:
            return await self._upload_audio_multipart(
                client=client,
                file_path=path,
                model=model,
                hotwords=hotwords,
                prompt=prompt,
                request_id=request_id or f"weclaw_{asyncio.get_event_loop().time()}",
                user_id=user_id,
            )
    
    def transcribe_sync(
        self,
        file_path: str,
        model: str = DEFAULT_MODEL,
        hotwords: Optional[List[str]] = None,
        prompt: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ASRResult:
        """同步转录音频文件为文本。
        
        Args:
            file_path: 音频文件路径
            model: 模型名称
            hotwords: 热词表
            prompt: 上下文提示
            request_id: 请求追踪 ID
            user_id: 终端用户 ID
            
        Returns:
            识别结果
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或过大
            GLMASRError: API 调用失败
        """
        return asyncio.run(self.transcribe_async(
            file_path=file_path,
            model=model,
            hotwords=hotwords,
            prompt=prompt,
            request_id=request_id,
            user_id=user_id,
        ))
    
    async def transcribe_base64_async(
        self,
        audio_base64: str,
        model: str = DEFAULT_MODEL,
        hotwords: Optional[List[str]] = None,
        prompt: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ASRResult:
        """通过 Base64 编码转录音频。
        
        适用于已加载到内存的音频数据。
        
        Args:
            audio_base64: 音频文件的 Base64 编码
            model: 模型名称
            hotwords: 热词表
            prompt: 上下文提示
            request_id: 请求追踪 ID
            user_id: 终端用户 ID
            
        Returns:
            识别结果
            
        Raises:
            GLMASRError: API 调用失败
        """
        url = f"{self.base_url}{self.TRANSCRIBE_ENDPOINT}"
        
        data = {
            "model": model,
            "stream": "false",
            "file_base64": audio_base64,
        }
        
        if hotwords:
            import json
            data["hotwords"] = json.dumps(hotwords)
        
        if prompt:
            data["prompt"] = prompt
        
        if request_id:
            data["request_id"] = request_id
        
        if user_id:
            data["user_id"] = user_id
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=data,
                    headers=self._get_headers(),
                    timeout=self.timeout,
                )
                
                response.raise_for_status()
                result_data = response.json()
                
                return ASRResult(
                    text=result_data.get("text", ""),
                    language="zh",
                    duration=0.0,
                    request_id=result_data.get("request_id", ""),
                    model=result_data.get("model", model),
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 状态错误：{e.response.status_code}")
            error_data = e.response.json() if e.response.content else {}
            raise GLMASRError(ASRError(
                code=str(e.response.status_code),
                message=error_data.get("error", {}).get("message", str(e)),
                request_id=error_data.get("request_id", ""),
            ))
        except httpx.RequestError as e:
            logger.error(f"请求错误：{e}")
            raise GLMASRError(ASRError(
                code="REQUEST_ERROR",
                message=f"网络请求失败：{str(e)}",
            ))


# ========== 便捷函数 ==========

async def transcribe_audio(
    file_path: str,
    api_key: Optional[str] = None,
    **kwargs,
) -> str:
    """便捷函数：转录音频文件并返回文本。
    
    Args:
        file_path: 音频文件路径
        api_key: API Key (可选，默认使用环境变量)
        **kwargs: 传递给 GLMASRClient.transcribe_async 的参数
        
    Returns:
        识别的文本内容
        
    Example:
        ```python
        text = await transcribe_audio("recording.wav")
        print(text)
        ```
    """
    client = GLMASRClient(api_key=api_key)
    result = await client.transcribe_async(file_path, **kwargs)
    return result.text
