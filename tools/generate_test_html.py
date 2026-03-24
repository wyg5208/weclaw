"""生成并打开英语口语 HTML 测试文件。"""

from src.ui.english_conversation_template import EnglishConversationHTMLTemplate


def test_html_generation():
    """测试 HTML 生成。"""
    print("=" * 60)
    print("生成英语口语 HTML 测试文件")
    print("=" * 60)
    
    # 准备测试数据
    vocabulary = [
        {"en": "menu", "cn": "菜单"},
        {"en": "order", "cn": "点餐"},
        {"en": "steak", "cn": "牛排"},
        {"en": "wine", "cn": "葡萄酒"},
    ]
    
    dialogue_history = [
        {
            "role": "ai",
            "speaker": "Waiter",
            "english": "Good evening! Welcome to our restaurant.",
            "chinese": "晚上好！欢迎光临我们餐厅。"
        },
        {
            "role": "user",
            "speaker": "You",
            "english": "I'd like to order some food.",
            "chinese": None
        }
    ]
    
    # 生成 HTML
    html = EnglishConversationHTMLTemplate.generate_scene_html(
        title_zh="餐厅点餐",
        title_en="Restaurant Dining",
        scene_image_path=None,
        character_image_path=None,
        vocabulary=vocabulary,
        dialogue_history=dialogue_history,
    )
    
    print(f"\n✅ HTML 生成成功!")
    print(f"   HTML 长度：{len(html)} 字符")
    
    # 保存到文件
    output_file = "test_english_conversation.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"💾 已保存到：{output_file}")
    print(f"\n💡 请在浏览器中打开此文件查看效果:")
    print(f"   1. 右键点击 {output_file}")
    print(f"   2. 选择 '用浏览器打开'")
    print(f"   3. 查看是否正常显示")
    print(f"\n📊 应该看到的内容:")
    print(f"   ✅ 紫色渐变背景")
    print(f"   ✅ 顶部标题：餐厅点餐 - Restaurant Dining")
    print(f"   ✅ 右侧 4 个紫色词汇卡片")
    print(f"   ✅ 左侧灰色占位图（场景）")
    print(f"   ✅ 右侧灰色占位图（角色）")
    print(f"   ✅ 2 条对话记录")
    print("=" * 60)


if __name__ == "__main__":
    test_html_generation()
