/**
 * PWA 前端日志工具类
 * 
 * 功能：
 * - 统一的日志记录接口（debug, info, warn, error）
 * - 支持日志级别控制
 * - 自动上报日志到后端服务器
 * - 离线缓存机制
 * - 隐私信息过滤
 */

// 日志级别枚举
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

// 日志条目结构
export interface LogEntry {
  level: string;
  message: string;
  timestamp: string;
  context?: Record<string, any>;
  url: string;
  sessionId: string;
  userId?: string;
}

// 日志配置
interface LoggerConfig {
  logLevel: LogLevel;
  enableReporting: boolean;
  reportInterval: number;
  batchSize: number;
  serverUrl: string;
}

// 默认配置
const defaultConfig: LoggerConfig = {
  logLevel: LogLevel.INFO,
  enableReporting: true,
  reportInterval: 5000, // 5 秒
  batchSize: 20,
  serverUrl: '/api/logs/pwa',
};

class LoggerClass {
  private config: LoggerConfig;
  private logBuffer: LogEntry[] = [];
  private reportTimer: NodeJS.Timeout | null = null;
  private sessionId: string;

  constructor() {
    this.config = this.loadConfig();
    this.sessionId = this.generateSessionId();
    
    // 启动定时上报
    if (this.config.enableReporting) {
      this.startReportTimer();
    }

    // 页面关闭前上报剩余日志
    window.addEventListener('beforeunload', () => {
      this.flushLogs();
    });

    // 监听可见性变化，页面隐藏时立即上报
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.flushLogs();
      }
    });
  }

  /**
   * 加载配置（从环境变量或默认值）
   */
  private loadConfig(): LoggerConfig {
    const logLevelStr = import.meta.env.VITE_LOG_LEVEL || 'info';
    const logLevelMap: Record<string, LogLevel> = {
      debug: LogLevel.DEBUG,
      info: LogLevel.INFO,
      warn: LogLevel.WARN,
      error: LogLevel.ERROR,
    };

    return {
      logLevel: logLevelMap[logLevelStr.toLowerCase()] || LogLevel.INFO,
      enableReporting: import.meta.env.VITE_ENABLE_LOG_REPORTING !== 'false',
      reportInterval: parseInt(import.meta.env.VITE_LOG_REPORT_INTERVAL || '5000'),
      batchSize: parseInt(import.meta.env.VITE_LOG_BATCH_SIZE || '20'),
      serverUrl: '/api/logs/pwa',
    };
  }

  /**
   * 生成会话 ID
   */
  private generateSessionId(): string {
    const stored = sessionStorage.getItem('session_id');
    if (stored) return stored;

    const newId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    sessionStorage.setItem('session_id', newId);
    return newId;
  }

  /**
   * 启动定时上报
   */
  private startReportTimer(): void {
    if (this.reportTimer) {
      clearInterval(this.reportTimer);
    }

    this.reportTimer = setInterval(() => {
      this.flushLogs();
    }, this.config.reportInterval);
  }

  /**
   * 记录日志
   */
  private log(level: LogLevel, levelStr: string, message: string, context?: Record<string, any>): void {
    // 检查日志级别
    if (level < this.config.logLevel) {
      return;
    }

    // 控制台输出
    const consoleMethod = levelStr.toLowerCase() as 'debug' | 'info' | 'warn' | 'error';
    const consoleArgs = [`[${levelStr}] ${message}`, context || ''];
    (console as any)[consoleMethod](...consoleArgs);

    // 构建日志条目
    const entry: LogEntry = {
      level: levelStr,
      message,
      timestamp: new Date().toISOString(),
      context: this.sanitizeContext(context),
      url: window.location.href,
      sessionId: this.sessionId,
      userId: this.getUserId(),
    };

    // 添加到缓冲区
    this.logBuffer.push(entry);

    // ERROR 级别立即上报
    if (level === LogLevel.ERROR && this.config.enableReporting) {
      this.flushLogs();
    }
    // 批量上报
    else if (this.logBuffer.length >= this.config.batchSize && this.config.enableReporting) {
      this.flushLogs();
    }
  }

  /**
   * 过滤上下文中的敏感信息
   */
  private sanitizeContext(context?: Record<string, any>): Record<string, any> {
    if (!context) return {};

    const sensitiveKeys = ['password', 'token', 'secret', 'key', 'auth', 'credential'];
    const sanitized: Record<string, any> = {};

    for (const [key, value] of Object.entries(context)) {
      const lowerKey = key.toLowerCase();
      if (sensitiveKeys.some(sk => lowerKey.includes(sk))) {
        sanitized[key] = '[REDACTED]';
      } else {
        // 深拷贝避免引用问题
        try {
          sanitized[key] = typeof value === 'object' ? JSON.parse(JSON.stringify(value)) : value;
        } catch {
          sanitized[key] = '[Circular Reference]';
        }
      }
    }

    return sanitized;
  }

  /**
   * 获取用户 ID（如果已登录）
   */
  private getUserId(): string | undefined {
    try {
      const userStr = localStorage.getItem('user_info');
      if (!userStr) return undefined;

      const user = JSON.parse(userStr);
      return user.id || user.user_id;
    } catch {
      return undefined;
    }
  }

  /**
   * 上报日志到服务器
   */
  private async flushLogs(): Promise<void> {
    if (this.logBuffer.length === 0 || !this.config.enableReporting) {
      return;
    }

    const logsToSend = [...this.logBuffer];
    this.logBuffer = [];

    try {
      await fetch(this.config.serverUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ logs: logsToSend }),
      });
    } catch (error) {
      // 上报失败，将日志存回缓冲区（下次再试）
      this.logBuffer.unshift(...logsToSend);
      
      // 如果缓冲区太大，丢弃最早的日志
      if (this.logBuffer.length > 100) {
        this.logBuffer = this.logBuffer.slice(0, 100);
      }

      console.error('[Logger] 日志上报失败:', error);
    }
  }

  // ========== 公共方法 ==========

  debug(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.DEBUG, 'DEBUG', message, context);
  }

  info(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.INFO, 'INFO', message, context);
  }

  warn(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.WARN, 'WARN', message, context);
  }

  error(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.ERROR, 'ERROR', message, context);
  }

  /**
   * 设置日志级别
   */
  setLogLevel(level: LogLevel): void {
    this.config.logLevel = level;
  }

  /**
   * 获取当前会话 ID
   */
  getSessionId(): string {
    return this.sessionId;
  }
}

// 导出单例
export const logger = new LoggerClass();
