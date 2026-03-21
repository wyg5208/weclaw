"""测试微信工具注册"""

from src.tools.registry import ToolRegistry

def main():
    print("=" * 50)
    print("测试微信工具注册")
    print("=" * 50)
    
    # 1. 创建注册表
    reg = ToolRegistry()
    print("\n✓ 工具注册表已创建")
    
    # 2. 加载配置
    reg.load_config()
    print("✓ 工具配置已加载")
    
    # 3. 检查 wechat 配置
    wechat_cfg = reg._tool_configs.get('wechat')
    
    if wechat_cfg:
        print("\n✓ WeChat 工具配置存在:")
        print(f"  - 模块：{wechat_cfg.get('module')}")
        print(f"  - 类别：{wechat_cfg.get('class')}")
        print(f"  - 启用：{wechat_cfg.get('enabled', True)}")
        print(f"  - 分类：{wechat_cfg.get('display', {}).get('category')}")
        print(f"  - 动作：{len(wechat_cfg.get('actions', []))} 个")
    else:
        print("\n✗ WeChat 工具配置不存在")
        print("\n可用工具列表:")
        for name in reg._tool_configs.keys():
            print(f"  - {name}")
    
    # 4. 尝试实例化
    try:
        from src.tools.wechat import WeChatTool
        tool = WeChatTool()
        print(f"\n✓ WeChatTool 实例化成功")
        print(f"  - 名称：{tool.name}")
        print(f"  - Emoji: {tool.emoji}")
        print(f"  - 标题：{tool.title}")
        print(f"  - 动作数：{len(tool.get_actions())}")
        
        # 显示所有动作
        print("\n支持的动作:")
        for action in tool.get_actions():
            print(f"  - {action.name}: {action.description}")
            
    except Exception as e:
        print(f"\n✗ WeChatTool 实例化失败：{e}")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == '__main__':
    main()
