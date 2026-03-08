#!/usr/bin/env python3
"""日志查看工具。

功能：
- 实时查看最新日志（类似 tail -f）
- 按级别过滤（只看 ERROR/WARNING）
- 按时间范围过滤
- 关键词搜索

使用示例：
    python scripts/view_logs.py              # 实时查看最新日志
    python scripts/view_logs.py --level ERROR  # 只看错误
    python scripts/view_logs.py --search "browser_use"  # 搜索关键词
    python scripts/view_logs.py --today      # 查看今天日志
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="WinClaw 日志查看工具")
    
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path.cwd() / "logs",
        help="日志目录路径 (默认：当前工作目录的 logs 文件夹)",
    )
    
    parser.add_argument(
        "--level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="只显示指定级别及以上的日志",
    )
    
    parser.add_argument(
        "--search",
        type=str,
        default=None,
        help="搜索包含关键词的日志行",
    )
    
    parser.add_argument(
        "--today",
        action="store_true",
        help="只查看今天的日志",
    )
    
    parser.add_argument(
        "--lines",
        type=int,
        default=50,
        help="初始显示的行数 (默认：50)",
    )
    
    parser.add_argument(
        "--follow",
        action="store_true",
        help="持续监控日志文件 (类似 tail -f)",
    )
    
    parser.add_argument(
        "--no-follow",
        action="store_true",
        help="不持续监控，只显示现有内容",
    )
    
    return parser.parse_args()


def get_log_files(log_dir: Path, today_only: bool = False) -> list[Path]:
    """获取日志文件列表。
    
    Args:
        log_dir: 日志目录
        today_only: 是否只返回今天的日志
        
    Returns:
        日志文件路径列表，按修改时间排序
    """
    if not log_dir.exists():
        return []
    
    log_files = []
    today = datetime.now().date()
    
    for f in log_dir.glob("*.log"):
        if f.name.startswith("error_"):
            continue  # 跳过错误日志（会在主日志中显示）
        
        if today_only:
            # 检查文件名是否包含今天的日期
            if today.strftime("%Y-%m-%d") not in f.name and f.name != "winclaw.log":
                continue
            
            # 或者检查文件修改时间
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime).date()
                if mtime != today:
                    continue
            except Exception:
                pass
        
        log_files.append(f)
    
    # 按修改时间排序，最新的在前
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return log_files


def filter_line(line: str, level: str | None = None, search: str | None = None) -> bool:
    """检查日志行是否满足过滤条件。
    
    Args:
        line: 日志行
        level: 日志级别过滤
        search: 关键词搜索
        
    Returns:
        True 表示应该显示此行
    """
    # 级别过滤
    if level:
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        try:
            # 查找日志行中的级别标记
            line_level = None
            for lvl in level_order:
                if lvl in line or f"[{lvl}]" in line or f"| {lvl} |" in line:
                    line_level = lvl
                    break
            
            if line_level is None:
                return False  # 无法识别级别，跳过
            
            # 只显示指定级别及以上
            if level_order.index(line_level) < level_order.index(level):
                return False
        except Exception:
            pass
    
    # 关键词搜索
    if search and search.lower() not in line.lower():
        return False
    
    return True


def read_log_lines(file_path: Path, num_lines: int = 50) -> list[str]:
    """读取文件最后 N 行。
    
    Args:
        file_path: 文件路径
        num_lines: 要读取的行数
        
    Returns:
        最后 N 行内容的列表
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-num_lines:] if len(lines) > num_lines else lines
    except Exception as e:
        return [f"[读取失败：{e}]"]


def view_logs(args):
    """查看日志的主函数。"""
    log_dir = args.log_dir
    
    if not log_dir.exists():
        print(f"[错误] 日志目录不存在：{log_dir}")
        print("请先运行 WinClaw 应用程序生成日志文件。")
        sys.exit(1)
    
    # 获取日志文件
    log_files = get_log_files(log_dir, today_only=args.today)
    
    if not log_files:
        print(f"[警告] 在 {log_dir} 目录下未找到日志文件")
        sys.exit(1)
    
    print(f"[信息] 找到 {len(log_files)} 个日志文件:")
    for i, lf in enumerate(log_files[:5], 1):  # 只显示前 5 个
        size_kb = lf.stat().st_size / 1024
        print(f"  {i}. {lf.name} ({size_kb:.1f} KB)")
    if len(log_files) > 5:
        print(f"  ... 还有 {len(log_files) - 5} 个文件")
    print()
    
    # 读取并显示日志
    main_log = log_files[0]  # 最新的日志
    print(f"=== 显示最新日志：{main_log.name} ===")
    print(f"级别过滤：{args.level or '无'}")
    print(f"关键词：{args.search or '无'}")
    print(f"初始行数：{args.lines}")
    print("=" * 60)
    print()
    
    # 显示初始内容
    lines = read_log_lines(main_log, args.lines)
    displayed_count = 0
    for line in lines:
        line = line.strip()
        if filter_line(line, level=args.level, search=args.search):
            print(line)
            displayed_count += 1
    
    if displayed_count == 0:
        print("[没有匹配的日志行]")
    
    print()
    print(f"[已显示 {displayed_count}/{len(lines)} 行]")
    
    # 持续监控
    if args.follow and not args.no_follow:
        print("\n[进入实时监控模式，按 Ctrl+C 退出]")
        print("-" * 60)
        
        try:
            # 定位到文件末尾
            with open(main_log, "r", encoding="utf-8") as f:
                f.seek(0, 2)  # 移动到文件末尾
                
                while True:
                    line = f.readline()
                    if line:
                        line = line.strip()
                        if filter_line(line, level=args.level, search=args.search):
                            print(line)
                        sys.stdout.flush()
                    else:
                        time.sleep(0.5)  # 等待新内容
        except KeyboardInterrupt:
            print("\n\n[退出实时监控]")


def main():
    """入口函数。"""
    args = parse_args()
    view_logs(args)


if __name__ == "__main__":
    main()
