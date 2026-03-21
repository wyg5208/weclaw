import sys
sys.path.insert(0, r'd:\python_projects\weclaw')

"""
测试 voice_output 工具的连续播放问题
诊断 pyttsx3 在 Windows 上的引擎状态问题
"""
import asyncio
import time
import pyttsx3


def test_direct_pyttsx3_reuse_engine():
    """测试1：复用同一个引擎实例（预期失败）"""
    print("\n" + "="*60)
    print("测试1：复用同一个引擎实例")
    print("="*60)
    
    engine = pyttsx3.init()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        engine.say(text)
        engine.runAndWait()
        elapsed = (time.time() - start) * 1000
        print(f"    耗时: {elapsed:.0f}ms")
    
    engine.stop()
    print("\n结论：如果后续播放耗时极短且无声音，说明引擎状态有问题")


def test_direct_pyttsx3_stop_before_speak():
    """测试2：每次播放前调用 stop()（之前的修复方案）"""
    print("\n" + "="*60)
    print("测试2：每次播放前调用 stop()")
    print("="*60)
    
    engine = pyttsx3.init()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        try:
            engine.stop()
        except:
            pass
        engine.say(text)
        engine.runAndWait()
        elapsed = (time.time() - start) * 1000
        print(f"    耗时: {elapsed:.0f}ms")
    
    engine.stop()
    print("\n结论：如果问题依旧，说明 stop() 不能解决状态残留")


def test_direct_pyttsx3_new_engine_each_time():
    """测试3：每次都创建新引擎实例（当前修复方案）"""
    print("\n" + "="*60)
    print("测试3：每次都创建新引擎实例")
    print("="*60)
    
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        engine = pyttsx3.init()  # 每次创建新实例
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except:
            pass
        elapsed = (time.time() - start) * 1000
        print(f"    耗时: {elapsed:.0f}ms")
    
    print("\n结论：如果问题依旧，可能是 pyttsx3.init() 内部有全局状态")


def test_direct_pyttsx3_new_engine_with_del():
    """测试4：每次创建新引擎并显式删除"""
    print("\n" + "="*60)
    print("测试4：每次创建新引擎并显式删除（del）")
    print("="*60)
    
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except:
            pass
        del engine  # 显式删除
        elapsed = (time.time() - start) * 1000
        print(f"    耗时: {elapsed:.0f}ms")
    
    print("\n结论：如果有效，说明需要显式释放引擎")


def test_direct_pyttsx3_endloop():
    """测试5：使用 endLoop() 替代依赖 runAndWait 的自动结束"""
    print("\n" + "="*60)
    print("测试5：每次使用新引擎 + 确保事件循环结束")
    print("="*60)
    
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        
        # 使用 driverName 参数强制创建全新实例
        engine = pyttsx3.init(driverName='sapi5')
        engine.say(text)
        engine.runAndWait()
        
        # 尝试多种清理方式
        try:
            engine.stop()
        except:
            pass
        
        del engine
        elapsed = (time.time() - start) * 1000
        print(f"    耗时: {elapsed:.0f}ms")
    
    print("\n结论：显式指定驱动可能有帮助")


async def test_voice_output_tool():
    """测试6：测试实际的 VoiceOutputTool"""
    print("\n" + "="*60)
    print("测试6：测试实际的 VoiceOutputTool")
    print("="*60)
    
    from src.tools.voice_output import VoiceOutputTool
    
    tool = VoiceOutputTool()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        result = await tool.execute("speak", {"text": text})
        elapsed = (time.time() - start) * 1000
        print(f"    结果: {result.status}, 输出: {result.output}")
        print(f"    耗时: {elapsed:.0f}ms")
    
    print("\n结论：检查工具类的实际行为")


def main():
    print("=" * 60)
    print("pyttsx3 Windows SAPI5 连续播放问题诊断")
    print("=" * 60)
    
    # 运行直接测试
    # test_direct_pyttsx3_reuse_engine()
    # input("\n按 Enter 继续下一个测试...")
    
    # test_direct_pyttsx3_stop_before_speak()
    # input("\n按 Enter 继续下一个测试...")
    
    test_direct_pyttsx3_new_engine_each_time()
    input("\n按 Enter 继续下一个测试...")
    
    test_direct_pyttsx3_new_engine_with_del()
    input("\n按 Enter 继续下一个测试...")
    
    test_direct_pyttsx3_endloop()
    input("\n按 Enter 继续下一个测试...")
    
    # 测试实际工具
    print("\n运行 VoiceOutputTool 测试...")
    asyncio.run(test_voice_output_tool())
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
