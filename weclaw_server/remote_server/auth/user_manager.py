"""用户管理器

管理用户注册、登录、会话等操作。
使用 SQLite 存储。
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

import bcrypt
import sqlite3

from ..models.user import User, UserSettings

logger = logging.getLogger(__name__)


class UserManager:
    """用户管理器"""
    
    def __init__(
        self,
        db_path: Path,
        max_login_attempts: int = 5,
        lockout_duration_minutes: int = 30
    ):
        """
        初始化用户管理器
        
        Args:
            db_path: 数据库文件路径
            max_login_attempts: 最大登录尝试次数
            lockout_duration_minutes: 锁定时长（分钟）
        """
        self.db_path = db_path
        self.max_login_attempts = max_login_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        
        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
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
                    locked_until TEXT,
                    tokens_revoked_at TEXT
                )
            """)
            
            # 创建会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)
            """)
            
            # 创建用户 - 设备绑定表（PWA 用户绑定到 WeClaw PC）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_bindings (
                    binding_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_id TEXT,
                    device_name TEXT,
                    device_fingerprint TEXT,
                    binding_token TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    bound_at TEXT,
                    last_connected TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # 创建基础索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bindings_user ON device_bindings(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bindings_token ON device_bindings(binding_token)
            """)
            
            # [建议 A] 设备指纹唯一约束（仅对 active 状态）：防止一个设备绑定多个用户
            # SQLite 局部唯一索引，保证 active 状态下同一指纹只能对应一个用户
            try:
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_bindings_fp_active
                    ON device_bindings(device_fingerprint) WHERE status = 'active'
                """)
            except sqlite3.IntegrityError as e:
                logger.warning(f"无法创建设备指纹唯一索引（可能存在重复数据）: {e}")
                logger.warning("请手动清理重复的设备指纹后重启服务")
                # 不阻塞启动，继续执行
            
            conn.commit()
            
            # ===== 数据库迁移：为现有数据库补充新字段 =====
            self._migrate_database(conn)
            
            logger.info(f"用户数据库初始化完成: {self.db_path}")
    
    def _migrate_database(self, conn):
        """对现有数据库执行迁移，补充新增字段"""
        cursor = conn.cursor()
        migrations = [
            # [建议C] 为 device_bindings 补充 expires_at 列
            ("ALTER TABLE device_bindings ADD COLUMN expires_at TEXT",
             "device_bindings.expires_at"),
            # [建议D] 为 users 表补充 tokens_revoked_at 列
            ("ALTER TABLE users ADD COLUMN tokens_revoked_at TEXT",
             "users.tokens_revoked_at"),
        ]
        for sql, desc in migrations:
            try:
                cursor.execute(sql)
                conn.commit()
                logger.info(f"数据库迁移成功: 添加 {desc}")
            except Exception:
                # 列已存在时 SQLite 会抛异常，忽略即可
                pass
        
        # [建议 A] 补充局部唯一索引（迁移时也尝试创建，防止旧库漏建）
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_bindings_fp_active
                ON device_bindings(device_fingerprint) WHERE status = 'active'
            """)
            conn.commit()
            logger.info("数据库迁移成功：创建设备指纹唯一索引")
        except sqlite3.IntegrityError as e:
            # 若旧数据已有重复指纹的 active 绑定，记录警告并提供解决 SQL
            logger.warning(f"创建设备指纹唯一索引失败（可能存在历史脏数据）: {e}")
            logger.warning("请使用以下 SQL 清理重复数据后重启服务：")
            logger.warning("DELETE FROM device_bindings WHERE binding_id NOT IN (")
            logger.warning("    SELECT MAX(binding_id) FROM device_bindings")
            logger.warning("    WHERE status = 'active' GROUP BY device_fingerprint")
            logger.warning(");")
    
    def create_user(
        self,
        username: str,
        password: str,
        public_key: str = "",
        device_fingerprint: Optional[str] = None
    ) -> User:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            public_key: RSA 公钥
            device_fingerprint: 设备指纹
            
        Returns:
            创建的用户对象
            
        Raises:
            ValueError: 用户名已存在或参数无效
        """
        # 验证参数
        if len(username) < 3 or len(username) > 32:
            raise ValueError("用户名长度必须在 3-32 字符之间")
        
        if len(password) < 8:
            raise ValueError("密码长度至少 8 个字符")
        
        # 检查用户名是否已存在
        if self.find_by_username(username):
            raise ValueError("用户名已存在")
        
        # 生成密码哈希
        password_hash = self._hash_password(password)
        
        # 创建用户
        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            password_hash=password_hash,
            public_key=public_key,
            created_at=datetime.now(),
            device_fingerprint=device_fingerprint,
            settings=UserSettings()
        )
        
        # 保存到数据库
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, password_hash, public_key, created_at,
                    is_active, device_fingerprint, settings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.user_id,
                user.username,
                user.password_hash,
                user.public_key,
                user.created_at.isoformat(),
                1 if user.is_active else 0,
                user.device_fingerprint,
                json.dumps(user.settings.to_dict())
            ))
            conn.commit()
        
        logger.info(f"创建新用户: {username} ({user.user_id})")
        return user
    
    def find_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 查找用户"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
        return None
    
    def find_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
        return None
    
    def verify_password(self, user: User, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(
            password.encode("utf-8"),
            user.password_hash.encode("utf-8")
        )
    
    def authenticate(
        self,
        username: str,
        password: str,
        device_fingerprint: Optional[str] = None
    ) -> Optional[User]:
        """
        验证用户登录
        
        Args:
            username: 用户名
            password: 密码
            device_fingerprint: 设备指纹
            
        Returns:
            验证成功返回用户对象，失败返回 None
        """
        user = self.find_by_username(username)
        
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {username}")
            return None
        
        # 检查账户是否被锁定
        if user.is_locked():
            logger.warning(f"登录失败: 账户已锁定 - {username}")
            return None
        
        # 检查账户是否激活
        if not user.is_active:
            logger.warning(f"登录失败: 账户未激活 - {username}")
            return None
        
        # 验证密码
        if not self.verify_password(user, password):
            # 记录失败尝试
            self._record_login_failure(user)
            logger.warning(f"登录失败: 密码错误 - {username}")
            return None
        
        # 检查设备指纹（如果设置了）
        if user.device_fingerprint and device_fingerprint:
            if user.device_fingerprint != device_fingerprint:
                logger.warning(f"登录失败: 设备不匹配 - {username}")
                return None
        
        # 重置登录失败计数
        user.reset_login_attempts()
        user.last_login = datetime.now()
        self._update_user(user)
        
        logger.info(f"用户登录成功: {username}")
        return user
    
    def _record_login_failure(self, user: User):
        """记录登录失败"""
        user.login_attempts += 1
        
        # 检查是否需要锁定
        if user.login_attempts >= self.max_login_attempts:
            user.locked_until = datetime.now() + timedelta(minutes=self.lockout_duration_minutes)
            logger.warning(f"账户已锁定: {user.username} 直到 {user.locked_until}")
        
        self._update_user(user)
    
    def _update_user(self, user: User):
        """更新用户信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET
                    last_login = ?,
                    is_active = ?,
                    device_fingerprint = ?,
                    settings = ?,
                    login_attempts = ?,
                    locked_until = ?
                WHERE user_id = ?
            """, (
                user.last_login.isoformat() if user.last_login else None,
                1 if user.is_active else 0,
                user.device_fingerprint,
                json.dumps(user.settings.to_dict()),
                user.login_attempts,
                user.locked_until.isoformat() if user.locked_until else None,
                user.user_id
            ))
            conn.commit()
    
    def update_public_key(self, user_id: str, public_key: str):
        """更新用户公钥"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET public_key = ? WHERE user_id = ?
            """, (public_key, user_id))
            conn.commit()
    
    def update_settings(self, user_id: str, settings: UserSettings):
        """更新用户设置"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET settings = ? WHERE user_id = ?
            """, (json.dumps(settings.to_dict()), user_id))
            conn.commit()
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def _hash_password(self, password: str) -> str:
        """生成密码哈希"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """将数据库行转换为用户对象"""
        settings_data = json.loads(row["settings"]) if row["settings"] else {}
        
        # 兼容旧数据库（tokens_revoked_at 列可能不存在）
        try:
            tokens_revoked_at_raw = row["tokens_revoked_at"]
        except (IndexError, KeyError):
            tokens_revoked_at_raw = None
        
        return User(
            user_id=row["user_id"],
            username=row["username"],
            password_hash=row["password_hash"],
            public_key=row["public_key"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
            is_active=bool(row["is_active"]),
            device_fingerprint=row["device_fingerprint"],
            settings=UserSettings.from_dict(settings_data),
            login_attempts=row["login_attempts"] or 0,
            locked_until=datetime.fromisoformat(row["locked_until"]) if row["locked_until"] else None,
            tokens_revoked_at=datetime.fromisoformat(tokens_revoked_at_raw) if tokens_revoked_at_raw else None
        )
    
    def close(self):
        """关闭数据库连接（SQLite 会自动关闭）"""
        pass
    
    # ===== 设备绑定管理 =====
    
    def generate_binding_token(self, user_id: str) -> str:
        """生成设备绑定 Token
            
        用户需要使用此 Token 在 WeClaw PC 端进行绑定
        """
        token = str(uuid.uuid4()) + str(uuid.uuid4())  # 64 字符
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 检查是否已有绑定
            cursor.execute("""
                SELECT binding_id FROM device_bindings 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
                
            if cursor.fetchone():
                # 已有绑定，返回 None 表示不能再绑定
                return None
                
            # [建议C] 设置明确的 expires_at 字段（10 分钟有效）
            now = datetime.now()
            expiry_time = now - timedelta(minutes=10)
            expires_at = now + timedelta(minutes=10)

            # 清理过期的 pending 记录
            cursor.execute("""
                DELETE FROM device_bindings 
                WHERE user_id = ? AND status = 'pending'
                AND (expires_at IS NOT NULL AND expires_at < ? OR created_at < ?)
            """, (user_id, now.isoformat(), expiry_time.isoformat()))
                
            # 生成新的绑定记录
            binding_id = str(uuid.uuid4())
                
            cursor.execute("""
                INSERT INTO device_bindings 
                (binding_id, user_id, binding_token, status, created_at, expires_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
            """, (binding_id, user_id, token, now.isoformat(), expires_at.isoformat()))
                
            conn.commit()
                
        return token
    
    def get_user_id_by_binding_token(self, binding_token: str) -> Optional[str]:
        """通过绑定 Token 获取用户 ID
        
        Args:
            binding_token: 绑定 Token
            
        Returns:
            用户 ID，未找到或已过期返回 None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            # [建议C] 检查 expires_at，同时兼容旧数据（expires_at 为 NULL 时也认为有效）
            cursor.execute("""
                SELECT user_id FROM device_bindings 
                WHERE binding_token = ? AND status = 'pending'
                AND (expires_at IS NULL OR expires_at > ?)
            """, (binding_token, now))
            
            row = cursor.fetchone()
            return row["user_id"] if row else None
    
    def bind_device(self, binding_token: str, device_id: str, device_name: str = "", device_fingerprint: str = "") -> bool:
        """绑定设备（WeClaw PC 端调用）
        
        Args:
            binding_token: 用户生成的绑定 Token
            device_id: 设备唯一标识
            device_name: 设备名称
            device_fingerprint: 设备指纹（用于验证）
            
        Returns:
            绑定是否成功
        """
        if not device_fingerprint:
            logger.warning("设备指纹为空，绑定失败")
            return False
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            
            # 查找待绑定的记录，[建议C] 同时检查 expires_at
            cursor.execute("""
                SELECT binding_id, user_id FROM device_bindings 
                WHERE binding_token = ? AND status = 'pending'
                AND (expires_at IS NULL OR expires_at > ?)
            """, (binding_token, now.isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            binding_id = row["binding_id"]
            user_id = row["user_id"]
            
            # [建议A] 检查该指纹是否已被任意用户（包括本用户）绑定
            # 防止同一设备被多个用户绑定，同时防止触发 DB 唯一约束异常
            cursor.execute("""
                SELECT binding_id, user_id FROM device_bindings 
                WHERE device_fingerprint = ? AND status = 'active'
            """, (device_fingerprint,))
            
            existing = cursor.fetchone()
            if existing:
                logger.warning(f"设备指纹已被用户 {existing['user_id']} 绑定，拒绝再次绑定")
                return False
            
            # 检查是否已有活跃绑定（防止并发）
            cursor.execute("""
                SELECT binding_id FROM device_bindings 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            if cursor.fetchone():
                logger.warning(f"用户 {user_id} 已有活跃绑定")
                return False
            
            # 更新绑定状态，并删除该用户的其他 pending 记录
            cursor.execute("""
                UPDATE device_bindings SET
                    device_id = ?,
                    device_name = ?,
                    device_fingerprint = ?,
                    status = 'active',
                    bound_at = ?,
                    binding_token = NULL,
                    expires_at = NULL
                WHERE binding_id = ?
            """, (device_id, device_name, device_fingerprint, now.isoformat(), binding_id))
            
            # 清理该用户的其他所有 pending 记录（包括当前这条的旧记录）
            cursor.execute("""
                DELETE FROM device_bindings 
                WHERE user_id = ? AND status = 'pending' AND binding_id != ?
            """, (user_id, binding_id))
            
            conn.commit()
            
        return True
    
    def get_user_device(self, user_id: str) -> Optional[dict]:
        """获取用户绑定的设备信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT device_id, device_name, bound_at, last_connected, status
                FROM device_bindings
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "device_id": row["device_id"],
                    "device_name": row["device_name"],
                    "bound_at": row["bound_at"],
                    "last_connected": row["last_connected"],
                    "status": row["status"]
                }
        return None
    
    def get_device_user(self, device_id: str) -> Optional[str]:
        """根据设备ID获取绑定的用户ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id FROM device_bindings
                WHERE device_id = ? AND status = 'active'
            """, (device_id,))
            
            row = cursor.fetchone()
            return row["user_id"] if row else None
    
    def get_user_by_fingerprint(self, device_fingerprint: str) -> Optional[str]:
        """根据设备指纹获取绑定的用户ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, device_id FROM device_bindings
                WHERE device_fingerprint = ? AND status = 'active'
            """, (device_fingerprint,))
            
            row = cursor.fetchone()
            if row:
                return row["user_id"], row["device_id"]
            return None, None
    
    def verify_device_fingerprint(self, device_fingerprint: str) -> Optional[str]:
        """验证设备指纹并返回绑定的用户ID
        
        Args:
            device_fingerprint: 设备指纹
            
        Returns:
            绑定的用户ID，未绑定返回 None
        """
        user_id, device_id = self.get_user_by_fingerprint(device_fingerprint)
        return user_id
    
    def update_device_last_connected(self, device_id: str):
        """更新设备最后连接时间"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE device_bindings SET last_connected = ?
                WHERE device_id = ? AND status = 'active'
            """, (datetime.now().isoformat(), device_id))
            conn.commit()
    
    def unbind_device(self, user_id: str) -> bool:
        """解绑设备"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE device_bindings SET status = 'inactive'
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ===== [建议D] Token 吊销管理 =====
    
    def revoke_tokens(self, user_id: str) -> bool:
        """吊销用户所有 Token
        
        设置吊销时间戳为当前 UTC 时间。
        此时间戳之前签发的所有 access_token/refresh_token 将不再有效。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            是否成功吊销
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET tokens_revoked_at = ?
                WHERE user_id = ?
            """, (datetime.utcnow().isoformat(), user_id))
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                logger.info(f"已吊销用户 {user_id[:8]} 的所有 token")
            return success
    
    def is_token_revoked(self, user_id: str, token_iat: float) -> bool:
        """检查 Token 是否已被吊销
        
        Args:
            user_id: 用户 ID
            token_iat: token 的签发时间（Unix 时间戳）
            
        Returns:
            True 表示已吊销
        """
        user = self.find_by_id(user_id)
        if not user or not user.tokens_revoked_at:
            return False
        # token_iat 是 Unix 时间戳（整数），tokens_revoked_at 是 UTC datetime
        token_issued = datetime.utcfromtimestamp(float(token_iat))
        return token_issued <= user.tokens_revoked_at
