"""快速验证 VoiceOutputTool 修复 - 模拟实际应用环境"""
import sys
sys.path.insert(0, r'd:\python_projects\weclaw')

import asyncio
import time
from src.tools.voice_output import VoiceOutputTool


async def test_direct():
    """测试1：直接调用（测试脚本方式）"""
    print("\n" + "="*60)
    print("测试1：直接调用 execute（测试脚本方式）")
    print("="*60)
    
    tool = VoiceOutputTool()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        result = await tool.execute("speak", {"text": text})
        elapsed = (time.time() - start) * 1000
        print(f"    结果: {result.status}, 耗时: {elapsed:.0f}ms")


async def test_with_wait_for():
    """测试2：通过 asyncio.wait_for 调用（模拟 safe_execute）"""
    print("\n" + "="*60)
    print("测试2：通过 asyncio.wait_for 调用（模拟 safe_execute）")
    print("="*60)
    
    tool = VoiceOutputTool()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        # 模拟 safe_execute 中的 wait_for 包装
        result = await asyncio.wait_for(
            tool.execute("speak", {"text": text}),
            timeout=60.0
        )
        elapsed = (time.time() - start) * 1000
        print(f"    结果: {result.status}, 耗时: {elapsed:.0f}ms")


async def test_persistent_loop():
    """测试3：模拟持久事件循环（桌面应用实际场景）"""
    print("\n" + "="*60)
    print("测试3：持久事件循环 + 间隔调用（模拟桌面应用）")
    print("="*60)
    
    tool = VoiceOutputTool()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        result = await asyncio.wait_for(
            tool.execute("speak", {"text": text}),
            timeout=60.0
        )
        elapsed = (time.time() - start) * 1000
        print(f"    结果: {result.status}, 耗时: {elapsed:.0f}ms")
        
        # 模拟用户对话间隔
        print("    等待 2 秒模拟用户对话间隔...")
        await asyncio.sleep(2)


async def test_new_tool_each_time():
    """测试4：每次创建新工具实例"""
    print("\n" + "="*60)
    print("测试4：每次创建新工具实例")
    print("="*60)
    
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        tool = VoiceOutputTool()  # 每次创建新实例
        start = time.time()
        result = await asyncio.wait_for(
            tool.execute("speak", {"text": text}),
            timeout=60.0
        )
        elapsed = (time.time() - start) * 1000
        print(f"    结果: {result.status}, 耗时: {elapsed:.0f}ms")
        del tool  # 显式删除
        
        await asyncio.sleep(2)


def main():
    print("="*60)
    print("VoiceOutputTool 多场景测试")
    print("="*60)
    
    # 测试1
    asyncio.run(test_direct())
    input("\n按 Enter 继续...")
    
    # 测试2
    asyncio.run(test_with_wait_for())
    input("\n按 Enter 继续...")
    
    # 测试3 - 最接近实际应用
    print("\n*** 测试3 最接近实际桌面应用场景 ***")
    asyncio.run(test_persistent_loop())
    input("\n按 Enter 继续...")
    
    # 测试4
    asyncio.run(test_new_tool_each_time())
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
