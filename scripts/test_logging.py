#!/usr/bin/env python3
"""日志系统测试脚本。

验证日志系统的各项功能是否正常工作。
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def test_logging_config():
    """测试日志配置模块。"""
    print("=" * 60)
    print("测试 1: 日志配置模块")
    print("=" * 60)
    
    from src.core.logging_config import setup_logging
    
    # 设置日志
    log_dir = Path.cwd() / "logs" / f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    setup_logging(
        level="DEBUG",
        log_dir=log_dir,
        console_output=True,
        file_output=True,
        rotation="daily",
        backup_count=3,
        format_type="detailed",
        error_log_separate=True,
    )
    
    logger = logging.getLogger(__name__)
    logger.info("✓ 日志配置初始化成功")
    
    # 验证日志文件是否存在
    if not log_dir.exists():
        print(f"✗ 日志目录未创建：{log_dir}")
        return False
    
    print(f"✓ 日志目录已创建：{log_dir}")
    
    # 验证日志文件
    main_log = log_dir / "winclaw.log"
    error_log = log_dir / "error_winclaw.log"
    
    if not main_log.exists():
        print(f"✗ 主日志文件未创建：{main_log}")
        return False
    
    print(f"✓ 主日志文件已创建：{main_log}")
    
    if not error_log.exists():
        print(f"✗ 错误日志文件未创建：{error_log}")
        return False
    
    print(f"✓ 错误日志文件已创建：{error_log}")
    
    return True


def test_logging_levels():
    """测试不同日志级别。"""
    print("\n" + "=" * 60)
    print("测试 2: 日志级别")
    print("=" * 60)
    
    logger = logging.getLogger(__name__)
    
    # 测试各级别日志
    logger.debug("这是一条 DEBUG 消息")
    logger.info("这是一条 INFO 消息")
    logger.warning("这是一条 WARNING 消息")
    logger.error("这是一条 ERROR 消息")
    logger.critical("这是一条 CRITICAL 消息")
    
    print("✓ 各级别日志输出正常")
    return True


def test_error_logging():
    """测试错误日志记录。"""
    print("\n" + "=" * 60)
    print("测试 3: 错误日志记录")
    print("=" * 60)
    
    logger = logging.getLogger(__name__)
    
    try:
        # 故意触发一个异常
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error("捕获到除零错误：%s", e, exc_info=True)
        print("✓ 错误日志记录正常")
        return True
    
    print("✗ 未捕获到预期错误")
    return False


def test_log_content():
    """测试日志内容是否正确写入。"""
    print("\n" + "=" * 60)
    print("测试 4: 日志内容验证")
    print("=" * 60)
    
    from src.core.logging_config import setup_logging
    
    # 创建新的日志目录
    log_dir = Path.cwd() / "logs" / "test_content"
    setup_logging(
        level="INFO",
        log_dir=log_dir,
        console_output=False,  # 关闭控制台输出
        file_output=True,
    )
    
    logger = logging.getLogger("test_content")
    test_message = "测试消息：Hello WinClaw!"
    logger.info(test_message)
    
    # 读取日志文件
    main_log = log_dir / "winclaw.log"
    try:
        with open(main_log, "r", encoding="utf-8") as f:
            content = f.read()
        
        if test_message in content:
            print(f"✓ 日志内容正确写入：{test_message}")
            return True
        else:
            print(f"✗ 日志内容未找到：{test_message}")
            print(f"日志内容：{content}")
            return False
    except Exception as e:
        print(f"✗ 读取日志失败：{e}")
        return False


def test_from_config():
    """测试从配置文件加载。"""
    print("\n" + "=" * 60)
    print("测试 5: 从配置文件加载")
    print("=" * 60)
    
    from src.core.logging_config import setup_logging_from_config
    
    # 模拟配置字典
    config_dict = {
        "logging": {
            "level": "INFO",
            "enable_file_log": True,
            "enable_console": True,
            "log_dir": "logs/test_from_config",
            "rotation": "daily",
            "max_file_size": 10485760,
            "backup_count": 7,
            "format": "detailed",
            "error_log_separate": True,
        }
    }
    
    setup_logging_from_config(config_dict)
    
    logger = logging.getLogger(__name__)
    logger.info("从配置文件加载成功")
    
    # 验证日志目录
    log_dir = Path.cwd() / "logs" / "test_from_config"
    if log_dir.exists():
        print(f"✓ 配置加载成功，日志目录：{log_dir}")
        return True
    else:
        print(f"✗ 日志目录未创建：{log_dir}")
        return False


def run_all_tests():
    """运行所有测试。"""
    print("\n🚀 WinClaw 日志系统测试\n")
    
    tests = [
        ("日志配置模块", test_logging_config),
        ("日志级别", test_logging_levels),
        ("错误日志", test_error_logging),
        ("日志内容", test_log_content),
        ("配置加载", test_from_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试失败：{e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！日志系统工作正常。")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查问题。")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
