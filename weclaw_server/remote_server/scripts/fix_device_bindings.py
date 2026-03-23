"""修复设备绑定表的 UNIQUE 约束问题

清理 binding_token 为空字符串的记录，将其设置为 NULL
"""

import sqlite3
from pathlib import Path
import sys

# 支持多种可能的数据库路径
possible_paths = [
    Path(__file__).parent.parent / "data" / "remote_users.db",
    Path(__file__).parent / "data" / "remote_users.db",
    Path("data/remote_users.db"),
    Path("../data/remote_users.db"),
]

# 查找存在的数据库文件
db_path = None
for path in possible_paths:
    if path.exists():
        db_path = path
        break

if not db_path:
    print("错误：找不到数据库文件")
    print("尝试的路径:")
    for path in possible_paths:
        print(f"  - {path}")
    sys.exit(1)

print(f"使用数据库：{db_path}")


def fix_database():
    """执行数据库修复"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 查看当前状态
    print("\n=== 修复前的数据状态 ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM device_bindings")
        print(f"总记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE binding_token = ''")
        print(f"binding_token 为空字符串的记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE binding_token IS NULL")
        print(f"binding_token 为 NULL 的记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'pending'")
        print(f"status 为 pending 的记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'active'")
        print(f"status 为 active 的记录数：{cursor.fetchone()[0]}")
    except sqlite3.OperationalError as e:
        print(f"表可能不存在，跳过检查：{e}")
        conn.close()
        return
    
    # 执行修复
    print("\n=== 开始修复 ===")
    
    # 1. 将空字符串的 binding_token 设置为 NULL
    try:
        cursor.execute("""
            UPDATE device_bindings 
            SET binding_token = NULL 
            WHERE binding_token = ''
        """)
        print(f"已更新 {cursor.rowcount} 条记录：binding_token 从空字符串设为 NULL")
    except sqlite3.OperationalError as e:
        print(f"更新失败：{e}")
    
    # 2. 删除重复的 pending 记录，只保留每个用户最新的一条
    try:
        cursor.execute("""
            DELETE FROM device_bindings 
            WHERE status = 'pending' 
            AND binding_id NOT IN (
                SELECT MAX(binding_id) 
                FROM device_bindings 
                WHERE status = 'pending' 
                GROUP BY user_id
            )
        """)
        print(f"已删除 {cursor.rowcount} 条重复的 pending 记录")
    except sqlite3.OperationalError as e:
        print(f"删除重复记录失败：{e}")
    
    # 3. 检查是否还有重复的 binding_token
    try:
        cursor.execute("""
            SELECT binding_token, COUNT(*) as cnt
            FROM device_bindings
            WHERE binding_token IS NOT NULL
            GROUP BY binding_token
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"\n警告：发现 {len(duplicates)} 个重复的 binding_token:")
            for token, count in duplicates:
                print(f"  - {token[:16]}... ({count}次)")
        else:
            print("\n✓ 未发现重复的 binding_token")
    except sqlite3.OperationalError as e:
        print(f"检查重复失败：{e}")
    
    conn.commit()
    
    # 再次查看状态
    print("\n=== 修复后的数据状态 ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM device_bindings")
        print(f"总记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE binding_token = ''")
        print(f"binding_token 为空字符串的记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE binding_token IS NULL")
        print(f"binding_token 为 NULL 的记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'pending'")
        print(f"status 为 pending 的记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'active'")
        print(f"status 为 active 的记录数：{cursor.fetchone()[0]}")
    except sqlite3.OperationalError as e:
        print(f"查询失败：{e}")
    
    conn.close()
    
    print("\n✓ 数据库修复完成！")


if __name__ == "__main__":
    fix_database()
