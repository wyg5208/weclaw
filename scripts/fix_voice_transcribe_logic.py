"""修复语音转录逻辑，根据引擎选择正确的转录方式。"""
import re
from pathlib import Path

file_path = Path("src/tools/voice_input.py")
content = file_path.read_text(encoding='utf-8')

# 查找并替换录音后的转录逻辑
old_code = '''            logger.info("录音完成，实际时长：%.1fs, 数据长度：%d, 范围：[%.4f, %.4f]",
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
            )'''

new_code = '''            logger.info("录音完成，实际时长：%.1fs, 数据长度：%d, 范围：[%.4f, %.4f]",
                        actual_duration, len(audio_data), audio_data.min(), audio_data.max())

            # 根据引擎选择转录方式
            if engine == "glm-asr":
                # 使用 GLM ASR 云端识别
                return await self._transcribe_with_glm_asr(
                    audio_data=audio_data,
                    actual_duration=actual_duration,
                    auto_stop=auto_stop,
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
                )'''

if old_code in content:
    content = content.replace(old_code, new_code)
    file_path.write_text(content, encoding='utf-8')
    print("✅ 修复成功！已添加引擎选择逻辑")
else:
    print("❌ 未找到目标代码段")
    print("可能代码格式有差异")
