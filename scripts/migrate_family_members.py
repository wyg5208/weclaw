"""迁移 user_profile 的家庭成员数据到 family_member 工具。

检查旧数据库中的家庭成员数据并迁移到新数据库。
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def migrate_family_members():
    """迁移家庭成员数据。"""
    # 旧数据库路径 (user_profile)
    old_db = Path.home() / ".winclaw" / "winclaw_tools.db"
    
    # 新数据库路径 (family_member)
    new_db = Path.home() / ".weclaw" / "weclaw_tools.db"
    
    print("=" * 60)
    print("家庭成员数据迁移工具")
    print("=" * 60)
    
    # 检查旧数据库
    if not old_db.exists():
        print(f"\n❌ 旧数据库不存在：{old_db}")
        return
    
    print(f"\n✅ 找到旧数据库：{old_db}")
    
    # 检查新数据库
    if new_db.exists():
        print(f"✅ 找到新数据库：{new_db}")
    else:
        print(f"📝 创建新数据库：{new_db}")
        new_db.parent.mkdir(parents=True, exist_ok=True)
    
    # 连接数据库
    old_conn = sqlite3.connect(str(old_db))
    new_conn = sqlite3.connect(str(new_db))
    
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # 检查旧数据库中的家庭成员表
    try:
        old_cursor.execute("SELECT * FROM family_members")
        old_members = old_cursor.fetchall()
        
        print(f"\n📊 旧数据库中有 {len(old_members)} 个家庭成员")
        
        if not old_members:
            print("⚠️ 旧数据库中没有家庭成员数据")
            old_conn.close()
            new_conn.close()
            return
        
        # 获取列名
        old_cursor.execute("PRAGMA table_info(family_members)")
        old_columns = [col[1] for col in old_cursor.fetchall()]
        print(f"旧表结构：{old_columns}")
        
    except sqlite3.OperationalError as e:
        print(f"\n❌ 旧数据库中没有 family_members 表：{e}")
        old_conn.close()
        new_conn.close()
        return
    
    # 在新数据库中创建表（如果不存在）
    new_cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
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
        )
    """)
    
    # 检查已存在的成员（避免重复）
    new_cursor.execute("SELECT name, relationship FROM family_members")
    existing = set(new_cursor.fetchall())
    
    print(f"\n📊 新数据库中已有 {len(existing)} 个家庭成员")
    
    # 迁移数据
    migrated_count = 0
    skipped_count = 0
    
    for old_member in old_members:
        # 解析旧数据
        member_dict = dict(zip(old_columns, old_member))
        
        # 检查是否已存在
        key = (member_dict['name'], member_dict['relationship'])
        if key in existing:
            print(f"⏭️  跳过已存在的成员：{member_dict['name']} ({member_dict['relationship']})")
            skipped_count += 1
            continue
        
        # 映射关系类型（如果需要）
        relationship = member_dict['relationship']
        
        # 准备新数据
        now = datetime.now().isoformat()
        new_data = (
            member_dict['name'],
            relationship,
            member_dict.get('birthday'),
            member_dict.get('gender'),
            None,  # phone
            None,  # wechat
            None,  # email
            None,  # address
            None,  # occupation
            None,  # company
            3,     # importance_level (默认)
            '{}',  # preferences
            member_dict.get('notes'),
            None,  # avatar_url
            0,     # is_minor
            None,  # guardian_id
            member_dict.get('created_at', now),
            member_dict.get('updated_at', now),
        )
        
        # 插入新数据库
        new_cursor.execute("""
            INSERT INTO family_members (
                name, relationship, birthday, gender, phone, wechat, email,
                address, occupation, company, importance_level, preferences,
                notes, avatar_url, is_minor, guardian_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, new_data)
        
        print(f"✅ 迁移成员：{member_dict['name']} ({relationship})")
        migrated_count += 1
    
    # 提交事务
    new_conn.commit()
    
    # 验证迁移结果
    new_cursor.execute("SELECT COUNT(*) FROM family_members")
    new_count = new_cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print(f"✅ 成功迁移：{migrated_count} 个家庭成员")
    print(f"⏭️  跳过重复：{skipped_count} 个家庭成员")
    print(f"📊 新数据库总计：{new_count} 个家庭成员")
    print("=" * 60)
    
    # 关闭连接
    old_conn.close()
    new_conn.close()
    
    print("\n💡 提示：请重启 WeClaw 应用以使更改生效")


if __name__ == "__main__":
    migrate_family_members()
