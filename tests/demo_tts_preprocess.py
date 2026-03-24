"""简单演示 TTS 文本预处理效果。"""

import re


def _preprocess_text(text: str) -> str:
    """预处理文本，移除无法朗读的字符（标点符号、Emoji、特殊符号）。"""
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


if __name__ == "__main__":
    print("=" * 70)
    print("TTS 文本预处理演示 - 朗读时将跳过标点符号和 Emoji")
    print("=" * 70)
    
    examples = [
        "你好，世界！",
        "今天天气真好😊，我们出去玩吧！",
        "Hello, World! How are you?",
        "【重要通知】明天早上 9 点开会‼️",
        "苹果🍎、香蕉🍌、橙子🍊都很好吃",
        "\"引号\"和'单引号'测试",
        "a@b#c$d%e^f&g*h 特殊符号",
    ]
    
    for original in examples:
        processed = _preprocess_text(original)
        print(f"\n原文：{original}")
        print(f"处理后：{processed}")
        print(f"长度：{len(original)} -> {len(processed)}")
    
    print("\n" + "=" * 70)
    print("✅ 处理完成！TTS 播放时会使用处理后的文本，自动跳过标点和 Emoji")
    print("=" * 70)
