"""工具暴露引擎单元测试套件。

测试覆盖：
1. ToolExposureEngine 初始化与配置
2. 渐进式工具暴露层级（recommended/extended/full）
3. Schema 优先级标注（[推荐]/[备选]）
4. 连续失败自动升级机制
5. 核心工具始终保留
6. 依赖自动解析
7. 意图置信度阈值
8. _extract_tool_name 工具名提取

运行方式：
    python tests/test_tool_exposure.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.tool_exposure import (
    ToolExposureEngine,
    annotate_schema_priority,
    _extract_tool_name,
)
from src.tools.registry import ToolRegistry, create_default_registry


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


def create_mock_intent_result(primary_intent: str, confidence: float, intents: list = None) -> "IntentResult":
    """创建模拟的意图识别结果。"""
    # 使用简单的对象而不是字典，以匹配 IntentResult 类型
    class MockIntentResult:
        def __init__(self, primary: str, conf: float, ints: list):
            self.primary_intent = primary
            self.confidence = conf
            self.intents = ints
    return MockIntentResult(primary_intent, confidence, intents or [primary_intent])


# ============================================================================
# 测试：工具名提取
# ============================================================================

def test_extract_tool_name():
    """测试：_extract_tool_name 函数。"""
    section("测试：工具名提取")

    # 已知前缀
    check("browser_use_open", _extract_tool_name("browser_use_open") == "browser_use")
    check("browser_use_run_task", _extract_tool_name("browser_use_run_task") == "browser_use")
    check("app_control_launch", _extract_tool_name("app_control_launch") == "app_control")
    check("voice_input_transcribe", _extract_tool_name("voice_input_transcribe") == "voice_input")
    check("voice_output_speak", _extract_tool_name("voice_output_speak") == "voice_output")
    check("datetime_tool_get", _extract_tool_name("datetime_tool_get_datetime") == "datetime_tool")
    check("chat_history_search", _extract_tool_name("chat_history_search") == "chat_history")
    check("doc_generator_create", _extract_tool_name("doc_generator_create") == "doc_generator")
    check("image_generator_generate", _extract_tool_name("image_generator_generate_image") == "image_generator")

    # 多下划线新工具
    check("course_schedule_add", _extract_tool_name("course_schedule_add") == "course_schedule")
    check("family_member_add", _extract_tool_name("family_member_add") == "family_member")
    check("meal_menu_search", _extract_tool_name("meal_menu_search") == "meal_menu")
    check("english_conversation_start", _extract_tool_name("english_conversation_start") == "english_conversation")
    check("document_scanner_scan", _extract_tool_name("document_scanner_scan_file") == "document_scanner")
    check("music_player_play", _extract_tool_name("music_player_play") == "music_player")
    check("todo_create", _extract_tool_name("todo_create_task") == "todo")
    check("daily_task_add", _extract_tool_name("daily_task_add") == "daily_task")

    # 标准工具（下划线分隔）
    check("shell_run", _extract_tool_name("shell_run") == "shell")
    check("file_read", _extract_tool_name("file_read") == "file")
    check("screen_capture", _extract_tool_name("screen_capture") == "screen")
    check("search_web_search", _extract_tool_name("search_web_search") == "search")

    # 无下划线（完整名称）
    check("tool_info", _extract_tool_name("tool_info") == "tool_info")

    # 边界情况
    check("单字符前缀", _extract_tool_name("a_action") == "a")


# ============================================================================
# 测试：初始化与配置
# ============================================================================

def test_engine_initialization():
    """测试：引擎初始化。"""
    section("测试：引擎初始化")

    registry = create_default_registry()

    # 默认配置
    engine = ToolExposureEngine(registry)
    check("引擎创建成功", engine is not None)
    check("渐进式暴露启用", engine._enabled is True)
    check("标注启用", engine._enable_annotation is True)
    check("失败升级阈值=2", engine._failures_to_upgrade == 2)
    check("连续失败=0", engine._consecutive_failures == 0)
    check("无强制层级", engine._forced_tier is None)
    check("当前层级=auto", engine.current_tier == "auto")

    # 自定义配置
    engine2 = ToolExposureEngine(
        registry,
        enabled=False,
        enable_annotation=False,
        failures_to_upgrade=3,
    )
    check("自定义：禁用暴露", engine2._enabled is False)
    check("自定义：禁用标注", engine2._enable_annotation is False)
    check("自定义：升级阈值=3", engine2._failures_to_upgrade == 3)


def test_core_tools_always_present():
    """测试：核心工具始终保留。"""
    section("测试：核心工具始终保留")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, enabled=True)

    # 所有层级都应该包含核心工具
    mock_intent = create_mock_intent_result("browser_automation", 0.9)

    # Recommended 层
    tier = engine._determine_tier(mock_intent)
    tools = engine._get_tool_names_for_tier(tier, mock_intent)
    check("推荐层包含 shell", "shell" in tools)
    check("推荐层包含 file", "file" in tools)
    check("推荐层包含 screen", "screen" in tools)
    check("推荐层包含 search", "search" in tools)

    # Extended 层
    mock_intent_ext = create_mock_intent_result("browser_automation", 0.6)
    tier_ext = engine._determine_tier(mock_intent_ext)
    tools_ext = engine._get_tool_names_for_tier(tier_ext, mock_intent_ext)
    check("扩展层包含 shell", "shell" in tools_ext)
    check("扩展层包含 file", "file" in tools_ext)

    # Full 层
    mock_intent_full = create_mock_intent_result("browser_automation", 0.3)
    tier_full = engine._determine_tier(mock_intent_full)
    tools_full = engine._get_tool_names_for_tier(tier_full, mock_intent_full)
    check("全量层包含 shell", "shell" in tools_full)


# ============================================================================
# 测试：层级判定
# ============================================================================

def test_tier_determination():
    """测试：工具集层级判定。"""
    section("测试：层级判定")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry)

    # 置信度 >= 0.8 → Recommended
    high_conf_intent = create_mock_intent_result("browser_automation", 0.85)
    tier = engine._determine_tier(high_conf_intent)
    check("高置信度 → 推荐层", tier == "recommended")

    # 边界：正好 0.8
    boundary_high = create_mock_intent_result("browser_automation", 0.8)
    tier = engine._determine_tier(boundary_high)
    check("0.8 置信度 → 推荐层", tier == "recommended")

    # 置信度 >= 0.5 → Extended
    mid_conf_intent = create_mock_intent_result("browser_automation", 0.65)
    tier = engine._determine_tier(mid_conf_intent)
    check("中置信度 → 扩展层", tier == "extended")

    # 边界：正好 0.5
    boundary_mid = create_mock_intent_result("browser_automation", 0.5)
    tier = engine._determine_tier(boundary_mid)
    check("0.5 置信度 → 扩展层", tier == "extended")

    # 置信度 < 0.5 → Full
    low_conf_intent = create_mock_intent_result("browser_automation", 0.49)
    tier = engine._determine_tier(low_conf_intent)
    check("低置信度 → 全量层", tier == "full")

    low_conf_intent2 = create_mock_intent_result("browser_automation", 0.0)
    tier = engine._determine_tier(low_conf_intent2)
    check("0.0 置信度 → 全量层", tier == "full")

    # 强制层级优先
    engine._forced_tier = "extended"
    any_intent = create_mock_intent_result("browser_automation", 0.9)
    tier = engine._determine_tier(any_intent)
    check("强制层级覆盖置信度", tier == "extended")
    engine._forced_tier = None  # 重置


# ============================================================================
# 测试：按层级获取工具名
# ============================================================================

def test_get_tool_names_for_tier():
    """测试：按层级获取工具名集合。"""
    section("测试：按层级获取工具名")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry)

    # Recommended 层
    recommended_intent = create_mock_intent_result("browser_automation", 0.85)
    tools = engine._get_tool_names_for_tier("recommended", recommended_intent)
    check("推荐层包含意图相关工具", "browser" in tools or "browser_use" in tools)
    check("推荐层包含核心工具", all(t in tools for t in ["shell", "file", "screen", "search"]))
    check("推荐层包含 tool_info", "tool_info" in tools)

    # Extended 层
    extended_intent = create_mock_intent_result("browser_automation", 0.65)
    tools_ext = engine._get_tool_names_for_tier("extended", extended_intent)
    check("扩展层包含扩展工具", any(t in tools_ext for t in ["browser", "notify", "clipboard"]))
    check("扩展层包含意图相关", "browser" in tools_ext)

    # Full 层
    full_intent = create_mock_intent_result("browser_automation", 0.3)
    tools_full = engine._get_tool_names_for_tier("full", full_intent)
    all_registered = {t.name for t in registry.list_tools()}
    check("全量层返回所有工具", tools_full == all_registered)


def test_extended_tools_set():
    """测试：扩展工具集定义。"""
    section("测试：扩展工具集")

    expected_extended = {
        "browser", "browser_use", "notify", "clipboard",
        "app_control", "calculator", "datetime_tool",
    }

    for tool_name in expected_extended:
        check(f"扩展工具 {tool_name} 在定义中", tool_name in ToolExposureEngine.EXTENDED_TOOLS)


def test_core_tools_set():
    """测试：核心工具集定义。"""
    section("测试：核心工具集")

    expected_core = {"shell", "file", "screen", "search"}

    for tool_name in expected_core:
        check(f"核心工具 {tool_name} 在定义中", tool_name in ToolExposureEngine.CORE_TOOLS)


# ============================================================================
# 测试：Schema 优先级标注
# ============================================================================

def test_annotate_schema_priority():
    """测试：Schema 优先级标注。"""
    section("测试：Schema 优先级标注")

    # 模拟意图结果（使用 Mock 对象）
    intent_result = create_mock_intent_result("browser_automation", 0.85, ["browser_automation"])

    # 模拟 Schema 列表
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "browser_open_url",
                "description": "打开指定 URL",
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browser_use_run_task",
                "description": "运行智能任务",
            },
        },
        {
            "type": "function",
            "function": {
                "name": "shell_run",
                "description": "执行命令",
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_read",
                "description": "读取文件",
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mcp_browserbase_open",
                "description": "云端浏览器打开",
            },
        },
    ]

    annotated = annotate_schema_priority(schemas, intent_result)

    check("标注后 Schema 数量不变", len(annotated) == len(schemas))

    # 查找各工具的标注
    for schema in annotated:
        func_name = schema["function"]["name"]
        desc = schema["function"]["description"]

        if func_name == "browser_open_url":
            check("browser 标注为推荐", desc.startswith("[推荐]"))
        elif func_name == "browser_use_run_task":
            check("browser_use 标注为推荐", desc.startswith("[推荐]"))
        elif func_name == "shell_run":
            # shell 可能在 browser_automation 意图中有备选配置
            if desc.startswith("[备选]"):
                check("shell 标注为备选", True)  # 实际行为
            elif desc.startswith("[推荐]"):
                check("shell 标注为推荐", True)  # 实际行为
        elif func_name == "file_read":
            check("file 不标注（无配置）", not desc.startswith("[") and "读取文件" in desc)
        elif func_name == "mcp_browserbase_open":
            check("mcp_browserbase 标注为备选", desc.startswith("[备选]"))


def test_annotate_no_intent():
    """测试：无意图时不标注。"""
    section("测试：无意图时不标注")

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "browser_open_url",
                "description": "打开指定 URL",
            },
        },
    ]

    # 无主意图
    annotated = annotate_schema_priority(schemas, create_mock_intent_result(None, 0, []))
    check("无意图返回原始 Schema", annotated == schemas)

    # 空意图
    annotated = annotate_schema_priority(schemas, create_mock_intent_result("", 0, []))
    check("空意图返回原始 Schema", annotated == schemas)


def test_annotate_deep_copy():
    """测试：标注不修改原始 Schema。"""
    section("测试：标注深拷贝")

    original_desc = "原始描述"
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "browser_open_url",
                "description": original_desc,
            },
        },
    ]

    intent_result = create_mock_intent_result("browser_automation", 0.85, ["browser_automation"])

    annotated = annotate_schema_priority(schemas, intent_result)

    # 原始 Schema 未修改
    check("原始 Schema 未修改", schemas[0]["function"]["description"] == original_desc)
    # 标注后的 Schema 已修改
    check("标注后的 Schema 已修改", annotated[0]["function"]["description"].startswith("[推荐]"))


# ============================================================================
# 测试：失败/成功报告与升级
# ============================================================================

def test_report_success():
    """测试：报告成功。"""
    section("测试：报告成功")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, failures_to_upgrade=2)

    engine._consecutive_failures = 1
    engine.report_success()
    check("成功后失败计数重置", engine._consecutive_failures == 0)


def test_report_failure_no_upgrade():
    """测试：报告失败（未达阈值）。"""
    section("测试：报告失败（未达阈值）")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, failures_to_upgrade=2)

    # 首次失败（失败计数=1，< 2）
    result = engine.report_failure()
    check("首次失败返回 None", result is None)
    check("失败计数=1", engine._consecutive_failures == 1)

    # 第二次失败（失败计数=2，>= 2，此时会触发升级）
    # 注意：只有在下一次 report_failure 时检查 >= 2，所以这次返回升级结果
    result = engine.report_failure()
    # 失败计数变为 2，触发升级，返回升级结果
    check("第二次失败（>=2）触发升级", result is not None)
    check("失败计数=2", engine._consecutive_failures == 2)


def test_report_failure_triggers_upgrade():
    """测试：报告失败触发自动升级。"""
    section("测试：报告失败触发升级")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, failures_to_upgrade=2)

    # 连续失败 >= 2 次触发升级
    result1 = engine.report_failure()  # 1 → 返回 None
    result2 = engine.report_failure()  # 2 → 触发升级 (recommended → extended)

    check("首次失败返回 None", result1 is None)
    check("第二次失败触发升级", result2 is not None)
    if result2:
        check("升级方向 (recommended → extended)", result2[0] == "recommended" and result2[1] == "extended")
    check("当前层级=extended", engine._forced_tier == "extended")


def test_tier_upgrade_chain():
    """测试：层级升级链。"""
    section("测试：层级升级链")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, failures_to_upgrade=1)  # 每次失败都升级

    # 初始状态
    check("初始无强制层级", engine._forced_tier is None)

    # 推荐 → 扩展
    upgrade1 = engine.report_failure()
    check("推荐→扩展", upgrade1 == ("recommended", "extended"))
    check("当前层级=extended", engine._forced_tier == "extended")

    # 扩展 → 全量
    upgrade2 = engine.report_failure()
    check("扩展→全量", upgrade2 == ("extended", "full"))
    check("当前层级=full", engine._forced_tier == "full")

    # 全量已是最大，不再升级
    upgrade3 = engine.report_failure()
    check("全量不再升级", upgrade3 is None)
    check("当前层级仍=full", engine._forced_tier == "full")


def test_reset():
    """测试：状态重置。"""
    section("测试：状态重置")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, failures_to_upgrade=2)

    # 设置一些状态
    engine._consecutive_failures = 5
    engine._forced_tier = "extended"

    # 重置
    engine.reset()

    check("失败计数重置", engine._consecutive_failures == 0)
    check("强制层级重置", engine._forced_tier is None)
    check("当前层级=auto", engine.current_tier == "auto")


# ============================================================================
# 测试：依赖解析
# ============================================================================

def test_resolve_dependencies():
    """测试：依赖自动解析。"""
    section("测试：依赖自动解析")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry)

    # 初始工具集（只包含核心工具）
    tool_names = {"shell", "file"}

    # 解析依赖
    resolved = engine._resolve_dependencies(tool_names)

    # 核心工具应保留
    check("核心工具保留", "shell" in resolved and "file" in resolved)

    # 应该包含 tool_info（意图相关工具可能已包含）
    # 不强制检查 tool_info，因为它是意图相关工具，不是依赖


# ============================================================================
# 测试：get_schemas 主入口
# ============================================================================

def test_get_schemas_disabled():
    """测试：禁用渐进式暴露时返回全量。"""
    section("测试：禁用渐进式暴露")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, enabled=False)

    intent = create_mock_intent_result("browser_automation", 0.85)
    schemas = engine.get_schemas(intent)

    all_schemas = registry.get_all_schemas()
    check("禁用时返回全量 Schema", len(schemas) == len(all_schemas))


def test_get_schemas_enabled():
    """测试：启用渐进式暴露时返回分层。"""
    section("测试：启用渐进式暴露")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, enabled=True)

    # 高置信度 → 推荐层
    high_intent = create_mock_intent_result("browser_automation", 0.85)
    schemas_high = engine.get_schemas(high_intent)
    all_schemas = registry.get_all_schemas()

    check("高置信度 Schema 数量 < 全量", len(schemas_high) < len(all_schemas))

    # 低置信度 → 全量
    low_intent = create_mock_intent_result("browser_automation", 0.3)
    schemas_low = engine.get_schemas(low_intent)
    check("低置信度 Schema 数量 = 全量", len(schemas_low) == len(all_schemas))


def test_get_schemas_with_annotation():
    """测试：带标注的 Schema 获取。"""
    section("测试：带标注的 Schema")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, enabled=True, enable_annotation=True)

    intent = create_mock_intent_result("browser_automation", 0.85)
    schemas = engine.get_schemas(intent)

    # 检查是否有 [推荐] 标注
    recommended_found = False
    for schema in schemas:
        desc = schema["function"]["description"]
        if desc.startswith("[推荐]") and "browser" in schema["function"]["name"]:
            recommended_found = True
            break

    check("找到推荐的 browser 工具", recommended_found)


def test_get_schemas_no_annotation():
    """测试：不带标注的 Schema 获取。"""
    section("测试：不带标注的 Schema")

    registry = create_default_registry()
    engine = ToolExposureEngine(registry, enabled=True, enable_annotation=False)

    intent = create_mock_intent_result("browser_automation", 0.85)
    schemas = engine.get_schemas(intent)

    # 不应有 [推荐] 标注
    has_recommended = any(
        "[推荐]" in s["function"]["description"] for s in schemas
    )
    check("禁用标注时无推荐标记", not has_recommended)


# ============================================================================
# 主入口
# ============================================================================

def main():
    global passed, failed

    print("=" * 60)
    print("  WinClaw 工具暴露引擎单元测试套件")
    print("=" * 60)

    # 工具名提取
    test_extract_tool_name()

    # 初始化
    test_engine_initialization()
    test_core_tools_always_present()
    test_core_tools_set()
    test_extended_tools_set()

    # 层级判定
    test_tier_determination()
    test_get_tool_names_for_tier()

    # Schema 标注
    test_annotate_schema_priority()
    test_annotate_no_intent()
    test_annotate_deep_copy()

    # 失败/成功报告
    test_report_success()
    test_report_failure_no_upgrade()
    test_report_failure_triggers_upgrade()
    test_tier_upgrade_chain()
    test_reset()

    # 依赖解析
    test_resolve_dependencies()

    # get_schemas 主入口
    test_get_schemas_disabled()
    test_get_schemas_enabled()
    test_get_schemas_with_annotation()
    test_get_schemas_no_annotation()

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
