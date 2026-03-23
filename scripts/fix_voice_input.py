"""修复 voice_input.py 中的 _record_and_transcribe 方法。"""
import re

file_path = "d:/python_projects/weclaw/src/tools/voice_input.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换日志输出（移除范围信息）
old_log = 'logger.info("录音完成，实际时长：%.1fs, 数据长度：%d, 范围：[%.4f, %.4f]",\n                        actual_duration, len(audio_data), audio_data.min(), audio_data.max())'
new_log = 'logger.info("录音完成，实际时长：%.1fs, 数据长度：%d",\n                        actual_duration, len(audio_data))'

content = content.replace(old_log, new_log)

# 替换整个转录逻辑部分
old_transcribe = '''            # 加载模型
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

new_transcribe = '''            # 根据引擎选择转录方式
            if engine == "glm-asr":
                return await self._transcribe_with_glm_asr(
                    audio_data, actual_duration, loop
                )
            else:
                # Whisper 路径
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
                        "engine": "whisper",
                    },
                )'''

content = content.replace(old_transcribe, new_transcribe)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ voice_input.py 修改完成")
