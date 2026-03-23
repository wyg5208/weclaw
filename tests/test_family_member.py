"""测试家庭成员管理工具。

验证家庭成员管理工具的基本功能：
- 创建成员
- 查询成员
- 更新成员
- 删除成员
- 家庭关系图谱
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.tools.family_member import FamilyMemberTool


def test_create_member(tool: FamilyMemberTool):
    """测试创建家庭成员。"""
    print("\n=== 测试创建家庭成员 ===")

    # 测试创建基本成员
    result = tool.execute(
        "create_member",
        {
            "name": "张三",
            "relationship": "spouse",
            "birthday": "1990-05-15",
            "gender": "male",
            "phone": "13800138000",
            "wechat": "zhangsan123",
            "email": "zhangsan@example.com",
            "occupation": "工程师",
            "company": "某某科技",
            "importance_level": 5,
            "notes": "我的配偶",
        },
    )

    print(f"状态：{result.status}")
    print(f"输出：\n{result.output}")
    print(f"数据：{result.data}")
    assert result.is_success, f"创建失败：{result.error}"

    return result


def test_query_members(tool: FamilyMemberTool):
    """测试查询家庭成员。"""
    print("\n=== 测试查询家庭成员 ===")

    # 测试查询所有成员
    result = tool.execute("query_members", {})
    print(f"查询所有成员:\n{result.output}")
    assert result.is_success

    # 测试按 ID 查询详情
    if result.data.get("members"):
        member_id = result.data["members"][0]["id"]
        result = tool.execute("query_members", {"member_id": member_id})
        print(f"\n查询成员详情 (ID: {member_id}):\n{result.output}")
        assert result.is_success

    # 测试按姓名搜索
    result = tool.execute("query_members", {"name": "张"})
    print(f"\n按姓名搜索 '张':\n{result.output}")
    assert result.is_success

    # 测试按关系筛选
    result = tool.execute("query_members", {"relationship": "spouse"})
    print(f"\n按关系筛选 'spouse':\n{result.output}")
    assert result.is_success


def test_update_member(tool: FamilyMemberTool, member_id: int):
    """测试更新家庭成员信息。"""
    print(f"\n=== 测试更新家庭成员 (ID: {member_id}) ===")

    result = tool.execute(
        "update_member",
        {
            "member_id": member_id,
            "phone": "13900139000",
            "company": "更新后的公司",
            "importance_level": 4,
        },
    )

    print(f"更新结果:\n{result.output}")
    assert result.is_success, f"更新失败：{result.error}"

    # 验证更新
    result = tool.execute("query_members", {"member_id": member_id})
    print(f"\n验证更新后的信息:\n{result.output}")
    assert result.is_success


def test_delete_member(tool: FamilyMemberTool, member_id: int):
    """测试删除家庭成员。"""
    print(f"\n=== 测试删除家庭成员 (ID: {member_id}) ===")

    # 先确认成员存在
    result = tool.execute("query_members", {"member_id": member_id})
    assert result.is_success and result.data.get("count", 0) > 0

    # 测试删除（需要确认）
    result = tool.execute("delete_member", {"member_id": member_id, "confirm": True})
    print(f"删除结果:\n{result.output}")
    assert result.is_success, f"删除失败：{result.error}"

    # 验证已删除
    result = tool.execute("query_members", {"member_id": member_id})
    print(f"\n验证删除后:\n{result.output}")
    assert result.data.get("count", 0) == 0, "成员未被删除"


def test_family_tree(tool: FamilyMemberTool):
    """测试获取家庭关系图谱。"""
    print("\n=== 测试家庭关系图谱 ===")

    # 先创建几个测试成员
    test_data = [
        {"name": "李四", "relationship": "parent"},
        {"name": "王五", "relationship": "child"},
        {"name": "赵六", "relationship": "sibling"},
    ]

    for data in test_data:
        result = tool.execute("create_member", data)
        print(f"创建 {data['name']}: {result.status}")

    # 获取关系图谱
    result = tool.execute("get_family_tree", {})
    print(f"\n家庭关系图谱:\n{result.output}")
    assert result.is_success


def test_upcoming_birthday(tool: FamilyMemberTool):
    """测试查询即将到来的生日。"""
    print("\n=== 测试查询即将到来的生日 ===")

    # 创建一个近期生日的成员
    from datetime import datetime, timedelta

    today = datetime.now()
    next_week = today + timedelta(days=7)
    birthday_str = f"{next_week.year}-{next_week.month:02d}-{next_week.day:02d}"

    result = tool.execute(
        "create_member",
        {
            "name": "周七",
            "relationship": "friend",
            "birthday": birthday_str,
        },
    )
    print(f"创建近期生日成员：{result.status}")

    # 查询未来 30 天内的生日
    result = tool.execute("query_members", {"upcoming_birthday_days": 30})
    print(f"\n未来 30 天内的生日:\n{result.output}")
    assert result.is_success


def main():
    """运行所有测试。"""
    print("=" * 60)
    print("家庭成员管理工具测试")
    print("=" * 60)

    try:
        # 使用临时文件数据库进行测试
        import tempfile
        temp_db = Path(tempfile.mktemp(suffix=".db"))
        print(f"\n使用临时数据库：{temp_db}")
        
        tool = FamilyMemberTool(db_path=str(temp_db))
        
        # 验证数据库表是否已创建
        import sqlite3
        conn = sqlite3.connect(str(temp_db))
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"数据库表：{tables}")
        conn.close()

        # 测试创建
        member_id_result = test_create_member(tool)
        member_id = member_id_result.data["member_id"]

        # 测试查询
        test_query_members(tool)

        # 测试更新
        test_update_member(tool, member_id)

        # 测试关系图谱
        test_family_tree(tool)

        # 测试生日查询
        test_upcoming_birthday(tool)

        # 测试删除
        test_delete_member(tool, member_id)

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
        # 清理临时数据库
        if temp_db.exists():
            temp_db.unlink()
            print(f"\n已清理临时数据库：{temp_db}")

    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
