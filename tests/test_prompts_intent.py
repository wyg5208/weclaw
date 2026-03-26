"""意图识别与工具映射单元测试套件。

测试覆盖：
1. INTENT_TOOL_MAPPING 完整性验证
2. INTENT_PRIORITY_MAP 完整性验证
3. 意图关键词覆盖度检测
4. 工具暴露层级一致性
5. 工具名前缀完整性

运行方式：
    python tests/test_prompts_intent.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.prompts import (
    INTENT_TOOL_MAPPING,
    INTENT_PRIORITY_MAP,
    INTENT_CATEGORIES,
)
from src.tools.registry import create_default_registry
from src.core.tool_exposure import _extract_tool_name, ToolExposureEngine


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
# 测试：INTENT_TOOL_MAPPING 完整性
# ============================================================================

def test_intent_tool_mapping_structure():
    """测试：INTENT_TOOL_MAPPING 结构。"""
    section("测试：INTENT_TOOL_MAPPING 结构")

    check("映射非空", len(INTENT_TOOL_MAPPING) > 0)
    check("至少 10 个意图", len(INTENT_TOOL_MAPPING) >= 10)

    # 每个意图应该是列表
    for intent_name, tools in INTENT_TOOL_MAPPING.items():
        check(f"意图 {intent_name} 是列表", isinstance(tools, list))
        check(f"意图 {intent_name} 非空", len(tools) > 0)


def test_intent_tool_mapping_keys():
    """测试：INTENT_TOOL_MAPPING 关键意图。"""
    section("测试：INTENT_TOOL_MAPPING 关键意图")

    expected_intents = [
        "browser_automation",
        "file_operation",
        "system_admin",
        "daily_assistant",
        "knowledge",
        "life_management",
        "multimedia",
        "communication",
    ]

    for intent in expected_intents:
        check(f"包含 {intent}", intent in INTENT_TOOL_MAPPING)


def test_tool_mapping_coverage():
    """测试：工具映射覆盖率。"""
    section("测试：工具映射覆盖率")

    registry = create_default_registry()
    registered_tools = {t.name for t in registry.list_tools()}

    # 收集所有映射的工具
    mapped_tools = set()
    for tools in INTENT_TOOL_MAPPING.values():
        mapped_tools.update(tools)

    # 检查核心工具是否在映射中
    core_tools = ToolExposureEngine.CORE_TOOLS
    for tool in core_tools:
        # 核心工具可能通过 intent 间接包含
        if tool not in mapped_tools:
            print(f"  ⚠️  核心工具 {tool} 未直接映射（可能通过意图间接包含）")

    # 检查新工具是否已映射
    new_tools = [
        "document_scanner", "music_player", "english_conversation",
        "family_member", "course_schedule", "meal_menu",
        "todo", "daily_task", "family_milestone",
    ]
    for tool in new_tools:
        is_mapped = tool in mapped_tools
        is_registered = tool in registered_tools
        if is_registered:
            check(f"新工具 {tool} 已映射", is_mapped, f"注册但未映射")


# ============================================================================
# 测试：INTENT_PRIORITY_MAP 完整性
# ============================================================================

def test_intent_priority_map_structure():
    """测试：INTENT_PRIORITY_MAP 结构。"""
    section("测试：INTENT_PRIORITY_MAP 结构")

    check("优先级映射非空", len(INTENT_PRIORITY_MAP) > 0)

    # 每个意图应该有 recommended 和 alternative
    for intent_name, priority in INTENT_PRIORITY_MAP.items():
        check(f"意图 {intent_name} 有 recommended", "recommended" in priority)
        check(f"意图 {intent_name} 有 alternative", "alternative" in priority)
        check(f"recommended 是列表", isinstance(priority["recommended"], list))
        check(f"alternative 是列表", isinstance(priority["alternative"], list))


def test_priority_map_coverage():
    """测试：优先级映射覆盖率。"""
    section("测试：优先级映射覆盖率")

    # 关键意图应该有推荐和备选工具
    key_intents = [
        "browser_automation",
        "file_operation",
        "system_admin",
        "daily_assistant",
        "knowledge",
        "life_management",
    ]

    for intent in key_intents:
        if intent in INTENT_PRIORITY_MAP:
            priority = INTENT_PRIORITY_MAP[intent]
            has_recommended = len(priority.get("recommended", [])) > 0
            check(f"意图 {intent} 有推荐工具", has_recommended)
        else:
            check(f"意图 {intent} 在优先级映射中", False, "缺失")


def test_recommended_vs_alternative():
    """测试：推荐工具和备选工具的关系。"""
    section("测试：推荐 vs 备选工具")

    for intent_name, priority in INTENT_PRIORITY_MAP.items():
        recommended = set(priority.get("recommended", []))
        alternative = set(priority.get("alternative", []))

        # 推荐和备选不应完全相同
        if recommended and alternative:
            check(f"意图 {intent_name} 推荐≠备选", recommended != alternative)


# ============================================================================
# 测试：意图关键词覆盖
# ============================================================================

def test_intent_categories_structure():
    """测试：INTENT_CATEGORIES 结构。"""
    section("测试：INTENT_CATEGORIES 结构")

    check("意图分类非空", len(INTENT_CATEGORIES) > 0)

    for intent_name, keywords in INTENT_CATEGORIES.items():
        # 每个分类的关键词应该是列表
        check(f"意图 {intent_name} keywords 是列表", isinstance(keywords, list))
        check(f"意图 {intent_name} keywords 非空", len(keywords) > 0)


def test_keyword_coverage():
    """测试：关键词覆盖度。"""
    section("测试：关键词覆盖度")

    # 常见场景应该有足够关键词
    test_cases = [
        ("browser_automation", ["浏览器", "打开网页", "网站"]),
        ("file_operation", ["文件", "读文件", "写文件", "文件夹"]),
        ("daily_assistant", ["天气", "时间", "日期", "计算"]),
    ]

    for intent, expected_keywords in test_cases:
        if intent in INTENT_CATEGORIES:
            keywords = INTENT_CATEGORIES[intent]
            found = sum(1 for kw in expected_keywords if kw in keywords)
            coverage = found / len(expected_keywords)
            check(f"意图 {intent} 关键词覆盖 {int(coverage*100)}%",
                  coverage >= 0.3,
                  f"仅覆盖 {found}/{len(expected_keywords)}")


# ============================================================================
# 测试：工具名前缀一致性
# ============================================================================

def test_tool_name_extraction_consistency():
    """测试：工具名提取一致性。"""
    section("测试：工具名提取一致性")

    registry = create_default_registry()

    # 收集所有注册的函数名
    func_names = set()
    for schema in registry.get_all_schemas():
        func_name = schema["function"]["name"]
        func_names.add(func_name)

    # 验证每个函数名都能正确提取工具名
    failed_extractions = []
    for func_name in func_names:
        extracted = _extract_tool_name(func_name)

        # 提取的工具名应该能解析
        resolved = registry.resolve_function_name(func_name)
        if resolved is None and extracted != "unknown":
            # 可能 _extract_tool_name 提取的不完全正确，但能解析就行
            pass

        # 验证：提取的工具名应该是已注册的工具或已知前缀
        known_prefixes = [
            "browser_use", "app_control", "voice_input", "voice_output",
            "datetime_tool", "chat_history", "doc_generator", "image_generator",
            "python_runner", "tool_info", "knowledge_rag", "batch_paper_analyzer",
            "user_profile", "course_schedule", "mind_map", "resume_builder",
            "data_processor", "coding_assistant", "data_visualization",
            "speech_to_text", "format_converter", "id_photo", "literature_search",
            "pdf_tool", "gif_maker", "ai_writer", "education_tool", "ppt_generator",
            "financial_report", "contract_generator", "family_member", "meal_menu",
            "document_scanner", "music_player", "english_conversation",
            "family_milestone", "todo", "daily_task",
        ]

        if extracted not in known_prefixes:
            # 检查是否是简单工具名
            if extracted not in ["shell", "file", "screen", "search", "browser",
                                  "notify", "clipboard", "calculator", "weather",
                                  "ocr", "statistics", "cron", "diary", "finance",
                                  "health", "email", "wechat"]:
                failed_extractions.append((func_name, extracted))

    check("所有函数名提取成功", len(failed_extractions) == 0,
          f"失败: {failed_extractions[:5]}")


# ============================================================================
# 测试：层级一致性
# ============================================================================

def test_tier_consistency():
    """测试：层级一致性。"""
    section("测试：层级一致性")

    # 推荐层级的工具应该都在 INTENT_TOOL_MAPPING 中有映射
    for intent_name, priority in INTENT_PRIORITY_MAP.items():
        recommended = priority.get("recommended", [])
        alternative = priority.get("alternative", [])

        if intent_name in INTENT_TOOL_MAPPING:
            mapping = set(INTENT_TOOL_MAPPING[intent_name])

            for tool in recommended:
                check(f"推荐工具 {tool} 在映射中", tool in mapping or tool in ToolExposureEngine.CORE_TOOLS,
                      f"意图 {intent_name}")

            for tool in alternative:
                check(f"备选工具 {tool} 在映射中", tool in mapping or tool in ToolExposureEngine.EXTENDED_TOOLS,
                      f"意图 {intent_name}")


def test_extended_tools_in_mapping():
    """测试：扩展工具在映射中。"""
    section("测试：扩展工具在映射中")

    extended = ToolExposureEngine.EXTENDED_TOOLS

    for tool in extended:
        # 检查工具是否在某个意图的映射中
        found = any(tool in tools for tools in INTENT_TOOL_MAPPING.values())
        if not found:
            print(f"  ⚠️  扩展工具 {tool} 未在任何意图映射中")


# ============================================================================
# 测试：新工具完整性
# ============================================================================

def test_new_tools_in_mapping():
    """测试：新工具完整性。"""
    section("测试：新工具完整性")

    registry = create_default_registry()
    registered = {t.name for t in registry.list_tools()}

    # Phase 6 新增的工具应该都在映射中
    new_tools = {
        "course_schedule", "family_member", "meal_menu",
        "english_conversation", "document_scanner", "music_player",
        "family_milestone", "todo", "daily_task",
    }

    for tool in new_tools:
        if tool in registered:
            # 应该在某个意图的映射中
            found = any(tool in tools for tools in INTENT_TOOL_MAPPING.values())
            check(f"新工具 {tool} 已映射", found,
                  f"{tool} 已注册但未映射到任何意图")


def test_new_tools_in_priority():
    """测试：新工具优先级配置。"""
    section("测试：新工具优先级配置")

    # 检查新增意图的优先级配置
    new_intents = [
        "document_processing", "data_analysis", "creative_content",
        "professional_docs", "development", "education", "research",
    ]

    for intent in new_intents:
        check(f"新意图 {intent} 有优先级配置", intent in INTENT_PRIORITY_MAP)


# ============================================================================
# 测试：边界情况
# ============================================================================

def test_empty_intent_handling():
    """测试：空意图处理。"""
    section("测试：空意图处理")

    # 空意图不应导致崩溃
    try:
        from src.core.tool_exposure import annotate_schema_priority
        schemas = [{"type": "function", "function": {"name": "test", "description": "test"}}]
        result = annotate_schema_priority(schemas, {
            "primary_intent": "",
            "confidence": 0,
            "intents": [],
        })
        check("空意图处理正确", result == schemas)
    except Exception as e:
        check("空意图不崩溃", False, str(e))


def test_none_intent_handling():
    """测试：None 意图处理。"""
    section("测试：None 意图处理")

    try:
        from src.core.tool_exposure import annotate_schema_priority
        schemas = [{"type": "function", "function": {"name": "test", "description": "test"}}]
        result = annotate_schema_priority(schemas, {
            "primary_intent": None,
            "confidence": 0,
            "intents": [],
        })
        check("None 意图处理正确", result == schemas)
    except Exception as e:
        check("None 意图不崩溃", False, str(e))


# ============================================================================
# 主入口
# ============================================================================

def main():
    global passed, failed

    print("=" * 60)
    print("  WinClaw 意图识别与工具映射测试套件")
    print("=" * 60)

    # INTENT_TOOL_MAPPING 测试
    test_intent_tool_mapping_structure()
    test_intent_tool_mapping_keys()
    test_tool_mapping_coverage()

    # INTENT_PRIORITY_MAP 测试
    test_intent_priority_map_structure()
    test_priority_map_coverage()
    test_recommended_vs_alternative()

    # 意图关键词测试
    test_intent_categories_structure()
    test_keyword_coverage()

    # 工具名前缀一致性
    test_tool_name_extraction_consistency()

    # 层级一致性
    test_tier_consistency()
    test_extended_tools_in_mapping()

    # 新工具完整性
    test_new_tools_in_mapping()
    test_new_tools_in_priority()

    # 边界情况
    test_empty_intent_handling()
    test_none_intent_handling()

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
