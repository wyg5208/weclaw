"""英语口语对话练习 - HTML 模板生成器。

提供场景 HTML 模板，支持快速更换图片和文本内容。
"""

from typing import Optional


class EnglishConversationHTMLTemplate:
    """英语口语对话 HTML 模板。
    
    功能:
    - 提供统一的 HTML 结构
    - 支持动态替换场景图片
    - 支持动态替换角色图片
    - 支持动态更新词汇卡片
    - 支持动态添加对话内容
    """
    
    @staticmethod
    def generate_scene_html(
        title_zh: str,
        title_en: str,
        scene_image_path: Optional[str] = None,
        character_image_path: Optional[str] = None,
        vocabulary: Optional[list[dict[str, str]]] = None,
        dialogue_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """生成完整的场景 HTML。
        
        Args:
            title_zh: 中文标题
            title_en: 英文标题
            scene_image_path: 场景图片路径（可选）
            character_image_path: 角色图片路径（可选）
            vocabulary: 词汇列表 [{"en": "menu", "cn": "菜单"}, ...]
            dialogue_history: 对话历史 [{"role": "user/ai", "speaker": "You/Waiter", "english": "...", "chinese": "..."}]
            
        Returns:
            完整的 HTML 字符串
        """
        # 场景图片显示
        if scene_image_path:
            scene_img_html = f'<img src="file:///{scene_image_path}" alt="Scene" class="scene-image">'
        else:
            scene_img_html = '<div class="placeholder-scene">🎬 场景加载中...</div>'
        
        # 角色图片显示
        if character_image_path:
            char_img_html = f'<img src="file:///{character_image_path}" alt="Character" class="character-image">'
        else:
            char_img_html = '<div class="placeholder-character">👤 角色加载中...</div>'
        
        # 词汇卡片
        vocab_html = ""
        if vocabulary:
            vocab_items = "".join([
                f'<div class="vocab-item"><strong>{word["en"]}</strong><span>{word["cn"]}</span></div>'
                for word in vocabulary
            ])
            vocab_html = f'''
            <div class="vocab-section">
                <h3>📚 关键词汇</h3>
                <div class="vocab-grid">{vocab_items}</div>
            </div>
            '''
        
        # 对话历史
        dialogue_html = ""
        if dialogue_history:
            dialogue_lines = "".join([
                f'''
                <div class="dialogue-line {line["role"]}">
                    <div class="speaker">{line["speaker"]}</div>
                    <div class="bubble">
                        <div class="english">{line["english"]}</div>
                        {f'<div class="chinese-tip">{line["chinese"]}</div>' if line.get("chinese") else ''}
                    </div>
                </div>
                '''
                for line in dialogue_history
            ])
            dialogue_html = f'''
            <div class="dialogue-section">
                <h3>💬 对话记录</h3>
                <div class="dialogue-container">{dialogue_lines}</div>
            </div>
            '''
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_zh} - {title_en}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* 头部 */
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
        }}
        
        .header h1 {{
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 18px;
            font-style: italic;
        }}
        
        /* 主内容区 */
        .main-content {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        /* 左侧面板 */
        .left-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        /* 场景图片 */
        .scene-section {{
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}
        
        .scene-section h2 {{
            color: #667eea;
            font-size: 24px;
            margin-bottom: 15px;
        }}
        
        .scene-image {{
            width: 100%;
            height: 400px;
            object-fit: cover;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }}
        
        .placeholder-scene {{
            width: 100%;
            height: 400px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: #666;
        }}
        
        /* 对话区域 */
        .dialogue-section {{
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            flex-grow: 1;
        }}
        
        .dialogue-section h2 {{
            color: #667eea;
            font-size: 24px;
            margin-bottom: 15px;
        }}
        
        .dialogue-container {{
            max-height: 500px;
            overflow-y: auto;
            padding: 10px;
        }}
        
        .dialogue-line {{
            display: flex;
            flex-direction: column;
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease-in;
        }}
        
        .dialogue-line.user {{
            align-items: flex-end;
        }}
        
        .dialogue-line.ai {{
            align-items: flex-start;
        }}
        
        .speaker {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
            font-weight: 600;
        }}
        
        .bubble {{
            max-width: 80%;
            padding: 15px 20px;
            border-radius: 18px;
            position: relative;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .dialogue-line.user .bubble {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }}
        
        .dialogue-line.ai .bubble {{
            background: #f0f0f0;
            color: #333;
            border-bottom-left-radius: 4px;
        }}
        
        .english {{
            font-size: 16px;
            line-height: 1.6;
        }}
        
        .chinese-tip {{
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            font-size: 14px;
            opacity: 0.8;
        }}
        
        /* 右侧面板 */
        .right-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        /* 角色卡片 */
        .character-section {{
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
        }}
        
        .character-section h2 {{
            color: #667eea;
            font-size: 24px;
            margin-bottom: 15px;
        }}
        
        .character-image {{
            width: 200px;
            height: 200px;
            object-fit: cover;
            border-radius: 50%;
            border: 5px solid #667eea;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }}
        
        .placeholder-character {{
            width: 200px;
            height: 200px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            margin: 0 auto;
        }}
        
        /* 词汇卡片 */
        .vocab-section {{
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}
        
        .vocab-section h2 {{
            color: #667eea;
            font-size: 24px;
            margin-bottom: 15px;
        }}
        
        .vocab-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 10px;
        }}
        
        .vocab-item {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .vocab-item:hover {{
            transform: translateY(-3px);
        }}
        
        .vocab-item strong {{
            display: block;
            font-size: 16px;
            margin-bottom: 5px;
        }}
        
        .vocab-item span {{
            font-size: 13px;
            opacity: 0.9;
        }}
        
        /* 动画 */
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        /* 滚动条美化 */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: #667eea;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: #764ba2;
        }}
        
        /* 响应式设计 */
        @media (max-width: 1024px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}
            
            .character-section, .vocab-section {{
                order: -1;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 状态提示栏 -->
        <div class="status-bar" style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 15px;
            font-size: 18px;
            font-weight: bold;
            display: none;
            animation: pulse 1.5s ease-in-out infinite;
        ">
            🎤 准备开始对话...
        </div>
        
        <!-- 头部 -->
        <div class="header">
            <h1>🗣️ {title_zh}</h1>
            <div class="subtitle">{title_en}</div>
        </div>
        
        <!-- 主内容区 -->
        <div class="main-content">
            <!-- 左侧：场景 + 对话 -->
            <div class="left-panel">
                <!-- 场景图片 -->
                <div class="scene-section">
                    <h2>🎬 场景</h2>
                    {scene_img_html}
                </div>
                
                <!-- 对话区域 -->
                {dialogue_html}
            </div>
            
            <!-- 右侧：角色 + 词汇 -->
            <div class="right-panel">
                <!-- 角色形象 -->
                <div class="character-section">
                    <h2>👤 AI 角色</h2>
                    {char_img_html}
                </div>
                
                <!-- 词汇卡片 -->
                {vocab_html}
            </div>
        </div>
    </div>
    
    <script>
        // 自动滚动到底部
        const dialogueContainer = document.querySelector('.dialogue-container');
        if (dialogueContainer) {{
            dialogueContainer.scrollTop = dialogueContainer.scrollHeight;
        }}
    </script>
</body>
</html>'''
        
        return html
    
    @staticmethod
    def generate_update_dialogue_script(
        role: str,
        speaker: str,
        english: str,
        chinese: Optional[str] = None,
    ) -> str:
        """生成 JavaScript 代码用于动态添加对话。
        
        Args:
            role: 角色（user/ai）
            speaker: 说话者名称
            english: 英文句子
            chinese: 中文提示（可选）
            
        Returns:
            JavaScript 代码字符串
        """
        chinese_tip_html = f'<div class="chinese-tip">{chinese}</div>' if chinese else ""
        
        script = f'''
        (function() {{
            const container = document.querySelector('.dialogue-container');
            if (!container) return;
            
            const lineHtml = `
                <div class="dialogue-line {role}">
                    <div class="speaker">{speaker}</div>
                    <div class="bubble">
                        <div class="english">{english}</div>
                        {chinese_tip_html}
                    </div>
                </div>
            `;
            
            container.insertAdjacentHTML('beforeend', lineHtml);
            container.scrollTop = container.scrollHeight;
        }})();
        '''
        
        return script
