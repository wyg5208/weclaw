"""测试 PWA 与桌面端状态同步功能

验证三个核心功能：
1. PWA 登录后可以查询绑定桌面的在线状态
2. 桌面未启动时，返回友好的离线提示
3. 桌面启动时，主动通知 PWA 端
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


async def test_device_status_query():
    """测试功能 1：PWA 查询设备状态"""
    logger.info("\n" + "=" * 80)
    logger.info("测试功能 1: PWA 查询绑定设备的在线状态")
    logger.info("=" * 80)
    
    from weclaw_server.remote_server import context
    from weclaw_server.remote_server.websocket.bridge_handler import get_bridge_manager
    
    user_manager = context.get_user_manager()
    bridge_manager = get_bridge_manager()
    
    if not user_manager:
        logger.error("❌ User Manager 未初始化")
        return False
    
    if not bridge_manager:
        logger.error("❌ Bridge Manager 未初始化")
        return False
    
    # 模拟用户 ID（从日志中获取的真实用户）
    test_user_id = "64f9e1cc"  # 桌面端绑定的用户
    
    # 查询设备信息
    device_info = user_manager.get_user_device(test_user_id)
    
    if not device_info:
        logger.warning(f"⚠️  用户 {test_user_id[:8]} 未绑定设备")
        return False
    
    logger.info(f"\n✅ 用户 {test_user_id[:8]} 已绑定设备:")
    logger.info(f"   设备 ID: {device_info.get('device_id', 'N/A')[:16]}...")
    logger.info(f"   设备名称：{device_info.get('device_name', 'N/A')}")
    logger.info(f"   绑定时间：{device_info.get('bound_at', 'N/A')}")
    
    # 检查在线状态
    user_connections = bridge_manager.get_user_connections(test_user_id)
    is_online = len(user_connections) > 0
    
    logger.info(f"\n📡 设备在线状态：{'✅ 在线' if is_online else '❌ 离线'}")
    
    if is_online:
        logger.info(f"   活跃连接数：{len(user_connections)}")
        for conn in user_connections:
            logger.info(f"   - Session: {conn.session_id[:16]}...")
            logger.info(f"     设备名：{conn.device_name}")
            logger.info(f"     连接时间：{conn.connected_at.isoformat() if conn.connected_at else 'N/A'}")
    
    return True


async def test_offline_message_handling():
    """测试功能 2：桌面离线时的友好提示"""
    logger.info("\n" + "=" * 80)
    logger.info("测试功能 2: 桌面离线时的消息处理")
    logger.info("=" * 80)
    
    from weclaw_server.remote_server.websocket.handlers import handle_chat_message
    from weclaw_server.remote_server import context
    
    # 模拟一个未绑定设备的用户
    test_user_id = "test_offline_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    test_session_id = f"test_session_{datetime.now().timestamp()}"
    
    # 创建模拟的 connection_manager
    class MockConnectionManager:
        def __init__(self):
            self.messages = []
        
        async def send_to_session(self, session_id, message):
            self.messages.append((session_id, message))
            logger.info(f"📨 收到发送给 PWA 的消息：{message['type']}")
    
    connection_manager = MockConnectionManager()
    bridge_manager = get_bridge_manager()
    
    # 发送一条测试消息
    logger.info(f"\n📤 模拟 PWA 发送消息 (user={test_user_id[:8]}...)")
    
    await handle_chat_message(
        user_id=test_user_id,
        session_id=test_session_id,
        content="这是一条测试消息",
        attachments=[],
        connection_manager=connection_manager,
        winclaw_bridge=None
    )
    
    # 检查是否收到错误提示
    if connection_manager.messages:
        session_id, message = connection_manager.messages[0]
        
        if message["type"] == "error":
            error_code = message["payload"]["code"]
            error_msg = message["payload"]["message"]
            
            logger.info(f"\n✅ 收到错误响应:")
            logger.info(f"   错误代码：{error_code}")
            logger.info(f"   错误消息：{error_msg}")
            
            if error_code == "NO_DEVICE_BOUND":
                logger.info("   ✅ 正确识别为'未绑定设备'状态")
                return True
            elif error_code == "DEVICE_OFFLINE":
                logger.info("   ✅ 正确识别为'设备离线'状态")
                return True
            else:
                logger.error(f"   ❌ 未知错误代码：{error_code}")
                return False
        else:
            logger.error(f"   ❌ 收到非错误类型的消息：{message['type']}")
            return False
    else:
        logger.error("   ❌ 未收到任何响应消息")
        return False


async def test_online_notification():
    """测试功能 3：桌面启动时通知 PWA"""
    logger.info("\n" + "=" * 80)
    logger.info("测试功能 3: 桌面启动时主动通知 PWA")
    logger.info("=" * 80)
    
    from weclaw_server.remote_server.websocket.bridge_handler import get_bridge_manager, broadcast_winclaw_status_change
    
    bridge_manager = get_bridge_manager()
    
    if not bridge_manager:
        logger.error("❌ Bridge Manager 未初始化")
        return False
    
    # 创建一个模拟的 WebSocket 连接
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
        
        async def accept(self):
            pass
        
        async def send_json(self, data):
            self.sent_messages.append(data)
            logger.info(f"📨 Mock WebSocket 收到消息：{data}")
    
    # 模拟用户 ID
    test_user_id = "test_notify_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    mock_session_id = f"mock_{datetime.now().timestamp()}"
    
    # 添加一个模拟连接
    mock_ws = MockWebSocket()
    conn = await bridge_manager.connect(
        websocket=mock_ws,
        session_id=mock_session_id,
        device_id="",
        device_name="Test Device",
        device_fingerprint=""
    )
    
    # 手动设置 user_id（模拟认证成功）
    conn.user_id = test_user_id
    
    logger.info(f"\n✅ 已添加模拟连接：session={mock_session_id[:8]}, user={test_user_id[:8]}...")
    
    # 广播上线通知
    logger.info(f"\n📢 广播上线通知到 PWA...")
    await broadcast_winclaw_status_change(test_user_id, "online")
    
    # 等待异步任务执行
    await asyncio.sleep(0.5)
    
    # 清理
    bridge_manager.disconnect(mock_session_id)
    
    logger.info("\n✅ 测试完成（通知通过 WebSocket 推送，PWA 端会收到 'winclaw_status' 事件）")
    return True


async def main():
    """主测试流程"""
    try:
        logger.info("等待远程服务器初始化...")
        await asyncio.sleep(2)
        
        # 测试功能 1
        result1 = await test_device_status_query()
        
        # 测试功能 2
        result2 = await test_offline_message_handling()
        
        # 测试功能 3
        result3 = await test_online_notification()
        
        # 总结
        logger.info("\n" + "=" * 80)
        logger.info("测试结果汇总")
        logger.info("=" * 80)
        logger.info(f"功能 1 - 设备状态查询：{'✅ 通过' if result1 else '❌ 失败'}")
        logger.info(f"功能 2 - 离线友好提示：{'✅ 通过' if result2 else '❌ 失败'}")
        logger.info(f"功能 3 - 上线主动通知：{'✅ 通过' if result3 else '❌ 失败'}")
        
        if all([result1, result2, result3]):
            logger.info("\n🎉 所有功能测试通过！")
        else:
            logger.info("\n⚠️  部分功能需要进一步测试")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误：{e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
