"""测试：在 qasync 环境下的语音播放（完全模拟桌面应用）"""
import sys
sys.path.insert(0, r'd:\python_projects\weclaw')

import asyncio
import time

# 必须在 Qt 之前导入
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from src.tools.voice_output import VoiceOutputTool


async def test_speak():
    """测试语音播放"""
    print("="*60)
    print("qasync 环境测试（完全模拟桌面应用）")
    print("="*60)
    
    tool = VoiceOutputTool()
    texts = ["你好", "再见", "测试"]
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}] 播放: {text}")
        start = time.time()
        result = await tool.execute("speak", {"text": text})
        elapsed = (time.time() - start) * 1000
        status = "✅" if elapsed > 800 else "❌ 可能未播放"
        print(f"    结果: {result.status}, 耗时: {elapsed:.0f}ms {status}")
        
        if i < len(texts):
            print("    等待 2 秒...")
            await asyncio.sleep(2)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    # 退出应用
    QApplication.instance().quit()


def main():
    # 创建 Qt 应用
    app = QApplication(sys.argv)
    
    # 使用 qasync 事件循环（与桌面应用完全相同）
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 启动测试
    loop.create_task(test_speak())
    
    # 运行事件循环
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
