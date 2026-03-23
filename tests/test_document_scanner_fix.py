"""测试高拍仪工具 GLM-4.6V 调用修复。"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.document_scanner import DocumentScannerTool


async def test_glm_vision():
    """测试 GLM-4.6V 调用。"""
    print("\n" + "=" * 80)
    print("📷 测试高拍仪工具 GLM-4.6V 调用")
    print("=" * 80)
    
    # 初始化
    scanner = DocumentScannerTool()
    
    # 查找测试图片
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    if not scan_dir.exists():
        print(f"❌ 扫描目录不存在：{scan_dir}")
        return
    
    image_files = list(scan_dir.glob("*.jpg")) + list(scan_dir.glob("*.png"))
    if not image_files:
        print(f"❌ 未找到图片文件")
        return
    
    test_file = image_files[0]
    print(f"\n📁 测试文件：{test_file.name}")
    print(f"📊 文件大小：{test_file.stat().st_size / (1024 * 1024):.2f} MB")
    
    # 执行扫描
    print("\n🔄 开始扫描...")
    result = await scanner.execute("scan_file", {
        "file_path": str(test_file),
        "subject": "数学",
        "grade_level": "小学"
    })
    
    if result.is_success:
        print(f"\n✅ 扫描成功！")
        print(result.output)
        
        if result.data:
            print(f"\n详细信息:")
            for key, value in result.data.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  - {key}: {value[:100]}...")
                else:
                    print(f"  - {key}: {value}")
    else:
        print(f"\n❌ 扫描失败：{result.error}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(test_glm_vision())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
