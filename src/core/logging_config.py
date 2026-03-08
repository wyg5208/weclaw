"""统一的日志配置模块。

提供全局的日志初始化功能，支持：
- 控制台和文件双路输出
- 日志轮转（按时间或大小）
- 可配置的日志级别和格式
- 错误日志单独记录
"""

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Literal


def setup_logging(
    level: str = "INFO",
    log_dir: Path | None = None,
    console_output: bool = True,
    file_output: bool = True,
    rotation: Literal["hourly", "daily", "weekly", "size"] = "daily",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 7,
    format_type: Literal["simple", "detailed", "json"] = "detailed",
    error_log_separate: bool = True,
) -> None:
    """设置统一的日志配置。

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_dir: 日志目录路径，None 则不启用文件日志
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        rotation: 日志轮转策略
            - hourly: 每小时轮转
            - daily: 每天轮转
            - weekly: 每周轮转
            - size: 按大小轮转
        max_bytes: 单个日志文件最大字节数（仅在 rotation="size" 时有效）
        backup_count: 保留的备份文件数量
        format_type: 日志格式类型
            - simple: 简单格式 [LEVEL] message
            - detailed: 详细格式 时间 | 模块 | 级别 | 消息
            - json: JSON 格式（待实现）
        error_log_separate: 是否单独记录错误日志
    """
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清空现有的 handler（避免重复）
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 日志格式
    formatters = {
        "simple": logging.Formatter(
            fmt="[%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        ),
        "detailed": logging.Formatter(
            fmt="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
        "json": None,  # TODO: 实现 JSON 格式
    }

    formatter = formatters.get(format_type, formatters["detailed"])
    if formatter is None:
        formatter = formatters["detailed"]

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if file_output and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # 主日志文件路径
        main_log_path = log_dir / "winclaw.log"

        # 根据轮转策略创建处理器
        if rotation == "size":
            file_handler = RotatingFileHandler(
                main_log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        elif rotation in ("hourly", "daily", "weekly"):
            interval_map = {
                "hourly": ("H", 1),
                "daily": ("D", 1),
                "weekly": ("W0", 1),  # 周一
            }
            interval, step = interval_map.get(rotation, ("D", 1))
            file_handler = TimedRotatingFileHandler(
                main_log_path,
                when=interval,
                interval=step,
                backupCount=backup_count,
                encoding="utf-8",
            )
        else:
            # 默认使用大小轮转
            file_handler = RotatingFileHandler(
                main_log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )

        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 错误日志单独记录
        if error_log_separate:
            error_log_path = log_dir / f"error_{Path(main_log_path).stem}.log"
            error_handler = logging.FileHandler(error_log_path, encoding="utf-8")
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)

    # 记录日志系统初始化完成
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成：级别=%s, 目录=%s", level, log_dir)


# 便捷函数：从配置加载并设置日志
def setup_logging_from_config(config_dict: dict | None = None) -> None:
    """从配置字典设置日志。

    Args:
        config_dict: 配置字典，包含 logging 节的配置
    """
    if config_dict is None:
        config_dict = {}

    logging_cfg = config_dict.get("logging", {})

    # 解析日志目录
    log_dir_str = logging_cfg.get("log_dir", "logs")
    if log_dir_str:
        log_dir = Path.cwd() / log_dir_str
    else:
        log_dir = None

    # 解析其他配置
    setup_logging(
        level=logging_cfg.get("level", "INFO"),
        log_dir=log_dir,
        console_output=logging_cfg.get("enable_console", True),
        file_output=logging_cfg.get("enable_file_log", True),
        rotation=logging_cfg.get("rotation", "daily"),
        max_bytes=logging_cfg.get("max_file_size", 10 * 1024 * 1024),
        backup_count=logging_cfg.get("backup_count", 7),
        format_type=logging_cfg.get("format", "detailed"),
        error_log_separate=logging_cfg.get("error_log_separate", True),
    )
