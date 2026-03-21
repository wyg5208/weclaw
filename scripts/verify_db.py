"""验证数据库修复结果"""
import sqlite3
from pathlib import Path

# 使用绝对路径
DB_PATH = Path(r"D:\python_projects\weclaw\weclaw_server\data\remote_users.db")
conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()

print("=== 数据库验证 ===\n")

# 检查重复
c.execute("""
    SELECT device_fingerprint, COUNT(*) as cnt
    FROM device_bindings
    WHERE status = 'active'
    GROUP BY device_fingerprint
    HAVING cnt > 1
""")
duplicates = c.fetchall()

if duplicates:
    print(f"❌ 仍有 {len(duplicates)} 个重复指纹:")
    for row in duplicates:
        print(f"  {row[0][:16]}... (重复数：{row[1]})")
else:
    print("✓ 无重复设备指纹")

# 统计
c.execute("SELECT COUNT(*) FROM device_bindings WHERE status='active'")
active = c.fetchone()[0]
print(f"\nActive 绑定数：{active}")

c.execute("SELECT COUNT(DISTINCT device_fingerprint) FROM device_bindings WHERE status='active'")
fps = c.fetchone()[0]
print(f"唯一设备指纹数：{fps}")

# 显示所有 active 绑定
print("\n所有 Active 绑定:")
c.execute("""
    SELECT binding_id, user_id, device_id, device_name, device_fingerprint[:16] 
    FROM device_bindings WHERE status='active'
""")
for row in c.fetchall():
    print(f"  {row[0]} | user={row[1][:8]}... | device={row[2][:8]}... | fp={row[4]}...")

conn.close()
print("\n✓ 验证完成")
