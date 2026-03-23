"""测试试卷解答工具 - 使用高拍仪扫描的图片。"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.study_solver import StudySolverTool


async def test_image_solving():
    """测试图片题目解答功能。"""
    print("=" * 60)
    print("📝 开始测试试卷解答工具")
    print("=" * 60)
    
    # 初始化解答工具
    solver = StudySolverTool()
    
    # 测试图片路径（使用你的高拍仪扫描目录）
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    
    if not scan_dir.exists():
        print(f"❌ 扫描目录不存在：{scan_dir}")
        return
    
    # 查找所有图片文件
    image_files = list(scan_dir.glob("*.jpg")) + list(scan_dir.glob("*.png"))
    
    if not image_files:
        print(f"❌ 在 {scan_dir} 中未找到图片文件")
        return
    
    print(f"📂 找到 {len(image_files)} 个图片文件:")
    for img in image_files:
        print(f"  - {img.name}")
    print()
    
    # 测试第一个图片
    test_image = image_files[0]
    print(f"🔍 开始处理：{test_image.name}")
    print("-" * 60)
    
    try:
        result = await solver.execute(
            "solve_from_image",
            {
                "image_path": str(test_image),
                "subject": "数学",
                "grade_level": "高中",
                "include_steps": True,
                "extract_formulas": True,
            }
        )
        
        if result.is_success:
            print(f"\n✅ 解答成功！")
            print(f"📄 输出文件：{result.data.get('md_file_path', 'N/A')}")
            if result.data.get('json_file_path'):
                print(f"📊 JSON 数据：{result.data['json_file_path']}")
            print(f"\n结果预览:")
            print("-" * 60)
            # 读取并显示前几行
            md_path = Path(result.data['md_file_path'])
            if md_path.exists():
                content = md_path.read_text(encoding='utf-8')
                lines = content.split('\n')[:20]  # 显示前 20 行
                print('\n'.join(lines))
                if len(content.split('\n')) > 20:
                    print("\n... (更多内容请查看完整文件)")
        else:
            print(f"\n❌ 解答失败：{result.error}")
            
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_batch_solving():
    """测试批量处理功能。"""
    print("\n" + "=" * 60)
    print("📚 开始测试批量处理功能")
    print("=" * 60)
    
    solver = StudySolverTool()
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    
    if not scan_dir.exists():
        print(f"❌ 扫描目录不存在：{scan_dir}")
        return
    
    try:
        result = await solver.execute(
            "batch_solve",
            {
                "folder_path": str(scan_dir),
                "subject": "数学",
                "grade_level": "高中",
                "file_pattern": "*.*",
            }
        )
        
        if result.is_success:
            print(f"\n✅ 批量处理完成！")
            print(f"📊 成功：{result.data['success_count']}/{result.data['total_files']}")
            print(f"📄 汇总报告：{result.data['summary_path']}")
            
            # 显示汇总报告内容
            summary_path = Path(result.data['summary_path'])
            if summary_path.exists():
                print(f"\n汇总报告预览:")
                print("-" * 60)
                content = summary_path.read_text(encoding='utf-8')
                print(content)
        else:
            print(f"\n❌ 批量处理失败：{result.error}")
            
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)


async def main():
    """主函数。"""
    # 检查 API Key
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    
    if not api_key:
        print("⚠️  警告：未检测到 GLM_API_KEY")
        print("请在 .env 文件中设置智谱AI 的 API Key")
        print("否则将无法调用 GLM-4.6V 视觉模型进行题目识别")
        print()
        response = input("是否继续测试？（y/N）: ")
        if response.lower() != 'y':
            return
    
    # 运行单个图片测试
    await test_image_solving()
    
    # 如果需要测试批量处理，取消下面的注释
    # await test_batch_solving()


if __name__ == "__main__":
    asyncio.run(main())
