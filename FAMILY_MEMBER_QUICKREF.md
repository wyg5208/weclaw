# 家庭成员管理工具快速参考

## 🚀 快速开始

### 1. 基本用法示例

```python
from src.tools.family_member import FamilyMemberTool

# 初始化工具
tool = FamilyMemberTool()

# 创建家庭成员
result = tool.execute("create_member", {
    "name": "张三",
    "relationship": "spouse",
    "birthday": "1990-05-15",
    "phone": "13800138000"
})
print(result.output)

# 查询所有成员
result = tool.execute("query_members", {})
print(result.output)

# 更新信息
result = tool.execute("update_member", {
    "member_id": 1,
    "phone": "13900139000"
})

# 删除成员（需要确认）
result = tool.execute("delete_member", {
    "member_id": 1,
    "confirm": True
})
```

## 📋 Actions 列表

| Action | 描述 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `create_member` | 创建家庭成员档案 | name, relationship | birthday, gender, phone, wechat, email, address, occupation, company, importance_level, preferences, notes, is_minor, guardian_id |
| `query_members` | 查询家庭成员 | (无) | member_id, name, relationship, upcoming_birthday_days, include_details |
| `update_member` | 更新成员信息 | member_id | 同 create_member 的可选参数 |
| `delete_member` | 删除成员记录 | member_id, confirm | (无) |
| `get_family_tree` | 获取关系图谱 | (无) | root_member_id, max_depth |

## 🎯 关系类型

- `spouse` - 配偶
- `child` - 子女
- `parent` - 父母
- `sibling` - 兄弟姐妹
- `grandparent` - 祖父母/外祖父母
- `grandchild` - 孙子女/外孙子女
- `uncle` - 叔叔/舅舅
- `aunt` - 阿姨/姑姑
- `nephew` - 侄子/外甥
- `niece` - 侄女/外甥女
- `cousin` - 表/堂兄弟姐妹
- `other` - 其他

## 💡 常用场景

### 添加新生儿
```python
tool.execute("create_member", {
    "name": "小明",
    "relationship": "child",
    "birthday": "2024-01-01",
    "is_minor": True,
    "guardian_id": 1  # 监护人 ID
})
```

### 查询即将到来的生日
```python
# 查询未来 30 天内的生日
result = tool.execute("query_members", {
    "upcoming_birthday_days": 30
})
```

### 按姓名搜索
```python
result = tool.execute("query_members", {
    "name": "张"  # 模糊搜索
})
```

### 查看完整家庭结构
```python
result = tool.execute("get_family_tree", {})
print(result.output)
```

## ⚙️ 配置

在 `config/tools.json` 中配置：

```json
{
  "family_member": {
    "enabled": true,
    "module": "src.tools.family_member",
    "class": "FamilyMemberTool",
    "config": {
      "db_path": ""  # 留空使用默认路径 ~/.weclaw/weclaw_tools.db
    }
  }
}
```

## 🧪 测试

运行测试：
```bash
python tests/test_family_member.py
```

## 📊 数据模型

**family_members 表结构：**
```sql
CREATE TABLE family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    birthday TEXT,
    gender TEXT,
    phone TEXT,
    wechat TEXT,
    email TEXT,
    address TEXT,
    occupation TEXT,
    company TEXT,
    importance_level INTEGER DEFAULT 3,
    preferences TEXT DEFAULT '{}',
    notes TEXT,
    avatar_url TEXT,
    is_minor INTEGER DEFAULT 0,
    guardian_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## 🔒 安全特性

- ✅ 删除操作需二次确认
- ✅ 有依赖关系时禁止删除（监护人）
- ✅ 数据本地存储
- ✅ 支持数据持久化

## 📝 最佳实践

1. **设置重要级别**：为核心成员设置 5 星优先级
2. **及时更新信息**：成员变化时及时更新
3. **记录特殊日期**：在备注中记录重要日期
4. **定期备份**：备份 `~/.weclaw/weclaw_tools.db`
5. **正确设置监护人**：为未成年成员指定监护人

---

**详细文档**: [FAMILY_MEMBER_TOOL_GUIDE.md](../docs/FAMILY_MEMBER_TOOL_GUIDE.md)  
**版本**: v1.0  
**最后更新**: 2026-03-24
