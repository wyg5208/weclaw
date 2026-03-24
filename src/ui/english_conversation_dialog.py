"""英语口语对话练习 - 可视化 UI 对话框。

基于 HTML 模板的场景展示，支持快速更换图片和句子。
功能:
- 显示场景图片和角色形象
- 展示相关词汇和短语
- 实时显示对话内容（中英文对照）
- 支持动态更新
"""

import logging
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    QWebEngineView = None

logger = logging.getLogger(__name__)


class EnglishConversationDialog(QDialog):
    """英语口语对话可视化对话框。
    
    功能:
    - 显示场景图片和角色形象
    - 展示相关词汇和短语
    - 实时显示对话内容（中英文对照）
    - 支持动态更新
    
    Signals:
        close_requested: 当用户点击关闭按钮时发出
    """
    
    close_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("英语口语练习 - 场景对话")
        self.setMinimumSize(1200, 800)
        
        # 状态变量
        self._scene_image_path: Optional[str] = None
        self._character_image_path: Optional[str] = None
        self._vocabulary: list[dict[str, str]] = []
        self._dialogue_history: list[dict[str, str]] = []
        self._current_topic: str = ""
        
        # 初始化 UI
        self._init_ui()
        
        logger.info("EnglishConversationDialog 初始化完成")
    
    def _init_ui(self):
        """初始化 UI 布局。"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        if WEB_ENGINE_AVAILABLE and QWebEngineView:
            # 使用 QWebEngineView 显示 HTML
            self.web_view = QWebEngineView()
            self.web_view.setMinimumSize(800, 600)  # 设置最小尺寸
            layout.addWidget(self.web_view)
            
            # 设置初始 HTML - 使用占位内容，等待正式内容加载
            initial_html = self._generate_placeholder_html()
            logger.debug(f"设置初始 HTML，长度：{len(initial_html)}")
            self.web_view.setHtml(initial_html)
            logger.info("初始 HTML 已设置")
            
            # 延迟刷新（给 QWebEngineView 一点时间）
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self.web_view.reload)  # 100ms 后刷新
            logger.debug("已安排延迟刷新")
        else:
            # 降级方案：使用 QTextBrowser
            from PySide6.QtWidgets import QTextBrowser
            self.text_browser = QTextBrowser()
            self.text_browser.setOpenExternalLinks(True)
            self.text_browser.setMarkdown("# 英语口语练习\n\n正在加载场景...")
            layout.addWidget(self.text_browser)
            
            logger.warning("QWebEngineView 不可用，使用降级方案")
        
        # 底部按钮栏
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新视图")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        button_layout.addWidget(self.refresh_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("❌ 关闭")
        self.close_btn.clicked.connect(self._on_close_clicked)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _generate_placeholder_html(self) -> str:
        """生成占位 HTML（立即显示，无需图片）。"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        .loading {
            text-align: center;
            animation: pulse 2s ease-in-out infinite;
        }
        .loading h1 {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .loading p {
            font-size: 24px;
            opacity: 0.8;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="loading">
        <h1>🗣️ 英语口语练习</h1>
        <p>正在准备场景...</p>
    </div>
</body>
</html>'''
    
    def _generate_welcome_html(self) -> str:
        """生成欢迎页面 HTML。"""
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }}
        .welcome-container {{
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }}
        h1 {{ font-size: 3em; margin-bottom: 20px; }}
        p {{ font-size: 1.2em; opacity: 0.9; }}
        .loading {{
            margin-top: 30px;
            font-size: 1.5em;
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 0.6; }}
            50% {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="welcome-container">
        <h1>🗣️ 英语口语练习</h1>
        <p>准备开始您的英语对话之旅...</p>
        <div class="loading">正在加载场景...</div>
    </div>
</body>
</html>'''
    
    def update_scene(self, topic: str, title_zh: str, title_en: str,
                     scene_image: Optional[str] = None,
                     character_image: Optional[str] = None,
                     vocabulary: Optional[list[dict]] = None):
        """更新场景显示。
        
        Args:
            topic: 主题 ID
            title_zh: 中文标题
            title_en: 英文标题
            scene_image: 场景图片路径
            character_image: 角色图片路径
            vocabulary: 词汇列表 [{"en": "menu", "cn": "菜单"}]
        """
        self._current_topic = topic
        self._scene_image_path = scene_image
        self._character_image_path = character_image
        self._vocabulary = vocabulary or []
        self._dialogue_history = []  # 清空对话历史
        
        # 使用新的 HTML 模板生成器
        from src.ui.english_conversation_template import EnglishConversationHTMLTemplate
        
        html = EnglishConversationHTMLTemplate.generate_scene_html(
            title_zh=title_zh,
            title_en=title_en,
            scene_image_path=scene_image,
            character_image_path=character_image,
            vocabulary=vocabulary,
            dialogue_history=[],
        )
        
        self._set_html(html)
        
        logger.info(f"场景已更新：{topic} - {title_zh}")
    
    def add_dialogue_line(self, role: str, speaker: str, 
                         english: str, chinese: Optional[str] = None):
        """添加一行对话。
        
        Args:
            role: 角色 ('user' 或 'ai')
            speaker: 说话者名称
            english: 英文内容
            chinese: 中文翻译（可选）
        """
        dialogue_entry = {
            "role": role,
            "speaker": speaker,
            "english": english,
            "chinese": chinese or ""
        }
        self._dialogue_history.append(dialogue_entry)
        
        # 使用 JavaScript 动态添加对话（更高效）
        if WEB_ENGINE_AVAILABLE and hasattr(self, 'web_view'):
            from src.ui.english_conversation_template import EnglishConversationHTMLTemplate
            js_script = EnglishConversationHTMLTemplate.generate_update_dialogue_script(
                role=role,
                speaker=speaker,
                english=english,
                chinese=chinese,
            )
            self.web_view.page().runJavaScript(js_script)
        else:
            # 降级方案：重新渲染整个页面
            self._refresh_dialogue()
        
        logger.debug(f"添加对话：{role} - {speaker}")
    
    def update_status(self, status_message: str):
        """更新状态提示（显示在顶部，告诉用户当前状态）。
        
        Args:
            status_message: 状态消息，如 "🎤 AI 正在说话，请稍候..." 或 "🎤 轮到你了，请说话..."
        """
        logger.debug(f"更新状态：{status_message}")
        
        if WEB_ENGINE_AVAILABLE and hasattr(self, 'web_view'):
            # 使用 JavaScript 更新状态提示区域
            js_script = f'''
            (function() {{
                const statusBar = document.querySelector('.status-bar');
                if (statusBar) {{
                    statusBar.textContent = '{status_message}';
                    statusBar.style.display = 'block';
                    
                    // 添加动画效果
                    statusBar.style.animation = 'pulse 1.5s ease-in-out infinite';
                }}
            }})();
            '''
            self.web_view.page().runJavaScript(js_script)
        
        
        # 同时更新窗口标题
        if status_message:
            self.setWindowTitle(f"英语口语练习 - {status_message}")
    
    def _refresh_dialogue(self):
        """刷新对话区域（重新渲染整个页面）。"""
        from src.tools.english_conversation import TOPIC_LIBRARY
        from src.ui.english_conversation_template import EnglishConversationHTMLTemplate
        
        # 获取标题
        if self._current_topic in TOPIC_LIBRARY:
            title_zh = TOPIC_LIBRARY[self._current_topic].title_zh
            title_en = TOPIC_LIBRARY[self._current_topic].title_en
        else:
            title_zh = "英语对话"
            title_en = "English Conversation"
        
        # 使用模板重新生成
        html = EnglishConversationHTMLTemplate.generate_scene_html(
            title_zh=title_zh,
            title_en=title_en,
            scene_image_path=self._scene_image_path,
            character_image_path=self._character_image_path,
            vocabulary=self._vocabulary,
            dialogue_history=self._dialogue_history,
        )
        
        self._set_html(html)
    
    def _get_current_title_zh(self) -> str:
        """获取当前主题的中文标题。"""
        from src.tools.english_conversation import TOPIC_LIBRARY
        if self._current_topic in TOPIC_LIBRARY:
            return TOPIC_LIBRARY[self._current_topic].title_zh
        return "英语对话"
    
    def _get_current_title_en(self) -> str:
        """获取当前主题的英文标题。"""
        from src.tools.english_conversation import TOPIC_LIBRARY
        if self._current_topic in TOPIC_LIBRARY:
            return TOPIC_LIBRARY[self._current_topic].title_en
        return "English Conversation"
    
    def _generate_scene_html(self, title_zh: str, title_en: str) -> str:
        """生成场景 HTML。"""
        # 处理图片路径（转换为本地 URL）
        scene_img_src = self._image_to_source(self._scene_image_path)
        char_img_src = self._image_to_source(self._character_image_path)
        
        # 生成词汇卡片
        vocab_html = self._generate_vocabulary_html()
        
        # 生成对话内容
        dialogue_html = self._generate_dialogue_html()
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header h2 {{ font-size: 1.5em; opacity: 0.9; }}
        
        /* Scene Images */
        .scene-section {{
            display: grid;
            grid-template-columns: 3fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .scene-img-container, .character-img-container {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .scene-img-container img {{ width: 100%; height: 400px; object-fit: cover; }}
        .character-img-container img {{ width: 100%; height: 400px; object-fit: cover; }}
        
        /* Vocabulary */
        .vocab-section {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .vocab-section h3 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .vocab-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 15px;
        }}
        .vocab-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s;
        }}
        .vocab-card:hover {{ transform: translateY(-5px); }}
        .vocab-card .word {{ font-size: 1.3em; font-weight: bold; margin-bottom: 5px; }}
        .vocab-card .meaning {{ font-size: 0.9em; opacity: 0.9; }}
        
        /* Dialogue */
        .dialogue-section {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .dialogue-section h3 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .dialogue-container {{ max-height: 500px; overflow-y: auto; }}
        .dialogue-line {{
            margin: 15px 0;
            padding: 20px;
            border-left: 5px solid;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .dialogue-line.user {{
            border-color: #4CAF50;
            background: #e8f5e9;
        }}
        .dialogue-line.ai {{
            border-color: #2196F3;
            background: #e3f2fd;
        }}
        .speaker {{
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
            font-size: 0.9em;
        }}
        .en-text {{
            font-size: 1.2em;
            color: #333;
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        .cn-text {{
            font-size: 1em;
            color: #666;
            font-style: italic;
        }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 10px; }}
        ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
        ::-webkit-scrollbar-thumb {{ background: #667eea; border-radius: 5px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #764ba2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title_zh}</h1>
            <h2>{title_en}</h2>
        </div>
        
        <div class="scene-section">
            <div class="scene-img-container">
                <img src="{scene_img_src}" alt="Scene">
            </div>
            <div class="character-img-container">
                <img src="{char_img_src}" alt="Character">
            </div>
        </div>
        
        {vocab_html}
        {dialogue_html}
    </div>
</body>
</html>'''
        
        return html
    
    def _generate_vocabulary_html(self) -> str:
        """生成词汇 HTML。"""
        if not self._vocabulary:
            return '<div class="vocab-section"><h3>📚 Key Vocabulary</h3><p>暂无词汇</p></div>'
        
        cards = []
        for vocab in self._vocabulary:
            word = vocab.get("en", "")
            meaning = vocab.get("cn", "")
            cards.append(f'''
            <div class="vocab-card">
                <div class="word">{word}</div>
                <div class="meaning">{meaning}</div>
            </div>
            ''')
        
        vocab_cards_html = "".join(cards)
        
        return f'''
        <div class="vocab-section">
            <h3>📚 Key Vocabulary</h3>
            <div class="vocab-grid">{vocab_cards_html}</div>
        </div>
        '''
    
    def _generate_dialogue_html(self) -> str:
        """生成对话 HTML。"""
        if not self._dialogue_history:
            return '<div class="dialogue-section"><h3>💬 Dialogue</h3><p>对话即将开始...</p></div>'
        
        lines = []
        for entry in self._dialogue_history:
            role = entry["role"]
            speaker = entry["speaker"]
            english = entry["english"]
            chinese = entry["chinese"]
            
            cn_html = f'<div class="cn-text">{chinese}</div>' if chinese else ''
            
            lines.append(f'''
            <div class="dialogue-line {role}">
                <div class="speaker">{speaker}</div>
                <div class="en-text">{english}</div>
                {cn_html}
            </div>
            ''')
        
        dialogue_lines_html = "".join(lines)
        
        return f'''
        <div class="dialogue-section">
            <h3>💬 Dialogue</h3>
            <div class="dialogue-container">{dialogue_lines_html}</div>
        </div>
        '''
    
    def _image_to_source(self, image_path: Optional[str]) -> str:
        """将图片路径转换为 HTML 可用的 source。"""
        if not image_path:
            # 返回占位图
            return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23ddd' width='400' height='300'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='20' fill='%23999'%3EImage Loading...%3C/text%3E%3C/svg%3E"
        
        # 转换为 file:// URL
        path = Path(image_path).resolve()
        if path.exists():
            return path.as_uri()
        else:
            logger.warning(f"图片不存在：{path}")
            return self._image_to_source(None)
    
    def _set_html(self, html: str):
        """设置 HTML 内容。"""
        logger.debug(f"准备设置 HTML，长度：{len(html)}")
        logger.debug(f"HTML 前 200 字符：{html[:200]}...")
        
        if WEB_ENGINE_AVAILABLE and hasattr(self, 'web_view'):
            logger.debug("使用 QWebEngineView 显示 HTML")
            
            # 方法 1: 直接 setHtml（可能有问题）
            self.web_view.setHtml(html)
            logger.info("HTML 已设置到 web_view (setHtml)")
            
            # 方法 2: 保存到临时文件并加载（更可靠）
            import tempfile
            from pathlib import Path
            from PySide6.QtCore import QUrl
            
            # 创建临时 HTML 文件
            temp_dir = Path(tempfile.gettempdir()) / "weclaw_english_ui"
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / "index.html"
            
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(html)
            
            logger.debug(f"临时文件已保存：{temp_file}")
            
            # 延迟加载临时文件（给 setHtml 一点时间）
            from PySide6.QtCore import QTimer
            def load_file():
                self.web_view.setUrl(QUrl.fromLocalFile(str(temp_file)))
                logger.info(f"HTML 已加载到 web_view (setUrl): {temp_file}")
            
            QTimer.singleShot(200, load_file)  # 200ms 后加载
            logger.debug("已安排延迟加载临时文件")
            
        elif hasattr(self, 'text_browser'):
            # 降级方案：转换为 Markdown
            import re
            logger.debug("使用 QTextBrowser 降级方案")
            # 简单转换：提取标题和文本
            title_match = re.search(r'<h1>([^<]+)</h1>', html)
            subtitle_match = re.search(r'<div class="subtitle">([^<]+)</div>', html)
            
            markdown = ""
            if title_match:
                markdown += f"# {title_match.group(1)}\n\n"
            if subtitle_match:
                markdown += f"**{subtitle_match.group(1)}**\n\n"
            
            self.text_browser.setMarkdown(markdown or "# 英语口语练习\n\n场景加载中...")
            logger.info(f"Markdown 已设置到 text_browser: {len(markdown)} 字符")
    
    def _on_refresh_clicked(self):
        """刷新按钮点击处理。"""
        self._refresh_dialogue()
        logger.info("用户点击刷新按钮")
    
    def _on_close_clicked(self):
        """关闭按钮点击处理。"""
        self.close_requested.emit()
        self.close()
        logger.info("用户关闭对话窗口")
    
    def closeEvent(self, event):
        """窗口关闭事件。"""
        self.close_requested.emit()
        event.accept()
