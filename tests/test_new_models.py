"""测试 GLM-5、Kimi K2.5、Qwen 3.5 Max 三个大模型

使用方法:
    python test_new_models.py

环境要求:
    - .env 文件中已配置 GLM_API_KEY、KIMI_API_KEY、QWEN_API_KEY
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# 加载 .env 文件
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_env()

sys.path.insert(0, str(Path(__file__).parent))

from src.models.registry import ModelRegistry


async def test_model(registry: ModelRegistry, model_key: str, test_message: str = "你好，请用一句话介绍自己"):
    """测试单个模型"""
    model_cfg = registry.get(model_key)
    if not model_cfg:
        return {"success": False, "error": f"模型 {model_key} 未找到"}
    
    # 检查 API Key
    if model_cfg.api_key_env and not os.environ.get(model_cfg.api_key_env):
        return {
            "success": False, 
            "error": f"缺少 API Key: {model_cfg.api_key_env}"
        }
    
    print(f"\n{'='*60}")
    print(f"测试模型: {model_cfg.name} ({model_key})")
    print(f"Provider: {model_cfg.provider}")
    print(f"API Key: {model_cfg.api_key_env}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        stream = registry.chat_stream(
            model_key=model_key,
            messages=[{"role": "user", "content": test_message}],
        )
        
        first_chunk_time = None
        chunk_count = 0
        content = ""
        
        async for chunk in stream:
            chunk_count += 1
            if first_chunk_time is None:
                first_chunk_time = time.time() - start_time
            
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                content += delta.content
                print(delta.content, end="", flush=True)
        
        total_time = time.time() - start_time
        
        print()  # 换行
        print(f"\n✓ 成功!")
        print(f"  首 chunk 时间: {first_chunk_time:.2f}s")
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  chunks 数量: {chunk_count}")
        print(f"  响应长度: {len(content)} 字符")
        
        return {
            "success": True,
            "model": model_cfg.name,
            "first_chunk_time": first_chunk_time,
            "total_time": total_time,
            "chunk_count": chunk_count,
            "content": content,
        }
        
    except Exception as e:
        print(f"\n✗ 失败: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """主测试函数"""
    print("="*60)
    print("WinClaw 新模型测试工具")
    print("="*60)
    
    # 检查环境变量
    print("\n环境变量检查:")
    for env in ["GLM_API_KEY", "KIMI_API_KEY", "QWEN_API_KEY"]:
        value = os.environ.get(env)
        status = "✓ 已设置" if value else "✗ 未设置"
        masked = value[:8] + "..." + value[-4:] if value and len(value) > 12 else "***"
        print(f"  {env}: {status} ({masked if value else 'N/A'})")
    
    # 初始化注册表
    print("\n初始化模型注册表...")
    registry = ModelRegistry()
    
    # 测试的模型
    models_to_test = [
        ("glm-5", "GLM-5"),
        ("kimi-k2-5", "Kimi K2.5"),
        ("moonshot-v1-8k", "Moonshot V1 8K"),
        ("qwen-max", "Qwen Max"),
        ("qwen-plus", "Qwen Plus"),
        ("qwen-turbo", "Qwen Turbo"),
    ]
    
    results = []
    
    for model_key, model_name in models_to_test:
        result = await test_model(registry, model_key)
        result["model_key"] = model_key
        result["model_name"] = model_name
        results.append(result)
    
    # 汇总报告
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    
    for r in results:
        status = "✓ 通过" if r["success"] else "✗ 失败"
        print(f"\n{status} {r['model_name']} ({r['model_key']})")
        if r["success"]:
            print(f"  首 chunk: {r['first_chunk_time']:.2f}s")
            print(f"  总耗时: {r['total_time']:.2f}s")
        else:
            print(f"  错误: {r.get('error', 'Unknown')}")
    
    # 统计
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\n总计: {passed}/{total} 个模型测试通过")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(130)
