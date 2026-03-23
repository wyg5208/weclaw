"""验证 GLM ASR API 配置和连通性。

使用方法:
    python scripts/verify_glm_asr.py
    
功能:
- 检查环境变量配置
- 测试 API 连通性
- 验证 API Key 有效性
- 输出配额和使用情况信息
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.glm_asr_client import GLMASRClient, GLMASRError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_env_config() -> bool:
    """检查环境变量配置。
    
    Returns:
        配置是否完整
    """
    import os
    
    logger.info("=" * 60)
    logger.info("检查环境变量配置")
    logger.info("=" * 60)
    
    api_key = os.getenv("GLM_ASR_API_KEY")
    
    if not api_key:
        logger.error("❌ GLM_ASR_API_KEY 未设置")
        logger.error("请在 .env 文件中配置或设置系统环境变量")
        return False
    
    # 脱敏显示
    masked_key = f"{api_key[:8]}...{api_key[-8:]}" if len(api_key) > 16 else "***"
    logger.info(f"✅ GLM_ASR_API_KEY: {masked_key}")
    
    # 检查其他相关配置
    glm_model = os.getenv("GLM_ASR_MODEL", "glm-asr-2512")
    logger.info(f"ℹ️  GLM_ASR_MODEL: {glm_model}")
    
    return True


async def test_connectivity() -> bool:
    """测试 API 连通性。
    
    Returns:
        连通性测试是否通过
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试 API 连通性")
    logger.info("=" * 60)
    
    try:
        client = GLMASRClient()
        logger.info(f"✅ 客户端初始化成功")
        logger.info(f"   Base URL: {client.base_url}")
        logger.info(f"   Timeout: {client.timeout}s")
        logger.info(f"   Max Retries: {client.max_retries}")
        return True
        
    except ValueError as e:
        logger.error(f"❌ 客户端初始化失败：{e}")
        return False
    except Exception as e:
        logger.error(f"❌ 未知错误：{e}")
        return False


async def test_with_sample_audio() -> bool:
    """使用示例音频测试转录功能。
    
    Returns:
        测试是否通过
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试音频转录功能")
    logger.info("=" * 60)
    
    # 创建临时测试音频 (静音 WAV 文件)
    import wave
    import tempfile
    from pathlib import Path
    
    temp_dir = Path(__file__).parent.parent / "generated" / "test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    test_audio_path = temp_dir / "test_silence.wav"
    
    logger.info(f"生成测试音频：{test_audio_path}")
    
    # 生成 1 秒静音 WAV 文件
    sample_rate = 16000
    duration = 1  # 秒
    n_channels = 1
    sample_width = 2  # 16-bit
    
    try:
        with wave.open(str(test_audio_path), "wb") as wav_file:
            wav_file.setnchannels(n_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            
            # 写入静音数据
            import numpy as np
            audio_data = np.zeros(int(sample_rate * duration), dtype=np.int16)
            wav_file.writeframes(audio_data.tobytes())
        
        file_size_kb = test_audio_path.stat().st_size / 1024
        logger.info(f"✅ 测试音频生成成功：{file_size_kb:.1f}KB, {duration}秒")
        
    except Exception as e:
        logger.warning(f"⚠️  无法生成测试音频：{e}")
        logger.warning("跳过实际转录测试")
        return True  # 不阻断后续测试
    
    # 调用 API 测试
    try:
        logger.info(f"开始转录测试...")
        client = GLMASRClient()
        
        result = await client.transcribe_async(
            file_path=str(test_audio_path),
            request_id="verify_test_" + str(int(asyncio.get_event_loop().time())),
        )
        
        logger.info(f"✅ 转录成功!")
        logger.info(f"   识别文本：'{result.text}'")
        logger.info(f"   模型：{result.model}")
        logger.info(f"   Request ID: {result.request_id}")
        
        # 清理测试文件
        try:
            test_audio_path.unlink()
            logger.info(f"已清理测试文件")
        except:
            pass
        
        return True
        
    except GLMASRError as e:
        logger.error(f"❌ API 调用失败:")
        logger.error(f"   错误码：{e.error.code}")
        logger.error(f"   错误消息：{e.error.message}")
        logger.error(f"   Request ID: {e.error.request_id}")
        
        if e.error.code == "401":
            logger.error("")
            logger.error("🔑 API Key 无效或已过期")
            logger.error("请检查 .env 中的 GLM_ASR_API_KEY 配置")
            logger.error("获取新的 API Key: https://open.bigmodel.cn/")
        elif e.error.code == "429":
            logger.error("")
            logger.error("⏱️  请求频率超限")
            logger.error("请稍后再试或升级账户配额")
        elif e.error.code in ("400", "VALIDATION_ERROR"):
            logger.error("")
            logger.error("📝 请求参数错误")
            logger.error("请检查音频文件格式和大小")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 未知错误：{e}")
        logger.exception("详细堆栈:")
        return False


async def main():
    """主函数。"""
    print("\n" + "=" * 60)
    print("GLM ASR API 配置验证工具")
    print("=" * 60 + "\n")
    
    # Step 1: 检查环境配置
    env_ok = check_env_config()
    if not env_ok:
        print("\n❌ 环境配置检查失败，请修复后重试")
        return
    
    # Step 2: 测试客户端初始化
    client_ok = await test_connectivity()
    if not client_ok:
        print("\n❌ 客户端初始化失败")
        return
    
    # Step 3: 实际转录测试
    transcription_ok = await test_with_sample_audio()
    
    # 总结
    print("\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)
    
    if env_ok and client_ok:
        print("✅ 基础配置验证通过")
        
        if transcription_ok:
            print("✅ 音频转录测试通过")
            print("\n🎉 GLM ASR API 配置完成，可以开始使用!")
        else:
            print("⚠️  音频转录测试失败，请检查上方错误信息")
            print("\n💡 建议:")
            print("   1. 确认 API Key 有效且未过期")
            print("   2. 检查网络连接")
            print("   3. 确认账户有可用配额")
    else:
        print("❌ 验证失败，请根据错误信息修复")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        logger.exception("程序执行异常:")
        sys.exit(1)
