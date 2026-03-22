"""Email 工具 — 邮箱管理（收发邮件）。

支持动作：
- add_email_account: 添加邮箱账户（自动检测 provider、连接测试）
- query_email_accounts: 查询已配置的邮箱账户
- fetch_emails: 收取新邮件
- query_emails: 查询本地邮件缓存
- get_email_detail: 获取单封邮件完整正文
- send_email: 发送邮件

支持邮箱：126 / 163 / QQ / 新浪（4种域名）
存储位置：~/.winclaw/winclaw_tools.db（email_accounts + emails 表）
密码安全：keyring（Windows DPAPI）加密存储
"""

from __future__ import annotations

import imaplib
import json
import logging
import smtplib
import socket
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from email import policy
from email.header import decode_header as _decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Any, Generator

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".winclaw" / "winclaw_tools.db"

# IMAP/SMTP 连接超时（秒）
_CONNECT_TIMEOUT = 15

# keyring 服务名
_KEYRING_SERVICE = "winclaw-email"

# ------------------------------------------------------------------
# 邮箱提供商预置配置
# ------------------------------------------------------------------

# IMAP 已发送文件夹名称映射（国内邮箱名称各异）
_SENT_FOLDER_NAMES: dict[str, str] = {
    "126": "&XfJT0ZAB-",           # 126 已发送
    "163": "&XfJT0ZAB-",           # 163 已发送
    "qq":  "Sent Messages",         # QQ 已发送
    "sina": "&XfJT0ZAB-",          # 新浪 已发送
}

EMAIL_PROVIDERS: dict[str, dict[str, Any]] = {
    "126": {
        "name": "126邮箱",
        "imap_host": "imap.126.com", "imap_port": 993,
        "smtp_host": "smtp.126.com", "smtp_port": 465,
        "use_ssl": True,
        "need_imap_id": True,
    },
    "163": {
        "name": "163邮箱",
        "imap_host": "imap.163.com", "imap_port": 993,
        "smtp_host": "smtp.163.com", "smtp_port": 465,
        "use_ssl": True,
        "need_imap_id": True,
    },
    "qq": {
        "name": "QQ邮箱",
        "imap_host": "imap.qq.com", "imap_port": 993,
        "smtp_host": "smtp.qq.com", "smtp_port": 465,
        "use_ssl": True,
        "need_imap_id": False,
    },
    "sina": {
        "name": "新浪邮箱",
        "imap_port": 993, "smtp_port": 465, "use_ssl": True,
        "need_imap_id": False,
        "domains": {
            "sina.com":     {"imap": "imap.sina.com",     "smtp": "smtp.sina.com"},
            "sina.cn":      {"imap": "imap.sina.cn",      "smtp": "smtp.sina.cn"},
            "vip.sina.com": {"imap": "imap.vip.sina.com", "smtp": "smtp.vip.sina.com"},
            "vip.sina.cn":  {"imap": "imap.vip.sina.cn",  "smtp": "smtp.vip.sina.cn"},
        },
    },
}

# 域名 → provider 映射（长域名优先匹配）
_DOMAIN_MAP: dict[str, str] = {
    "126.com": "126",
    "163.com": "163",
    "qq.com": "qq",
    "vip.sina.com": "sina",
    "vip.sina.cn": "sina",
    "sina.com": "sina",
    "sina.cn": "sina",
}

# charset 降级链
_CHARSET_FALLBACKS = ("utf-8", "gbk", "gb2312", "gb18030", "latin-1")


class EmailTool(BaseTool):
    """邮件管理工具。

    支持邮箱账户管理、邮件收发，数据存储到
    ~/.winclaw/winclaw_tools.db 的 email_accounts + emails 表。
    密码通过 keyring（Windows DPAPI）安全存储。
    """

    name = "email"
    emoji = "📧"
    title = "邮件管理"
    description = "管理邮箱账户、收取和发送邮件，支持 126/163/QQ/新浪邮箱（请使用客户端授权密码）"
    timeout = 60  # 邮件涉及网络 I/O，高于默认值

    def __init__(self, db_path: str = ""):
        super().__init__()
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._db_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """初始化 email_accounts + emails 表。"""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_accounts (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_address   TEXT NOT NULL UNIQUE,
                    provider        TEXT NOT NULL,
                    auth_credential TEXT NOT NULL,
                    imap_host       TEXT NOT NULL,
                    imap_port       INTEGER DEFAULT 993,
                    smtp_host       TEXT NOT NULL,
                    smtp_port       INTEGER DEFAULT 465,
                    use_ssl         INTEGER DEFAULT 1,
                    is_active       INTEGER DEFAULT 1,
                    last_sync_time  TEXT,
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id      INTEGER NOT NULL REFERENCES email_accounts(id),
                    message_id      TEXT UNIQUE,
                    subject         TEXT,
                    sender          TEXT,
                    recipients      TEXT,
                    date            TEXT,
                    body_text       TEXT,
                    body_html       TEXT,
                    is_read         INTEGER DEFAULT 0,
                    folder          TEXT DEFAULT 'INBOX',
                    has_attachment  INTEGER DEFAULT 0,
                    created_at      TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_email_account ON emails(account_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_email_date ON emails(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_email_msgid ON emails(message_id)")
            conn.commit()

    # ------------------------------------------------------------------
    # keyring 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _save_password(email_address: str, password: str) -> bool:
        """将授权密码存入 keyring。"""
        try:
            import keyring
            keyring.set_password(_KEYRING_SERVICE, email_address, password)
            logger.info("已保存邮箱密码: %s", email_address)
            return True
        except Exception as e:
            logger.error("保存邮箱密码失败 %s: %s", email_address, e)
            return False

    @staticmethod
    def _load_password(email_address: str) -> str | None:
        """从 keyring 读取授权密码。"""
        try:
            import keyring
            return keyring.get_password(_KEYRING_SERVICE, email_address)
        except Exception as e:
            logger.error("读取邮箱密码失败 %s: %s", email_address, e)
            return None

    @staticmethod
    def _delete_password(email_address: str) -> bool:
        """从 keyring 删除授权密码。"""
        try:
            import keyring
            keyring.delete_password(_KEYRING_SERVICE, email_address)
            logger.info("已删除邮箱密码: %s", email_address)
            return True
        except Exception as e:
            logger.error("删除邮箱密码失败 %s: %s", email_address, e)
            return False

    # ------------------------------------------------------------------
    # Provider 检测与配置解析
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_provider(email_address: str) -> tuple[str, dict[str, Any]]:
        """根据邮箱地址自动检测 provider 并返回配置。"""
        domain = email_address.split("@")[1].lower()
        # 先匹配长域名再匹配短域名
        for d in sorted(_DOMAIN_MAP, key=len, reverse=True):
            if domain == d:
                provider_key = _DOMAIN_MAP[d]
                config = EmailTool._resolve_config(provider_key, domain)
                return provider_key, config
        raise ValueError(f"不支持的邮箱域名: {domain}，目前支持 126/163/QQ/新浪")

    @staticmethod
    def _resolve_config(provider_key: str, domain: str) -> dict[str, Any]:
        """解析完整的 IMAP/SMTP 配置（新浪需要按域名匹配）。"""
        provider = EMAIL_PROVIDERS[provider_key]
        config: dict[str, Any] = {
            "name": provider["name"],
            "imap_port": provider["imap_port"],
            "smtp_port": provider["smtp_port"],
            "use_ssl": provider["use_ssl"],
            "need_imap_id": provider["need_imap_id"],
        }
        if "domains" in provider:
            # 新浪：按域名查找
            domain_cfg = provider["domains"].get(domain)
            if domain_cfg:
                config["imap_host"] = domain_cfg["imap"]
                config["smtp_host"] = domain_cfg["smtp"]
            else:
                # 默认使用 sina.com
                fallback = provider["domains"]["sina.com"]
                config["imap_host"] = fallback["imap"]
                config["smtp_host"] = fallback["smtp"]
        else:
            config["imap_host"] = provider["imap_host"]
            config["smtp_host"] = provider["smtp_host"]
        return config

    # ------------------------------------------------------------------
    # IMAP ID 双重备用机制
    # ------------------------------------------------------------------

    @staticmethod
    def _send_imap_id(imap: imaplib.IMAP4_SSL) -> None:
        """发送 IMAP ID 命令（126/163 官方要求）。

        执行时序：login() -> _send_imap_id() -> select('INBOX')
        """
        id_params = '("name" "WeClaw" "version" "2.12.0" "vendor" "WeClaw")'
        try:
            # 方法1（推荐）：使用 _command
            typ, dat = imap._command('ID', id_params)
            imap._command_complete('ID', typ)
            logger.info("IMAP ID 命令成功（_command）: %s", typ)
        except Exception as e:
            logger.warning("_command 方式失败: %s，尝试手动发送", e)
            try:
                # 方法2（备用）：手动构造 IMAP 命令
                tag = imap._new_tag().decode()
                id_line = f'{tag} ID {id_params}\r\n'
                imap.send(id_line.encode('utf-8'))
                while True:
                    line = imap.readline().decode('utf-8', errors='ignore')
                    if line.startswith(tag):
                        if ' OK ' in line:
                            logger.info("IMAP ID 命令成功（手动）")
                        else:
                            logger.warning("IMAP ID 手动发送返回非 OK: %s", line.strip())
                        break
            except Exception as e2:
                # ID 失败不中断流程，继续尝试 SELECT
                logger.warning("IMAP ID 手动发送也失败: %s", e2)

    # ------------------------------------------------------------------
    # 邮件解码辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_subject(raw_subject: str | None) -> str:
        """解码邮件主题（RFC 2047）。"""
        if not raw_subject:
            return "(无主题)"
        parts = _decode_header(raw_subject)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                if charset:
                    try:
                        decoded.append(part.decode(charset, errors='replace'))
                    except (LookupError, UnicodeDecodeError):
                        decoded.append(part.decode('utf-8', errors='replace'))
                else:
                    decoded.append(part.decode('utf-8', errors='replace'))
            else:
                decoded.append(str(part))
        return "".join(decoded)

    @staticmethod
    def _safe_decode(payload: bytes, declared_charset: str | None) -> str:
        """使用 charset 降级链安全解码邮件内容。"""
        charsets: list[str] = []
        if declared_charset:
            charsets.append(declared_charset)
        charsets.extend(c for c in _CHARSET_FALLBACKS if c != declared_charset)
        for cs in charsets:
            try:
                return payload.decode(cs)
            except (UnicodeDecodeError, LookupError):
                continue
        return payload.decode('latin-1', errors='replace')

    @staticmethod
    def _extract_body(msg) -> tuple[str, str, bool]:
        """提取邮件正文和附件信息。

        Returns:
            (body_text, body_html, has_attachment)
        """
        body_text = ""
        body_html = ""
        has_attachment = False

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()
                if disposition == "attachment":
                    has_attachment = True
                    continue
                if content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset()
                        body_text = EmailTool._safe_decode(payload, charset)
                elif content_type == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset()
                        body_html = EmailTool._safe_decode(payload, charset)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset()
                content_type = msg.get_content_type()
                text = EmailTool._safe_decode(payload, charset)
                if content_type == "text/html":
                    body_html = text
                else:
                    body_text = text

        return body_text, body_html, has_attachment

    # ------------------------------------------------------------------
    # IMAP 连接辅助
    # ------------------------------------------------------------------

    def _create_imap_connection(
        self, account: dict[str, Any], folder: str = "INBOX"
    ) -> imaplib.IMAP4_SSL:
        """创建 IMAP 连接，含 login + IMAP ID + SELECT。

        Args:
            account: 账户信息字典
            folder: IMAP 文件夹名，默认 INBOX。常见值:
                    INBOX / Sent Messages / Drafts / &XfJT0ZAB- (已发送, 国内邮箱)
        """
        imap = imaplib.IMAP4_SSL(
            account["imap_host"],
            account["imap_port"],
            timeout=_CONNECT_TIMEOUT,
        )
        password = self._load_password(account["email_address"])
        if not password:
            raise ValueError(f"无法读取邮箱密码: {account['email_address']}")

        imap.login(account["email_address"], password)

        # 126/163 需要发送 IMAP ID
        provider = EMAIL_PROVIDERS.get(account["provider"], {})
        if provider.get("need_imap_id", False):
            self._send_imap_id(imap)

        imap.select(folder)
        return imap

    # ------------------------------------------------------------------
    # get_actions
    # ------------------------------------------------------------------

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="add_email_account",
                description="添加邮箱账户（使用客户端授权密码，非登录密码），自动检测类型并测试连接",
                parameters={
                    "email_address": {
                        "type": "string",
                        "description": "邮箱地址，如 user@163.com",
                    },
                    "auth_password": {
                        "type": "string",
                        "description": "客户端授权密码（非登录密码），需在邮箱设置中开启 IMAP 后获取",
                    },
                    "provider": {
                        "type": "string",
                        "description": "邮箱类型: 126/163/qq/sina（可选，默认自动检测）",
                    },
                },
                required_params=["email_address", "auth_password"],
            ),
            ActionDef(
                name="query_email_accounts",
                description="列出所有已配置的邮箱账户（不返回密码）",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="fetch_emails",
                description="从邮箱服务器收取新邮件到本地",
                parameters={
                    "account_id": {
                        "type": "integer",
                        "description": "邮箱账户 ID",
                    },
                    "folder": {
                        "type": "string",
                        "description": "IMAP 文件夹: INBOX(收件箱,默认) / SENT(已发送)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多收取邮件数量，默认 10",
                    },
                },
                required_params=["account_id"],
            ),
            ActionDef(
                name="query_emails",
                description="查询本地已缓存的邮件列表",
                parameters={
                    "account_id": {
                        "type": "integer",
                        "description": "邮箱账户 ID（可选，不填则查所有）",
                    },
                    "folder": {
                        "type": "string",
                        "description": "文件夹，默认 INBOX",
                    },
                    "is_read": {
                        "type": "integer",
                        "description": "是否已读: 0=未读, 1=已读（可选）",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，匹配主题和发件人",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数，默认 20",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="get_email_detail",
                description="获取单封邮件的完整正文内容，并自动标记为已读",
                parameters={
                    "email_id": {
                        "type": "integer",
                        "description": "邮件 ID",
                    },
                },
                required_params=["email_id"],
            ),
            ActionDef(
                name="send_email",
                description="通过已配置的邮箱账户发送邮件",
                parameters={
                    "account_id": {
                        "type": "integer",
                        "description": "发件邮箱账户 ID",
                    },
                    "to_addresses": {
                        "type": "string",
                        "description": "收件人地址，多个用逗号分隔",
                    },
                    "subject": {
                        "type": "string",
                        "description": "邮件主题",
                    },
                    "body": {
                        "type": "string",
                        "description": "邮件正文",
                    },
                    "cc": {
                        "type": "string",
                        "description": "抄送地址，多个用逗号分隔（可选）",
                    },
                },
                required_params=["account_id", "to_addresses", "subject", "body"],
            ),
        ]

    # ------------------------------------------------------------------
    # execute 分发
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        handlers = {
            "add_email_account": self._add_email_account,
            "query_email_accounts": self._query_email_accounts,
            "fetch_emails": self._fetch_emails,
            "query_emails": self._query_emails,
            "get_email_detail": self._get_email_detail,
            "send_email": self._send_email,
        }
        handler = handlers.get(action)
        if handler is None:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"不支持的动作: {action}")
        try:
            return handler(params)
        except socket.timeout:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="无法连接邮件服务器，请检查网络连接",
            )
        except ConnectionRefusedError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="邮件服务器拒绝连接，请检查网络或邮箱配置",
            )
        except Exception as e:
            error_msg = str(e)
            # 友好错误提示
            if "Unsafe Login" in error_msg:
                error_msg = "126/163 邮箱安全限制，请在邮箱设置中开启 IMAP 服务并允许第三方客户端"
            elif "LOGIN" in error_msg.upper() and ("NO" in error_msg.upper() or "FAIL" in error_msg.upper()):
                error_msg = f"认证失败，请确认使用的是客户端授权密码而非登录密码。原始错误: {error_msg}"
            logger.error("邮件操作失败: %s", e)
            return ToolResult(status=ToolResultStatus.ERROR, error=error_msg)

    # ------------------------------------------------------------------
    # 动作实现
    # ------------------------------------------------------------------

    def _add_email_account(self, params: dict[str, Any]) -> ToolResult:
        """添加邮箱账户。"""
        email_address = params.get("email_address", "").strip()
        auth_password = params.get("auth_password", "").strip()
        provider_hint = params.get("provider", "").strip()

        if not email_address or "@" not in email_address:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供有效的邮箱地址")
        if not auth_password:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供客户端授权密码")

        # 检查是否已存在
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM email_accounts WHERE email_address = ?",
                (email_address,),
            ).fetchone()
            if row:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"邮箱已存在 (ID: {row[0]})，无需重复添加",
                )

        # 检测 provider
        try:
            if provider_hint and provider_hint in EMAIL_PROVIDERS:
                domain = email_address.split("@")[1].lower()
                config = self._resolve_config(provider_hint, domain)
                provider_key = provider_hint
            else:
                provider_key, config = self._detect_provider(email_address)
        except ValueError as e:
            return ToolResult(status=ToolResultStatus.ERROR, error=str(e))

        imap_host = config["imap_host"]
        imap_port = config["imap_port"]
        smtp_host = config["smtp_host"]
        smtp_port = config["smtp_port"]

        # --- IMAP 连接测试 ---
        try:
            imap = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=_CONNECT_TIMEOUT)
            imap.login(email_address, auth_password)
            # 126/163 发送 IMAP ID
            if config.get("need_imap_id", False):
                self._send_imap_id(imap)
            imap.select("INBOX")
            imap.logout()
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "Unsafe Login" in error_msg:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="126/163 邮箱安全限制，请在邮箱设置中开启 IMAP 服务并允许第三方客户端",
                )
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"IMAP 连接测试失败，请确认使用的是客户端授权密码: {error_msg}",
            )

        # --- SMTP 连接测试 ---
        try:
            smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=_CONNECT_TIMEOUT)
            smtp.login(email_address, auth_password)
            smtp.quit()
        except smtplib.SMTPAuthenticationError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"SMTP 认证失败: {e}",
            )

        # --- 保存密码到 keyring ---
        if not self._save_password(email_address, auth_password):
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="密码保存到安全存储失败",
            )

        # --- 保存到数据库 ---
        credential_key = f"{_KEYRING_SERVICE}/{email_address}"
        now = datetime.now().isoformat()

        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO email_accounts (
                    email_address, provider, auth_credential,
                    imap_host, imap_port, smtp_host, smtp_port,
                    use_ssl, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
            """, (
                email_address, provider_key, credential_key,
                imap_host, imap_port, smtp_host, smtp_port,
                now, now,
            ))
            conn.commit()
            account_id = cursor.lastrowid

        output = (
            f"✅ 邮箱账户已添加 (ID: {account_id})\n"
            f"  📧 邮箱: {email_address}\n"
            f"  📦 类型: {config['name']} ({provider_key})\n"
            f"  📥 IMAP: {imap_host}:{imap_port} ✓\n"
            f"  📤 SMTP: {smtp_host}:{smtp_port} ✓\n"
            f"  🔐 密码已安全存储（keyring）"
        )

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "account_id": account_id,
                "email_address": email_address,
                "provider": provider_key,
            },
        )

    def _query_email_accounts(self, params: dict[str, Any]) -> ToolResult:
        """查询所有邮箱账户（安全字段过滤）。"""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT id, email_address, provider, is_active, last_sync_time, created_at
                FROM email_accounts
                ORDER BY id
            """).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="暂无邮箱账户，请使用 add_email_account 添加。",
                data={"accounts": []},
            )

        lines = [f"📧 邮箱账户 ({len(rows)} 个):"]
        accounts = []
        for row in rows:
            aid, email, provider, is_active, sync_time, created = row
            status = "✅" if is_active else "❌"
            sync_str = sync_time[:19] if sync_time else "从未同步"
            lines.append(f"  {status} ID:{aid} | {email} | {provider} | 最后同步: {sync_str}")
            accounts.append({
                "id": aid,
                "email_address": email,
                "provider": provider,
                "is_active": bool(is_active),
                "last_sync_time": sync_time,
                "created_at": created,
            })

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"accounts": accounts},
        )

    def _fetch_emails(self, params: dict[str, Any]) -> ToolResult:
        """从邮箱服务器收取新邮件。"""
        account_id = params.get("account_id")
        folder_param = params.get("folder", "INBOX").strip().upper()
        limit = min(params.get("limit", 10), 50)

        if account_id is None:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供 account_id")

        # 获取账户信息
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, email_address, provider, imap_host, imap_port "
                "FROM email_accounts WHERE id = ? AND is_active = 1",
                (account_id,),
            ).fetchone()

        if not row:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"邮箱账户不存在或已停用: ID {account_id}",
            )

        _, email_address, provider, imap_host, imap_port = row
        account = {
            "email_address": email_address,
            "provider": provider,
            "imap_host": imap_host,
            "imap_port": imap_port,
        }

        # 解析 folder：将用户友好名称映射为 IMAP 文件夹名
        if folder_param in ("SENT", "已发送"):
            imap_folder = _SENT_FOLDER_NAMES.get(provider, "Sent Messages")
            local_folder = "SENT"
        else:
            imap_folder = "INBOX"
            local_folder = "INBOX"

        # 连接 IMAP
        imap = self._create_imap_connection(account, folder=imap_folder)
        try:
            # 搜索邮件
            typ, data = imap.search(None, "ALL")
            if typ != "OK" or not data[0]:
                imap.logout()
                now = datetime.now().isoformat()
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE email_accounts SET last_sync_time = ?, updated_at = ? WHERE id = ?",
                        (now, now, account_id),
                    )
                    conn.commit()
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=f"📭 {local_folder} 文件夹为空，没有邮件。",
                    data={"fetched": 0, "folder": local_folder},
                )

            msg_ids = data[0].split()
            # 取最新的 limit 封
            msg_ids = msg_ids[-limit:]

            parser = BytesParser(policy=policy.compat32)
            fetched_count = 0
            skipped_count = 0

            for msg_id in reversed(msg_ids):
                typ, msg_data = imap.fetch(msg_id, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = parser.parsebytes(raw_email)

                # 提取 Message-ID（去重）
                message_id = msg.get("Message-ID", "").strip()

                # 检查是否已存在
                if message_id:
                    with self._conn() as conn:
                        existing = conn.execute(
                            "SELECT id FROM emails WHERE message_id = ?",
                            (message_id,),
                        ).fetchone()
                        if existing:
                            skipped_count += 1
                            continue

                # 解码主题
                subject = self._decode_subject(msg.get("Subject"))

                # 发件人
                sender_raw = msg.get("From", "")
                sender_name, sender_addr = parseaddr(sender_raw)
                if sender_name:
                    sender_name = self._decode_subject(sender_name)
                sender = f"{sender_name} <{sender_addr}>" if sender_name else sender_addr

                # 收件人
                recipients_raw = msg.get("To", "")
                recipients = [addr.strip() for addr in recipients_raw.split(",") if addr.strip()]

                # 日期
                date_str = msg.get("Date", "")
                try:
                    dt = parsedate_to_datetime(date_str)
                    date_formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_formatted = date_str

                # 正文
                body_text, body_html, has_attachment = self._extract_body(msg)

                # 存入数据库
                now = datetime.now().isoformat()
                with self._conn() as conn:
                    try:
                        conn.execute("""
                            INSERT INTO emails (
                                account_id, message_id, subject, sender,
                                recipients, date, body_text, body_html,
                                is_read, folder, has_attachment, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                        """, (
                            account_id, message_id or None, subject, sender,
                            json.dumps(recipients, ensure_ascii=False),
                            date_formatted, body_text, body_html,
                            local_folder, 1 if has_attachment else 0, now,
                        ))
                        conn.commit()
                        fetched_count += 1
                    except sqlite3.IntegrityError:
                        # message_id 重复，跳过
                        skipped_count += 1

            imap.logout()
        except Exception:
            try:
                imap.logout()
            except Exception:
                pass
            raise

        # 更新同步时间
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE email_accounts SET last_sync_time = ?, updated_at = ? WHERE id = ?",
                (now, now, account_id),
            )
            conn.commit()

        output = f"📬 邮件收取完成 ({email_address})\n"
        output += f"  新邮件: {fetched_count} 封\n"
        if skipped_count:
            output += f"  已存在跳过: {skipped_count} 封\n"
        output += f"  同步时间: {now[:19]}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "fetched": fetched_count,
                "skipped": skipped_count,
                "account_id": account_id,
            },
        )

    def _query_emails(self, params: dict[str, Any]) -> ToolResult:
        """查询本地邮件缓存。"""
        account_id = params.get("account_id")
        folder = params.get("folder", "INBOX").strip()
        is_read = params.get("is_read")
        keyword = params.get("keyword", "").strip()
        limit = min(params.get("limit", 20), 100)

        conditions: list[str] = []
        values: list[Any] = []

        if account_id is not None:
            conditions.append("account_id = ?")
            values.append(account_id)

        if folder:
            conditions.append("folder = ?")
            values.append(folder)

        if is_read is not None:
            conditions.append("is_read = ?")
            values.append(int(is_read))

        if keyword:
            conditions.append("(subject LIKE ? OR sender LIKE ?)")
            values.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        values.append(limit)

        sql = f"""
            SELECT id, account_id, subject, sender, date, is_read, has_attachment
            FROM emails
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT ?
        """

        with self._conn() as conn:
            rows = conn.execute(sql, values).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="📭 没有找到符合条件的邮件。",
                data={"emails": [], "count": 0},
            )

        lines = [f"📧 邮件列表 ({len(rows)} 封):"]
        email_list = []

        for row in rows:
            eid, aid, subject, sender, date, read, attachment = row
            read_icon = "📖" if read else "📩"
            attach_icon = " 📎" if attachment else ""
            # 截断长主题
            short_subject = (subject[:40] + "...") if subject and len(subject) > 40 else (subject or "(无主题)")
            # 截断长发件人
            short_sender = (sender[:30] + "...") if sender and len(sender) > 30 else (sender or "未知")
            date_str = date[:16] if date else "未知时间"

            lines.append(
                f"  {read_icon} ID:{eid} | {date_str} | {short_sender} | {short_subject}{attach_icon}"
            )
            email_list.append({
                "id": eid,
                "account_id": aid,
                "subject": subject,
                "sender": sender,
                "date": date,
                "is_read": bool(read),
                "has_attachment": bool(attachment),
            })

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"emails": email_list, "count": len(email_list)},
        )

    def _get_email_detail(self, params: dict[str, Any]) -> ToolResult:
        """获取单封邮件完整正文。"""
        email_id = params.get("email_id")
        if email_id is None:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供 email_id")

        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, account_id, subject, sender, recipients, date, "
                "body_text, body_html, is_read, folder, has_attachment "
                "FROM emails WHERE id = ?",
                (email_id,),
            ).fetchone()

        if not row:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"邮件不存在: ID {email_id}")

        (eid, aid, subject, sender, recipients_json, date,
         body_text, body_html, is_read, folder, has_attachment) = row

        # 自动标记已读
        if not is_read:
            with self._conn() as conn:
                conn.execute("UPDATE emails SET is_read = 1 WHERE id = ?", (email_id,))
                conn.commit()

        # 解析收件人
        try:
            recipients = json.loads(recipients_json) if recipients_json else []
        except json.JSONDecodeError:
            recipients = []

        # 正文：优先纯文本
        body = body_text or body_html or "(无正文内容)"
        # 截断过长正文
        original_len = len(body)
        if original_len > 5000:
            body = body[:5000] + f"\n\n... (正文已截断，共 {original_len} 字符)"

        lines = [
            f"📧 邮件详情 (ID: {eid})",
            f"  📌 主题: {subject}",
            f"  👤 发件人: {sender}",
            f"  👥 收件人: {', '.join(recipients) if recipients else '未知'}",
            f"  📅 日期: {date}",
            f"  📁 文件夹: {folder}",
        ]
        if has_attachment:
            lines.append("  📎 包含附件")
        lines.append(f"\n{'─' * 40}\n{body}")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={
                "id": eid,
                "subject": subject,
                "sender": sender,
                "recipients": recipients,
                "date": date,
                "body_text": body_text,
                "body_html": body_html,
                "has_attachment": bool(has_attachment),
            },
        )

    def _send_email(self, params: dict[str, Any]) -> ToolResult:
        """发送邮件。"""
        account_id = params.get("account_id")
        to_addresses = params.get("to_addresses", "").strip()
        subject = params.get("subject", "").strip()
        body = params.get("body", "").strip()
        cc = params.get("cc", "").strip()

        if account_id is None:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供 account_id")
        if not to_addresses:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供收件人地址")
        if not subject:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供邮件主题")
        if not body:
            return ToolResult(status=ToolResultStatus.ERROR, error="请提供邮件正文")

        # 获取账户信息
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, email_address, provider, smtp_host, smtp_port "
                "FROM email_accounts WHERE id = ? AND is_active = 1",
                (account_id,),
            ).fetchone()

        if not row:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"邮箱账户不存在或已停用: ID {account_id}",
            )

        _, email_address, provider, smtp_host, smtp_port = row

        # 读取密码
        password = self._load_password(email_address)
        if not password:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无法读取邮箱密码: {email_address}",
            )

        # 解析收件人
        to_list = [addr.strip() for addr in to_addresses.split(",") if addr.strip()]
        cc_list = [addr.strip() for addr in cc.split(",") if addr.strip()] if cc else []

        # 构造邮件
        msg = MIMEMultipart()
        msg["From"] = email_address
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 发送
        all_recipients = to_list + cc_list
        smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=_CONNECT_TIMEOUT)
        try:
            smtp.login(email_address, password)
            smtp.sendmail(email_address, all_recipients, msg.as_string())
        finally:
            smtp.quit()

        # 发送成功后保存到本地数据库（SENT 文件夹）
        now = datetime.now()
        now_iso = now.isoformat()
        with self._conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO emails (
                        account_id, message_id, subject, sender,
                        recipients, date, body_text, body_html,
                        is_read, folder, has_attachment, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '', 1, 'SENT', 0, ?)
                """, (
                    account_id, None, subject, email_address,
                    json.dumps(all_recipients, ensure_ascii=False),
                    now.strftime("%Y-%m-%d %H:%M:%S"), body, now_iso,
                ))
                conn.commit()
            except Exception as e:
                # 保存失败不影响发送结果
                logger.warning("已发送邮件保存到本地失败: %s", e)

        output = (
            f"✅ 邮件已发送\n"
            f"  📤 发件人: {email_address}\n"
            f"  📥 收件人: {', '.join(to_list)}\n"
        )
        if cc_list:
            output += f"  📋 抄送: {', '.join(cc_list)}\n"
        output += f"  📌 主题: {subject}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "sent": True,
                "from": email_address,
                "to": to_list,
                "cc": cc_list,
                "subject": subject,
            },
        )
