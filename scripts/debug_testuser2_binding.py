"""诊断 testuser2 的设备绑定问题"""
import sqlite3
from datetime import datetime

# 连接数据库
conn = sqlite3.connect('d:/python_projects/weclaw/weclaw_server/data/remote_users.db')
cursor = conn.cursor()

print("=" * 80)
print("诊断报告：testuser2 设备绑定问题")
print("=" * 80)

# 1. 检查用户信息
print("\n【1. 用户信息】")
cursor.execute("""
    SELECT user_id, username, tokens_revoked_at, created_at 
    FROM users 
    WHERE username = 'testuser2'
""")
row = cursor.fetchone()
if row:
    user_id, username, tokens_revoked_at, created_at = row
    print(f"✓ 用户存在：{username}")
    print(f"  user_id: {user_id}")
    print(f"  created_at: {created_at}")
    print(f"  tokens_revoked_at: {tokens_revoked_at or 'NULL'}")
else:
    print("✗ 用户不存在！")
    conn.close()
    exit(1)

# 2. 检查设备绑定
print("\n【2. 设备绑定信息】")
cursor.execute("""
    SELECT binding_id, device_id, device_name, device_fingerprint, 
           status, bound_at, expires_at, created_at
    FROM device_bindings
    WHERE user_id = ?
""", (user_id,))
bindings = cursor.fetchall()

if not bindings:
    print("✗ 未找到任何绑定记录！")
else:
    print(f"✓ 找到 {len(bindings)} 条绑定记录:")
    for i, b in enumerate(bindings, 1):
        print(f"\n  绑定 #{i}:")
        print(f"    binding_id: {b[0]}")
        print(f"    device_id: {b[1]}")
        print(f"    device_name: {b[2]}")
        print(f"    device_fingerprint: {b[3][:16] + '...' if b[3] else 'NULL'}")
        print(f"    status: {b[4]}")
        print(f"    bound_at: {b[5]}")
        print(f"    expires_at: {b[6] or 'NULL'}")
        print(f"    created_at: {b[7]}")

# 3. 检查 active 状态的绑定
print("\n【3. Active 状态绑定详情】")
cursor.execute("""
    SELECT device_id, device_name, device_fingerprint, bound_at
    FROM device_bindings
    WHERE user_id = ? AND status = 'active'
""", (user_id,))
active_binding = cursor.fetchone()

if active_binding:
    print(f"✓ 存在 active 绑定:")
    print(f"  device_id: {active_binding[0]}")
    print(f"  device_name: {active_binding[1]}")
    print(f"  fingerprint: {active_binding[2][:16] + '...' if active_binding[2] else 'NULL'}")
    print(f"  bound_at: {active_binding[3]}")
    
    # 检查指纹唯一性
    print("\n【4. 指纹唯一性检查】")
    cursor.execute("""
        SELECT user_id, device_id FROM device_bindings
        WHERE device_fingerprint = ? AND status = 'active'
    """, (active_binding[2],))
    matching = cursor.fetchall()
    
    if len(matching) == 1:
        print(f"✓ 指纹唯一，仅绑定到此用户")
    elif len(matching) > 1:
        print(f"✗ 警告：该指纹被 {len(matching)} 个用户绑定（存在冲突）:")
        for m in matching:
            print(f"  - user_id={m[0]}, device_id={m[1]}")
    else:
        print(f"✗ 异常：未找到该指纹的 active 绑定")
else:
    print("✗ 没有 active 状态的绑定！")

# 4. 模拟 get_user_device 查询
print("\n【5. 模拟 API 查询 (get_user_device)】")
cursor.execute("""
    SELECT device_id, device_name, bound_at, last_connected, status
    FROM device_bindings
    WHERE user_id = ? AND status = 'active'
""", (user_id,))
result = cursor.fetchone()

if result:
    print(f"✓ 查询成功，返回数据:")
    print(f"  device_id: {result[0]}")
    print(f"  device_name: {result[1]}")
    print(f"  status: {result[4]}")
    print(f"\n→ API 应该返回 200 OK，而不是 404")
else:
    print(f"✗ 查询返回 NULL")
    print(f"\n→ API 会抛出 404 异常：'未绑定设备'")

# 5. 检查吊销时间戳
print("\n【6. Token 吊销状态检查】")
if tokens_revoked_at:
    print(f"⚠ 用户有 tokens_revoked_at 记录：{tokens_revoked_at}")
    print(f"   这会导致所有在此时间之前签发的 JWT Token 被拒绝")
    print(f"   → 如果 PWA 使用的是旧 Token，会被 get_current_user_with_db 拒绝")
else:
    print(f"✓ 无 Token 吊销记录")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)

conn.close()
