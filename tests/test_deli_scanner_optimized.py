"""高拍仪扫描图片分析测试 - 优化版。

支持：
- 图片压缩（如果过大）
- 自动重试机制
- 详细的错误诊断
- 分步处理
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_environment():
    """检查环境配置。"""
    print("=" * 80)
    print("🔍 环境检查")
    print("=" * 80)
    
    # 检查 API Key
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    
    if not api_key:
        print("❌ 未配置 GLM_API_KEY")
        print("\n请在 .env 文件中添加:")
        print("GLM_API_KEY=your_api_key_here")
        print("\n获取地址：https://open.bigmodel.cn/")
        return False
    
    # 隐藏显示 API Key（只显示前 8 位）
    masked_key = api_key[:8] + "..." if len(api_key) > 8 else "***"
    print(f"✅ API Key 已配置：{masked_key}")
    
    # 检查依赖包
    try:
        import zai
        print(f"✅ zai-sdk 版本：{zai.__version__}")
    except ImportError:
        print("❌ zai-sdk 未安装")
        return False
    
    try:
        import tenacity
        print(f"✅ tenacity 已安装")
    except ImportError:
        print("⚠️  tenacity 未安装，将使用基础重试机制")
    
    # 检查扫描目录
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    if not scan_dir.exists():
        print(f"❌ 扫描目录不存在：{scan_dir}")
        return False
    
    print(f"✅ 扫描目录：{scan_dir}")
    
    # 查找图片文件
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]:
        image_files.extend(scan_dir.glob(ext))
    
    if not image_files:
        print(f"❌ 未找到图片文件")
        return False
    
    print(f"✅ 找到 {len(image_files)} 个图片文件:")
    for i, img in enumerate(image_files, 1):
        size_mb = img.stat().st_size / (1024 * 1024)
        status = "⚠️  较大" if size_mb > 5 else "✅"
        print(f"   {i}. {img.name} ({size_mb:.2f} MB) {status}")
    
    print()
    return True


async def test_single_image(image_path: Path, use_compression: bool = False):
    """测试单张图片解答。
    
    Args:
        image_path: 图片路径
        use_compression: 是否使用压缩
    """
    from src.tools.study_solver import StudySolverTool
    from PIL import Image
    import io
    
    print("-" * 80)
    print(f"📸 开始处理：{image_path.name}")
    print("-" * 80)
    
    # 检查文件大小
    file_size_mb = image_path.stat().st_size / (1024 * 1024)
    print(f"📊 原始大小：{file_size_mb:.2f} MB")
    
    # 如果需要压缩
    if use_compression and file_size_mb > 5:
        print("🔄 正在压缩图片...")
        try:
            img = Image.open(image_path)
            
            # 调整大小
            max_size = (1920, 1080)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 保存到临时文件
            compressed_path = image_path.parent / f"compressed_{image_path.name}"
            img.save(compressed_path, quality=85, optimize=True)
            
            new_size_mb = compressed_path.stat().st_size / (1024 * 1024)
            print(f"✅ 压缩后大小：{new_size_mb:.2f} MB")
            
            image_path = compressed_path
            
        except Exception as e:
            print(f"⚠️  压缩失败：{e}，使用原始图片")
    
    # 初始化解答工具
    solver = StudySolverTool()
    
    print(f"⏱️  超时设置：120 秒")
    print(f"🔄 重试次数：最多 3 次")
    print()
    
    # 执行解答
    start_time = datetime.now()
    
    try:
        result = await solver.execute("solve_from_image", {
            "image_path": str(image_path),
            "subject": "数学",
            "grade_level": "高中",
            "include_steps": True,
            "extract_formulas": True,
        })
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if result.is_success:
            print(f"\n✅ 解答成功！耗时：{duration}")
            print(f"📄 Markdown: {Path(result.data['md_file_path']).name}")
            
            if result.data.get('json_file_path'):
                print(f"📊 JSON: {Path(result.data['json_file_path']).name}")
            
            # 显示内容预览
            md_path = Path(result.data['md_file_path'])
            if md_path.exists():
                content = md_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                print(f"\n📖 内容预览 (前 20 行):")
                print("-" * 60)
                for line in lines[:20]:
                    print(line)
                
                if len(lines) > 20:
                    print(f"\n... (还有 {len(lines) - 20} 行)")
                
                print("-" * 60)
                
                # 统计信息
                problem_count = content.count("**题目**:")
                print(f"\n📝 识别到 {problem_count} 道题目")
            
            return True, result.data
            
        else:
            print(f"\n❌ 解答失败：{result.error}")
            return False, {"error": result.error}
    
    except Exception as e:
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n❌ 发生异常：{e}")
        print(f"⏱️  耗时：{duration}")
        
        import traceback
        traceback.print_exc()
        
        return False, {"error": str(e)}


async def main():
    """主函数。"""
    print("\n")
    
    # 环境检查
    if not check_environment():
        print("\n⚠️  环境检查未通过，请修复后再运行")
        return
    
    # 选择要处理的图片
    scan_dir = Path("D:/python_projects/weclaw/docs/deli_scan_image")
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]:
        image_files.extend(scan_dir.glob(ext))
    
    if len(image_files) == 0:
        print("\n❌ 未找到图片文件")
        return
    
    print("=" * 80)
    print("📋 选择要处理的图片")
    print("=" * 80)
    
    for i, img in enumerate(image_files, 1):
        size_mb = img.stat().st_size / (1024 * 1024)
        print(f"{i}. {img.name} ({size_mb:.2f} MB)")
    
    print()
    
    if len(image_files) == 1:
        choice = 1
    else:
        choice_input = input(f"请输入图片编号 (1-{len(image_files)}) [默认：1]: ").strip()
        choice = int(choice_input) if choice_input else 1
    
    if choice < 1 or choice > len(image_files):
        print(f"❌ 无效的选择：{choice}")
        return
    
    selected_image = image_files[choice - 1]
    
    # 询问是否压缩
    file_size_mb = selected_image.stat().st_size / (1024 * 1024)
    use_compression = False
    
    if file_size_mb > 5:
        compress_input = input(f"图片较大 ({file_size_mb:.2f} MB)，是否压缩？(y/N): ").strip().lower()
        use_compression = compress_input == 'y'
    
    print()
    print("=" * 80)
    print("🚀 开始处理")
    print("=" * 80)
    print()
    
    # 执行测试
    success, data = await test_single_image(selected_image, use_compression)
    
    # 输出总结
    print()
    print("=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    
    if success:
        print("✅ 测试成功！")
        print(f"\n💡 下一步操作:")
        print(f"   1. 查看 Markdown 文件：{data.get('md_file_path', 'N/A')}")
        print(f"   2. 在浏览器中打开：start {data.get('md_file_path', '')}")
        
        # 询问是否打开浏览器
        open_browser = input("\n是否在浏览器中打开结果？(y/N): ").strip().lower()
        if open_browser == 'y':
            import webbrowser
            webbrowser.open(data['md_file_path'])
            print("🌐 已在浏览器中打开")
    else:
        print("❌ 测试失败")
        print(f"\n错误信息：{data.get('error', '未知错误')}")
        print(f"\n💡 建议:")
        print(f"   1. 检查网络连接是否正常")
        print(f"   2. 确认 API Key 是否有效")
        print(f"   3. 如果是大图片，尝试压缩后重试")
        print(f"   4. 查看详细日志：logs/winclaw.log")
    
    print()
    print("=" * 80)
    print("✨ 完成！")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
