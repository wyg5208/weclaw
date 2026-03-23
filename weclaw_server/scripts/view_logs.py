#!/usr/bin/env python3
"""日志查看脚本

提供便捷的日志查看功能：
- 实时查看最新日志（类似 tail -f）
- 按级别过滤
- 按时间范围过滤
- 关键词搜索
- 查看 PWA 上报日志
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="WinClaw 服务器日志查看工具")
    
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="日志目录路径 (默认：logs)"
    )
    
    parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="显示最后 N 行日志 (默认：100)"
    )
    
    parser.add_argument(
        "--level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="只显示指定级别及以上的日志"
    )
    
    parser.add_argument(
        "--search",
        type=str,
        help="搜索包含关键词的日志"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        choices=["server", "pwa"],
        default="server",
        help="日志来源 (默认：server)"
    )
    
    parser.add_argument(
        "--follow",
        action="store_true",
        help="持续跟踪日志更新 (类似 tail -f)"
    )
    
    parser.add_argument(
        "--today",
        action="store_true",
        help="只看今天的日志"
    )
    
    return parser.parse_args()


def get_log_files(log_dir: str, source: str, today_only: bool = False) -> list[Path]:
    """获取日志文件列表"""
    log_path = Path(log_dir)
    
    if not log_path.exists():
        print(f"[错误] 日志目录不存在：{log_path}", file=sys.stderr)
        sys.exit(1)
    
    # 根据来源选择文件模式
    if source == "pwa":
        pattern = "*pwa*.log"
    else:
        pattern = "remote_server*.log"
    
    # 获取所有匹配的日志文件
    if today_only:
        today_str = datetime.now().strftime("%Y-%m-%d")
        files = [
            f for f in log_path.glob(pattern)
            if today_str in f.name or f.name.endswith(".log")
        ]
    else:
        files = list(log_path.glob(pattern))
    
    # 按修改时间排序
    return sorted(files, key=lambda f: f.stat().st_mtime)


def filter_line(line: str, level: str = None, search: str = None) -> bool:
    """检查日志行是否应该显示"""
    # 级别过滤
    if level:
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        line_level = None
        
        for lvl in level_order:
            if lvl in line.upper():
                line_level = lvl
                break
        
        if line_level and level_order.index(line_level) < level_order.index(level):
            return False
    
    # 关键词搜索
    if search and search.lower() not in line.lower():
        return False
    
    return True


def read_log_file(file_path: Path, lines: int = None) -> list[str]:
    """读取日志文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
            if lines:
                return all_lines[-lines:]
            return all_lines
    except Exception as e:
        print(f"[警告] 读取文件失败 {file_path}: {e}", file=sys.stderr)
        return []


def display_logs(lines: list[str], file_name: str = ""):
    """显示日志"""
    for line in lines:
        # 如果是多个文件，显示文件名
        if file_name:
            print(f"[{file_name}] {line}", end='')
        else:
            print(line, end='')


def follow_logs(log_files: list[Path], level: str = None, search: str = None):
    """持续跟踪日志更新"""
    if not log_files:
        print("[提示] 未找到日志文件", file=sys.stderr)
        return
    
    # 打开所有文件
    files = [open(f, 'r', encoding='utf-8') for f in log_files]
    
    try:
        positions = [0] * len(files)
        
        while True:
            for i, (file_obj, log_file) in enumerate(zip(files, log_files)):
                # 移动到上次位置
                file_obj.seek(positions[i])
                
                # 读取新行
                new_lines = file_obj.readlines()
                positions[i] = file_obj.tell()
                
                # 显示过滤后的日志
                for line in new_lines:
                    if filter_line(line, level, search):
                        display_logs([line], log_file.name)
            
            # 等待一段时间
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[提示] 停止跟踪日志")
    finally:
        for f in files:
            f.close()


def main():
    """主函数"""
    args = parse_args()
    
    # 获取日志文件
    log_files = get_log_files(
        args.log_dir,
        args.source,
        args.today
    )
    
    if not log_files:
        print(f"[错误] 未找到日志文件", file=sys.stderr)
        sys.exit(1)
    
    # 如果只查看最新文件
    if not args.follow:
        # 读取最新的日志文件
        latest_file = log_files[-1]
        lines = read_log_file(latest_file, args.tail)
        
        # 过滤并显示
        filtered_lines = [
            line for line in lines
            if filter_line(line, args.level, args.search)
        ]
        
        display_logs(filtered_lines)
    
    # 持续跟踪模式
    else:
        print(f"[信息] 开始跟踪日志 (来源={args.source}, 级别={args.level or 'ALL'})")
        if args.search:
            print(f"[信息] 搜索关键词：{args.search}")
        print("-" * 60)
        
        follow_logs(log_files, args.level, args.search)


if __name__ == "__main__":
    main()
