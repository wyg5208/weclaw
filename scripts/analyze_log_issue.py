"""
分析日志中揭示的问题

从日志看：
1. testuser2 登录成功
2. 但查询设备状态时，日志显示"用户 testuser 查询设备状态"
3. PWA 显示"未绑定任何设备"

这说明：
- PWA 可能使用了错误的 Token（testuser 的而不是 testuser2 的）
- 或者服务器端认证逻辑有问题
"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('d:/python_projects/weclaw/weclaw_server/data/remote_users.db')
cursor = conn.cursor()

print("=" * 80)
print("问题分析报告")
print("=" * 80)

# 检查两个用户的信息
print("\n【1. 检查 testuser 和 testuser2】")
for username in ['testuser', 'testuser2']:
    cursor.execute("""
        SELECT user_id, username, tokens_revoked_at, created_at 
        FROM users 
        WHERE username = ?
    """, (username,))
    row = cursor.fetchone()
    
    if row:
        user_id, username, tokens_revoked_at, created_at = row
        print(f"\n{username}:")
        print(f"  user_id: {user_id}")
        print(f"  tokens_revoked_at: {tokens_revoked_at or 'NULL'}")
        
        # 检查该用户的设备绑定
        cursor.execute("""
            SELECT status, device_fingerprint, bound_at
            FROM device_bindings
            WHERE user_id = ?
        """, (user_id,))
        bindings = cursor.fetchall()
        
        if bindings:
            for b in bindings:
                print(f"  绑定 [{b[0]}]: fp={b[1][:16] if b[1] else 'NULL'}..., bound_at={b[2]}")
        else:
            print(f"  ✗ 无绑定记录")
    else:
        print(f"\n✗ {username} 不存在")

# 关键分析
print("\n" + "=" * 80)
print("【2. 问题分析】")
print("=" * 80)

print("""
根据日志：
[INFO] remote_server.api.auth: 用户 testuser 查询设备状态：在线

这说明：
1. API 端点 get_device_info() 被调用
2. 依赖注入 get_current_user_with_db() 验证通过
3. 获取到的 user.username 是 "testuser"（不是"testuser2"）
4. get_user_device(user.user_id) 返回了设备信息（因为日志继续执行到第 470 行）
5. 设备状态为"在线"

矛盾点：
- 如果 testuser2 登录，Token 中的 sub 应该是 testuser2 的 user_id
- 但日志显示的是 testuser
- 这说明 PWA 使用的 Token 可能是 testuser 的旧 Token！

可能的原因：
1. PWA 端 localStorage 中保存的是 testuser 的 Token
2. 用户切换账号时没有清除旧 Token
3. 或者登录接口返回的 Token 没有被正确保存
""")

print("\n【3. 验证假设】")
print("检查 testuser 的设备绑定状态...")

cursor.execute("""
    SELECT device_id, device_name, device_fingerprint, status
    FROM device_bindings
    WHERE user_id = (SELECT user_id FROM users WHERE username = 'testuser')
    AND status = 'active'
""")
row = cursor.fetchone()

if row:
    print(f"✓ testuser 有 active 绑定:")
    print(f"  device_id: {row[0]}")
    print(f"  device_name: {row[1]}")
    print(f"  fingerprint: {row[2][:16] if row[2] else 'NULL'}...")
    print(f"\n→ 这解释了为什么日志显示'在线'：设备确实连接着！")
else:
    print(f"✗ testuser 没有 active 绑定")

print("\n【4. 结论】")
print("=" * 80)
print("""
根本原因：PWA 端使用了错误的 JWT Token

场景重现：
1. 用户先用 testuser 登录，Token_A 被保存到 localStorage
2. 用户退出登录（或未退出），然后切换到 testuser2 登录
3. 登录接口返回 Token_B，但 PWA 前端没有正确更新 localStorage
4. PWA 后续请求仍然使用 Token_A（testuser 的 Token）
5. 服务器验证 Token_A，识别出是 testuser
6. 查询 testuser 的设备绑定，返回"在线"状态
7. 但 PWA 期望看到的是 testuser2 的状态（应该是"未绑定"或"离线"）

解决方案：
1. 检查 PWA 前端登录逻辑，确保登录后正确保存新 Token
2. 登出时清除 localStorage 中的 Token
3. Token 刷新时使用正确的 refresh_token
4. 在服务器端增加调试日志，打印 Token 中的 user_id 和用户名
""")

conn.close()
