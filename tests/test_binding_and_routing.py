"""绑定关系与消息路由整改测试

覆盖以下整改点：
  建议A - 设备指纹唯一约束
  建议B - 消息路由精准化（防止广播到其他浏览器标签页）
  建议C - binding_token 过期时间（expires_at）
  建议D - Token 吊销机制
  建议E - 1:1 绑定模型语义

运行方式：
    cd d:\\python_projects\\weclaw
    python -m pytest tests/test_binding_and_routing.py -v
"""

import sys
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

# 将 weclaw_server 目录加入路径，绕过根目录损屏的 __init__.py
WINCLAW_SERVER_DIR = str(Path(__file__).parent.parent / "weclaw_server")
if WINCLAW_SERVER_DIR not in sys.path:
    sys.path.insert(0, WINCLAW_SERVER_DIR)

# 确保项目根目录也在路径中（用于其他测试）
ROOT_DIR = str(Path(__file__).parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(1, ROOT_DIR)


# =============================================================================
# 辅助函数
# =============================================================================

def make_user_manager(db_path: Path):
    """创建一个使用临时数据库的 UserManager"""
    from remote_server.auth.user_manager import UserManager
    return UserManager(db_path=db_path)


# =============================================================================
# 建议A：设备指纹唯一约束测试
# =============================================================================

class TestDeviceFingerprintUniqueConstraint:
    """建议A：验证 device_fingerprint 在 active 状态下唯一"""

    def test_same_fingerprint_cannot_bind_two_users(self, tmp_path):
        """同一设备指纹不能同时绑定两个不同用户"""
        um = make_user_manager(tmp_path / "test.db")

        # 注册两个用户
        user1 = um.create_user("user1", "password123")
        user2 = um.create_user("user2", "password456")
        fingerprint = "a" * 64  # 模拟一个固定的设备指纹

        # 用户1 生成绑定 token
        token1 = um.generate_binding_token(user1.user_id)
        assert token1 is not None, "用户1 应能生成绑定 token"

        # 用户1 成功绑定
        success1 = um.bind_device(
            binding_token=token1,
            device_id="device_abc",
            device_name="TestPC",
            device_fingerprint=fingerprint
        )
        assert success1, "用户1 首次绑定应成功"

        # 用户2 生成绑定 token
        token2 = um.generate_binding_token(user2.user_id)
        assert token2 is not None, "用户2 应能生成绑定 token"

        # 用户2 尝试用相同指纹绑定（应失败，触发唯一约束或应用层检查）
        success2 = um.bind_device(
            binding_token=token2,
            device_id="device_abc",
            device_name="TestPC",
            device_fingerprint=fingerprint
        )
        assert not success2, "相同设备指纹不应被两个用户绑定"

    def test_unique_index_exists_in_db(self, tmp_path):
        """验证数据库中确实创建了局部唯一索引"""
        make_user_manager(tmp_path / "test.db")
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_bindings_fp_active'"
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None, "idx_bindings_fp_active 索引应存在"

    def test_same_fingerprint_allowed_after_unbind(self, tmp_path):
        """解绑后同一指纹可以被其他用户绑定"""
        um = make_user_manager(tmp_path / "test.db")
        fingerprint = "b" * 64

        user1 = um.create_user("user1", "password123")
        user2 = um.create_user("user2", "password456")

        # user1 绑定
        token1 = um.generate_binding_token(user1.user_id)
        um.bind_device(token1, "dev1", "PC1", fingerprint)

        # user1 解绑
        um.unbind_device(user1.user_id)

        # user2 用同一指纹绑定（应成功）
        token2 = um.generate_binding_token(user2.user_id)
        success = um.bind_device(token2, "dev1", "PC1", fingerprint)
        assert success, "解绑后同一指纹应可以被其他用户绑定"


# =============================================================================
# 建议C：binding_token 过期时间测试
# =============================================================================

class TestBindingTokenExpiry:
    """建议C：验证 binding_token 的 expires_at 字段生效"""

    def test_token_has_expires_at_in_db(self, tmp_path):
        """生成的 token 在数据库中应有 expires_at 字段"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")
        token = um.generate_binding_token(user.user_id)
        assert token is not None

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT expires_at FROM device_bindings WHERE binding_token = ?",
            (token,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None, "绑定记录应存在"
        assert row["expires_at"] is not None, "expires_at 字段不应为空"

        # 验证过期时间约为当前时间 + 10 分钟
        expires_at = datetime.fromisoformat(row["expires_at"])
        now = datetime.now()
        diff = (expires_at - now).total_seconds()
        assert 540 <= diff <= 660, f"过期时间应在 9-11 分钟之间，实际: {diff:.1f}s"

    def test_expired_token_cannot_be_used(self, tmp_path):
        """过期的 token 不能用于绑定"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")
        token = um.generate_binding_token(user.user_id)

        # 手动将 expires_at 设置为过去时间，模拟 token 已过期
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        past = (datetime.now() - timedelta(minutes=1)).isoformat()
        conn.execute(
            "UPDATE device_bindings SET expires_at = ? WHERE binding_token = ?",
            (past, token)
        )
        conn.commit()
        conn.close()

        # 查询应返回 None
        result = um.get_user_id_by_binding_token(token)
        assert result is None, "过期的 token 不应返回用户 ID"

        # 绑定应失败
        success = um.bind_device(token, "dev1", "PC1", "c" * 64)
        assert not success, "过期的 token 不应能绑定"

    def test_valid_token_can_be_used(self, tmp_path):
        """有效 token 可以正常查询和绑定"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")
        token = um.generate_binding_token(user.user_id)

        result = um.get_user_id_by_binding_token(token)
        assert result == user.user_id, "有效 token 应能查询到用户 ID"

        success = um.bind_device(token, "dev1", "PC1", "d" * 64)
        assert success, "有效 token 应能绑定"


# =============================================================================
# 建议D：Token 吊销机制测试
# =============================================================================

class TestTokenRevocation:
    """建议D：验证 Token 吊销功能"""

    def test_revoke_tokens_updates_db(self, tmp_path):
        """revoke_tokens 应正确更新数据库中的 tokens_revoked_at 字段"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")

        before = datetime.utcnow()
        success = um.revoke_tokens(user.user_id)
        after = datetime.utcnow()

        assert success, "revoke_tokens 应返回 True"

        # 从数据库验证
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT tokens_revoked_at FROM users WHERE user_id = ?", (user.user_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["tokens_revoked_at"] is not None, "tokens_revoked_at 不应为 None"
        revoked_at = datetime.fromisoformat(row["tokens_revoked_at"])
        assert before <= revoked_at <= after, "吊销时间应在调用前后之间"

    def test_token_before_revoke_is_revoked(self, tmp_path):
        """在吊销时间点之前签发的 token 应被认定为已吊销"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")

        # 模拟 1 分钟前签发的 token（Unix 时间戳）
        old_iat = (datetime.utcnow() - timedelta(minutes=1)).timestamp()

        # 吊销所有 token
        um.revoke_tokens(user.user_id)

        # 旧 token 应被吊销
        assert um.is_token_revoked(user.user_id, old_iat), "吊销前的 token 应被标记为已吊销"

    def test_token_after_revoke_is_valid(self, tmp_path):
        """在吊销时间点之后签发的 token 应有效"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")

        # 先吊销
        um.revoke_tokens(user.user_id)

        # 模拟吊销后 1 秒签发的 token
        # 使用 time.time() 而非 datetime.utcnow().timestamp()，避免非 UTC 机器时区偏移 Bug
        new_iat = time.time() + 1

        assert not um.is_token_revoked(user.user_id, new_iat), "吊销后的新 token 不应被吊销"

    def test_no_revoke_record_means_not_revoked(self, tmp_path):
        """未执行过吊销的用户，任何 token 都不应被吊销"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")

        old_iat = (datetime.utcnow() - timedelta(days=365)).timestamp()
        assert not um.is_token_revoked(user.user_id, old_iat), "未吊销过的用户 token 不应被认为已吊销"


# =============================================================================
# 建议A+E：1:1 绑定模型完整性测试
# =============================================================================

class TestOneToOneBindingModel:
    """建议A+E：验证严格 1:1 绑定模型"""

    def test_user_cannot_have_two_active_bindings(self, tmp_path):
        """一个用户不能同时有两个活跃绑定"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")

        # 第一次绑定
        token1 = um.generate_binding_token(user.user_id)
        um.bind_device(token1, "dev1", "PC1", "e" * 64)

        # 尝试生成第二个绑定 token（应失败，因为已有活跃绑定）
        token2 = um.generate_binding_token(user.user_id)
        assert token2 is None, "已有活跃绑定时不应能生成新的绑定 token"

    def test_get_user_device_returns_single_device(self, tmp_path):
        """get_user_device 只应返回一个设备"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")
        token = um.generate_binding_token(user.user_id)
        um.bind_device(token, "dev1", "PC1", "f" * 64)

        device = um.get_user_device(user.user_id)
        assert device is not None
        assert device["device_id"] == "dev1"
        assert device["status"] == "active"

    def test_unbind_allows_rebinding(self, tmp_path):
        """解绑后可以重新绑定"""
        um = make_user_manager(tmp_path / "test.db")
        user = um.create_user("testuser", "password123")

        token = um.generate_binding_token(user.user_id)
        um.bind_device(token, "dev1", "PC1", "g" * 64)
        um.unbind_device(user.user_id)

        # 重新绑定
        token2 = um.generate_binding_token(user.user_id)
        assert token2 is not None, "解绑后应能生成新的绑定 token"
        success = um.bind_device(token2, "dev2", "PC2", "h" * 64)
        assert success, "解绑后应能重新绑定"


# =============================================================================
# 建议B：消息路由精准化测试
# =============================================================================

class TestMessageRouting:
    """建议B：验证 WebSocket 消息路由精准化"""

    def test_forward_to_pwa_uses_session_routing(self):
        """forward_to_pwa_by_request 应优先使用 session 定点路由"""
        import asyncio
        from remote_server.websocket.bridge_handler import (
            BridgeConnectionManager, forward_to_pwa_by_request
        )

        manager = BridgeConnectionManager()

        # 注册一个 PWA 请求，pwa_session_id 是 WS session
        request_id = "req_test_001"
        user_id = "user_abc"
        ws_session_id = f"remote_{user_id}_9999"
        manager.register_pwa_request(request_id, user_id, ws_session_id)

        # Mock pwa_manager 的 send_to_session 方法
        mock_pwa_manager = MagicMock()
        mock_pwa_manager.send_to_session = AsyncMock(return_value=True)
        mock_pwa_manager.send_message = AsyncMock(return_value=True)

        message = {"type": "content", "payload": {"delta": "hello"}}

        with patch(
            "remote_server.context.get_connection_manager",
            return_value=mock_pwa_manager
        ):
            asyncio.run(forward_to_pwa_by_request(manager, request_id, message))

        # send_to_session 应被调用，而非 send_message（广播）
        mock_pwa_manager.send_to_session.assert_called_once_with(ws_session_id, message)
        mock_pwa_manager.send_message.assert_not_called()

    def test_forward_to_pwa_falls_back_to_broadcast_when_session_not_found(self):
        """当 session 不在 WS 管理器中时，应降级为广播"""
        import asyncio
        from remote_server.websocket.bridge_handler import (
            BridgeConnectionManager, forward_to_pwa_by_request
        )

        manager = BridgeConnectionManager()
        request_id = "req_test_002"
        user_id = "user_xyz"
        http_session_id = f"remote_{user_id}_http_123"
        manager.register_pwa_request(request_id, user_id, http_session_id)

        mock_pwa_manager = MagicMock()
        # send_to_session 返回 False（session 不在 WS 中）
        mock_pwa_manager.send_to_session = AsyncMock(return_value=False)
        mock_pwa_manager.send_message = AsyncMock(return_value=True)

        message = {"type": "winclaw_status", "payload": {"status": "online"}}

        with patch(
            "remote_server.context.get_connection_manager",
            return_value=mock_pwa_manager
        ):
            asyncio.run(forward_to_pwa_by_request(manager, request_id, message))

        # session 路由失败后应降级为广播
        mock_pwa_manager.send_message.assert_called_once_with(user_id, message)

    def test_post_handler_does_not_send_to_winclaw(self):
        """POST /api/chat 不再直接发送消息到 WinClaw（防止双发）"""
        import ast
        import inspect
        # 直接从文件路径导入，避免包导入问题
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "chat",
            str(Path(__file__).parent.parent / "weclaw_server" / "remote_server" / "api" / "chat.py")
        )
        # 只读取源文件内容检查即可
        source = Path(
            Path(__file__).parent.parent / "weclaw_server" / "remote_server" / "api" / "chat.py"
        ).read_text(encoding="utf-8")
        
        # 在 send_message 函数体中找到其范围
        lines = source.splitlines()
        in_send_message = False
        func_body_lines = []
        indent_level = None
        for i, line in enumerate(lines):
            if "async def send_message(" in line:
                in_send_message = True
                indent_level = len(line) - len(line.lstrip())
                continue
            if in_send_message:
                if line.strip() == "":
                    func_body_lines.append(line)
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip():
                    break
                func_body_lines.append(line)
        
        func_body = "\n".join(func_body_lines)
        assert "send_to_user_winclaws" not in func_body, (
            "POST 处理函数不应包含 send_to_user_winclaws 调用（防止双发）"
        )
        assert "send_to_winclaw" not in func_body, (
            "POST 处理函数不应包含 send_to_winclaw 调用（防止双发）"
        )


# =============================================================================
# 数据库迁移测试
# =============================================================================

class TestDatabaseMigration:
    """验证数据库迁移逻辑对现有数据库有效"""

    def test_migration_adds_columns_to_existing_db(self, tmp_path):
        """迁移应为缺少新字段的旧数据库添加列"""
        db_path = tmp_path / "old.db"

        # 创建一个「旧版本」数据库（不含 expires_at 和 tokens_revoked_at）
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                public_key TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                device_fingerprint TEXT,
                settings TEXT,
                login_attempts INTEGER DEFAULT 0,
                locked_until TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE device_bindings (
                binding_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_id TEXT,
                device_name TEXT,
                device_fingerprint TEXT,
                binding_token TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                bound_at TEXT,
                last_connected TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # 用新版 UserManager 打开（应触发迁移）
        make_user_manager(db_path)

        # 验证新列已被添加
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        user_cols = {row[1] for row in cursor.fetchall()}

        cursor.execute("PRAGMA table_info(device_bindings)")
        binding_cols = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "tokens_revoked_at" in user_cols, "users 表应有 tokens_revoked_at 列"
        assert "expires_at" in binding_cols, "device_bindings 表应有 expires_at 列"


# =============================================================================
# pytest 入口（无需特殊配置直接运行）
# =============================================================================

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
