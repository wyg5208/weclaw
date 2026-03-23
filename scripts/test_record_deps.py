"""测试录音依赖检查。

验证录音功能独立于识别引擎。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 导入后重置状态以重新加载
from tools import voice_input
voice_input.RECORD_AVAILABLE = None
voice_input._sd = None

from tools.voice_input import _check_record_dependencies, _check_voice_dependencies

print("=" * 60)
print("录音依赖检查")
print("=" * 60)

# 测试录音依赖
record_ok = _check_record_dependencies()
# 重新导入以获取最新值
from tools.voice_input import _sd as sd_current
print(f"录音依赖：{'✅ 可用' if record_ok else '❌ 不可用'}")
print(f"sounddevice: {'✅ 已加载' if sd_current is not None else '❌ 未加载'}")
print()

# 测试 Whisper 依赖
whisper_ok = _check_voice_dependencies()
print(f"Whisper 依赖：{'✅ 可用' if whisper_ok else '⚠️  不可用（可使用 GLM ASR）'}")
print()

if record_ok and sd_current is not None:
    print("✅ 成功！录音功能可用，可以使用 GLM ASR 云端识别")
else:
    print("❌ 错误！录音功能不可用，需要安装 sounddevice 和 scipy")
    print("   pip install sounddevice scipy")

print("=" * 60)
