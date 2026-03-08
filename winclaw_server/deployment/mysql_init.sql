-- WinClaw Remote Server MySQL 数据库初始化脚本
-- 适用于 MySQL 8.0+

-- 创建数据库
CREATE DATABASE IF NOT EXISTS winclaw 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE winclaw;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY COMMENT '用户唯一ID',
    username VARCHAR(32) UNIQUE NOT NULL COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希(bcrypt)',
    public_key TEXT COMMENT 'RSA公钥(可选)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_login DATETIME COMMENT '最后登录时间',
    is_active TINYINT DEFAULT 1 COMMENT '是否激活',
    device_fingerprint VARCHAR(255) COMMENT '设备指纹',
    settings JSON COMMENT '用户设置',
    login_attempts INT DEFAULT 0 COMMENT '登录尝试次数',
    locked_until DATETIME COMMENT '锁定截止时间',
    INDEX idx_users_username (username),
    INDEX idx_users_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY COMMENT '会话ID',
    user_id VARCHAR(36) NOT NULL COMMENT '用户ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_active DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活动时间',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '会话状态',
    message_count INT DEFAULT 0 COMMENT '消息数量',
    metadata JSON COMMENT '会话元数据',
    title VARCHAR(255) COMMENT '会话标题',
    INDEX idx_sessions_user (user_id),
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_last_active (last_active),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(36) PRIMARY KEY COMMENT '消息ID',
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
    role VARCHAR(20) NOT NULL COMMENT '角色(user/assistant/system)',
    content TEXT NOT NULL COMMENT '消息内容',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    metadata JSON COMMENT '消息元数据(如token数等)',
    parent_id VARCHAR(36) COMMENT '父消息ID(用于分支对话)',
    INDEX idx_messages_session (session_id),
    INDEX idx_messages_created (created_at),
    INDEX idx_messages_role (role),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- 附件表
CREATE TABLE IF NOT EXISTS attachments (
    attachment_id VARCHAR(36) PRIMARY KEY COMMENT '附件ID',
    message_id VARCHAR(36) NOT NULL COMMENT '消息ID',
    type VARCHAR(20) NOT NULL COMMENT '附件类型(image/audio/video/document)',
    filename VARCHAR(255) NOT NULL COMMENT '原始文件名',
    mime_type VARCHAR(100) NOT NULL COMMENT 'MIME类型',
    size_bytes INT NOT NULL COMMENT '文件大小(字节)',
    storage_path VARCHAR(500) NOT NULL COMMENT '存储路径',
    thumbnail_path VARCHAR(500) COMMENT '缩略图路径',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_attachments_message (message_id),
    INDEX idx_attachments_type (type),
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='附件表';

-- 工具调用记录表
CREATE TABLE IF NOT EXISTS tool_calls (
    call_id VARCHAR(36) PRIMARY KEY COMMENT '调用ID',
    message_id VARCHAR(36) NOT NULL COMMENT '消息ID',
    tool_name VARCHAR(50) NOT NULL COMMENT '工具名称',
    action VARCHAR(50) NOT NULL COMMENT '动作名称',
    arguments JSON COMMENT '调用参数',
    result TEXT COMMENT '返回结果',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态(pending/running/success/failed)',
    duration_ms INT COMMENT '执行时长(毫秒)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    completed_at DATETIME COMMENT '完成时间',
    error_message TEXT COMMENT '错误信息',
    INDEX idx_tool_calls_message (message_id),
    INDEX idx_tool_calls_status (status),
    INDEX idx_tool_calls_tool (tool_name),
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工具调用记录表';

-- 登录日志表
CREATE TABLE IF NOT EXISTS login_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) COMMENT '用户ID',
    username VARCHAR(32) COMMENT '登录用户名',
    ip_address VARCHAR(45) NOT NULL COMMENT 'IP地址',
    user_agent VARCHAR(500) COMMENT 'User-Agent',
    status VARCHAR(20) NOT NULL COMMENT '状态(success/failed/locked)',
    failure_reason VARCHAR(255) COMMENT '失败原因',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
    INDEX idx_login_logs_user (user_id),
    INDEX idx_login_logs_ip (ip_address),
    INDEX idx_login_logs_created (created_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登录日志表';

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(100) PRIMARY KEY COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置描述',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('max_sessions_per_user', '10', '每用户最大会话数'),
('max_messages_per_session', '1000', '每会话最大消息数'),
('max_attachment_size', '52428800', '最大附件大小(字节, 50MB)'),
('allowed_attachment_types', '["image/jpeg","image/png","image/gif","audio/mp3","audio/wav","video/mp4","application/pdf"]', '允许的附件类型'),
('rate_limit_requests', '100', '每分钟请求限制'),
('token_expire_minutes', '15', 'Access Token过期时间(分钟)'),
('refresh_token_expire_days', '7', 'Refresh Token过期时间(天)'),
('login_max_attempts', '5', '最大登录尝试次数'),
('login_lock_minutes', '30', '登录锁定时间(分钟)')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 创建视图 - 用户会话统计
CREATE OR REPLACE VIEW v_user_session_stats AS
SELECT 
    u.user_id,
    u.username,
    COUNT(DISTINCT s.session_id) as total_sessions,
    COUNT(m.message_id) as total_messages,
    MAX(s.last_active) as last_activity,
    SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) as user_messages,
    SUM(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages
FROM users u
LEFT JOIN sessions s ON u.user_id = s.user_id
LEFT JOIN messages m ON s.session_id = m.session_id
GROUP BY u.user_id, u.username;

-- 创建视图 - 会话详情
CREATE OR REPLACE VIEW v_session_details AS
SELECT 
    s.session_id,
    s.user_id,
    u.username,
    s.title,
    s.status,
    s.message_count,
    s.created_at,
    s.last_active,
    TIMESTAMPDIFF(MINUTE, s.created_at, s.last_active) as duration_minutes
FROM sessions s
JOIN users u ON s.user_id = u.user_id;

-- 创建存储过程 - 清理过期会话
DELIMITER //
CREATE PROCEDURE sp_cleanup_expired_sessions(IN days_old INT)
BEGIN
    DELETE FROM sessions 
    WHERE last_active < DATE_SUB(NOW(), INTERVAL days_old DAY)
    AND status = 'inactive';
    
    SELECT ROW_COUNT() as deleted_sessions;
END //
DELIMITER ;

-- 创建存储过程 - 用户登录验证
DELIMITER //
CREATE PROCEDURE sp_check_login_lock(IN p_username VARCHAR(32))
BEGIN
    SELECT 
        user_id,
        login_attempts,
        locked_until,
        CASE 
            WHEN locked_until IS NULL THEN 0
            WHEN locked_until > NOW() THEN 1
            ELSE 0
        END as is_locked
    FROM users
    WHERE username = p_username;
END //
DELIMITER ;

-- 创建事件 - 每日清理任务 (需要开启事件调度器)
-- SET GLOBAL event_scheduler = ON;

CREATE EVENT IF NOT EXISTS evt_daily_cleanup
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    -- 清理30天前的非活跃会话
    CALL sp_cleanup_expired_sessions(30);
    
    -- 清理90天前的登录日志
    DELETE FROM login_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
END;

-- 创建专用用户 (生产环境推荐)
-- CREATE USER 'winclaw_app'@'%' IDENTIFIED BY 'YourStrongPassword123!';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON winclaw.* TO 'winclaw_app'@'%';
-- FLUSH PRIVILEGES;

-- 完成提示
SELECT 'WinClaw MySQL 数据库初始化完成!' as message;
