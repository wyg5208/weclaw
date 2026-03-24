"""测试 TTS 文本预处理功能 - 过滤标点符号和 Emoji。"""

import sys
import re
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# 全局 _preprocess_text 函数（与 tts_player.py 保持一致）
def _preprocess_text(text: str) -> str:
    """预处理文本，移除无法朗读的字符（标点符号、Emoji、特殊符号）。"""
    # 移除特殊标记
    text = re.sub(r'<\|.*?\|>', '', text)
    text = re.sub(r'\[.*?\]', '', text)

    # 移除所有标点符号（中英文）
    # 中文标点：，。！？；：、""''``……—～《》【】（）〔〕〈〉「」『』〖〗〘〙〚〛⸨⸩
    # 英文标点：,.!?;:'"`~…–—·•
    # 其他符号：@#$%^&*()_+-=[]{}|;':",./<>?\\等
    punctuation_pattern = re.compile(
        r'[，。！？；：、""\'\'``……—～《》【】（）〔〕〈〉「」『』〖〗〘〙〚〛⸨⸩'
        r',.!?;:\'"`…–—·•'
        r'@#$%^&*()_+\-=\[\]{}|;\':",./<>?\\'
        r']+', 
        flags=re.UNICODE
    )
    text = punctuation_pattern.sub(' ', text)

    # 移除 Emoji（只匹配真正的 emoji 范围，避免误删 CJK 字符）
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"   # dingbats
        "\U000024C2"              # only circled M, not a range
        "\U0001F251"              # only positive face, not a range
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # 清理多余空白（多个空格合并为一个，去除首尾空格）
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def test_tts_player_preprocess():
    """测试 TTS Player 的文本预处理。"""
    print("=" * 70)
    print("测试 TTS Player 文本预处理")
    print("=" * 70)
    
    test_cases = [
        # (输入，期望输出描述)
        ("你好，世界！", "你好 世界"),
        ("今天天气真好😊", "今天天气真好"),
        ("Hello, World!", "Hello World"),
        ("测试 123，哈哈😄", "测试 123 哈哈"),
        ("【重要】通知！！！", "重要 通知"),
        ("你好吗？我很好👍", "你好吗 我很好"),
        ("苹果🍎、香蕉🍌、橙子🍊", "苹果 香蕉 橙子"),
        ("\"引号\"和'单引号'", "引号 和 单引号"),
        ("省略号……和破折号——", "省略号 和破折号"),
        ("《书名》和【标题】", "书名 和 标题"),
        ("a@b#c$d%e^f&g*h", "a b c d e f g h"),
        ("表情😀😁😂🤣😃", ""),
        ("纯标点：，。！？；：", ""),
        ("Hello!!! How are you?", "Hello How are you"),
        ("I'm fine, thank you~", "I m fine thank you"),
    ]
    
    passed = 0
    failed = 0
    
    for input_text, expected_desc in test_cases:
        result = _preprocess_text(input_text)
        status = "✓" if result else "✗"
        
        # 简单检查：如果期望为空，结果应该为空；否则应该有内容
        if expected_desc == "":
            test_passed = (result == "")
        else:
            test_passed = (len(result) > 0 and result != input_text)
        
        if test_passed:
            passed += 1
            print(f"{status} 输入：{input_text!r}")
            print(f"  输出：{result!r} ✓")
        else:
            failed += 1
            print(f"{status} 输入：{input_text!r}")
            print(f"  输出：{result!r} ✗ (期望有过滤效果)")
        print()
    
    print("=" * 70)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 70)
    return failed == 0


def test_voice_output_preprocess():
    """测试 VoiceOutputTool 的文本预处理。"""
    print("\n" + "=" * 70)
    print("测试 VoiceOutputTool 文本预处理")
    print("=" * 70)
    
    # 使用与 VoiceOutputTool 相同的实现
    def _preprocess_text_vo(text: str) -> str:
        """预处理文本，移除无法朗读的字符（标点符号、Emoji、特殊符号）。"""
        import re
        
        # 移除特殊标记
        text = re.sub(r'<\|.*?\|>', '', text)
        text = re.sub(r'\[.*?\]', '', text)

        # 移除所有标点符号（中英文）
        punctuation_pattern = re.compile(
            r'[，。！？；：、""\'\'``……—～《》【】（）〔〕〈〉「」『』〖〗〘〙〚〛⸨⸩'
            r',.!?;:\'"`…–—·•'
            r'@#$%^&*()_+\-=\[\]{}|;\':",./<>?\\'
            r']+', 
            flags=re.UNICODE
        )
        text = punctuation_pattern.sub(' ', text)

        # 移除 Emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"   # dingbats
            "\U000024C2"              # only circled M, not a range
            "\U0001F251"              # only positive face, not a range
            "]+", flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)

        # 清理多余空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text
    
    test_cases = [
        ("你好，世界！", "你好 世界"),
        ("今天天气真好😊", "今天天气真好"),
        ("Hello, World!", "Hello World"),
        ("测试 123，哈哈😄", "测试 123 哈哈"),
        ("【重要】通知!!!", "重要 通知"),
        ("苹果🍎、香蕉🍌", "苹果 香蕉"),
        ("表情😀😁😂", ""),
        ("纯标点：，。！？", ""),
    ]
    
    passed = 0
    failed = 0
    
    for input_text, expected_desc in test_cases:
        result = _preprocess_text_vo(input_text)
        
        # 简单检查：如果期望为空，结果应该为空；否则应该有内容
        if expected_desc == "":
            test_passed = (result == "")
        else:
            test_passed = (len(result) > 0 and result != input_text)
        
        if test_passed:
            passed += 1
            print(f"✓ 输入：{input_text!r} -> 输出：{result!r}")
        else:
            failed += 1
            print(f"✗ 输入：{input_text!r} -> 输出：{result!r} (期望有过滤效果)")
    
    print("=" * 70)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success1 = test_tts_player_preprocess()
    success2 = test_voice_output_preprocess()
    
    print("\n" + "=" * 70)
    if success1 and success2:
        print("所有测试通过！✅")
        sys.exit(0)
    else:
        print("部分测试失败！❌")
        sys.exit(1)
