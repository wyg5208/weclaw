# -*- coding: utf-8 -*-
"""测试PPT预设模板"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

# 直接导入避免 __init__.py 的循环依赖问题
from src.tools.ppt_templates.content_expander import ContentExpander
from src.tools.ppt_generator import PPTTool


def show_templates():
    """显示所有预设模板"""
    expander = ContentExpander()
    templates = expander.list_templates()
    
    print("\n" + "="*60)
    print("  PPT 预设模板列表")
    print("="*60)
    for i, t in enumerate(templates, 1):
        print(f"\n  {i}. {t['name']}")
        print(f"     {t['description']}")
    print("\n" + "="*60)


async def test_template(template_name: str, topic: str, outline: list):
    """测试指定模板"""
    print(f"\n--- 测试模板: {template_name} ---")
    
    expander = ContentExpander()
    template = expander.get_template(template_name)
    
    if not template:
        print(f"  模板不存在: {template_name}")
        return
    
    print(f"  名称: {template['name']}")
    print(f"  描述: {template['description']}")
    print(f"  页面结构:")
    for i, s in enumerate(template['structure'], 1):
        print(f"    {i}. type={s.get('type')}, layout={s.get('layout')}")
    
    # 扩展大纲为完整配置
    slides = expander.expand_outline(topic, outline)
    
    print(f"\n  扩展后幻灯片数量: {len(slides)}")
    for i, s in enumerate(slides, 1):
        slide_type = s.get('type')
        slide_title = s.get('title', '')
        print(f"    {i}. [{slide_type}] {slide_title}")
    
    # 生成PPT
    tool = PPTTool(output_dir="generated")
    result = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": topic,
            "slides_config": json.dumps(slides, ensure_ascii=False),
            "style": "business",
        }
    )
    
    if result.is_success:
        print(f"\n  PPT 生成成功!")
        print(f"  文件: {result.data['file_path']}")
        return result.data['file_path']
    else:
        print(f"\n  PPT 生成失败: {result.error}")
        return None


async def main():
    show_templates()
    
    # 测试案例大纲
    outline = [
        "项目背景与目标",
        "市场需求分析",
        "产品功能设计",
        "技术架构方案",
        "实施计划",
    ]
    
    topic = "智能产品研发方案"
    
    # 测试商务汇报模板
    file1 = await test_template("business_report", topic, outline)
    
    # 测试产品介绍模板
    file2 = await test_template("product_intro", topic, outline)
    
    # 测试学术报告模板
    file3 = await test_template("academic_presentation", topic, outline)
    
    print("\n" + "="*60)
    print("  模板测试完成")
    print("="*60)
    if file1:
        print(f"\n  1. 商务汇报: {Path(file1).name}")
    if file2:
        print(f"  2. 产品介绍: {Path(file2).name}")
    if file3:
        print(f"  3. 学术报告: {Path(file3).name}")


if __name__ == "__main__":
    asyncio.run(main())
