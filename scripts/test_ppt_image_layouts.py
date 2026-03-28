# -*- coding: utf-8 -*-
"""测试PPT图片布局功能"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, '.')
from src.tools.ppt_generator import PPTTool

# 测试图片目录
TEST_IMG_DIR = Path("generated/test_images")


async def test_image_layouts():
    """测试各种图片布局"""
    print("\n" + "="*60)
    print("  PPT 图片布局测试（真实图片）")
    print("="*60)

    tool = PPTTool(output_dir="generated")

    slides_config = [
        {
            "type": "title",
            "title": "图文并茂PPT测试",
            "subtitle": "真实图片插入演示"
        },
        {
            "type": "image",
            "title": "左图右文布局",
            "subtitle": "左侧大图，右侧要点列表",
            "image_path": str(TEST_IMG_DIR / "blue_test.png"),
            "image_layout": "left_large",
            "content": [
                "深度学习技术快速发展",
                "大模型时代已经到来",
                "多模态成为主流趋势",
                "AI赋能千行百业"
            ]
        },
        {
            "type": "image",
            "title": "右图左文布局",
            "subtitle": "左侧要点列表，右侧图片",
            "image_path": str(TEST_IMG_DIR / "purple_test.png"),
            "image_layout": "right_large",
            "content": [
                "技术创新不断突破",
                "产业应用持续深化",
                "生态体系日趋完善",
                "人才需求日益增长"
            ]
        },
        {
            "type": "image",
            "title": "上图下文布局",
            "subtitle": "上方大图，下方详细说明",
            "image_path": str(TEST_IMG_DIR / "green_test.png"),
            "image_layout": "top_bottom",
            "content": [
                "市场前景广阔",
                "政策支持力度加大",
                "资本投入持续增长"
            ]
        },
        {
            "type": "grid_images",
            "title": "四图网格布局",
            "image_count": 4,
            "images": [
                str(TEST_IMG_DIR / "blue_test.png"),
                str(TEST_IMG_DIR / "purple_test.png"),
                str(TEST_IMG_DIR / "green_test.png"),
                str(TEST_IMG_DIR / "orange_test.png"),
            ]
        },
        {
            "type": "grid_images",
            "title": "双图并排布局",
            "image_count": 2,
            "images": [
                str(TEST_IMG_DIR / "red_test.png"),
                str(TEST_IMG_DIR / "cyan_test.png"),
            ]
        },
        {
            "type": "thank",
            "title": "感谢聆听",
            "subtitle": "THANK YOU"
        }
    ]

    result = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "PPT图片布局测试",
            "slides_config": json.dumps(slides_config, ensure_ascii=False),
            "style": "business",
        }
    )

    if result.is_success:
        print(f"\n  PPT 生成成功!")
        print(f"  文件: {result.data['file_path']}")
        print(f"  页数: {result.data['slide_count']}")
        return result.data['file_path']
    else:
        print(f"\n  PPT 生成失败: {result.error}")
        return None


async def main():
    file_path = await test_image_layouts()
    
    print("\n" + "="*60)
    print("  图片布局说明")
    print("="*60)
    print("""
  新增的 image 类型支持以下布局：
  
  1. left_half   - 左侧50%图片，右侧内容
  2. left_large  - 左侧60%大图，右侧内容
  3. right_half  - 左侧内容，右侧50%图片
  4. right_large - 左侧内容，右侧60%大图
  5. top_bottom  - 上方大图，下方内容
  6. full_bg     - 全屏背景图
  
  grid_images 类型支持：
  - image_count: 1, 2, 3, 4, 6 等数量
  - images: 传入图片路径列表，会显示真实图片
    """)
    print("="*60)
    
    return file_path


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print(f"\n请打开查看: {result}")
