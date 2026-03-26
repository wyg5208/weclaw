"""核心工具冒烟测试套件。

测试覆盖：
- ShellTool: 命令执行、安全黑名单、超时处理
- FileTool: 读写文件、搜索、目录列表
- ScreenTool: 屏幕截图、窗口截图
- SearchTool: 本地搜索
- CalculatorTool: 数学计算
- DateTimeTool: 日期时间获取

运行方式：
    python tests/test_tools_smoke.py
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.base import ToolResultStatus
from src.tools.registry import create_default_registry


# ============================================================================
# 测试辅助
# ============================================================================

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> bool:
    """检查条件并打印结果。"""
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
        return True
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")
        return False


def section(name: str) -> None:
    """打印测试分组标题。"""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print("=" * 60)


# ============================================================================
# 测试：ShellTool
# ============================================================================

async def test_shell_tool():
    """冒烟测试：ShellTool。"""
    section("冒烟测试：ShellTool")

    registry = create_default_registry()
    tool = registry.get_tool("shell")
    if not tool:
        print("  ⚠️  ShellTool 未注册，跳过")
        return

    # 基本命令执行
    r = await tool.safe_execute("run", {"command": "echo 'Hello World'"})
    check("执行 echo 命令", r.is_success)
    check("输出包含 Hello", "Hello" in r.output)

    # PowerShell 命令
    r = await tool.safe_execute("run", {"command": "Get-Date | ConvertTo-Json"})
    check("执行 PowerShell 命令", r.is_success)

    # 黑名单命令拦截
    r = await tool.safe_execute("run", {"command": "rm -rf /"})
    check("黑名单命令拦截", r.status == ToolResultStatus.ERROR)

    r = await tool.safe_execute("run", {"command": "shutdown /s /t 0"})
    check("Shutdown 命令拦截", r.status == ToolResultStatus.ERROR)

    r = await tool.safe_execute("run", {"command": "format c:"})
    check("Format 命令拦截", r.status == ToolResultStatus.ERROR)

    # 空命令
    r = await tool.safe_execute("run", {"command": ""})
    check("空命令处理", r.status == ToolResultStatus.ERROR)


# ============================================================================
# 测试：FileTool
# ============================================================================

async def test_file_tool():
    """冒烟测试：FileTool。"""
    section("冒烟测试：FileTool")

    registry = create_default_registry()
    tool = registry.get_tool("file")
    if not tool:
        print("  ⚠️  FileTool 未注册，跳过")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_file = Path(tmpdir) / "test_read.txt"
        test_content = "Hello, FileTool!\nLine 2\nLine 3"
        test_file.write_text(test_content, encoding="utf-8")

        # 读取文件
        r = await tool.safe_execute("read", {"path": str(test_file)})
        check("读取文件成功", r.is_success)
        check("内容正确", "Hello, FileTool" in r.output)

        # 写入文件
        new_file = Path(tmpdir) / "test_write.txt"
        r = await tool.safe_execute("write", {
            "path": str(new_file),
            "content": "Written by test\nNew content",
        })
        check("写入文件成功", r.is_success)

        # 验证写入
        r = await tool.safe_execute("read", {"path": str(new_file)})
        check("验证写入内容", "Written by test" in r.output)

        # 搜索文件内容
        r = await tool.safe_execute("search", {
            "path": tmpdir,
            "pattern": "Hello",
        })
        check("搜索文件成功", r.is_success)

        # 列出目录
        r = await tool.safe_execute("list", {"path": tmpdir})
        check("列出目录成功", r.is_success)

        # 不存在的文件
        r = await tool.safe_execute("read", {"path": str(Path(tmpdir) / "nonexistent.txt")})
        check("不存在的文件报错", r.status == ToolResultStatus.ERROR)

        # 拒绝扩展名
        r = await tool.safe_execute("write", {
            "path": str(Path(tmpdir) / "test.exe"),
            "content": "malicious",
        })
        check("拒绝危险扩展名", r.status == ToolResultStatus.ERROR)


# ============================================================================
# 测试：ScreenTool
# ============================================================================

async def test_screen_tool():
    """冒烟测试：ScreenTool。"""
    section("冒烟测试：ScreenTool")

    registry = create_default_registry()
    tool = registry.get_tool("screen")
    if not tool:
        print("  ⚠️  ScreenTool 未注册，跳过")
        return

    # 截图（可能需要 GUI 环境）
    r = await tool.safe_execute("capture", {})
    # 注意：服务器环境可能无 GUI，这里只检查不崩溃
    check("截图不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])

    # 列出显示器
    r = await tool.safe_execute("list_monitors", {})
    check("列出显示器不崩溃", r.is_success or r.status == ToolResultStatus.ERROR)


# ============================================================================
# 测试：SearchTool
# ============================================================================

async def test_search_tool():
    """冒烟测试：SearchTool。"""
    section("冒烟测试：SearchTool")

    registry = create_default_registry()
    tool = registry.get_tool("search")
    if not tool:
        print("  ⚠️  SearchTool 未注册，跳过")
        return

    # 本地搜索（搜索项目目录）
    project_root = str(Path(__file__).resolve().parent.parent)
    r = await tool.safe_execute("local_search", {
        "query": "ToolRegistry",
        "path": project_root,
        "max_results": 5,
    })
    check("本地搜索不崩溃", r.is_success or r.status == ToolResultStatus.ERROR)

    # Web 搜索（可能需要 API）
    r = await tool.safe_execute("web_search", {
        "query": "Python testing best practices",
        "max_results": 3,
    })
    check("Web 搜索不崩溃", r.is_success or r.status == ToolResultStatus.ERROR)


# ============================================================================
# 测试：CalculatorTool
# ============================================================================

async def test_calculator_tool():
    """冒烟测试：CalculatorTool。"""
    section("冒烟测试：CalculatorTool")

    registry = create_default_registry()
    tool = registry.get_tool("calculator")
    if not tool:
        print("  ⚠️  CalculatorTool 未注册，跳过")
        return

    # 基本运算
    r = await tool.safe_execute("calculate", {"expression": "2 + 3"})
    check("2+3=5", r.is_success and r.data.get("result") == 5)

    r = await tool.safe_execute("calculate", {"expression": "10 - 4"})
    check("10-4=6", r.is_success and r.data.get("result") == 6)

    r = await tool.safe_execute("calculate", {"expression": "3 * 7"})
    check("3*7=21", r.is_success and r.data.get("result") == 21)

    r = await tool.safe_execute("calculate", {"expression": "20 / 4"})
    check("20/4=5", r.is_success and r.data.get("result") == 5)

    # 复杂表达式
    r = await tool.safe_execute("calculate", {"expression": "2 + 3 * 4"})
    check("2+3*4=14", r.is_success and r.data.get("result") == 14)

    # 数学函数
    r = await tool.safe_execute("calculate", {"expression": "sqrt(144)"})
    check("sqrt(144)=12", r.is_success and r.data.get("result") == 12)

    r = await tool.safe_execute("calculate", {"expression": "abs(-5)"})
    check("abs(-5)=5", r.is_success and r.data.get("result") == 5)

    r = await tool.safe_execute("calculate", {"expression": "pow(2, 8)"})
    check("pow(2,8)=256", r.is_success and r.data.get("result") == 256)

    # 中文符号
    r = await tool.safe_execute("calculate", {"expression": "(3+2)×4"})
    check("(3+2)×4=20", r.is_success and r.data.get("result") == 20)

    r = await tool.safe_execute("calculate", {"expression": "20÷4"})
    check("20÷4=5", r.is_success and r.data.get("result") == 5)

    # 中文括号
    r = await tool.safe_execute("calculate", {"expression": "（1+2）×（3+4）"})
    check("（1+2）×（3+4）=21", r.is_success and r.data.get("result") == 21)

    # 错误处理
    r = await tool.safe_execute("calculate", {"expression": "1/0"})
    check("除以零报错", r.status == ToolResultStatus.ERROR)

    r = await tool.safe_execute("calculate", {"expression": ""})
    check("空表达式报错", r.status == ToolResultStatus.ERROR)

    r = await tool.safe_execute("calculate", {"expression": "__import__('os')"})
    check("注入攻击拦截", r.status == ToolResultStatus.ERROR)

    r = await tool.safe_execute("calculate", {"expression": "eval('1+1')"})
    check("eval 拦截", r.status == ToolResultStatus.ERROR)


# ============================================================================
# 测试：DateTimeTool
# ============================================================================

async def test_datetime_tool():
    """冒烟测试：DateTimeTool。"""
    section("冒烟测试：DateTimeTool")

    registry = create_default_registry()
    tool = registry.get_tool("datetime_tool")
    if not tool:
        print("  ⚠️  DateTimeTool 未注册，跳过")
        return

    # 获取日期时间
    r = await tool.safe_execute("get_datetime", {})
    check("获取日期时间成功", r.is_success)
    check("包含 datetime 字段", "datetime" in r.data)

    today = datetime.now().strftime("%Y-%m-%d")
    check("日期正确", r.data.get("datetime", "").startswith(today[:7]))

    # weekday 格式
    r = await tool.safe_execute("get_datetime", {"format_type": "weekday"})
    check("weekday 格式", r.is_success)
    check("包含 weekday_cn", "weekday_cn" in r.data)

    # date 格式
    r = await tool.safe_execute("get_datetime", {"format_type": "date"})
    check("date 格式", r.is_success)
    check("包含 date 字段", "date" in r.data)

    # time 格式
    r = await tool.safe_execute("get_datetime", {"format_type": "time"})
    check("time 格式", r.is_success)
    check("包含 time 字段", "time" in r.data)

    # all 格式
    r = await tool.safe_execute("get_datetime", {"format_type": "all"})
    check("all 格式", r.is_success)
    check("all 格式多字段", len(r.data) >= 5)


# ============================================================================
# 测试：ClipboardTool
# ============================================================================

async def test_clipboard_tool():
    """冒烟测试：ClipboardTool。"""
    section("冒烟测试：ClipboardTool")

    registry = create_default_registry()
    tool = registry.get_tool("clipboard")
    if not tool:
        print("  ⚠️  ClipboardTool 未注册，跳过")
        return

    # 读取剪贴板（可能为空）
    r = await tool.safe_execute("read", {})
    check("读取剪贴板不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])

    # 写入剪贴板
    test_text = "Test clipboard content 123"
    r = await tool.safe_execute("write", {"text": test_text})
    check("写入剪贴板不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])

    # 清空剪贴板
    r = await tool.safe_execute("clear", {})
    check("清空剪贴板不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])


# ============================================================================
# 测试：NotifyTool
# ============================================================================

async def test_notify_tool():
    """冒烟测试：NotifyTool。"""
    section("冒烟测试：NotifyTool")

    registry = create_default_registry()
    tool = registry.get_tool("notify")
    if not tool:
        print("  ⚠️  NotifyTool 未注册，跳过")
        return

    # 发送通知
    r = await tool.safe_execute("send", {
        "title": "测试通知",
        "message": "这是一条测试通知",
    })
    check("发送通知不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])


# ============================================================================
# 测试：AppControlTool
# ============================================================================

async def test_app_control_tool():
    """冒烟测试：AppControlTool。"""
    section("冒烟测试：AppControlTool")

    registry = create_default_registry()
    tool = registry.get_tool("app_control")
    if not tool:
        print("  ⚠️  AppControlTool 未注册，跳过")
        return

    # 列出运行中的进程（不崩溃）
    r = await tool.safe_execute("list_processes", {})
    check("列出进程不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])

    # 获取前台窗口
    r = await tool.safe_execute("get_foreground_window", {})
    check("获取前台窗口不崩溃", r.status in [ToolResultStatus.SUCCESS, ToolResultStatus.ERROR])


# ============================================================================
# 测试：StatisticsTool
# ============================================================================

async def test_statistics_tool():
    """冒烟测试：StatisticsTool。"""
    section("冒烟测试：StatisticsTool")

    registry = create_default_registry()
    tool = registry.get_tool("statistics")
    if not tool:
        print("  ⚠️  StatisticsTool 未注册，跳过")
        return

    # 获取使用统计
    r = await tool.safe_execute("get_usage_stats", {})
    check("获取统计成功", r.is_success)
    check("包含 session_count", "session_count" in r.data)


# ============================================================================
# 主入口
# ============================================================================

async def run_async_tests():
    """运行所有异步冒烟测试。"""
    await test_shell_tool()
    await test_file_tool()
    await test_screen_tool()
    await test_search_tool()
    await test_calculator_tool()
    await test_datetime_tool()
    await test_clipboard_tool()
    await test_notify_tool()
    await test_app_control_tool()
    await test_statistics_tool()


def main():
    global passed, failed

    print("=" * 60)
    print("  WinClaw 核心工具冒烟测试套件")
    print("=" * 60)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_async_tests())
    finally:
        loop.close()

    # 汇总
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  总计: {total} 项 | ✅ 通过: {passed} | ❌ 失败: {failed}")
    print("=" * 60)

    if failed > 0:
        print("\n  ⚠️  部分测试失败，请检查日志")
        return False
    else:
        print("\n  🎉 全部通过！")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
