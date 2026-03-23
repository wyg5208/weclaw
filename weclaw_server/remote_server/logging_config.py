"""日志配置模块

为 WeClaw 远程服务器提供统一的日志配置，支持：
- 控制台和文件双路输出
- 按时间轮转（小时/天/周）
- 错误日志单独记录
- 可配置的日志格式
"""

import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    format_type: str = "detailed",
    rotation: str = "D",
    backup_count: int = 7,
    enable_console: bool = True,
    enable_file: bool = True,
    separate_error: bool = True,
) -> None:
    """设置统一的日志配置。
    
    Args:
        log_dir: 日志目录路径
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 日志格式类型 (simple, detailed)
        rotation: 轮转策略 (S=秒，M=分，H=时，D=天，W=周，midnight)
        backup_count: 保留的备份文件数量
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        separate_error: 是否单独记录错误日志
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除已有的 handler（避免重复）
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # 定义日志格式
    formats = {
        "simple": logging.Formatter("[%(levelname)s] %(name)s: %(message)s"),
        "detailed": logging.Formatter(
            "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ),
    }
    
    file_formatter = formats.get(format_type, formats["detailed"])
    console_formatter = formats.get("simple")
    
    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # 文件处理器（主日志）
    if enable_file:
        # 使用 TimedRotatingFileHandler 实现按时间轮转
        # when 参数：'S'=秒，'M'=分，'H'=时，'D'=天，'W'=周
        log_file = log_path / "remote_server.log"
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when=rotation,  # 使用字母代号而非字符串
            interval=1,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        file_handler.suffix = "_%Y-%m-%d.log"  # 备份文件后缀
        root_logger.addHandler(file_handler)
        
        # 错误日志单独记录
        if separate_error:
            error_log_file = log_path / f"error_{datetime.now().strftime('%Y-%m-%d')}.log"
            error_handler = TimedRotatingFileHandler(
                filename=error_log_file,
                when=rotation,  # 使用字母代号
                interval=1,
                backupCount=backup_count,
                encoding="utf-8"
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            error_handler.suffix = "_%Y-%m-%d.log"
            root_logger.addHandler(error_handler)
    
    # 记录配置完成信息
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    logger.info(f"日志目录：{log_path.absolute()}")
    logger.info(f"日志级别：{level}")
    logger.info(f"轮转策略：{rotation}")
    logger.info(f"保留天数：{backup_count}")
    if separate_error and enable_file:
        logger.info("错误日志已启用单独记录")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger。
    
    Args:
        name: logger 名称（通常使用 __name__）
    
    Returns:
        配置好的 Logger 实例
    """
    return logging.getLogger(name)
