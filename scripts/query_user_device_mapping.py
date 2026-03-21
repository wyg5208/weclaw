"""查询用户与设备绑定关系"""
import sqlite3
from pathlib import Path

DB_PATH = Path(r"D:\python_projects\weclaw\weclaw_server\data\remote_users.db")
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=" * 80)
print("用户与设备绑定关系查询")
print("=" * 80)

# 1. 统计所有用户
c.execute("SELECT COUNT(*) FROM users")
total_users = c.fetchone()[0]
print(f"\n【用户统计】")
print(f"总用户数：{total_users}")

# 2. 统计已绑定的用户
c.execute("""
    SELECT COUNT(DISTINCT user_id) 
    FROM device_bindings 
    WHERE status = 'active'
""")
bound_users = c.fetchone()[0]
print(f"已绑定设备的用户数：{bound_users}")

# 3. 统计未绑定的用户
c.execute(f"""
    SELECT user_id, username, created_at, tokens_revoked_at
    FROM users
    WHERE user_id NOT IN (
        SELECT user_id FROM device_bindings WHERE status = 'active'
    )
""")
unbound_users = c.fetchall()
print(f"未绑定设备的用户数：{len(unbound_users)}")

# 4. 统计设备总数
c.execute("SELECT COUNT(*) FROM device_bindings WHERE status = 'active'")
total_devices = c.fetchone()[0]
print(f"\n【设备统计】")
print(f"Active 设备总数：{total_devices}")

c.execute("SELECT COUNT(DISTINCT device_id) FROM device_bindings WHERE status = 'active'")
unique_device_ids = c.fetchone()[0]
print(f"唯一设备 ID 数：{unique_device_ids}")

c.execute("SELECT COUNT(DISTINCT device_fingerprint) FROM device_bindings WHERE status = 'active'")
unique_fps = c.fetchone()[0]
print(f"唯一设备指纹数：{unique_fps}")

# 5. 显示所有活跃绑定关系
print(f"\n【绑定关系详情】")
c.execute("""
    SELECT 
        db.binding_id,
        db.user_id,
        u.username,
        db.device_id,
        db.device_name,
        db.device_fingerprint,
        db.bound_at,
        db.last_connected
    FROM device_bindings db
    LEFT JOIN users u ON db.user_id = u.user_id
    WHERE db.status = 'active'
    ORDER BY db.bound_at DESC
""")

bindings = c.fetchall()
if bindings:
    print(f"共 {len(bindings)} 个活跃绑定：\n")
    for i, row in enumerate(bindings, 1):
        print(f"{i}. 用户：{row['username']} ({row['user_id'][:8]}...)")
        print(f"   设备 ID: {row['device_id'][:16]}...")
        print(f"   设备名：{row['device_name'] or 'N/A'}")
        print(f"   指纹：{row['device_fingerprint'][:16]}...")
        print(f"   绑定时间：{row['bound_at']}")
        print(f"   最后连接：{row['last_connected'] or '从未'}")
        print()
else:
    print("没有活跃的绑定记录")

# 6. 显示未绑定用户的详细信息
if unbound_users:
    print(f"\n【未绑定设备的用户】")
    for row in unbound_users:
        print(f"  - {row['username']} (ID: {row['user_id'][:8]}..., 创建：{row['created_at']})")
        if row['tokens_revoked_at']:
            print(f"    Token 已吊销：{row['tokens_revoked_at']}")

# 7. 检查一对多关系
print(f"\n【一对一关系验证】")
c.execute("""
    SELECT user_id, COUNT(*) as cnt
    FROM device_bindings
    WHERE status = 'active'
    GROUP BY user_id
    HAVING cnt > 1
""")
multi_bindings = c.fetchall()
if multi_bindings:
    print(f"⚠ 警告：发现 {len(multi_bindings)} 个用户有多个设备绑定！")
    for row in multi_bindings:
        print(f"  用户 {row['user_id'][:8]}... 绑定了 {row['cnt']} 个设备")
else:
    print("✓ 所有用户都只绑定了一个设备（符合 1:1 设计）")

# 8. 检查设备被多用户绑定
c.execute("""
    SELECT device_fingerprint, COUNT(*) as cnt
    FROM device_bindings
    WHERE status = 'active'
    GROUP BY device_fingerprint
    HAVING cnt > 1
""")
multi_user_devices = c.fetchall()
if multi_user_devices:
    print(f"⚠ 警告：发现 {len(multi_user_devices)} 个设备被多个用户绑定！")
    for row in multi_user_devices:
        print(f"  设备指纹 {row['device_fingerprint'][:16]}... 被 {row['cnt']} 个用户绑定")
else:
    print("✓ 所有设备都只被一个用户绑定（符合 1:1 设计）")

conn.close()
print("\n" + "=" * 80)
