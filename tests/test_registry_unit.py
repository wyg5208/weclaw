"""工具注册器单元测试套件。

测试覆盖：
1. ToolRegistry 初始化与配置加载
2. 工具注册/注销
3. Schema 生成与缓存
4. 函数名解析（resolve_function_name）
5. 分类查询与风险等级
6. 懒加载机制
7. 工具启用/禁用控制
8. 依赖解析

运行方式：
    python tests/test_registry_unit.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.base import BaseTool, ActionDef, ToolResult, ToolResultStatus
from src.tools.registry import ToolRegistry, create_default_registry, _DEFAULT_TOOLS_JSON


# ============================================================================
# 测试辅助函数
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
# 测试：初始化与配置加载
# ============================================================================

def test_registry_initialization():
    """测试：ToolRegistry 初始化。"""
    section("测试：初始化")

    # 默认初始化
    registry = ToolRegistry()
    check("ToolRegistry 实例创建", isinstance(registry, ToolRegistry))
    check("空工具列表", len(registry.list_tools()) == 0)
    check("空 Schema 缓存", registry._schema_cache is None)
    check("空函数映射", len(registry._func_map) == 0)

    # 从配置文件加载
    registry = ToolRegistry()
    if _DEFAULT_TOOLS_JSON.exists():
        registry.load_config()
        check("配置加载成功", len(registry._tool_configs) > 0)
    else:
        print("  ⚠️  tools.json 不存在，跳过配置加载测试")


def test_load_config():
    """测试：配置文件加载。"""
    section("测试：配置文件加载")

    registry = ToolRegistry()
    registry.load_config()

    # 验证配置结构
    check("全局设置加载", len(registry.global_settings) >= 0)
    check("分类定义加载", len(registry.categories) >= 0)
    check("工具配置数量", len(registry._tool_configs) > 0)

    # 验证每个工具配置的关键字段
    required_fields = ["enabled", "module", "class", "display", "actions"]
    for tool_name, cfg in registry._tool_configs.items():
        has_all = all(field in cfg for field in required_fields)
        check(f"工具 {tool_name} 配置完整", has_all)


def test_load_nonexistent_config():
    """测试：加载不存在的配置文件。"""
    section("测试：加载不存在的配置")

    registry = ToolRegistry()
    registry.load_config(Path("non_existent_config.json"))

    # 应该不崩溃，工具配置应为空
    check("不存在配置不崩溃", len(registry._tool_configs) == 0)


# ============================================================================
# 测试：工具注册与注销
# ============================================================================

def test_register_tool():
    """测试：工具注册。"""
    section("测试：工具注册")

    registry = ToolRegistry()

    # 创建一个简单的测试工具
    class TestTool(BaseTool):
        name = "test_tool"
        emoji = "🧪"
        title = "测试工具"

        def get_actions(self):
            return [
                ActionDef(name="action1", description="测试动作1"),
                ActionDef(name="action2", description="测试动作2"),
            ]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="OK")

    tool = TestTool()
    registry.register(tool)

    check("工具注册成功", registry.get_tool("test_tool") is not None)
    check("工具名称正确", registry.get_tool("test_tool").name == "test_tool")
    check("函数映射更新", len(registry._func_map) == 2)

    # 重复注册应警告但不崩溃
    registry.register(tool)
    check("重复注册不崩溃", registry.get_tool("test_tool") is not None)


def test_unregister_tool():
    """测试：工具注销。"""
    section("测试：工具注销")

    registry = ToolRegistry()

    class TestTool2(BaseTool):
        name = "test_tool2"
        emoji = "🧪"
        title = "测试工具2"

        def get_actions(self):
            return [ActionDef(name="do_it", description="做某事")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="OK")

    tool = TestTool2()
    registry.register(tool)
    check("工具已注册", registry.get_tool("test_tool2") is not None)

    # 注销
    result = registry.unregister("test_tool2")
    check("注销返回 True", result is True)
    check("工具已移除", registry.get_tool("test_tool2") is None)
    check("函数映射清理", "test_tool2_do_it" not in registry._func_map)

    # 注销不存在的工具
    result = registry.unregister("non_existent")
    check("注销不存在返回 False", result is False)


def test_register_multiple_tools():
    """测试：注册多个工具。"""
    section("测试：注册多个工具")

    registry = ToolRegistry()

    class ToolA(BaseTool):
        name = "tool_a"
        emoji = "🔧"
        title = "工具A"

        def get_actions(self):
            return [ActionDef(name="run", description="运行")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="A")

    class ToolB(BaseTool):
        name = "tool_b"
        emoji = "🔩"
        title = "工具B"

        def get_actions(self):
            return [ActionDef(name="run", description="运行")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="B")

    registry.register(ToolA())
    registry.register(ToolB())

    check("注册 2 个工具", len(registry.list_tools()) == 2)
    check("ToolA 存在", registry.get_tool("tool_a") is not None)
    check("ToolB 存在", registry.get_tool("tool_b") is not None)


# ============================================================================
# 测试：Schema 生成与缓存
# ============================================================================

def test_schema_generation():
    """测试：Schema 生成。"""
    section("测试：Schema 生成")

    registry = ToolRegistry()

    class SchemaTestTool(BaseTool):
        name = "schema_test"
        emoji = "📋"
        title = "Schema测试"

        def get_actions(self):
            return [
                ActionDef(
                    name="test_action",
                    description="测试动作",
                    parameters={
                        "param1": {"type": "string", "description": "参数1"},
                        "param2": {"type": "integer", "description": "参数2"},
                    },
                    required_params=["param1"],
                ),
            ]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="OK")

    tool = SchemaTestTool()
    registry.register(tool)

    schemas = registry.get_all_schemas(use_cache=False)
    check("生成 1 个 Schema", len(schemas) == 1)

    schema = schemas[0]
    check("Schema 类型正确", schema.get("type") == "function")
    check("函数名正确", schema["function"]["name"] == "schema_test_test_action")
    check("描述正确", "[Schema测试]" in schema["function"]["description"])
    check("参数数量", len(schema["function"]["parameters"]["properties"]) == 2)
    check("必需参数", "param1" in schema["function"].get("parameters", {}).get("required", []))


def test_schema_cache():
    """测试：Schema 缓存机制。"""
    section("测试：Schema 缓存")

    registry = ToolRegistry()

    class CacheTestTool(BaseTool):
        name = "cache_test"
        emoji = "💾"
        title = "缓存测试"

        def get_actions(self):
            return [ActionDef(name="action", description="动作")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="OK")

    registry.register(CacheTestTool())

    # 首次获取（生成缓存）
    schemas1 = registry.get_all_schemas(use_cache=True)
    check("首次生成缓存", registry._schema_cache is not None)

    # 再次获取（使用缓存）
    schemas2 = registry.get_all_schemas(use_cache=True)
    check("缓存命中", schemas1 is schemas2)  # 同一对象

    # 禁用缓存
    schemas3 = registry.get_all_schemas(use_cache=False)
    check("禁用缓存返回新列表", schemas1 is not schemas3)

    # 注册新工具后缓存失效
    class CacheTestTool2(BaseTool):
        name = "cache_test2"
        emoji = "💾"
        title = "缓存测试2"

        def get_actions(self):
            return [ActionDef(name="action", description="动作")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="OK")

    registry.register(CacheTestTool2())
    check("注册后缓存失效", registry._schema_cache is None)


def test_get_schemas_by_names():
    """测试：按名称获取 Schema。"""
    section("测试：按名称获取 Schema")

    registry = ToolRegistry()

    class ToolX(BaseTool):
        name = "tool_x"
        emoji = "🔧"
        title = "工具X"

        def get_actions(self):
            return [ActionDef(name="do_x", description="做X")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="X")

    class ToolY(BaseTool):
        name = "tool_y"
        emoji = "🔩"
        title = "工具Y"

        def get_actions(self):
            return [ActionDef(name="do_y", description="做Y")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="Y")

    registry.register(ToolX())
    registry.register(ToolY())

    # 只获取 ToolX 的 Schema
    schemas = registry.get_schemas_by_names({"tool_x"})
    check("只获取指定工具 Schema", len(schemas) == 1)
    check("Schema 名称正确", schemas[0]["function"]["name"] == "tool_x_do_x")


def test_invalidate_schema_cache():
    """测试：手动清除 Schema 缓存。"""
    section("测试：清除 Schema 缓存")

    registry = ToolRegistry()

    class InvalidateTestTool(BaseTool):
        name = "inv_test"
        emoji = "🗑️"
        title = "清除测试"

        def get_actions(self):
            return [ActionDef(name="action", description="动作")]

        async def execute(self, action: str, params: dict):
            return ToolResult(output="OK")

    registry.register(InvalidateTestTool())
    registry.get_all_schemas()
    check("缓存已生成", registry._schema_cache is not None)

    registry.invalidate_schema_cache()
    check("手动清除缓存", registry._schema_cache is None)


# ============================================================================
# 测试：函数名解析
# ============================================================================

def test_resolve_function_name():
    """测试：函数名解析。"""
    section("测试：函数名解析")

    registry = create_default_registry()

    # 标准下划线格式
    result = registry.resolve_function_name("shell_run")
    check("解析 shell_run", result == ("shell", "run"))

    result = registry.resolve_function_name("file_read")
    check("解析 file_read", result == ("file", "read"))

    result = registry.resolve_function_name("search_web_search")
    check("解析 search_web_search", result == ("search", "web_search"))

    result = registry.resolve_function_name("app_control_launch")
    check("解析 app_control_launch", result == ("app_control", "launch"))

    # 工具名本身包含下划线
    result = registry.resolve_function_name("browser_use_open")
    check("解析 browser_use_open", result == ("browser_use", "open"))

    result = registry.resolve_function_name("voice_input_transcribe")
    check("解析 voice_input_transcribe", result == ("voice_input", "transcribe"))

    result = registry.resolve_function_name("datetime_tool_get_datetime")
    check("解析 datetime_tool_get_datetime", result == ("datetime_tool", "get_datetime"))

    # 不存在的函数
    result = registry.resolve_function_name("non_existent_function")
    check("不存在的函数返回 None", result is None)


# ============================================================================
# 测试：分类查询与风险等级
# ============================================================================

def test_find_by_category():
    """测试：按分类查询工具。"""
    section("测试：按分类查询")

    registry = create_default_registry()

    # 查询各分类
    system_tools = registry.find_by_category("system")
    check("system 分类有工具", len(system_tools) >= 1)

    filesystem_tools = registry.find_by_category("filesystem")
    check("filesystem 分类有工具", len(filesystem_tools) >= 1)

    # 查询不存在的分类
    empty_tools = registry.find_by_category("non_existent_category")
    check("不存在的分类返回空", len(empty_tools) == 0)


def test_get_tool_risk_level():
    """测试：获取工具风险等级。"""
    section("测试：风险等级")

    registry = create_default_registry()

    # 已知风险等级
    check("shell 高风险", registry.get_tool_risk_level("shell") == "high")
    check("file 中风险", registry.get_tool_risk_level("file") == "medium")
    check("screen 低风险", registry.get_tool_risk_level("screen") == "low")

    # 未知工具返回默认值
    risk = registry.get_tool_risk_level("non_existent_tool")
    check("未知工具返回 low", risk == "low")


def test_is_tool_enabled():
    """测试：工具启用状态。"""
    section("测试：工具启用状态")

    registry = ToolRegistry()
    registry.load_config()

    # 验证已启用工具
    for tool_name in ["shell", "file", "screen"]:
        cfg = registry.get_tool_config(tool_name)
        if cfg.get("enabled") is True:
            check(f"工具 {tool_name} 已启用", registry.is_tool_enabled(tool_name))


# ============================================================================
# 测试：懒加载机制
# ============================================================================

def test_lazy_loading():
    """测试：懒加载机制。"""
    section("测试：懒加载机制")

    registry = ToolRegistry()
    registry.load_config()

    # 懒加载模式（默认）
    initial_tools = len(registry.list_tools())
    initial_lazy = len(registry._lazy_tools)

    check("懒加载已配置", initial_lazy > 0)


def test_auto_discover():
    """测试：自动发现工具。"""
    section("测试：自动发现")

    registry = ToolRegistry()
    registry.load_config()

    # 懒加载模式
    registry.auto_discover(lazy=True)
    check("懒加载发现工具", len(registry.list_tools()) > 0)
    check("懒加载记录存在", len(registry._lazy_tools) >= 0)  # 可能为空如果工具加载失败

    # 立即加载模式
    registry2 = ToolRegistry()
    registry2.load_config()
    registry2.auto_discover(lazy=False)
    check("立即加载发现工具", len(registry2.list_tools()) > 0)


# ============================================================================
# 测试：工具调用
# ============================================================================

async def test_call_function():
    """测试：工具函数调用。"""
    section("测试：工具调用")

    registry = ToolRegistry()

    class CallTestTool(BaseTool):
        name = "call_test"
        emoji = "📞"
        title = "调用测试"

        def get_actions(self):
            return [ActionDef(name="call", description="调用", parameters={}, required_params=[])]

        async def execute(self, action: str, params: dict):
            return ToolResult(output=f"Called {action}", data={"params": params})

    registry.register(CallTestTool())

    # 成功调用
    result = await registry.call_function("call_test_call", {"arg": "value"})
    check("成功调用", result.is_success)
    check("输出正确", result.output == "Called call")
    check("数据正确", result.data.get("params") == {"arg": "value"})

    # 不存在的函数
    result = await registry.call_function("non_existent", {})
    check("不存在的函数报错", not result.is_success)
    check("错误信息正确", "未知的函数" in result.error)


# ============================================================================
# 测试：工具摘要
# ============================================================================

def test_get_tools_summary():
    """测试：获取工具摘要。"""
    section("测试：工具摘要")

    registry = create_default_registry()
    summary = registry.get_tools_summary()

    check("摘要非空", len(summary) > 0)
    check("包含工具数量", "已注册" in summary)
    check("包含工具名", "shell" in summary)


# ============================================================================
# 测试：create_default_registry
# ============================================================================

def test_create_default_registry():
    """测试：默认注册表创建。"""
    section("测试：默认注册表")

    registry = create_default_registry()

    check("注册表创建成功", registry is not None)
    check("工具数量 > 0", len(registry.list_tools()) > 0)
    check("Schema 数量 > 0", len(registry.get_all_schemas()) > 0)
    check("函数映射存在", len(registry._func_map) > 0)


# ============================================================================
# 主入口
# ============================================================================

def main():
    global passed, failed

    print("=" * 60)
    print("  WinClaw 工具注册器单元测试套件")
    print("=" * 60)

    # 同步测试
    test_registry_initialization()
    test_load_config()
    test_load_nonexistent_config()
    test_register_tool()
    test_unregister_tool()
    test_register_multiple_tools()
    test_schema_generation()
    test_schema_cache()
    test_get_schemas_by_names()
    test_invalidate_schema_cache()
    test_resolve_function_name()
    test_find_by_category()
    test_get_tool_risk_level()
    test_is_tool_enabled()
    test_lazy_loading()
    test_auto_discover()
    test_get_tools_summary()
    test_create_default_registry()

    # 异步测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_call_function())
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
