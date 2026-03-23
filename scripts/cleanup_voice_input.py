"""清理 voice_input.py 中的旧代码和注释。"""
from pathlib import Path

file_path = Path("src/tools/voice_input.py")
content = file_path.read_text(encoding='utf-8')

# 删除第 432 行的 "#新代码" 注释
content = content.replace("            #新代码\n", "")

# 删除 "### 旧" 和三引号包裹的旧代码
old_block = """            ### 旧
            '''
            logger.info("录音完成，实际时长：%.1fs, 数据长度：%d, 范围：[%.4f, %.4f]",
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
            )
            '''"""

if old_block in content:
    content = content.replace(old_block, "")
    print("✅ 已删除旧代码块")
else:
    print("❌ 未找到旧代码块")

file_path.write_text(content, encoding='utf-8')
print("✅ 文件已更新")
