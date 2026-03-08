#!/usr/bin/env python3
"""日志清理工具。

功能：
- 清理超过 N 天的日志
- 压缩旧日志到 zip
- 显示日志目录占用空间

使用示例：
    python scripts/cleanup_logs.py              # 预览要清理的文件
    python scripts/cleanup_logs.py --days 7     # 清理 7 天前的日志
    python scripts/cleanup_logs.py --compress   # 压缩旧日志
    python scripts/cleanup_logs.py --execute    # 执行清理（默认只是预览）
"""

import argparse
import os
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="WinClaw 日志清理工具")
    
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path.cwd() / "logs",
        help="日志目录路径 (默认：当前工作目录的 logs 文件夹)",
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="保留最近 N 天的日志 (默认：7)",
    )
    
    parser.add_argument(
        "--compress",
        action="store_true",
        help="压缩旧日志到 zip 文件而不是删除",
    )
    
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行清理操作 (默认只是预览)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示将要进行的操作，不实际执行",
    )
    
    return parser.parse_args()


def get_log_files(log_dir: Path) -> list[Path]:
    """获取日志目录下的所有日志文件。
    
    Args:
        log_dir: 日志目录
        
    Returns:
        日志文件路径列表
    """
    if not log_dir.exists():
        return []
    
    log_files = []
    
    # 收集所有 .log 文件
    for f in log_dir.glob("*.log"):
        log_files.append(f)
    
    # 也收集归档目录中的文件
    archive_dir = log_dir / "archive"
    if archive_dir.exists():
        for f in archive_dir.glob("*.log"):
            log_files.append(f)
        for f in archive_dir.glob("*.zip"):
            log_files.append(f)
    
    return log_files


def get_file_age_days(file_path: Path) -> int:
    """获取文件年龄（天数）。
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件年龄（天数）
    """
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.days
    except Exception:
        return 0


def get_file_date_from_name(file_path: Path) -> datetime | None:
    """从文件名解析日期。
    
    支持格式：
    - winclaw_2026-02-26.log
    - error_winclaw_2026-02-26.log
    
    Args:
        file_path: 文件路径
        
    Returns:
        解析到的日期，失败返回 None
    """
    name = file_path.stem  # 不含扩展名
    
    # 尝试查找 YYYY-MM-DD 格式
    import re
    match = re.search(r"\d{4}-\d{2}-\d{2}", name)
    if match:
        try:
            return datetime.strptime(match.group(), "%Y-%m-%d")
        except ValueError:
            pass
    
    return None


def calculate_directory_size(dir_path: Path) -> int:
    """计算目录总大小（字节）。
    
    Args:
        dir_path: 目录路径
        
    Returns:
        总大小（字节）
    """
    total_size = 0
    if dir_path.exists():
        for f in dir_path.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size
    return total_size


def format_size(size_bytes: int) -> str:
    """格式化文件大小显示。
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的大小字符串
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def compress_file(file_path: Path, archive_dir: Path) -> Path | None:
    """压缩单个日志文件。
    
    Args:
        file_path: 要压缩的文件
        archive_dir: 归档目录
        
    Returns:
        压缩文件的路径，失败返回 None
    """
    try:
        zip_path = archive_dir / f"{file_path.name}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加文件到压缩包，使用相对路径
            zipf.write(file_path, arcname=file_path.name)
        
        # 压缩成功后删除原文件
        file_path.unlink()
        
        return zip_path
    except Exception as e:
        print(f"[错误] 压缩 {file_path.name} 失败：{e}")
        return None


def cleanup_logs(args):
    """清理日志的主函数。"""
    log_dir = args.log_dir
    
    if not log_dir.exists():
        print(f"[信息] 日志目录不存在：{log_dir}")
        print("无需清理。")
        sys.exit(0)
    
    # 显示日志目录信息
    total_size = calculate_directory_size(log_dir)
    print(f"[信息] 日志目录：{log_dir}")
    print(f"[信息] 当前占用：{format_size(total_size)}")
    print(f"[信息] 保留策略：{args.days} 天")
    print(f"[信息] 操作模式：{'压缩' if args.compress else '删除'}")
    print()
    
    # 获取所有日志文件
    log_files = get_log_files(log_dir)
    
    if not log_files:
        print("[信息] 未发现日志文件")
        sys.exit(0)
    
    print(f"[信息] 找到 {len(log_files)} 个日志文件")
    
    # 分析哪些文件需要清理
    cutoff_date = datetime.now() - timedelta(days=args.days)
    files_to_cleanup = []
    files_to_keep = []
    
    for f in log_files:
        # 跳过最新的日志文件（winclaw.log 和当前的错误日志）
        if f.name == "winclaw.log" or f.name == f"error_{datetime.now().strftime('%Y-%m-%d')}.log":
            files_to_keep.append(f)
            continue
        
        # 尝试从文件名解析日期
        file_date = get_file_date_from_name(f)
        
        if file_date:
            # 如果文件日期早于截止日期，则需要清理
            if file_date < cutoff_date:
                files_to_cleanup.append(f)
            else:
                files_to_keep.append(f)
        else:
            # 无法从文件名判断，使用文件修改时间
            age_days = get_file_age_days(f)
            if age_days > args.days:
                files_to_cleanup.append(f)
            else:
                files_to_keep.append(f)
    
    print(f"\n[统计]")
    print(f"  - 保留文件：{len(files_to_keep)} 个")
    print(f"  - 待清理文件：{len(files_to_cleanup)} 个")
    
    if not files_to_cleanup:
        print("\n[信息] 没有需要清理的文件")
        sys.exit(0)
    
    # 显示待清理文件列表
    print(f"\n[待清理的文件]")
    total_cleanup_size = 0
    for i, f in enumerate(files_to_cleanup[:10], 1):  # 只显示前 10 个
        size_kb = f.stat().st_size / 1024
        age_days = get_file_age_days(f)
        print(f"  {i}. {f.name} ({format_size(f.stat().st_size)}, {age_days} 天前)")
        total_cleanup_size += f.stat().st_size
    
    if len(files_to_cleanup) > 10:
        print(f"  ... 还有 {len(files_to_cleanup) - 10} 个文件")
    
    print(f"\n预计释放空间：{format_size(total_cleanup_size)}")
    
    # 确认执行
    if args.dry_run:
        print("\n[预览模式] 未执行任何操作")
        print("使用 --execute 参数执行清理")
        sys.exit(0)
    
    if not args.execute:
        print("\n提示：")
        print("  - 使用 --execute 执行清理操作")
        print("  - 使用 --compress 压缩旧日志而不是删除")
        print("  - 使用 --days N 修改保留天数")
        sys.exit(0)
    
    # 执行清理
    print(f"\n[开始清理...]")
    
    # 确保归档目录存在
    archive_dir = log_dir / "archive"
    if args.compress and not archive_dir.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        print(f"[信息] 创建归档目录：{archive_dir}")
    
    success_count = 0
    failed_count = 0
    freed_size = 0
    
    for f in files_to_cleanup:
        try:
            file_size = f.stat().st_size
            
            if args.compress:
                # 压缩文件
                result = compress_file(f, archive_dir)
                if result:
                    print(f"✓ 压缩：{f.name} → {result.name}")
                    success_count += 1
                    freed_size += file_size
                else:
                    failed_count += 1
            else:
                # 直接删除
                f.unlink()
                print(f"✓ 删除：{f.name}")
                success_count += 1
                freed_size += file_size
        except Exception as e:
            print(f"✗ 失败：{f.name} - {e}")
            failed_count += 1
    
    # 清理空的归档目录
    if archive_dir.exists() and not any(archive_dir.iterdir()):
        try:
            archive_dir.rmdir()
            print(f"[信息] 删除空目录：{archive_dir}")
        except Exception:
            pass
    
    print(f"\n[清理完成]")
    print(f"  - 成功：{success_count} 个文件")
    print(f"  - 失败：{failed_count} 个文件")
    print(f"  - 释放空间：{format_size(freed_size)}")
    
    # 显示新的占用空间
    new_total_size = calculate_directory_size(log_dir)
    print(f"\n[结果]")
    print(f"  - 清理前：{format_size(total_size)}")
    print(f"  - 清理后：{format_size(new_total_size)}")


def main():
    """入口函数。"""
    args = parse_args()
    cleanup_logs(args)


if __name__ == "__main__":
    main()
