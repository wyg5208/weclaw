"""测试噪音过滤功能。"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.conversation.manager import NoiseFilterConfig


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
    ]

    print('=' * 60)
    print('噪音过滤测试结果')
    print('=' * 60)

    passed = 0
    failed = 0

    for text, expected_is_noise, desc in test_cases:
        actual = NoiseFilterConfig.is_noise(text)
        status = '✓' if actual == expected_is_noise else '✗'
        if actual == expected_is_noise:
            passed += 1
        else:
            failed += 1
        print(f'{status} {desc}: "{text}" -> 噪音={actual} (期望={expected_is_noise})')

    print('=' * 60)
    print(f'测试结果: {passed} 通过, {failed} 失败')
    print('=' * 60)

    return failed == 0


if __name__ == '__main__':
    success = test_noise_filter()
    sys.exit(0 if success else 1)
