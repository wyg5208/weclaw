"""Qwen3-TTS 快速测试脚本

用于测试 Qwen3-TTS 是否正常工作
"""

import os
import sys

# 设置 HuggingFace 镜像（国内加速）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("=" * 60)
print("Qwen3-TTS 快速测试")
print("=" * 60)

# 测试 1: 检查 PyTorch CUDA
print("\n[1] 检查 PyTorch CUDA 支持...")
import torch
print(f"    PyTorch 版本: {torch.__version__}")
print(f"    CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"    CUDA 版本: {torch.version.cuda}")
    print(f"    GPU: {torch.cuda.get_device_name(0)}")
    print(f"    显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# 测试 2: 检查 qwen-tts
print("\n[2] 检查 qwen-tts 包...")
try:
    import qwen_tts
    print(f"    qwen-tts 已安装")
except ImportError as e:
    print(f"    错误: {e}")
    sys.exit(1)

# 检查 GPU
has_cuda = torch.cuda.is_available()
if not has_cuda:
    print("\n    [警告] PyTorch 没有 CUDA 支持，将在 CPU 上运行（非常慢）")
    print("    [建议] 安装 PyTorch GPU 版本: pip install torch --index-url https://download.pytorch.org/whl/cu121")

# 测试 3: 尝试加载模型
print("\n[3] 尝试加载 Qwen3-TTS 模型...")
try:
    from qwen_tts import Qwen3TTSModel
    
    print("    正在加载模型 (首次可能需要下载，约 3.5GB)...")
    print("    这可能需要几分钟时间，请耐心等待...")
    
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        device_map="cuda:0" if torch.cuda.is_available() else "cpu",
        dtype=torch.bfloat16 if hasattr(torch, 'bfloat16') else torch.float16,
    )
    
    print("    模型加载成功！")
    
    # 测试 4: 生成语音
    print("\n[4] 测试语音生成...")
    test_text = "你好，这是一段测试语音。Qwen3-TTS 是一个非常强大的语音合成模型。"
    
    wavs, sr = model.generate_custom_voice(
        text=test_text,
        language="Chinese",
        speaker="vivian",
        speed=1.0
    )
    
    print(f"    生成成功！采样率: {sr}Hz")
    print(f"    音频长度: {len(wavs[0]) / sr:.2f} 秒")
    
    # 保存测试音频
    print("\n[5] 保存测试音频...")
    import soundfile as sf
    output_path = "test_qwen_tts_output.wav"
    sf.write(output_path, wavs[0], sr)
    print(f"    已保存到: {output_path}")
    
    print("\n" + "=" * 60)
    print("测试完成！Qwen3-TTS 工作正常！")
    print("=" * 60)
    
except Exception as e:
    print(f"\n    错误: {e}")
    import traceback
    traceback.print_exc()
    print("\n如果下载超时，请稍后重试或手动下载模型。")
    sys.exit(1)
