"""测试 GLM ASR 默认配置。

验证默认使用 GLM ASR 引擎而不是 Whisper。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.voice_input import VoiceInputTool

# 创建工具实例
tool = VoiceInputTool()

print("=" * 60)
print("VoiceInputTool 默认配置检查")
print("=" * 60)
print(f"默认引擎：{tool._engine}")
print(f"预期引擎：glm-asr")
print()

if tool._engine == "glm-asr":
    print("✅ 正确！默认使用 GLM ASR 云端引擎")
else:
    print(f"❌ 错误！默认引擎是 {tool._engine}，应该是 glm-asr")

print()
print("可通过环境变量修改:")
print("  VOICE_RECOGNITION_ENGINE=whisper  # 切换到 Whisper")
print("  VOICE_RECOGNITION_ENGINE=glm-asr  # 使用 GLM ASR（默认）")
print("=" * 60)
