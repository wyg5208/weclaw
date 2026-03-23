"""测试高拍仪扫描的数学试卷 - 专用测试脚本。

本脚本用于测试和分析 D:/python_projects/weclaw/docs/deli_scan_image 目录中的数学试卷图片。
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.study_solver import StudySolverTool


async def analyze_scan_images():
    """分析高拍仪扫描目录中的所有图片。"""
    print("=" * 80)
    print("📝 高拍仪扫描数学试卷分析测试")
    print("=" * 80)
    print()
    
    # 扫描目录
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    
    if not scan_dir.exists():
        print(f"❌ 扫描目录不存在：{scan_dir}")
        return
    
    print(f"📂 扫描目录：{scan_dir}")
    print()
    
    # 查找所有图片文件
    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]
    image_files = []
    for ext in image_extensions:
        image_files.extend(scan_dir.glob(ext))
    
    if not image_files:
        print(f"❌ 在 {scan_dir} 中未找到图片文件")
        return
    
    print(f"✅ 找到 {len(image_files)} 个图片文件:")
    for i, img in enumerate(image_files, 1):
        size_mb = img.stat().st_size / (1024 * 1024)
        print(f"   {i}. {img.name} ({size_mb:.2f} MB)")
    print()
    
    # 初始化解答工具
    solver = StudySolverTool()
    
    print("⚙️  工具配置:")
    print(f"   输出目录：{solver.output_dir}")
    print(f"   默认科目：数学")
    print(f"   默认年级：高中")
    print(f"   详细步骤：是")
    print(f"   LaTeX 公式：是")
    print()
    
    # 检查 API Key
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    
    if not api_key:
        print("⚠️  警告：未检测到 GLM_API_KEY")
        print("请在 .env 文件中设置智谱AI 的 API Key")
        print()
        response = input("是否继续测试？（y/N）: ")
        if response.lower() != 'y':
            print("测试已取消")
            return
        print()
    
    # 逐个处理图片
    results = []
    success_count = 0
    error_count = 0
    
    start_time = datetime.now()
    
    for i, img_file in enumerate(image_files, 1):
        print("-" * 80)
        print(f"[{i}/{len(image_files)}] 处理：{img_file.name}")
        print("-" * 80)
        
        try:
            # 执行解答
            result = await solver.execute("solve_from_image", {
                "image_path": str(img_file),
                "subject": "数学",
                "grade_level": "高中",
                "include_steps": True,
                "extract_formulas": True,
            })
            
            if result.is_success:
                success_count += 1
                print(f"\n✅ 解答成功！")
                print(f"📄 Markdown: {Path(result.data['md_file_path']).name}")
                
                if result.data.get('json_file_path'):
                    print(f"📊 JSON: {Path(result.data['json_file_path']).name}")
                
                # 显示内容预览
                md_path = Path(result.data['md_file_path'])
                if md_path.exists():
                    content = md_path.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    print(f"\n📖 内容预览 (前 15 行):")
                    print("-" * 60)
                    for line in lines[:15]:
                        print(line)
                    
                    if len(lines) > 15:
                        print(f"\n... (还有 {len(lines) - 15} 行，请查看完整文件)")
                    
                    print("-" * 60)
                
                results.append({
                    "file": img_file.name,
                    "status": "success",
                    "md_file": result.data['md_file_path'],
                    "json_file": result.data.get('json_file_path')
                })
                
            else:
                error_count += 1
                print(f"\n❌ 解答失败：{result.error}")
                results.append({
                    "file": img_file.name,
                    "status": "error",
                    "error": result.error
                })
        
        except Exception as e:
            error_count += 1
            print(f"\n❌ 发生异常：{e}")
            import traceback
            traceback.print_exc()
            results.append({
                "file": img_file.name,
                "status": "exception",
                "error": str(e)
            })
        
        print()
    
    # 生成汇总报告
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("=" * 80)
    print("📊 测试汇总报告")
    print("=" * 80)
    print()
    print(f"⏱️  总耗时：{duration}")
    print(f"📁 总文件数：{len(image_files)}")
    print(f"✅ 成功：{success_count}")
    print(f"❌ 失败：{error_count}")
    print()
    
    # 成功率统计
    if len(image_files) > 0:
        success_rate = (success_count / len(image_files)) * 100
        print(f"📈 成功率：{success_rate:.1f}%")
        print()
    
    # 结果列表
    print("📋 详细结果:")
    print("-" * 80)
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        print(f"{status_icon} {r['file']}")
        if r["status"] == "success":
            print(f"   📄 MD: {Path(r['md_file']).name}")
            if r.get('json_file'):
                print(f"   📊 JSON: {Path(r['json_file']).name}")
        else:
            print(f"   ⚠️ 错误：{r.get('error', '未知')}")
    print()
    
    # 生成汇总 Markdown 文件
    summary_md = f"""# 高拍仪扫描数学试卷分析 - 汇总报告

**测试时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**扫描目录**: {scan_dir}  
**总耗时**: {duration}

## 统计信息

| 指标 | 数值 |
|------|------|
| 总文件数 | {len(image_files)} |
| 成功 | {success_count} |
| 失败 | {error_count} |
| 成功率 | {success_rate:.1f}% |

## 处理结果

| 文件名 | 状态 | 输出文件 |
|--------|------|----------|
"""
    
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        output_files = ""
        if r["status"] == "success":
            output_files = f"[MD]({r['md_file']})"
            if r.get('json_file'):
                output_files += f", [JSON]({r['json_file']})"
        else:
            output_files = f"失败：{r.get('error', '未知')}"
        
        summary_md += f"| {r['file']} | {status_icon} | {output_files} |\n"
    
    # 保存汇总报告
    summary_path = solver.output_dir / f"高拍仪测试汇总_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    summary_path.write_text(summary_md, encoding="utf-8")
    
    print("=" * 80)
    print("📄 汇总报告已保存:")
    print(f"   {summary_path.name}")
    print()
    
    # 打开汇总报告
    print("💡 提示：使用以下命令查看汇总报告:")
    print(f"   cd {solver.output_dir}")
    print(f"   start {summary_path.name}")
    print()
    
    # 询问是否打开浏览器
    if success_count > 0:
        response = input("是否在浏览器中打开第一个成功的解答文件？(y/N): ")
        if response.lower() == 'y':
            first_success = next((r for r in results if r["status"] == "success"), None)
            if first_success and first_success.get('md_file'):
                import webbrowser
                webbrowser.open(first_success['md_file'])
                print(f"🌐 已打开：{first_success['md_file']}")
    
    print()
    print("=" * 80)
    print("✨ 测试完成！")
    print("=" * 80)
    
    return {
        "total_files": len(image_files),
        "success_count": success_count,
        "error_count": error_count,
        "duration": str(duration),
        "results": results,
        "summary_path": str(summary_path)
    }


async def main():
    """主函数。"""
    try:
        await analyze_scan_images()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
    except Exception as e:
        print(f"\n\n❌ 测试过程发生严重错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
