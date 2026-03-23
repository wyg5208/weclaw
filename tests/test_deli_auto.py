"""自动测试高拍仪扫描图片 - 无需交互。

此脚本会自动处理 deli_scan_image 目录中的所有图片，无需用户输入。
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def auto_test():
    """自动测试所有图片。"""
    print("\n" + "=" * 80)
    print("🚀 高拍仪扫描图片自动测试")
    print("=" * 80)
    print()
    
    # 检查环境
    print("📋 环境检查...")
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    
    if not api_key:
        print("❌ 错误：未配置 GLM_API_KEY")
        print("\n请在 .env 文件中添加:")
        print("GLM_API_KEY=your_api_key_here")
        return
    
    masked_key = api_key[:10] + "..." if len(api_key) > 10 else "***"
    print(f"✅ API Key: {masked_key}")
    
    # 检查扫描目录
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    
    if not scan_dir.exists():
        print(f"❌ 错误：目录不存在 {scan_dir}")
        return
    
    # 查找图片
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]:
        image_files.extend(scan_dir.glob(ext))
    
    if not image_files:
        print(f"❌ 错误：未找到图片文件")
        return
    
    print(f"✅ 找到 {len(image_files)} 个图片")
    for i, img in enumerate(image_files, 1):
        size_mb = img.stat().st_size / (1024 * 1024)
        print(f"   {i}. {img.name} ({size_mb:.2f} MB)")
    
    print()
    print("-" * 80)
    print("开始处理...")
    print("-" * 80)
    print()
    
    # 导入工具
    from src.tools.study_solver import StudySolverTool
    
    solver = StudySolverTool()
    
    results = []
    start_time = datetime.now()
    
    # 处理每个图片
    for i, img_file in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] 处理：{img_file.name}")
        
        try:
            # 执行解答（不压缩，直接处理）
            result = await solver.execute("solve_from_image", {
                "image_path": str(img_file),
                "subject": "数学",
                "grade_level": "高中",
                "include_steps": True,
                "extract_formulas": True,
            })
            
            if result.is_success:
                print(f"   ✅ 成功")
                print(f"   📄 {Path(result.data['md_file_path']).name}")
                
                # 显示简要预览
                md_path = Path(result.data['md_file_path'])
                if md_path.exists():
                    content = md_path.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    # 显示前 5 行
                    print(f"   📖 预览:")
                    for line in lines[:5]:
                        if line.strip():
                            print(f"      {line}")
                    
                    if len(lines) > 5:
                        print(f"      ... (共 {len(lines)} 行)")
                
                results.append({
                    "file": img_file.name,
                    "status": "success",
                    "md_file": result.data['md_file_path']
                })
            else:
                print(f"   ❌ 失败：{result.error}")
                results.append({
                    "file": img_file.name,
                    "status": "error",
                    "error": result.error
                })
        
        except Exception as e:
            print(f"   ❌ 异常：{e}")
            results.append({
                "file": img_file.name,
                "status": "exception",
                "error": str(e)
            })
        
        print()
    
    # 总结
    end_time = datetime.now()
    duration = end_time - start_time
    
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    
    print("=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print()
    print(f"⏱️  总耗时：{duration}")
    print(f"📁 总文件数：{len(image_files)}")
    print(f"✅ 成功：{success_count}")
    print(f"❌ 失败：{error_count}")
    
    if len(image_files) > 0:
        success_rate = (success_count / len(image_files)) * 100
        print(f"📈 成功率：{success_rate:.1f}%")
    
    print()
    print("📋 详细结果:")
    print("-" * 80)
    
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        print(f"{status_icon} {r['file']}")
        if r["status"] == "success":
            print(f"   📄 MD: {Path(r['md_file']).name}")
    
    print()
    print("=" * 80)
    print("✨ 完成！")
    print("=" * 80)
    
    # 如果有成功的结果，询问是否打开浏览器
    if success_count > 0:
        first_success = next((r for r in results if r["status"] == "success"), None)
        if first_success:
            print(f"\n💡 查看结果：{first_success['md_file']}")
            print(f"   命令：start {first_success['md_file']}")


if __name__ == "__main__":
    try:
        asyncio.run(auto_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
