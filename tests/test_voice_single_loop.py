"""测试：单一持久事件循环中的连续调用（最接近实际桌面应用）"""
import sys
sys.path.insert(0, r'd:\python_projects\weclaw')

import asyncio
import time
from src.tools.voice_output import VoiceOutputTool


async def single_speak(tool, text, index):
    """单次播放"""
    print(f"\n[{index}] 播放: {text}")
    start = time.time()
    result = await asyncio.wait_for(
        tool.execute("speak", {"text": text}),
        timeout=60.0
    )
    elapsed = (time.time() - start) * 1000
    print(f"    结果: {result.status}, 耗时: {elapsed:.0f}ms")
    return elapsed


async def main():
    """在同一个事件循环中模拟多次独立的用户请求"""
    print("="*60)
    print("测试：单一持久事件循环（模拟真实桌面应用）")
    print("="*60)
    
    # 工具实例（模拟 registry 中的缓存实例）
    tool = VoiceOutputTool()
    
    # 模拟用户的多次请求（每次请求之间有间隔）
    requests = [
        "笑嘻嘻",
        "望天门山",
        "你好",
    ]
    
    for i, text in enumerate(requests, 1):
        print(f"\n--- 模拟第 {i} 次用户请求 ---")
        elapsed = await single_speak(tool, text, i)
        
        if elapsed < 800:  # 如果耗时太短，可能没有实际播放
            print(f"    ⚠️ 警告：耗时过短，可能未播放！")
        
        # 模拟用户对话间隔（实际应用中用户需要时间输入）
        if i < len(requests):
            print("    等待 3 秒模拟用户输入间隔...")
            await asyncio.sleep(3)
    
    print("\n" + "="*60)
    print("如果三次都能听到声音且耗时相近（约1500ms），则修复成功")
    print("如果后续播放耗时很短（<500ms）且无声，问题仍存在")
    print("="*60)


if __name__ == "__main__":
    # 关键：使用单一事件循环运行全部测试
    # 这更接近实际桌面应用的运行方式
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
