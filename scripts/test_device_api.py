"""测试 /api/auth/device 接口返回"""
import requests
import json

BASE_URL = "http://localhost:8188"

print("=" * 80)
print("测试设备查询接口")
print("=" * 80)

# 第一步：登录 testuser2
print("\n【1. 登录 testuser2】")
login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "testuser2",
    "password": "your_password_here"  # ⚠️ 替换为真实密码
})

if login_response.status_code == 200:
    login_data = login_response.json()
    access_token = login_data["access_token"]
    print(f"✓ 登录成功")
    print(f"  User ID: {login_data['user']['user_id'][:8]}")
    print(f"  Username: {login_data['user']['username']}")
    
    # 第二步：查询设备
    print("\n【2. 查询设备信息】")
    headers = {"Authorization": f"Bearer {access_token}"}
    device_response = requests.get(f"{BASE_URL}/api/auth/device", headers=headers)
    
    print(f"响应状态码：{device_response.status_code}")
    
    if device_response.status_code == 200:
        device_data = device_response.json()
        print(f"✓ 查询成功")
        print(f"  Device ID: {device_data['device_id']}")
        print(f"  Device Name: {device_data['device_name']}")
        print(f"  Status: {device_data['status']}")
        print(f"  Is Online: {device_data.get('is_online', False)}")
        print(f"\n完整响应:")
        print(json.dumps(device_data, indent=2))
        
    elif device_response.status_code == 404:
        print(f"✗ 返回 404：{device_response.json().get('detail', 'Unknown error')}")
        print(f"\n→ 这说明 get_user_device() 返回了 None")
        
    else:
        print(f"✗ 未知错误：{device_response.status_code}")
        print(f"  响应：{device_response.text}")
        
else:
    print(f"✗ 登录失败：{login_response.status_code}")
    print(f"  响应：{login_response.text}")

print("\n" + "=" * 80)
