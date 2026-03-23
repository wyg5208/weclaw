"""GLM ASR 客户端单元测试。

测试范围:
- GLMASRClient 初始化
- 音频文件验证
- API 调用 (mock)
- 错误处理
- 重试机制

运行方式:
    pytest tests/test_glm_asr.py -v
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.glm_asr_client import (
    GLMASRClient,
    GLMASRError,
    ASRResult,
    ASRError,
    transcribe_audio,
)


class TestGLMASRClientInit:
    """测试 GLMASRClient 初始化。"""

    def test_init_with_api_key(self):
        """测试使用 API Key 初始化。"""
        api_key = "test_api_key_123456"
        client = GLMASRClient(api_key=api_key)
        
        assert client.api_key == api_key
        assert client.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert client.timeout == 60.0
        assert client.max_retries == 3

    def test_init_from_env(self):
        """测试从环境变量读取 API Key。"""
        with patch.dict(os.environ, {"GLM_ASR_API_KEY": "env_api_key_123456"}):
            client = GLMASRClient()
            assert client.api_key == "env_api_key_123456"

    def test_init_without_api_key(self):
        """测试未提供 API Key 时抛出异常。"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GLMASRClient()
            
            assert "GLM ASR API Key 未提供" in str(exc_info.value)

    def test_init_custom_config(self):
        """测试自定义配置初始化。"""
        client = GLMASRClient(
            api_key="test_key",
            base_url="https://custom.api.com",
            timeout=30.0,
            max_retries=5,
        )
        
        assert client.api_key == "test_key"
        assert client.base_url == "https://custom.api.com"
        assert client.timeout == 30.0
        assert client.max_retries == 5


class TestAudioFileValidation:
    """测试音频文件验证。"""

    def test_validate_valid_wav_file(self, tmp_path):
        """测试验证有效的 WAV 文件。"""
        # 创建临时 WAV 文件
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        client = GLMASRClient(api_key="test_key")
        # 不应该抛出异常
        client._validate_audio_file(wav_file)

    def test_validate_valid_mp3_file(self, tmp_path):
        """测试验证有效的 MP3 文件。"""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"fake mp3 data")
        
        client = GLMASRClient(api_key="test_key")
        client._validate_audio_file(mp3_file)

    def test_validate_nonexistent_file(self):
        """测试验证不存在的文件。"""
        client = GLMASRClient(api_key="test_key")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            client._validate_audio_file(Path("/nonexistent/file.wav"))
        
        assert "音频文件不存在" in str(exc_info.value)

    def test_validate_unsupported_format(self, tmp_path):
        """测试验证不支持的格式。"""
        # 创建临时文件
        txt_file = tmp_path / "test.txt"
        txt_file.write_bytes(b"some text")
        
        client = GLMASRClient(api_key="test_key")
        
        with pytest.raises(ValueError) as exc_info:
            client._validate_audio_file(txt_file)
        
        assert "不支持的音频格式" in str(exc_info.value)

    def test_validate_oversized_file(self, tmp_path):
        """测试验证过大的文件。"""
        # 创建一个大文件 (>25MB)
        large_file = tmp_path / "large.wav"
        size_26mb = 26 * 1024 * 1024
        large_file.write_bytes(b"x" * size_26mb)
        
        client = GLMASRClient(api_key="test_key")
        
        with pytest.raises(ValueError) as exc_info:
            client._validate_audio_file(large_file)
        
        assert "音频文件过大" in str(exc_info.value)


class TestASRResult:
    """测试 ASRResult 数据类。"""

    def test_asr_result_default(self):
        """测试默认参数。"""
        result = ASRResult(text="测试文本")
        
        assert result.text == "测试文本"
        assert result.language == "zh"
        assert result.duration == 0.0
        assert result.request_id == ""
        assert result.model == "glm-asr-2512"

    def test_asr_result_custom(self):
        """测试自定义参数。"""
        result = ASRResult(
            text="Hello",
            language="en",
            duration=5.5,
            request_id="req_123",
            model="glm-asr-2512",
        )
        
        assert result.text == "Hello"
        assert result.language == "en"
        assert result.duration == 5.5
        assert result.request_id == "req_123"


class TestASRError:
    """测试 ASRError 数据类。"""

    def test_asr_error_default(self):
        """测试默认参数。"""
        error = ASRError(code="400", message="错误消息")
        
        assert error.code == "400"
        assert error.message == "错误消息"
        assert error.request_id == ""

    def test_asr_error_with_request_id(self):
        """测试带请求 ID 的错误。"""
        error = ASRError(
            code="401",
            message="认证失败",
            request_id="req_err_123",
        )
        
        assert error.code == "401"
        assert error.message == "认证失败"
        assert error.request_id == "req_err_123"


class TestGLMASRError:
    """测试 GLMASRError 异常。"""

    def test_glm_asr_error(self):
        """测试 GLMASRError 异常。"""
        asr_error = ASRError(code="500", message="服务器错误")
        
        with pytest.raises(GLMASRError) as exc_info:
            raise GLMASRError(asr_error)
        
        assert exc_info.value.error.code == "500"
        assert exc_info.value.error.message == "服务器错误"


class TestTranscribeAsync:
    """测试异步转录方法。"""

    @pytest.mark.asyncio
    async def test_transcribe_success(self, tmp_path):
        """测试成功转录。"""
        # 创建临时 WAV 文件
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "这是识别结果",
            "request_id": "req_test_123",
            "model": "glm-asr-2512",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            client = GLMASRClient(api_key="test_key")
            result = await client.transcribe_async(str(wav_file))
            
            assert result.text == "这是识别结果"
            assert result.request_id == "req_test_123"
            assert result.model == "glm-asr-2512"

    @pytest.mark.asyncio
    async def test_transcribe_http_error(self, tmp_path):
        """测试 HTTP 错误处理。"""
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        # Mock HTTP 状态错误
        from httpx import HTTPStatusError
        
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b'{"error": {"message": "Auth failed"}}'
        mock_response.json.return_value = {
            "error": {"message": "认证失败"}
        }
        
        error = HTTPStatusError("认证失败", request=mock_request, response=mock_response)
        
        with patch("httpx.AsyncClient.post", side_effect=error):
            client = GLMASRClient(api_key="test_key")
            
            with pytest.raises(GLMASRError) as exc_info:
                await client.transcribe_async(str(wav_file))
            
            assert exc_info.value.error.code == "401"

    @pytest.mark.asyncio
    async def test_transcribe_network_error(self, tmp_path):
        """测试网络错误处理。"""
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        from httpx import RequestError
        
        with patch("httpx.AsyncClient.post", side_effect=RequestError("网络错误")):
            client = GLMASRClient(api_key="test_key")
            
            with pytest.raises(GLMASRError) as exc_info:
                await client.transcribe_async(str(wav_file))
            
            assert "网络请求失败" in str(exc_info.value.error.message)


class TestTranscribeSync:
    """测试同步转录方法。"""

    def test_transcribe_sync(self, tmp_path):
        """测试同步转录。"""
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "同步识别结果",
            "request_id": "req_sync_123",
            "model": "glm-asr-2512",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            client = GLMASRClient(api_key="test_key")
            result = client.transcribe_sync(str(wav_file))
            
            assert result.text == "同步识别结果"


class TestTranscribeAudioFunction:
    """测试便捷函数 transcribe_audio。"""

    @pytest.mark.asyncio
    async def test_transcribe_audio_convenience(self, tmp_path):
        """测试便捷函数。"""
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "便捷函数结果",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await transcribe_audio(str(wav_file), api_key="test_key")
            
            assert result == "便捷函数结果"


class TestRetryMechanism:
    """测试重试机制。"""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, tmp_path):
        """测试失败后重试。"""
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav data")
        
        # 前两次失败，第三次成功
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "text": "重试成功",
        }
        
        from httpx import HTTPStatusError
        
        mock_request = MagicMock()
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        
        http_error = HTTPStatusError("Server error", request=mock_request, response=mock_response_error)
        
        call_count = 0
        
        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise http_error
            return mock_response_success
        
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            client = GLMASRClient(api_key="test_key")
            result = await client.transcribe_async(str(wav_file))
            
            assert result.text == "重试成功"
            assert call_count == 3  # 确认重试了 3 次


# ========== 集成测试 ==========

class TestIntegration:
    """集成测试（需要真实 API Key）。"""

    @pytest.mark.skipif(
        not os.getenv("GLM_ASR_API_KEY"),
        reason="需要 GLM_ASR_API_KEY 环境变量"
    )
    @pytest.mark.asyncio
    async def test_real_api_connection(self):
        """测试真实 API 连接。"""
        # 这个测试会真正调用 GLM ASR API
        # 仅在配置了有效 API Key 时运行
        
        client = GLMASRClient()
        
        # 创建一个静音 WAV 文件用于测试
        import wave
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(temp_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                # 写入 1 秒静音
                wav.writeframes(b"\x00\x00" * 16000)
        
        try:
            result = await client.transcribe_async(temp_path)
            # 如果能成功返回结果（即使是空字符串），说明连接正常
            assert isinstance(result, ASRResult)
        except GLMASRError as e:
            # API 调用失败，但错误应该是预期的（如识别失败）
            # 而不是网络连接错误
            assert e.error.code in ("400", "401", "500")
        finally:
            # 清理临时文件
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
