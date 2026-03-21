"""测试设备指纹匹配修复

验证当 PWA 用户与桌面端绑定用户不一致时，消息能否正确路由。
"""

import asyncio
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-40s | %(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)


async def test_fingerprint_matching():
    """测试设备指纹匹配逻辑"""
    logger.info("=" * 80)
    logger.info("测试开始：设备指纹匹配修复")
    logger.info("=" * 80)
    
    # 模拟场景
    pwa_user_id = "6a5f6c84-4463-412d-9c46-8a72548783ce"  # PWA 端登录的用户 (testuser)
    desktop_user_id = "64f9e1cc"  # 桌面端绑定的用户（从设备指纹推导）
    device_fingerprint = "1892f5fb4d2996beefb1f8fa8377eebddf84d54a25468b45cdc2163e90681ddc"
    
    logger.info(f"\nPWA 用户 ID: {pwa_user_id}")
    logger.info(f"桌面端绑定用户 ID: {desktop_user_id}")
    logger.info(f"设备指纹：{device_fingerprint[:32]}...")
    
    # 检查 user_manager 的 verify_device_fingerprint 方法
    from weclaw_server.remote_server import context
    
    user_manager = context.get_user_manager()
    if not user_manager:
        logger.error("❌ User Manager 未初始化")
        return False
    
    # 测试 1: 验证设备指纹属于哪个用户
    logger.info("\n--- 测试 1: 验证设备指纹归属 ---")
    fingerprint_owner = user_manager.verify_device_fingerprint(device_fingerprint)
    logger.info(f"设备指纹所有者：{fingerprint_owner}")
    
    if fingerprint_owner == desktop_user_id:
        logger.info(f"✅ 设备指纹正确归属于桌面端用户 {desktop_user_id}")
    else:
        logger.warning(f"⚠️  设备指纹归属用户 {fingerprint_owner} 与预期 {desktop_user_id} 不一致")
    
    # 测试 2: 检查 Bridge Manager 的连接查找逻辑
    logger.info("\n--- 测试 2: 测试 Bridge Manager 查找连接 ---")
    from weclaw_server.remote_server.websocket.bridge_handler import get_bridge_manager
    
    bridge_manager = get_bridge_manager()
    if not bridge_manager:
        logger.error("❌ Bridge Manager 未初始化")
        return False
    
    # 模拟一个连接
    class MockWebSocket:
        async def send_json(self, data):
            logger.info(f"Mock WebSocket 发送数据：{data}")
    
    # 添加一个模拟连接到 bridge_manager
    mock_session_id = f"test_{datetime.now().timestamp()}"
    conn = await bridge_manager.connect(
        websocket=MockWebSocket(),
        session_id=mock_session_id,
        device_id="",
        device_name="Test Device",
        device_fingerprint=device_fingerprint
    )
    
    logger.info(f"已添加模拟连接：session={mock_session_id[:8]}, fingerprint={device_fingerprint[:16]}...")
    
    # 测试使用 PWA 用户 ID 查找连接
    logger.info(f"\n使用 PWA 用户 ID 查找连接：{pwa_user_id[:8]}...")
    found_conn = bridge_manager.get_user_connection(pwa_user_id)
    
    if found_conn:
        logger.info(f"✅ 成功找到连接：session={found_conn.session_id[:8]}, user={found_conn.user_id}")
        
        # 验证找到的连接是否正确
        if found_conn.device_fingerprint == device_fingerprint:
            logger.info("✅ 连接的设备指纹匹配")
        else:
            logger.warning(f"⚠️  连接的设备指纹不匹配：{found_conn.device_fingerprint}")
        
        # 清理测试连接
        bridge_manager.disconnect(mock_session_id)
        logger.info("已清理测试连接")
        
        return True
    else:
        logger.error("❌ 未找到连接 - 修复可能未生效")
        
        # 清理测试连接
        bridge_manager.disconnect(mock_session_id)
        return False


async def main():
    """主函数"""
    try:
        # 等待服务器启动
        logger.info("等待远程服务器初始化...")
        await asyncio.sleep(2)
        
        success = await test_fingerprint_matching()
        
        logger.info("\n" + "=" * 80)
        if success:
            logger.info("✅ 测试通过：设备指纹匹配修复有效")
        else:
            logger.error("❌ 测试失败：请检查实现逻辑")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误：{e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
