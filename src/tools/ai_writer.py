"""AI 写作工具 — 生成结构化的写作框架和模板。

本工具的核心功能是生成结构化的写作提示词并以 Markdown 格式输出到文件。
它不直接调用 LLM API（LLM 调用由上层 conversation 模块处理）。

支持功能：
- 论文框架生成
- 文章大纲生成
- 小说创作结构
- 续写提纲
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class AIWriterTool(BaseTool):
    """AI 辅助写作工具。

    生成结构化的写作框架、大纲和模板，输出为 Markdown 格式文件。
    """

    name = "ai_writer"
    emoji = "✍️"
    title = "AI写作"
    description = "AI 辅助写作：生成论文框架、文章大纲、小说结构、续写提纲"
    timeout = 60

    def __init__(self, output_dir: str = "") -> None:
        """初始化 AI 写作工具。

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
                name="write_paper",
                description="生成学术论文的标准结构框架与模板，包含摘要、引言、文献综述、研究方法、结果、讨论、结论等章节",
                parameters={
                    "topic": {
                        "type": "string",
                        "description": "论文主题",
                    },
                    "subject": {
                        "type": "string",
                        "description": "学科领域，如：计算机科学、经济学、教育学",
                    },
                    "length": {
                        "type": "string",
                        "description": "目标字数：short(3000字)/medium(5000字)/long(10000字)",
                        "enum": ["short", "medium", "long"],
                    },
                    "requirements": {
                        "type": "string",
                        "description": "特殊要求，如：需要包含实证分析、文献综述等",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["topic"],
            ),
            ActionDef(
                name="write_article",
                description="生成文章内容框架，支持科普、叙事、议论、技术等多种风格",
                parameters={
                    "topic": {
                        "type": "string",
                        "description": "文章主题",
                    },
                    "style": {
                        "type": "string",
                        "description": "风格: informative(科普)/narrative(叙事)/persuasive(议论)/technical(技术)",
                        "enum": ["informative", "narrative", "persuasive", "technical"],
                    },
                    "length": {
                        "type": "string",
                        "description": "目标字数：short(1000字)/medium(2000字)/long(5000字)",
                        "enum": ["short", "medium", "long"],
                    },
                    "keywords": {
                        "type": "string",
                        "description": "关键词，逗号分隔",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["topic"],
            ),
            ActionDef(
                name="write_novel",
                description="生成小说创作框架，包含世界观设定、角色设定、章节大纲和核心冲突",
                parameters={
                    "genre": {
                        "type": "string",
                        "description": "题材: fantasy(奇幻)/romance(言情)/mystery(悬疑)/scifi(科幻)/historical(历史)",
                        "enum": ["fantasy", "romance", "mystery", "scifi", "historical"],
                    },
                    "plot": {
                        "type": "string",
                        "description": "故事梗概",
                    },
                    "characters": {
                        "type": "string",
                        "description": "主要角色描述",
                    },
                    "chapters": {
                        "type": "integer",
                        "description": "章节数，默认10",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["genre"],
            ),
            ActionDef(
                name="continue_writing",
                description="分析已有文本，生成续写的大纲和方向建议",
                parameters={
                    "text": {
                        "type": "string",
                        "description": "已有文本内容",
                    },
                    "length": {
                        "type": "string",
                        "description": "续写字数：short(500字)/medium(1000字)/long(2000字)",
                        "enum": ["short", "medium", "long"],
                    },
                    "style": {
                        "type": "string",
                        "description": "续写风格提示",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["text"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的写作动作。"""
        action_map = {
            "write_paper": self._write_paper,
            "write_article": self._write_article,
            "write_novel": self._write_novel,
            "continue_writing": self._continue_writing,
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
            logger.error("写作工具执行失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"写作框架生成失败: {e}",
            )

    def _write_paper(self, params: dict[str, Any]) -> ToolResult:
        """生成论文框架与模板。"""
        topic = params.get("topic", "").strip()
        if not topic:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="论文主题不能为空",
            )

        subject = params.get("subject", "综合").strip() or "综合"
        length = params.get("length", "medium")
        requirements = params.get("requirements", "").strip()
        filename = params.get("output_filename", "").strip()

        length_map = {"short": 3000, "medium": 5000, "long": 10000}
        target_words = length_map.get(length, 5000)

        # 生成论文框架
        content = f"""# {topic}

## 摘要

[在此处撰写摘要，约200-300字，概括研究目的、方法、主要发现和结论]

**关键词**：{topic}；{subject}；[补充3-5个关键词]

---

## 1. 引言

### 1.1 研究背景
[阐述{topic}的研究背景和现实意义]

- 当前领域发展现状
- 存在的主要问题与挑战
- 研究的紧迫性与必要性

### 1.2 研究目的
[明确本文的研究目的和研究问题]

- 核心研究问题
- 研究假设（如适用）
- 预期达成的目标

### 1.3 研究意义
[阐述理论意义和实践价值]

- 理论贡献
- 实践应用价值
- 对相关领域的启示

## 2. 文献综述

### 2.1 核心概念界定
[定义本研究涉及的核心概念和术语]

### 2.2 国内研究现状
[综述国内相关研究]

- 主要研究成果
- 研究方法特点
- 现有研究的贡献

### 2.3 国外研究现状
[综述国外相关研究]

- 国际前沿进展
- 代表性研究与理论
- 研究趋势

### 2.4 研究述评
[对已有研究进行评述，指出不足和研究空白]

- 已有研究的贡献总结
- 现有研究的局限性
- 本研究的切入点

## 3. 研究方法

### 3.1 研究设计
[描述研究设计和技术路线]

- 总体研究框架
- 研究路径与步骤
- 技术路线图

### 3.2 数据来源
[说明数据收集方法和来源]

- 数据收集方式
- 样本选择与规模
- 数据质量保证

### 3.3 分析方法
[描述采用的分析方法]

- 主要分析工具与软件
- 分析步骤与流程
- 信效度检验

## 4. 研究结果

### 4.1 描述性分析
[呈现基本数据和描述统计]

- 样本基本特征
- 变量描述统计
- 数据分布情况

### 4.2 主要发现
[呈现核心研究发现]

- 发现一：[标题]
  - 具体结果
  - 数据支持
  
- 发现二：[标题]
  - 具体结果
  - 数据支持

### 4.3 假设检验（如适用）
[呈现假设检验结果]

## 5. 讨论

### 5.1 结果讨论
[对研究结果进行深入讨论]

- 主要发现的解释
- 与已有研究的比较
- 结果的合理性分析

### 5.2 理论贡献
[阐述理论层面的贡献]

- 对现有理论的验证/修正/扩展
- 新的理论见解

### 5.3 实践启示
[阐述实践层面的启示]

- 对实践者的建议
- 政策启示
- 应用前景

## 6. 结论

### 6.1 主要结论
[总结研究的主要结论]

1. 结论一
2. 结论二
3. 结论三

### 6.2 研究局限
[说明本研究的局限性]

- 数据局限
- 方法局限
- 推广性局限

### 6.3 未来研究方向
[提出未来可能的研究方向]

- 研究延伸方向一
- 研究延伸方向二

## 参考文献

[按照{subject}学科规范格式列出参考文献，建议使用 GB/T 7714 或 APA 格式]

1. [作者]. [题名][文献类型标识]. [出版地]: [出版者], [出版年].
2. [作者]. [题名][J]. [刊名], [年], [卷](期): 页码.

---

> **写作说明**
> - 学科领域：{subject}
> - 目标字数：约 {target_words} 字
> - 特殊要求：{requirements if requirements else "无"}
> - 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

> **使用提示**
> - 方括号 `[...]` 中的内容为写作提示，请替换为实际内容
> - 可根据实际研究需要调整章节结构
> - 建议先完成大纲，再逐步填充内容
"""

        # 保存到文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paper_{timestamp}"
        
        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")
        file_size = output_path.stat().st_size

        logger.info("论文框架已生成: %s", output_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 写作框架已生成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📝 类型: 学术论文\n🎯 目标字数: {target_words}",
            data={
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "writing_type": "paper",
                "target_words": target_words,
                "topic": topic,
                "subject": subject,
            },
        )

    def _write_article(self, params: dict[str, Any]) -> ToolResult:
        """生成文章内容框架。"""
        topic = params.get("topic", "").strip()
        if not topic:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="文章主题不能为空",
            )

        style = params.get("style", "informative")
        length = params.get("length", "medium")
        keywords = params.get("keywords", "").strip()
        filename = params.get("output_filename", "").strip()

        length_map = {"short": 1000, "medium": 2000, "long": 5000}
        target_words = length_map.get(length, 2000)

        style_names = {
            "informative": "科普知识类",
            "narrative": "叙事故事类",
            "persuasive": "议论说服类",
            "technical": "技术教程类",
        }
        style_name = style_names.get(style, "科普知识类")

        # 根据风格生成不同的框架
        if style == "informative":
            content = self._generate_informative_article(topic, keywords, target_words)
        elif style == "narrative":
            content = self._generate_narrative_article(topic, keywords, target_words)
        elif style == "persuasive":
            content = self._generate_persuasive_article(topic, keywords, target_words)
        elif style == "technical":
            content = self._generate_technical_article(topic, keywords, target_words)
        else:
            content = self._generate_informative_article(topic, keywords, target_words)

        # 保存到文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"article_{timestamp}"
        
        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")
        file_size = output_path.stat().st_size

        logger.info("文章框架已生成: %s", output_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 写作框架已生成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📝 类型: {style_name}\n🎯 目标字数: {target_words}",
            data={
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "writing_type": "article",
                "style": style,
                "target_words": target_words,
                "topic": topic,
            },
        )

    def _generate_informative_article(self, topic: str, keywords: str, target_words: int) -> str:
        """生成科普/知识类文章框架。"""
        return f"""# {topic}

> **文章类型**：科普知识类
> **目标字数**：{target_words} 字
> **关键词**：{keywords if keywords else topic}

---

## 引言

[开篇引入，可以使用以下方式之一]
- 提出一个引人思考的问题
- 描述一个有趣的现象或事实
- 讲述一个相关的小故事
- 引用一句名言或数据

## 什么是{topic}？

### 基本定义
[清晰准确地定义核心概念]

### 起源与发展
[简述历史背景和发展脉络]

## 核心知识点

### 要点一：[标题]
[详细解释第一个知识要点]
- 关键信息
- 举例说明
- 实际应用

### 要点二：[标题]
[详细解释第二个知识要点]
- 关键信息
- 举例说明
- 实际应用

### 要点三：[标题]
[详细解释第三个知识要点]

## 常见误区

[列举读者可能存在的误解]
- ❌ 误区一：[描述]
  - ✅ 正确理解：[解释]
- ❌ 误区二：[描述]
  - ✅ 正确理解：[解释]

## 实用建议

[给读者的实际行动建议]
1. 建议一
2. 建议二
3. 建议三

## 总结

[用简洁的语言总结全文要点，强化读者印象]

---

> **写作提示**
> - 使用通俗易懂的语言，避免过多专业术语
> - 多用类比、比喻帮助读者理解
> - 适当加入图表、数据增强说服力
> - 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _generate_narrative_article(self, topic: str, keywords: str, target_words: int) -> str:
        """生成叙事类文章框架。"""
        return f"""# {topic}

> **文章类型**：叙事故事类
> **目标字数**：{target_words} 字
> **关键词**：{keywords if keywords else topic}

---

## 开篇：设置悬念

[用一个吸引人的场景或问题开始]
- 时间、地点、人物
- 制造悬念或情感共鸣
- 引出故事主线

## 第一幕：背景铺垫

### 人物介绍
[主要人物的基本信息和性格特点]

### 场景描写
[故事发生的环境和氛围]

### 起因
[故事的起因，是什么触发了后续的事件]

## 第二幕：发展与冲突

### 转折点一
[第一个重要转折]
- 发生了什么
- 人物的反应
- 情感变化

### 冲突升级
[矛盾激化的过程]

### 转折点二
[第二个重要转折]

## 第三幕：高潮

[故事最紧张、最精彩的部分]
- 核心冲突的爆发
- 人物的选择与行动
- 悬念的最高点

## 第四幕：结局

### 问题解决
[冲突如何被解决]

### 人物成长
[主人公的变化与成长]

### 余韵
[给读者留下的思考空间]

## 结尾：点题升华

[总结故事的意义，引发读者共鸣]

---

> **写作提示**
> - 注重细节描写，让读者身临其境
> - 人物对话要生动自然
> - 把握好叙事节奏，避免平铺直叙
> - 情感真挚，能打动读者
> - 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _generate_persuasive_article(self, topic: str, keywords: str, target_words: int) -> str:
        """生成议论/说服类文章框架。"""
        return f"""# {topic}

> **文章类型**：议论说服类
> **目标字数**：{target_words} 字
> **关键词**：{keywords if keywords else topic}

---

## 引言：提出论点

[开门见山，明确表达你的核心观点]

**核心论点**：[一句话概括你的主张]

## 背景分析

### 现状描述
[客观描述当前情况]

### 问题所在
[指出现存问题或争议]

### 为什么重要
[阐述讨论这个话题的意义]

## 论证一：[分论点1]

### 观点陈述
[清晰表达第一个支持论点的理由]

### 论据支持
- 事实依据：[数据、案例]
- 理论支撑：[权威观点、研究结论]
- 逻辑推理：[因果关系分析]

### 小结
[简短总结本段论证]

## 论证二：[分论点2]

### 观点陈述
[清晰表达第二个支持论点的理由]

### 论据支持
- 事实依据
- 理论支撑
- 逻辑推理

### 小结

## 论证三：[分论点3]

### 观点陈述

### 论据支持

### 小结

## 反驳预设质疑

### 可能的反对意见
[列举读者可能的质疑]

### 回应与反驳
[逐一回应这些质疑]

## 行动呼吁

[号召读者采取行动或改变观念]
1. 具体建议一
2. 具体建议二
3. 具体建议三

## 结论

[总结全文，重申核心论点，强化说服效果]

---

> **写作提示**
> - 论点要明确，论据要充分
> - 逻辑要严密，层层递进
> - 语言要有力，但避免过于偏激
> - 尊重不同观点，展现理性态度
> - 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _generate_technical_article(self, topic: str, keywords: str, target_words: int) -> str:
        """生成技术类文章框架。"""
        return f"""# {topic}

> **文章类型**：技术教程类
> **目标字数**：{target_words} 字
> **关键词**：{keywords if keywords else topic}

---

## 概述

### 是什么
[简明定义这个技术/工具/方法]

### 解决什么问题
[说明它的应用场景和解决的痛点]

### 适用人群
[明确目标读者和前置知识要求]

## 环境准备

### 系统要求
- 操作系统：
- 硬件配置：
- 依赖软件：

### 安装步骤
```bash
# 安装命令示例
```

### 验证安装
```bash
# 验证命令
```

## 快速入门

### Hello World 示例
[最简单的入门示例]

```
# 代码示例
```

### 运行结果
```
# 预期输出
```

## 核心概念

### 概念一：[名称]
[解释第一个核心概念]

### 概念二：[名称]
[解释第二个核心概念]

### 概念三：[名称]
[解释第三个核心概念]

## 实战案例

### 案例背景
[描述实际应用场景]

### 实现步骤

#### 步骤一：[标题]
```
# 代码
```
[解释说明]

#### 步骤二：[标题]
```
# 代码
```
[解释说明]

#### 步骤三：[标题]
```
# 代码
```
[解释说明]

### 完整代码
```
# 完整示例代码
```

### 运行效果
[展示最终效果]

## 常见问题

### Q1: [问题描述]
**A**: [解答]

### Q2: [问题描述]
**A**: [解答]

## 最佳实践

1. **实践一**：[描述]
2. **实践二**：[描述]
3. **实践三**：[描述]

## 进阶学习

### 推荐资源
- 官方文档：[链接]
- 相关教程：[链接]
- 社区论坛：[链接]

### 延伸话题
[列举可以进一步学习的相关主题]

## 总结

[总结本文重点，鼓励读者动手实践]

---

> **写作提示**
> - 代码示例要完整可运行
> - 步骤说明要清晰准确
> - 截图/图表辅助理解
> - 提供常见错误的解决方案
> - 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _write_novel(self, params: dict[str, Any]) -> ToolResult:
        """生成小说创作框架。"""
        genre = params.get("genre", "").strip()
        if not genre:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="小说题材不能为空",
            )

        plot = params.get("plot", "").strip()
        characters = params.get("characters", "").strip()
        chapters = params.get("chapters", 10)
        filename = params.get("output_filename", "").strip()

        if not isinstance(chapters, int) or chapters < 1:
            chapters = 10

        genre_names = {
            "fantasy": "奇幻",
            "romance": "言情",
            "mystery": "悬疑",
            "scifi": "科幻",
            "historical": "历史",
        }
        genre_name = genre_names.get(genre, "奇幻")

        # 生成小说框架
        content = self._generate_novel_framework(genre, genre_name, plot, characters, chapters)

        # 保存到文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"novel_{genre}_{timestamp}"
        
        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")
        file_size = output_path.stat().st_size

        logger.info("小说框架已生成: %s", output_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 写作框架已生成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📝 类型: {genre_name}小说\n📖 章节数: {chapters}",
            data={
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "writing_type": "novel",
                "genre": genre,
                "chapters": chapters,
            },
        )

    def _generate_novel_framework(self, genre: str, genre_name: str, plot: str, characters: str, chapters: int) -> str:
        """生成小说创作框架内容。"""
        # 根据题材生成不同的世界观提示
        worldbuilding_hints = {
            "fantasy": "魔法体系、种族设定、神话传说、地理版图",
            "romance": "社会背景、人物关系网、情感氛围",
            "mystery": "案件背景、线索布局、嫌疑人关系",
            "scifi": "科技水平、星际政治、未来社会形态",
            "historical": "历史时期、社会制度、风俗习惯",
        }
        
        conflict_hints = {
            "fantasy": "善恶对抗、力量追求、命运抉择",
            "romance": "误会与和解、身份差异、三角关系",
            "mystery": "真相与谎言、正义与私欲、信任与背叛",
            "scifi": "人性与科技、生存与毁灭、自由与控制",
            "historical": "家国情怀、权力斗争、时代变革",
        }

        # 生成章节大纲
        chapter_outlines = []
        for i in range(1, chapters + 1):
            chapter_outlines.append(f"""### 第{i}章：[章节标题]

**本章概要**：
[简述本章主要内容]

**关键场景**：
- 场景一：[描述]
- 场景二：[描述]

**情节推进**：
[本章对主线剧情的推进作用]

**伏笔/悬念**：
[本章埋下的伏笔或留下的悬念]

---
""")

        chapters_content = "\n".join(chapter_outlines)

        return f"""# {genre_name}小说创作框架

> **题材类型**：{genre_name}
> **计划章节**：{chapters} 章
> **故事梗概**：{plot if plot else "[待填写]"}
> **生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、世界观设定

### 1.1 基础设定
[描述故事发生的世界/时代背景]

**时代背景**：
[具体时间、历史时期或虚构纪元]

**地理环境**：
[主要地点、地图概念]

**社会形态**：
[政治制度、社会阶层、经济形态]

### 1.2 特殊设定
[{genre_name}题材的特殊元素]

参考设定方向：{worldbuilding_hints.get(genre, "自由发挥")}

**核心设定一**：
[详细描述]

**核心设定二**：
[详细描述]

### 1.3 规则与限制
[世界观中的特殊规则]

- 规则一：
- 规则二：
- 限制条件：

---

## 二、角色设定

### 2.1 主角
{f"参考描述：{characters}" if characters else ""}

**姓名**：[主角姓名]

**基本信息**：
- 年龄：
- 性别：
- 身份/职业：
- 外貌特征：

**性格特点**：
- 优点：
- 缺点：
- 口头禅/习惯：

**人物背景**：
[成长经历、重要转折]

**目标与动机**：
[主角想要什么？为什么？]

**人物弧光**：
[从开始到结束，主角的成长变化]

### 2.2 重要配角

#### 配角一：[姓名]
- 与主角关系：
- 性格特点：
- 在故事中的作用：

#### 配角二：[姓名]
- 与主角关系：
- 性格特点：
- 在故事中的作用：

### 2.3 反派/对手

**姓名**：[反派姓名]

**基本信息**：
- 身份/职业：
- 外貌特征：

**动机**：
[反派的目标和行动理由]

**与主角的关系**：
[对立的根源]

---

## 三、核心冲突

### 3.1 主线冲突
参考方向：{conflict_hints.get(genre, "自由设定")}

**冲突类型**：[人与人/人与自然/人与社会/人与自我]

**冲突描述**：
[详细描述核心矛盾]

**矛盾根源**：
[冲突产生的根本原因]

### 3.2 次要冲突线

**次线一**：
[描述]

**次线二**：
[描述]

### 3.3 内心冲突
[主角的内心挣扎与成长]

---

## 四、故事结构

### 4.1 三幕式结构

**第一幕：建置（约占25%）**
- 介绍主角和世界
- 日常状态
- 触发事件
- 进入第二幕的转折

**第二幕：对抗（约占50%）**
- 主角追求目标
- 遭遇阻碍
- 中点转折
- 最低谷

**第三幕：解决（约占25%）**
- 高潮对决
- 问题解决
- 新的平衡

### 4.2 情节曲线

```
      高潮
       /\\
      /  \\
     /    \\  
    /      \\ 结局
   /   上升  \\___
  /    阶段    
 /              
起点___________  
  建置   发展   对抗   高潮  结局
```

---

## 五、章节大纲

{chapters_content}

---

## 六、写作备忘

### 6.1 主要伏笔清单
| 伏笔内容 | 埋设章节 | 揭示章节 | 状态 |
|---------|---------|---------|------|
| [伏笔1] | 第X章 | 第X章 | 待写 |
| [伏笔2] | 第X章 | 第X章 | 待写 |

### 6.2 人物关系图
[可用文字描述或后续绘制]

### 6.3 时间线
[重要事件的时间顺序]

### 6.4 待解决问题
- [ ] [问题1]
- [ ] [问题2]

---

> **创作提示**
> - 每章字数建议：3000-5000字
> - 注意节奏把控，张弛有度
> - 保持人物性格一致性
> - 伏笔要有回收，不要烂尾
> - 先完成再完美，初稿不求完美
"""

    def _continue_writing(self, params: dict[str, Any]) -> ToolResult:
        """生成续写提纲。"""
        text = params.get("text", "").strip()
        if not text:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="已有文本内容不能为空",
            )

        length = params.get("length", "medium")
        style = params.get("style", "").strip()
        filename = params.get("output_filename", "").strip()

        length_map = {"short": 500, "medium": 1000, "long": 2000}
        target_words = length_map.get(length, 1000)

        # 提取文本的最后部分作为上下文（最多500字）
        context_text = text[-500:] if len(text) > 500 else text
        
        # 分析文本特征
        text_analysis = self._analyze_text(text)

        # 生成续写提纲
        content = f"""# 续写提纲

> **目标续写字数**：{target_words} 字
> **续写风格提示**：{style if style else "保持原文风格"}
> **生成时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、原文分析

### 1.1 内容概要
**文本长度**：约 {len(text)} 字

**最后段落摘要**：
> {context_text[:200]}{"..." if len(context_text) > 200 else ""}

### 1.2 文本特征分析

{text_analysis}

---

## 二、续写方向建议

### 方向一：顺承发展
[沿着当前情节/论述自然发展]

**内容提示**：
- 承接点：[从哪里承接]
- 发展方向：[往哪个方向发展]
- 预期效果：[达到什么效果]

### 方向二：转折变化
[引入新的转折或变化]

**内容提示**：
- 转折类型：[情节转折/观点转变/新角色/新冲突]
- 转折内容：[具体是什么]
- 铺垫方式：[如何自然过渡]

### 方向三：深化拓展
[对现有内容进行深化或拓展]

**内容提示**：
- 深化对象：[人物内心/细节描写/理论分析]
- 拓展方向：[延伸到什么方面]

---

## 三、续写大纲

### 段落一（约 {target_words // 4} 字）
**功能**：过渡衔接

**要点**：
- [承上启下的内容]
- [建立新的叙述节奏]

### 段落二（约 {target_words // 3} 字）
**功能**：核心展开

**要点**：
- [主要内容展开]
- [关键信息/情节推进]

### 段落三（约 {target_words // 4} 字）
**功能**：发展递进

**要点**：
- [进一步发展]
- [制造张力或深化论述]

### 段落四（约 {target_words // 6} 字）
**功能**：收束/留白

**要点**：
- [小结或悬念]
- [为后续内容做准备]

---

## 四、写作要点提醒

### 4.1 风格一致性
- 保持与原文相似的叙述视角
- 维持一致的语言风格和用词习惯
- 注意段落长度和节奏感

### 4.2 衔接技巧
- 使用过渡词/句承接上文
- 避免突兀的话题转换
- 保持人物性格/论述逻辑的连贯

### 4.3 避免问题
- 不要重复原文已有内容
- 避免与原文矛盾
- 不要引入过多新元素导致散乱

---

## 五、续写开头示例

基于原文风格，以下是几个可能的开头方式：

**示例一（顺承）**：
> [根据原文风格拟写的顺承开头]

**示例二（转折）**：
> [根据原文风格拟写的转折开头]

**示例三（深化）**：
> [根据原文风格拟写的深化开头]

---

> **使用说明**
> - 本提纲为续写方向参考，具体内容需根据创作需要调整
> - 建议先确定续写方向，再按大纲逐段完成
> - 写完后通读全文，确保前后衔接自然
"""

        # 保存到文件
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"continue_{timestamp}"
        
        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(content, encoding="utf-8")
        file_size = output_path.stat().st_size

        logger.info("续写提纲已生成: %s", output_path)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 写作框架已生成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📝 类型: 续写提纲\n🎯 目标字数: {target_words}",
            data={
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "writing_type": "continue",
                "target_words": target_words,
                "original_length": len(text),
            },
        )

    def _analyze_text(self, text: str) -> str:
        """分析文本特征。"""
        # 简单的文本分析
        lines = text.split('\n')
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        
        # 检测可能的文本类型
        has_dialogue = '"' in text or '"' in text or '「' in text
        has_code = '```' in text or '    ' in text[:500]
        has_headers = any(line.startswith('#') for line in lines)
        has_list = any(line.strip().startswith(('-', '*', '1.')) for line in lines)
        
        text_type_hints = []
        if has_dialogue:
            text_type_hints.append("包含对话（可能是叙事/小说）")
        if has_code:
            text_type_hints.append("包含代码（可能是技术文章）")
        if has_headers:
            text_type_hints.append("包含标题结构")
        if has_list:
            text_type_hints.append("包含列表")
        
        return f"""**段落数**：{len(paragraphs)} 段
**行数**：{len(lines)} 行
**特征识别**：
{chr(10).join(f"- {hint}" for hint in text_type_hints) if text_type_hints else "- 普通文本"}

**语言风格判断**：
- [请根据原文判断：正式/口语/文学/技术]
- [叙述视角：第一人称/第三人称/客观陈述]
"""


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = AIWriterTool()
        
        # 测试论文框架生成
        result = await tool.execute("write_paper", {
            "topic": "人工智能在教育领域的应用研究",
            "subject": "教育技术",
            "length": "medium",
        })
        print(result.output)
        print("---")
        
        # 测试文章框架生成
        result = await tool.execute("write_article", {
            "topic": "如何提高工作效率",
            "style": "informative",
            "length": "short",
        })
        print(result.output)

    asyncio.run(test())
