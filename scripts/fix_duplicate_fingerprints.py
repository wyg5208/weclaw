"""
数据库修复脚本 - 清理重复的设备指纹数据

用于修复设备指纹唯一约束冲突问题。
执行后会删除重复的 active 绑定记录，只保留每个指纹最新的一条。

使用方法:
    python fix_duplicate_fingerprints.py

备份建议:
    执行前请先备份原始数据库文件！
"""

import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "weclaw_server" / "data" / "remote_users.db"


def check_duplicates(conn: sqlite3.Connection) -> list:
    """检查重复的设备指纹"""
    cursor = conn.cursor()
    
    # 查找重复的指纹
    cursor.execute("""
        SELECT device_fingerprint, COUNT(*) as cnt,
               GROUP_CONCAT(binding_id) as binding_ids
        FROM device_bindings
        WHERE status = 'active'
        GROUP BY device_fingerprint
        HAVING cnt > 1
    """)
    
    duplicates = []
    for row in cursor.fetchall():
        duplicates.append({
            'fingerprint': row[0],
            'count': row[1],
            'binding_ids': row[2]
        })
    
    return duplicates


def cleanup_duplicates(conn: sqlite3.Connection) -> int:
    """清理重复的设备指纹记录
    
    保留策略：对于每个重复的指纹，只保留 binding_id 最大的那条（最新的）
    
    Returns:
        被删除的记录数
    """
    cursor = conn.cursor()
    
    # 先统计要删除多少条
    cursor.execute("""
        SELECT COUNT(*) FROM device_bindings
        WHERE binding_id NOT IN (
            SELECT MAX(binding_id)
            FROM device_bindings
            WHERE status = 'active'
            GROUP BY device_fingerprint
        )
        AND status = 'active'
        AND device_fingerprint IN (
            SELECT device_fingerprint
            FROM device_bindings
            WHERE status = 'active'
            GROUP BY device_fingerprint
            HAVING COUNT(*) > 1
        )
    """)
    
    to_delete_count = cursor.fetchone()[0]
    
    if to_delete_count == 0:
        print("✓ 没有发现需要清理的重复数据")
        return 0
    
    print(f"\n⚠ 将要删除 {to_delete_count} 条重复记录...")
    
    # 显示即将删除的记录详情
    cursor.execute("""
        SELECT binding_id, user_id, device_id, device_name, 
               device_fingerprint, bound_at
        FROM device_bindings
        WHERE binding_id NOT IN (
            SELECT MAX(binding_id)
            FROM device_bindings
            WHERE status = 'active'
            GROUP BY device_fingerprint
        )
        AND status = 'active'
        AND device_fingerprint IN (
            SELECT device_fingerprint
            FROM device_bindings
            WHERE status = 'active'
            GROUP BY device_fingerprint
            HAVING COUNT(*) > 1
        )
        ORDER BY device_fingerprint, binding_id
    """)
    
    print("\n即将删除的记录:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"  binding_id={row[0]}, user={row[1]}, device={row[2]}, "
              f"fingerprint={row[4][:16]}..., bound_at={row[5]}")
    
    print("-" * 80)
    
    # 执行删除
    cursor.execute("""
        DELETE FROM device_bindings
        WHERE binding_id NOT IN (
            SELECT MAX(binding_id)
            FROM device_bindings
            WHERE status = 'active'
            GROUP BY device_fingerprint
        )
        AND status = 'active'
        AND device_fingerprint IN (
            SELECT device_fingerprint
            FROM device_bindings
            WHERE status = 'active'
            GROUP BY device_fingerprint
            HAVING COUNT(*) > 1
        )
    """)
    
    deleted = cursor.rowcount
    conn.commit()
    
    print(f"\n✓ 成功删除 {deleted} 条重复记录")
    return deleted


def verify_cleanup(conn: sqlite3.Connection):
    """验证清理结果"""
    cursor = conn.cursor()
    
    # 再次检查是否还有重复
    cursor.execute("""
        SELECT device_fingerprint, COUNT(*) as cnt
        FROM device_bindings
        WHERE status = 'active'
        GROUP BY device_fingerprint
        HAVING cnt > 1
    """)
    
    remaining = cursor.fetchall()
    
    if remaining:
        print("\n❌ 警告：仍然存在重复数据！")
        for row in remaining:
            print(f"  fingerprint={row[0][:16]}..., count={row[1]}")
        return False
    else:
        print("\n✓ 验证通过：没有重复的设备指纹了")
        return True


def show_stats(conn: sqlite3.Connection):
    """显示数据库统计信息"""
    cursor = conn.cursor()
    
    print("\n=== 数据库统计 ===")
    
    # 总绑定数
    cursor.execute("SELECT COUNT(*) FROM device_bindings")
    total = cursor.fetchone()[0]
    print(f"总绑定记录数：{total}")
    
    # Active 绑定数
    cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'active'")
    active = cursor.fetchone()[0]
    print(f"Active 绑定数：{active}")
    
    # Pending 绑定数
    cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    print(f"Pending 绑定数：{pending}")
    
    # 唯一用户数
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM device_bindings WHERE status = 'active'")
    users = cursor.fetchone()[0]
    print(f"已绑定的唯一用户数：{users}")
    
    # 唯一设备指纹数
    cursor.execute("SELECT COUNT(DISTINCT device_fingerprint) FROM device_bindings WHERE status = 'active'")
    fingerprints = cursor.fetchone()[0]
    print(f"唯一设备指纹数：{fingerprints}")


def main():
    """主函数"""
    print("=" * 80)
    print("数据库修复脚本 - 清理重复设备指纹")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"\n❌ 错误：数据库文件不存在：{DB_PATH}")
        return
    
    print(f"\n数据库路径：{DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 1. 显示当前统计
        show_stats(conn)
        
        # 2. 检查重复
        duplicates = check_duplicates(conn)
        
        if duplicates:
            print(f"\n⚠ 发现 {len(duplicates)} 个重复的设备指纹:")
            for dup in duplicates:
                print(f"  指纹：{dup['fingerprint'][:16]}..., "
                      f"重复数：{dup['count']}, "
                      f"binding_ids: {dup['binding_ids']}")
            
            # 3. 执行清理
            cleanup_duplicates(conn)
            
            # 4. 验证结果
            if verify_cleanup(conn):
                print("\n✓ 数据库修复完成！")
            else:
                print("\n❌ 清理后仍有问题，请手动检查")
        else:
            print("\n✓ 没有发现重复的设备指纹数据")
        
        # 5. 最终统计
        show_stats(conn)
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("修复完成！可以将数据库复制回服务器了")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
