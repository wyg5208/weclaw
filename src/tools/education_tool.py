"""教育学习辅助工具 — 生成测验、闪卡、学习计划和概念解释。

本工具生成结构化的教育学习材料，支持：
- 测验题目生成（选择题、填空题、判断题、简答题）
- 交互式闪卡制作（HTML翻转卡片）
- 科学的学习计划（间隔重复原则）
- 概念解释文档
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class EducationTool(BaseTool):
    """教育学习辅助工具。

    生成测验题目、学习闪卡、学习计划和概念解释文档。
    """

    name = "education_tool"
    emoji = "📚"
    title = "教育学习"
    description = "教育学习辅助工具"
    timeout = 120

    def __init__(self, output_dir: str = None) -> None:
        """初始化教育学习工具。

        Args:
            output_dir: 输出目录，默认为项目的 generated/日期/ 目录
        """
        super().__init__()
        self.output_dir = (
            Path(output_dir) if output_dir
            else Path(__file__).parent.parent.parent / "generated" / datetime.now().strftime("%Y-%m-%d")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="generate_quiz",
                description="生成测验题目，支持选择题、填空题、判断题、简答题等多种题型",
                parameters={
                    "subject": {
                        "type": "string",
                        "description": "科目，如：数学、物理、编程、历史",
                    },
                    "topic": {
                        "type": "string",
                        "description": "具体主题，如：二次函数、牛顿定律、Python基础",
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "难度等级",
                        "enum": ["easy", "medium", "hard"],
                    },
                    "count": {
                        "type": "integer",
                        "description": "题目数量，默认10题",
                    },
                    "question_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["choice", "fill_blank", "true_false", "short_answer"],
                        },
                        "description": "题型列表：choice(选择题)、fill_blank(填空题)、true_false(判断题)、short_answer(简答题)",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["subject", "topic", "difficulty"],
            ),
            ActionDef(
                name="create_flashcards",
                description="制作学习闪卡，生成可翻转的交互式HTML闪卡页面",
                parameters={
                    "topic": {
                        "type": "string",
                        "description": "闪卡主题",
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "front": {"type": "string", "description": "正面（问题）"},
                                "back": {"type": "string", "description": "背面（答案）"},
                            },
                            "required": ["front", "back"],
                        },
                        "description": "闪卡内容列表，每项包含front(问题)和back(答案)",
                    },
                    "style": {
                        "type": "string",
                        "description": "闪卡风格",
                        "enum": ["simple", "detailed", "visual"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["topic", "items"],
            ),
            ActionDef(
                name="generate_study_plan",
                description="生成科学的学习计划，基于间隔重复原则安排每日学习内容",
                parameters={
                    "subject": {
                        "type": "string",
                        "description": "学习科目",
                    },
                    "duration_days": {
                        "type": "integer",
                        "description": "学习天数",
                    },
                    "goal": {
                        "type": "string",
                        "description": "学习目标",
                    },
                    "level": {
                        "type": "string",
                        "description": "当前水平",
                        "enum": ["beginner", "intermediate", "advanced"],
                    },
                    "hours_per_day": {
                        "type": "number",
                        "description": "每日学习小时数，默认2小时",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["subject", "duration_days", "goal", "level"],
            ),
            ActionDef(
                name="explain_concept",
                description="生成概念解释文档，包含定义、原理、示例、类比和相关概念",
                parameters={
                    "concept": {
                        "type": "string",
                        "description": "要解释的概念",
                    },
                    "level": {
                        "type": "string",
                        "description": "目标受众水平",
                        "enum": ["elementary", "middle", "high", "college", "expert"],
                    },
                    "examples": {
                        "type": "boolean",
                        "description": "是否包含示例，默认true",
                    },
                    "analogies": {
                        "type": "boolean",
                        "description": "是否包含类比，默认true",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["concept"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的教育学习动作。"""
        action_map = {
            "generate_quiz": self._generate_quiz,
            "create_flashcards": self._create_flashcards,
            "generate_study_plan": self._generate_study_plan,
            "explain_concept": self._explain_concept,
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}，支持的动作: {list(action_map.keys())}",
            )

        try:
            return handler(params)
        except Exception as e:
            logger.error("教育工具执行失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"教育学习内容生成失败: {e}",
            )

    def _generate_quiz(self, params: dict[str, Any]) -> ToolResult:
        """生成测验题目。"""
        subject = params.get("subject", "").strip()
        topic = params.get("topic", "").strip()
        difficulty = params.get("difficulty", "medium")
        count = params.get("count", 10)
        question_types = params.get("question_types", ["choice", "fill_blank", "true_false"])
        filename = params.get("output_filename", "").strip()

        if not subject:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="科目不能为空",
            )
        if not topic:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="主题不能为空",
            )

        if not isinstance(count, int) or count < 1:
            count = 10
        count = min(count, 50)  # 限制最多50题

        difficulty_names = {"easy": "简单", "medium": "中等", "hard": "困难"}
        difficulty_name = difficulty_names.get(difficulty, "中等")

        type_names = {
            "choice": "选择题",
            "fill_blank": "填空题",
            "true_false": "判断题",
            "short_answer": "简答题",
        }

        # 生成Markdown测验内容
        md_content = self._generate_quiz_markdown(
            subject, topic, difficulty, difficulty_name, count, question_types, type_names
        )

        # 生成JSON数据结构
        json_data = self._generate_quiz_json(
            subject, topic, difficulty, count, question_types
        )

        # 保存Markdown文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quiz_{subject}_{timestamp}"

        md_path = self.output_dir / f"{filename}.md"
        md_path.write_text(md_content, encoding="utf-8")

        json_path = self.output_dir / f"{filename}.json"
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info("测验题目已生成: %s", md_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 测验题目已生成\n📁 Markdown: {md_path.name}\n📁 JSON: {json_path.name}\n📝 科目: {subject}\n📖 主题: {topic}\n⭐ 难度: {difficulty_name}\n🔢 题目数: {count}",
            data={
                "md_file_path": str(md_path),
                "json_file_path": str(json_path),
                "subject": subject,
                "topic": topic,
                "difficulty": difficulty,
                "count": count,
                "question_types": question_types,
            },
        )

    def _generate_quiz_markdown(
        self, subject: str, topic: str, difficulty: str, difficulty_name: str,
        count: int, question_types: list, type_names: dict
    ) -> str:
        """生成测验题目的Markdown内容。"""
        types_str = "、".join(type_names.get(t, t) for t in question_types)

        content = f"""# {subject} 测验：{topic}

> **科目**：{subject}
> **主题**：{topic}
> **难度**：{difficulty_name}
> **题目数量**：{count} 题
> **题型**：{types_str}
> **生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 答题说明

- 请在规定时间内独立完成所有题目
- 选择题每题只有一个正确答案
- 填空题请填写完整准确的答案
- 判断题请选择"正确"或"错误"
- 简答题请条理清晰地作答

---

## 试题部分

"""
        question_num = 1

        # 根据题型分配题目数量
        type_count = len(question_types)
        base_count = count // type_count
        remainder = count % type_count

        for idx, qtype in enumerate(question_types):
            type_questions = base_count + (1 if idx < remainder else 0)
            if type_questions == 0:
                continue

            type_name = type_names.get(qtype, qtype)
            content += f"### {type_name}\n\n"

            for i in range(type_questions):
                if qtype == "choice":
                    content += self._generate_choice_template(question_num)
                elif qtype == "fill_blank":
                    content += self._generate_fill_blank_template(question_num)
                elif qtype == "true_false":
                    content += self._generate_true_false_template(question_num)
                elif qtype == "short_answer":
                    content += self._generate_short_answer_template(question_num)
                question_num += 1

        # 添加答案部分
        content += """---

## 参考答案

"""
        question_num = 1
        for idx, qtype in enumerate(question_types):
            type_questions = base_count + (1 if idx < remainder else 0)
            type_name = type_names.get(qtype, qtype)
            if type_questions > 0:
                content += f"### {type_name}答案\n\n"
                for i in range(type_questions):
                    content += f"**第{question_num}题**\n"
                    content += "- **答案**：[填写正确答案]\n"
                    content += "- **解析**：[填写解题思路和知识点说明]\n\n"
                    question_num += 1

        content += f"""---

> **使用提示**
> - 方括号 `[...]` 中的内容为模板占位符，请替换为实际内容
> - 可根据实际教学需要调整题目难度和数量
> - 建议结合{topic}的核心知识点出题
> - 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        return content

    def _generate_choice_template(self, num: int) -> str:
        """生成选择题模板。"""
        return f"""**{num}. [在此填写题目内容]**

A. [选项A]

B. [选项B]

C. [选项C]

D. [选项D]

"""

    def _generate_fill_blank_template(self, num: int) -> str:
        """生成填空题模板。"""
        return f"""**{num}. [在此填写题目内容，使用 ______ 表示空白处]**

______

"""

    def _generate_true_false_template(self, num: int) -> str:
        """生成判断题模板。"""
        return f"""**{num}. [在此填写判断题陈述]**

- [ ] 正确
- [ ] 错误

"""

    def _generate_short_answer_template(self, num: int) -> str:
        """生成简答题模板。"""
        return f"""**{num}. [在此填写简答题题目]**

**参考答题要点**：
- 要点1：[...]
- 要点2：[...]
- 要点3：[...]

"""

    def _generate_quiz_json(
        self, subject: str, topic: str, difficulty: str, count: int, question_types: list
    ) -> dict:
        """生成测验的JSON数据结构。"""
        questions = []
        type_count = len(question_types)
        base_count = count // type_count
        remainder = count % type_count

        question_id = 1
        for idx, qtype in enumerate(question_types):
            type_questions = base_count + (1 if idx < remainder else 0)
            for i in range(type_questions):
                question = {
                    "id": question_id,
                    "type": qtype,
                    "question": f"[第{question_id}题题目内容]",
                    "answer": "[正确答案]",
                    "explanation": "[答案解析]",
                }
                if qtype == "choice":
                    question["options"] = {
                        "A": "[选项A]",
                        "B": "[选项B]",
                        "C": "[选项C]",
                        "D": "[选项D]",
                    }
                elif qtype == "true_false":
                    question["answer"] = "[true/false]"
                questions.append(question)
                question_id += 1

        return {
            "quiz": {
                "subject": subject,
                "topic": topic,
                "difficulty": difficulty,
                "total_questions": count,
                "question_types": question_types,
                "created_at": datetime.now().isoformat(),
            },
            "questions": questions,
        }

    def _create_flashcards(self, params: dict[str, Any]) -> ToolResult:
        """创建学习闪卡。"""
        topic = params.get("topic", "").strip()
        items = params.get("items", [])
        style = params.get("style", "simple")
        filename = params.get("output_filename", "").strip()

        if not topic:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="闪卡主题不能为空",
            )
        if not items or not isinstance(items, list):
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="闪卡内容不能为空，需要提供items数组",
            )

        # 验证items格式
        valid_items = []
        for item in items:
            if isinstance(item, dict) and "front" in item and "back" in item:
                valid_items.append({
                    "front": str(item["front"]).strip(),
                    "back": str(item["back"]).strip(),
                })

        if not valid_items:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="闪卡内容格式错误，每项需包含front和back字段",
            )

        style_names = {"simple": "简约", "detailed": "详细", "visual": "视觉"}
        style_name = style_names.get(style, "简约")

        # 生成HTML闪卡
        html_content = self._generate_flashcard_html(topic, valid_items, style)

        # 生成Markdown文本版本
        md_content = self._generate_flashcard_markdown(topic, valid_items, style_name)

        # 保存文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flashcards_{timestamp}"

        html_path = self.output_dir / f"{filename}.html"
        html_path.write_text(html_content, encoding="utf-8")

        md_path = self.output_dir / f"{filename}.md"
        md_path.write_text(md_content, encoding="utf-8")

        logger.info("学习闪卡已生成: %s", html_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 学习闪卡已生成\n📁 HTML(交互版): {html_path.name}\n📁 Markdown(文本版): {md_path.name}\n📖 主题: {topic}\n🃏 卡片数: {len(valid_items)}\n🎨 风格: {style_name}",
            data={
                "html_file_path": str(html_path),
                "md_file_path": str(md_path),
                "topic": topic,
                "card_count": len(valid_items),
                "style": style,
            },
        )

    def _generate_flashcard_html(self, topic: str, items: list, style: str) -> str:
        """生成交互式HTML闪卡页面。"""
        # 根据风格设置颜色
        colors = {
            "simple": {"primary": "#4A90D9", "secondary": "#67B26F", "bg": "#f5f7fa"},
            "detailed": {"primary": "#6B5B95", "secondary": "#88B04B", "bg": "#f0f0f5"},
            "visual": {"primary": "#FF6B6B", "secondary": "#4ECDC4", "bg": "#2C3E50"},
        }
        color = colors.get(style, colors["simple"])

        # 生成卡片数据JSON
        cards_json = json.dumps(items, ensure_ascii=False)

        text_color = "#ffffff" if style == "visual" else "#333333"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📚 {topic} - 学习闪卡</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: {color['bg']};
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            color: {text_color};
        }}

        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}

        .header h1 {{
            font-size: 2rem;
            color: {color['primary']};
            margin-bottom: 10px;
        }}

        .progress {{
            font-size: 1.2rem;
            color: {"#aaa" if style == "visual" else "#666"};
        }}

        .card-container {{
            perspective: 1000px;
            width: 100%;
            max-width: 600px;
            height: 350px;
            margin-bottom: 30px;
        }}

        .card {{
            width: 100%;
            height: 100%;
            position: relative;
            transform-style: preserve-3d;
            transition: transform 0.6s ease;
            cursor: pointer;
        }}

        .card.flipped {{
            transform: rotateY(180deg);
        }}

        .card-face {{
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .card-front {{
            background: linear-gradient(135deg, {color['primary']}, {color['primary']}dd);
            color: white;
        }}

        .card-back {{
            background: linear-gradient(135deg, {color['secondary']}, {color['secondary']}dd);
            color: white;
            transform: rotateY(180deg);
        }}

        .card-content {{
            font-size: 1.5rem;
            line-height: 1.6;
            max-height: 250px;
            overflow-y: auto;
        }}

        .card-label {{
            position: absolute;
            top: 15px;
            left: 20px;
            font-size: 0.9rem;
            opacity: 0.8;
        }}

        .card-hint {{
            position: absolute;
            bottom: 15px;
            font-size: 0.85rem;
            opacity: 0.7;
        }}

        .controls {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .btn {{
            padding: 12px 30px;
            font-size: 1rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }}

        .btn-prev, .btn-next {{
            background: {color['primary']};
            color: white;
        }}

        .btn-flip {{
            background: {color['secondary']};
            color: white;
        }}

        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}

        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}

        .shortcuts {{
            margin-top: 30px;
            text-align: center;
            font-size: 0.9rem;
            color: {"#888" if style == "visual" else "#999"};
        }}

        .shortcuts kbd {{
            background: {"#444" if style == "visual" else "#e0e0e0"};
            padding: 3px 8px;
            border-radius: 4px;
            font-family: monospace;
        }}

        @media (max-width: 600px) {{
            .card-container {{
                height: 300px;
            }}
            .card-content {{
                font-size: 1.2rem;
            }}
            .btn {{
                padding: 10px 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 {topic}</h1>
        <div class="progress">
            <span id="current">1</span> / <span id="total">{len(items)}</span>
        </div>
    </div>

    <div class="card-container">
        <div class="card" id="flashcard" onclick="flipCard()">
            <div class="card-face card-front">
                <span class="card-label">❓ 问题</span>
                <div class="card-content" id="front-content"></div>
                <span class="card-hint">点击翻转查看答案</span>
            </div>
            <div class="card-face card-back">
                <span class="card-label">💡 答案</span>
                <div class="card-content" id="back-content"></div>
                <span class="card-hint">点击翻转返回问题</span>
            </div>
        </div>
    </div>

    <div class="controls">
        <button class="btn btn-prev" id="prevBtn" onclick="prevCard()">⬅️ 上一张</button>
        <button class="btn btn-flip" onclick="flipCard()">🔄 翻转</button>
        <button class="btn btn-next" id="nextBtn" onclick="nextCard()">下一张 ➡️</button>
    </div>

    <div class="shortcuts">
        快捷键：<kbd>空格</kbd> 翻转 | <kbd>←</kbd> 上一张 | <kbd>→</kbd> 下一张
    </div>

    <script>
        const cards = {cards_json};
        let currentIndex = 0;
        let isFlipped = false;

        function updateCard() {{
            const card = cards[currentIndex];
            document.getElementById('front-content').textContent = card.front;
            document.getElementById('back-content').textContent = card.back;
            document.getElementById('current').textContent = currentIndex + 1;
            document.getElementById('total').textContent = cards.length;

            // 重置翻转状态
            isFlipped = false;
            document.getElementById('flashcard').classList.remove('flipped');

            // 更新按钮状态
            document.getElementById('prevBtn').disabled = currentIndex === 0;
            document.getElementById('nextBtn').disabled = currentIndex === cards.length - 1;
        }}

        function flipCard() {{
            isFlipped = !isFlipped;
            document.getElementById('flashcard').classList.toggle('flipped');
        }}

        function prevCard() {{
            if (currentIndex > 0) {{
                currentIndex--;
                updateCard();
            }}
        }}

        function nextCard() {{
            if (currentIndex < cards.length - 1) {{
                currentIndex++;
                updateCard();
            }}
        }}

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') {{
                e.preventDefault();
                flipCard();
            }} else if (e.code === 'ArrowLeft') {{
                prevCard();
            }} else if (e.code === 'ArrowRight') {{
                nextCard();
            }}
        }});

        // 初始化
        updateCard();
    </script>
</body>
</html>"""

    def _generate_flashcard_markdown(self, topic: str, items: list, style_name: str) -> str:
        """生成闪卡的Markdown文本版本。"""
        content = f"""# 📚 学习闪卡：{topic}

> **卡片数量**：{len(items)} 张
> **风格**：{style_name}
> **生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 闪卡列表

"""
        for idx, item in enumerate(items, 1):
            content += f"""### 卡片 {idx}

**❓ 问题**：{item['front']}

**💡 答案**：{item['back']}

---

"""

        content += """## 学习建议

1. **首次学习**：按顺序浏览所有卡片，熟悉内容
2. **间隔复习**：使用间隔重复法，逐步延长复习间隔
3. **主动回忆**：看到问题先尝试回忆，再翻转查看答案
4. **标记难点**：对不熟悉的卡片重点复习

---

> 💡 提示：打开 HTML 文件可以获得交互式翻转卡片体验
"""
        return content

    def _generate_study_plan(self, params: dict[str, Any]) -> ToolResult:
        """生成学习计划。"""
        subject = params.get("subject", "").strip()
        duration_days = params.get("duration_days", 30)
        goal = params.get("goal", "").strip()
        level = params.get("level", "beginner")
        hours_per_day = params.get("hours_per_day", 2)
        filename = params.get("output_filename", "").strip()

        if not subject:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学习科目不能为空",
            )
        if not goal:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学习目标不能为空",
            )

        if not isinstance(duration_days, int) or duration_days < 1:
            duration_days = 30
        duration_days = min(duration_days, 365)  # 限制最长一年

        if not isinstance(hours_per_day, (int, float)) or hours_per_day < 0.5:
            hours_per_day = 2
        hours_per_day = min(hours_per_day, 12)  # 限制每天最多12小时

        level_names = {"beginner": "初学者", "intermediate": "中级", "advanced": "高级"}
        level_name = level_names.get(level, "初学者")

        # 生成学习计划
        content = self._generate_study_plan_content(
            subject, duration_days, goal, level, level_name, hours_per_day
        )

        # 保存文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"study_plan_{subject}_{timestamp}"

        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")

        logger.info("学习计划已生成: %s", output_path)

        total_hours = duration_days * hours_per_day

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 学习计划已生成\n📁 文件: {output_path.name}\n📚 科目: {subject}\n🎯 目标: {goal}\n📅 周期: {duration_days}天\n⏰ 每日: {hours_per_day}小时\n📊 总学时: {total_hours}小时",
            data={
                "file_path": str(output_path),
                "subject": subject,
                "goal": goal,
                "duration_days": duration_days,
                "hours_per_day": hours_per_day,
                "total_hours": total_hours,
                "level": level,
            },
        )

    def _generate_study_plan_content(
        self, subject: str, duration_days: int, goal: str,
        level: str, level_name: str, hours_per_day: float
    ) -> str:
        """生成学习计划的Markdown内容。"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        total_hours = duration_days * hours_per_day

        # 根据水平设置学习阶段比例
        level_phases = {
            "beginner": {"基础": 0.4, "进阶": 0.35, "巩固": 0.25},
            "intermediate": {"基础": 0.2, "进阶": 0.5, "巩固": 0.3},
            "advanced": {"基础": 0.1, "进阶": 0.4, "巩固": 0.5},
        }
        phases = level_phases.get(level, level_phases["beginner"])

        # 计算每个阶段的天数
        phase_days = {
            name: int(duration_days * ratio)
            for name, ratio in phases.items()
        }
        # 调整剩余天数
        remaining = duration_days - sum(phase_days.values())
        phase_days["巩固"] += remaining

        content = f"""# 📚 {subject} 学习计划

## 计划概览

| 项目 | 内容 |
|------|------|
| 🎯 **学习目标** | {goal} |
| 📚 **学习科目** | {subject} |
| 🏆 **当前水平** | {level_name} |
| 📅 **开始日期** | {start_date.strftime("%Y年%m月%d日")} |
| 📅 **结束日期** | {end_date.strftime("%Y年%m月%d日")} |
| ⏱️ **计划周期** | {duration_days} 天 |
| ⏰ **每日学时** | {hours_per_day} 小时 |
| 📊 **总学习时长** | {total_hours} 小时 |

---

## 🧠 学习方法论：间隔重复原则

本计划基于**艾宾浩斯遗忘曲线**和**间隔重复**原则设计：

```
记忆保持率
    100% ┤●
         │ \\
     80% ┤  \\  ← 第一次复习
         │   \\__●
     60% ┤       \\
         │        \\__●  ← 第二次复习
     40% ┤             \\__
         │                 \\__●  ← 第三次复习
     20% ┤                      \\____●____●
         └──────────────────────────────────→ 时间
          1天  2天  4天  7天  15天  30天
```

**复习时间节点**：
- 📌 学习后 20 分钟内：第一次复习
- 📌 学习后 1 天：第二次复习
- 📌 学习后 2-4 天：第三次复习
- 📌 学习后 7 天：第四次复习
- 📌 学习后 15 天：第五次复习
- 📌 学习后 30 天：第六次复习

---

## 📋 阶段规划

"""
        current_day = 1
        for phase_name, days in phase_days.items():
            if days <= 0:
                continue
            end_day = current_day + days - 1
            phase_start = start_date + timedelta(days=current_day - 1)
            phase_end = start_date + timedelta(days=end_day - 1)

            content += f"""### 阶段：{phase_name}（第 {current_day}-{end_day} 天）

**时间范围**：{phase_start.strftime("%m月%d日")} - {phase_end.strftime("%m月%d日")}（共 {days} 天）

**阶段目标**：[根据{subject}的{phase_name}阶段目标填写]

**核心内容**：
1. [知识点/技能 1]
2. [知识点/技能 2]
3. [知识点/技能 3]

**每日安排模板**：
- ⏰ 前 {int(hours_per_day * 0.6 * 60)} 分钟：学习新内容
- ⏰ 中间 {int(hours_per_day * 0.25 * 60)} 分钟：练习巩固
- ⏰ 最后 {int(hours_per_day * 0.15 * 60)} 分钟：复习回顾

**阶段验收标准**：
- [ ] [验收项目 1]
- [ ] [验收项目 2]

---

"""
            current_day = end_day + 1

        # 生成每周计划模板
        weeks = (duration_days + 6) // 7
        content += """## 📅 每周详细计划

"""
        for week in range(1, min(weeks + 1, 13)):  # 最多显示12周
            week_start = (week - 1) * 7 + 1
            week_end = min(week * 7, duration_days)
            week_start_date = start_date + timedelta(days=week_start - 1)
            week_end_date = start_date + timedelta(days=week_end - 1)

            content += f"""### 第 {week} 周（{week_start_date.strftime("%m/%d")} - {week_end_date.strftime("%m/%d")}）

| 日期 | 学习内容 | 练习任务 | 复习内容 | 完成情况 |
|------|---------|---------|---------|---------|
"""
            for day_offset in range(week_start - 1, week_end):
                day_date = start_date + timedelta(days=day_offset)
                day_num = day_offset + 1
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day_date.weekday()]
                content += f"| {day_date.strftime('%m/%d')} {weekday} | [内容] | [练习] | [复习] | ⬜ |\n"

            content += "\n"

            if week >= 4:
                content += f"""... (共 {weeks} 周，此处省略后续周计划模板)

"""
                break

        content += f"""---

## 📝 学习资源清单

### 必备资源
1. **教材/书籍**：[推荐的{subject}学习教材]
2. **在线课程**：[推荐的网课平台和课程]
3. **练习平台**：[刷题/练习网站]

### 补充资源
1. **视频资源**：[B站/YouTube相关频道]
2. **文档资料**：[官方文档/技术博客]
3. **社区论坛**：[交流讨论平台]

---

## 🎯 里程碑检查点

| 检查点 | 时间 | 目标达成标准 | 状态 |
|--------|------|-------------|------|
| 🏁 起点测评 | 第 1 天 | 完成入门测试，确定基准水平 | ⬜ |
| 📍 阶段一结束 | 第 {phase_days.get("基础", 7)} 天 | [基础阶段验收标准] | ⬜ |
| 📍 中期检查 | 第 {duration_days // 2} 天 | 完成 50% 学习内容 | ⬜ |
| 📍 阶段二结束 | 第 {phase_days.get("基础", 7) + phase_days.get("进阶", 14)} 天 | [进阶阶段验收标准] | ⬜ |
| 🏆 终点评估 | 第 {duration_days} 天 | {goal} | ⬜ |

---

## 📈 学习追踪表

### 每日学习记录模板

```markdown
## {start_date.strftime("%Y-%m-%d")} 学习记录

### 今日学习内容
- [ ] 

### 遇到的问题
- 

### 明日计划
- 

### 学习时长
- 计划：{hours_per_day} 小时
- 实际：__ 小时

### 今日收获
- 
```

---

## 💡 学习建议

1. **保持规律**：每天固定时间学习，养成习惯
2. **及时复习**：遵循间隔重复原则，定时回顾
3. **主动输出**：通过做笔记、教别人来加深理解
4. **循序渐进**：不要贪多，确保每个知识点都理解透彻
5. **劳逸结合**：适当休息，保证学习效率

---

> **生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 
> 📌 本计划为框架模板，请根据实际情况调整具体内容
"""
        return content

    def _explain_concept(self, params: dict[str, Any]) -> ToolResult:
        """生成概念解释文档。"""
        concept = params.get("concept", "").strip()
        level = params.get("level", "college")
        include_examples = params.get("examples", True)
        include_analogies = params.get("analogies", True)
        filename = params.get("output_filename", "").strip()

        if not concept:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="概念不能为空",
            )

        level_names = {
            "elementary": "小学",
            "middle": "初中",
            "high": "高中",
            "college": "大学",
            "expert": "专家",
        }
        level_name = level_names.get(level, "大学")

        # 生成概念解释文档
        content = self._generate_concept_explanation(
            concept, level, level_name, include_examples, include_analogies
        )

        # 保存文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concept_{timestamp}"

        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")

        logger.info("概念解释已生成: %s", output_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 概念解释已生成\n📁 文件: {output_path.name}\n📖 概念: {concept}\n🎓 难度: {level_name}水平\n📝 包含示例: {'是' if include_examples else '否'}\n🔗 包含类比: {'是' if include_analogies else '否'}",
            data={
                "file_path": str(output_path),
                "concept": concept,
                "level": level,
                "include_examples": include_examples,
                "include_analogies": include_analogies,
            },
        )

    def _generate_concept_explanation(
        self, concept: str, level: str, level_name: str,
        include_examples: bool, include_analogies: bool
    ) -> str:
        """生成概念解释的Markdown内容。"""
        # 根据难度级别调整语言复杂度提示
        language_hints = {
            "elementary": "使用简单词汇，短句为主，多用比喻",
            "middle": "使用日常词汇，适当引入术语并解释",
            "high": "可使用专业术语，注重逻辑推导",
            "college": "使用学术语言，强调理论体系",
            "expert": "使用专业术语，深入技术细节",
        }
        language_hint = language_hints.get(level, language_hints["college"])

        content = f"""# 📖 概念解释：{concept}

> **目标受众**：{level_name}水平
> **语言风格**：{language_hint}
> **生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、定义

### 简明定义
[用一句话清晰定义{concept}]

### 详细解释
[展开说明{concept}的含义，适合{level_name}水平读者理解]

**关键要素**：
1. **要素一**：[核心组成部分或特征]
2. **要素二**：[核心组成部分或特征]
3. **要素三**：[核心组成部分或特征]

---

## 二、原理/机制

### 基本原理
[解释{concept}背后的工作原理或理论基础]

### 运作机制
[描述{concept}如何运作或发生作用]

```
[可选：用图表或流程说明]

    输入 → [处理过程] → 输出
           ↑      ↓
        [反馈/循环]
```

### 核心公式/规则（如适用）
[列出相关的数学公式、定律或规则]

---

"""

        if include_examples:
            content += """## 三、示例

### 示例 1：基础应用
**场景**：[描述具体场景]

**说明**：
[详细解释这个示例如何体现概念]

### 示例 2：进阶应用
**场景**：[描述更复杂的场景]

**说明**：
[详细解释]

### 示例 3：实际案例
**背景**：[真实世界的案例]

**分析**：
[分析案例如何应用该概念]

---

"""

        if include_analogies:
            content += f"""## {"四" if include_examples else "三"}、类比理解

### 类比 1：生活类比
**类比对象**：[选择日常生活中的事物]

**相似之处**：
- {concept} 就像 [类比对象]，因为...
- 两者都具有 [共同特征]...

### 类比 2：形象比喻
**比喻**：[用形象的比喻解释]

**解释**：
[为什么这个比喻是恰当的]

---

"""

        section_num = 3
        if include_examples:
            section_num += 1
        if include_analogies:
            section_num += 1

        content += f"""## {["一", "二", "三", "四", "五", "六"][section_num]}、相关概念

### 上位概念（更广泛的概念）
- **[概念名称]**：[简要说明与{concept}的关系]

### 下位概念（更具体的概念）
- **[概念名称]**：[简要说明是{concept}的一种具体形式]

### 相关概念
| 概念 | 与{concept}的关系 | 区别 |
|------|-----------------|------|
| [概念A] | [关系说明] | [主要区别] |
| [概念B] | [关系说明] | [主要区别] |
| [概念C] | [关系说明] | [主要区别] |

### 对比概念
**{concept} vs [对比概念]**

| 方面 | {concept} | [对比概念] |
|------|----------|-----------|
| 定义 | ... | ... |
| 特点 | ... | ... |
| 应用 | ... | ... |

---

## {["一", "二", "三", "四", "五", "六", "七"][section_num + 1]}、应用场景

### 典型应用
1. **应用领域一**：[描述如何应用]
2. **应用领域二**：[描述如何应用]
3. **应用领域三**：[描述如何应用]

### 实践价值
[说明掌握{concept}的实际意义和价值]

---

## {["一", "二", "三", "四", "五", "六", "七", "八"][section_num + 2]}、常见误区

### 误区 1
❌ **错误理解**：[常见的错误认识]

✅ **正确理解**：[纠正后的正确认识]

### 误区 2
❌ **错误理解**：[另一个常见错误]

✅ **正确理解**：[正确的理解方式]

---

## 延伸阅读

### 推荐资源
1. **书籍**：[相关书籍推荐]
2. **文章**：[相关文章/论文]
3. **视频**：[相关视频教程]

### 深入学习路径
1. 先理解：[前置概念]
2. 再掌握：{concept}
3. 后学习：[后续概念]

---

## 快速回顾

### 核心要点
- ✅ {concept}是...
- ✅ 核心原理是...
- ✅ 主要应用于...

### 一句话总结
> [用一句话概括{concept}的本质]

---

> **使用提示**
> - 方括号 `[...]` 中的内容为模板占位符，请替换为实际内容
> - 根据{level_name}水平读者的认知特点调整语言复杂度
> - 示例和类比应贴近目标读者的经验背景
"""
        return content


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = EducationTool()

        # 测试生成测验
        result = await tool.execute("generate_quiz", {
            "subject": "Python编程",
            "topic": "列表和字典",
            "difficulty": "medium",
            "count": 5,
            "question_types": ["choice", "fill_blank"],
        })
        print(result.output)
        print("---")

        # 测试创建闪卡
        result = await tool.execute("create_flashcards", {
            "topic": "Python基础",
            "items": [
                {"front": "什么是列表？", "back": "列表是Python中的有序可变序列，用方括号[]表示"},
                {"front": "如何创建空字典？", "back": "使用 {} 或 dict()"},
            ],
            "style": "simple",
        })
        print(result.output)
        print("---")

        # 测试生成学习计划
        result = await tool.execute("generate_study_plan", {
            "subject": "Python",
            "duration_days": 30,
            "goal": "掌握Python基础语法和常用库",
            "level": "beginner",
            "hours_per_day": 2,
        })
        print(result.output)
        print("---")

        # 测试概念解释
        result = await tool.execute("explain_concept", {
            "concept": "递归",
            "level": "high",
            "examples": True,
            "analogies": True,
        })
        print(result.output)

    asyncio.run(test())
