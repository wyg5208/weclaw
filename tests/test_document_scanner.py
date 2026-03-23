"""测试高拍仪文档扫描工具。

功能:
- 测试单文件解析
- 测试批量文件夹扫描
- 测试缓存机制
- 测试数据库查询
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.document_scanner import DocumentScannerTool


async def test_single_file():
    """测试单个文件解析。"""
    print("\n" + "=" * 80)
    print("📝 测试 1: 单个文件解析")
    print("=" * 80)
    
    # 初始化工具
    scanner = DocumentScannerTool()
    
    # 测试文件
    test_file = Path("D:/python_projects/weclaw/docs/deli_scan_image/IMG_20260323_233137.jpg")
    
    if not test_file.exists():
        print(f"❌ 测试文件不存在：{test_file}")
        return
    
    print(f"\n📁 文件：{test_file.name}")
    print(f"📊 大小：{test_file.stat().st_size / (1024 * 1024):.2f} MB")
    print()
    
    # 执行解析
    result = await scanner.execute("scan_file", {
        "file_path": str(test_file),
        "subject": "数学",
        "grade_level": "高中"
    })
    
    if result.is_success:
        print(f"\n✅ 解析成功！")
        print(result.output)
        
        if result.data:
            print(f"\n详细信息:")
            for key, value in result.data.items():
                if key != "cached":  # cached 会在 output 中显示
                    print(f"  - {key}: {value}")
    else:
        print(f"\n❌ 解析失败：{result.error}")


async def test_folder_scan():
    """测试批量文件夹扫描。"""
    print("\n" + "=" * 80)
    print("📝 测试 2: 批量文件夹扫描")
    print("=" * 80)
    
    # 初始化工具
    scanner = DocumentScannerTool()
    
    # 扫描文件夹
    scan_folder = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    
    if not scan_folder.exists():
        print(f"❌ 扫描文件夹不存在：{scan_folder}")
        return
    
    print(f"\n📂 扫描目录：{scan_folder}")
    
    # 查找文件
    files = []
    for ext in ["*.jpg", "*.png", "*.bmp"]:
        files.extend(scan_folder.glob(ext))
    
    print(f"📊 找到 {len(files)} 个图片文件")
    print()
    
    # 执行批量扫描
    result = await scanner.execute("scan_folder", {
        "folder_path": str(scan_folder),
        "subject": "数学",
        "grade_level": "高中",
        "file_pattern": "*.jpg,*.png,*.bmp",
        "force_reprocess": False  # 使用缓存
    })
    
    if result.is_success:
        print(f"\n✅ 批量扫描完成！")
        print(result.output)
        
        if result.data:
            print(f"\n统计信息:")
            print(f"  - 总文件数：{result.data.get('total_files', 0)}")
            print(f"  - 成功：{result.data.get('success_count', 0)}")
            print(f"  - 失败：{result.data.get('error_count', 0)}")
            print(f"  - 缓存命中：{result.data.get('cache_hit_count', 0)}")
            print(f"  - 耗时：{result.data.get('duration', 'N/A')}")
    else:
        print(f"\n❌ 批量扫描失败：{result.error}")


async def test_cache_mechanism():
    """测试缓存机制。"""
    print("\n" + "=" * 80)
    print("📝 测试 3: 缓存机制测试")
    print("=" * 80)
    
    scanner = DocumentScannerTool()
    test_file = Path("D:/python_projects/weclaw/docs/deli_scan_image/IMG_20260323_233137.jpg")
    
    if not test_file.exists():
        print(f"❌ 测试文件不存在")
        return
    
    print(f"\n第一次扫描（应该处理）...")
    result1 = await scanner.execute("scan_file", {
        "file_path": str(test_file),
        "subject": "数学",
        "grade_level": "高中"
    })
    
    if result1.is_success:
        cached1 = result1.data.get("cached", False) if result1.data else False
        print(f"结果：{'✅ 使用缓存' if cached1 else '🆕 新处理'}")
    
    print(f"\n第二次扫描（应该使用缓存）...")
    result2 = await scanner.execute("scan_file", {
        "file_path": str(test_file),
        "subject": "数学",
        "grade_level": "高中"
    })
    
    if result2.is_success:
        cached2 = result2.data.get("cached", False) if result2.data else False
        print(f"结果：{'✅ 使用缓存' if cached2 else '🆕 新处理'}")
        
        if cached2:
            print(f"\n✨ 缓存机制工作正常！")
        else:
            print(f"\n⚠️  缓存可能未生效")


async def test_query_history():
    """测试查询历史记录。"""
    print("\n" + "=" * 80)
    print("📝 测试 4: 查询历史记录")
    print("=" * 80)
    
    scanner = DocumentScannerTool()
    
    # 查询所有记录
    result = await scanner.execute("query_history", {
        "status": "all",
        "limit": 10
    })
    
    if result.is_success:
        records = result.data.get("records", []) if result.data else []
        print(f"\n📊 查询到 {len(records)} 条记录\n")
        
        for i, record in enumerate(records, 1):
            print(f"{i}. {record.get('file_name', 'N/A')}")
            print(f"   状态：{record.get('status', 'N/A')}")
            print(f"   题目数：{record.get('problem_count', 0)}")
            print(f"   时间：{record.get('updated_at', 'N/A')}")
            print()
    else:
        print(f"\n❌ 查询失败：{result.error}")


async def main():
    """主函数。"""
    print("\n" + "=" * 80)
    print("📷 高拍仪文档扫描工具测试")
    print("=" * 80)
    
    # 检查 API Key
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    
    if not api_key:
        print("\n⚠️  警告：未检测到 GLM_API_KEY")
        print("请在 .env 文件中设置智谱AI 的 API Key")
        print("\n继续测试将跳过需要 API 的部分...")
        print()
    
    # 运行所有测试
    await asyncio.gather(
        test_single_file(),
        test_folder_scan(),
        test_cache_mechanism(),
        test_query_history()
    )
    
    print("\n" + "=" * 80)
    print("✨ 测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
