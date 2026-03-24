"""独立测试噪音过滤功能（无需 PySide6）。"""

import re
from typing import ClassVar


class NoiseFilterConfig:
    """噪音过滤配置（独立副本，用于测试）。"""
    
    # 纯符号模式（只包含标点符号、空格、特殊字符）
    PURE_SYMBOL_PATTERN = re.compile(r'^[\s\.,;:!\?，。；：！？、\-_\(\)\[\]（）“”"\'\'…~`@#$%^&*+=|\\<>\/]+$')
    
    # 单字语气词（常见无意义语气词）
    SINGLE_FILLERS: ClassVar[set] = {
        # 中文语气词
        '嗯', '啊', '哦', '呃', '哈', '额', '唉', '哎', '噢', '咦',
        '唔', '唔', '哼', '嘿', '哇', '耶', '咯', '啦', '嘞', '哒',
        # 英文语气词
        'uh', 'oh', 'ah', 'um', 'hm', 'eh', 'ha', 'mm', 'hmm',
        # 常见杂音识别结果
        '。', '，', '、', '...', '。。', '。。。',
    }
    
    # 双字语气词组合
    DOUBLE_FILLERS: ClassVar[set] = {
        '嗯嗯', '啊啊', '哦哦', '呃呃', '哈哈', '嘿嘿', '嗯啊', '啊嗯',
        '哦啊', '嗯哦', '好的', '好的', '那个', '这个', '就是',
        '然后', '所以', '因为', '但是', '不过', '其实',
    }
    
    # 最小有效输入长度（中文按字，英文按词）
    MIN_EFFECTIVE_LENGTH = 2
    
    # 无意义短语模式（语音识别常见的错误输出）
    MEANINGLESS_PHRASES: ClassVar[list] = [
        # 通用废话模式（注意：不包含“好”、“是”、“对”、“行”等有意义短词）
        r'^(好的|可以|嗯|哦)[，。！？,.!?]*$',
        r'^(我在这里|需要什么帮助|请告诉我)[，。！？,.!?]*$',
        # 纯数字
        r'^\d+[.,，。]*$',
        # 纯标点
        r'^[\s\.,;:!\?，。；：！？、\-_]+$'
    ]
    
    @classmethod
    def is_noise(cls, text: str) -> bool:
        """检查文本是否为噪音/无意义输入。"""
        if not text:
            return True
            
        # 1. 去除首尾空白
        text = text.strip()
        if not text:
            return True
            
        # 2. 检查纯符号
        if cls.PURE_SYMBOL_PATTERN.match(text):
            return True
            
        # 3. 检查单字语气词
        if text in cls.SINGLE_FILLERS:
            return True
            
        # 4. 检查双字语气词
        if text in cls.DOUBLE_FILLERS:
            return True
            
        # 5. 检查无意义短语模式
        for pattern in cls.MEANINGLESS_PHRASES:
            if re.match(pattern, text, re.IGNORECASE):
                return True
                
        # 6. 检查过短输入（但排除一些有意义的短词）
        meaningful_shorts = {'是', '好', '行', '对', '不', '否', '来', '去', '吃', '喝', '睡',
                            'ok', 'yes', 'no', 'go', 'hi', 'hey'}
        if len(text) < cls.MIN_EFFECTIVE_LENGTH and text.lower() not in meaningful_shorts:
            return True
            
        return False


def test_noise_filter():
    """测试噪音过滤功能。"""
    test_cases = [
        # (输入, 期望结果, 描述)
        ('', True, '空字符串'),
        ('...', True, '纯符号...'),
        ('。。。', True, '中文句号'),
        ('嗯', True, '单字语气词-嗯'),
        ('啊', True, '单字语气词-啊'),
        ('哦', True, '单字语气词-哦'),
        ('呃', True, '单字语气词-呃'),
        ('嗯嗯', True, '双字语气词-嗯嗯'),
        ('哈哈', True, '双字语气词-哈哈'),
        ('好的。', True, '无意义短语-好的'),
        ('好的！我在这里。需要什么帮助请告诉我！', False, '有效句子'),
        ('今天天气怎么样', False, '有效问题'),
        ('请帮我写一首诗', False, '有效请求'),
        ('你好', False, '有效问候'),
        ('是', False, '有意义短词-是'),
        ('好', False, '有意义短词-好'),
        ('OK', False, '有意义短词-OK'),
        ('123', True, '纯数字'),
        ('。。。。。', True, '多个句号'),
        ('我今天想吃苹果', False, '有效陈述'),
        ('      ', True, '纯空格'),
        ('、', True, '单个顿号'),
        ('，，，', True, '多个逗号'),
        ('哈', True, '单字哈'),
        ('嘿嘿', True, '双字嘿嘿'),
    ]

    print('=' * 60)
    print('噪音过滤测试结果')
    print('=' * 60)

    passed = 0
    failed = 0
    failures = []

    for text, expected_is_noise, desc in test_cases:
        actual = NoiseFilterConfig.is_noise(text)
        status = '✓' if actual == expected_is_noise else '✗'
        if actual == expected_is_noise:
            passed += 1
        else:
            failed += 1
            failures.append((text, expected_is_noise, actual, desc))
        print(f'{status} {desc}: "{text}" -> 噪音={actual} (期望={expected_is_noise})')

    print('=' * 60)
    print(f'测试结果: {passed} 通过, {failed} 失败')
    
    if failures:
        print('\n失败的测试用例:')
        for text, expected, actual, desc in failures:
            print(f'  - {desc}: "{text}" -> 期望={expected}, 实际={actual}')
    
    print('=' * 60)

    return failed == 0


if __name__ == '__main__':
    import sys
    success = test_noise_filter()
    sys.exit(0 if success else 1)
