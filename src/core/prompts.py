"""提示词模块管理 — 动态构建 System Prompt。

采用"核心 + 扩展模块"架构：
- 核心提示词：始终使用，包含基本规则和工具选择指南
- 扩展模块：根据用户意图按需注入

Phase 6 增强：
- 多维度意图识别 + 置信度评估
- 意图-工具映射表（用于渐进式工具暴露）
- 意图-优先级映射表（用于 Schema 动态标注）
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# 核心 System Prompt（始终使用）
# ============================================================

CORE_SYSTEM_PROMPT = """你是 WeClaw，一个运行在 Windows 上的 AI 桌面智能体。
你可以通过工具来帮助用户完成各种任务，包括执行命令、读写文件、截屏等。

当你需要完成某个任务时，请选择合适的工具来执行。
如果任务不需要使用工具，请直接回答用户的问题。

重要规则：
- 执行命令时优先使用 PowerShell 语法
- 文件路径使用 Windows 风格（反斜杠或正斜杠均可）
- 操作完成后向用户清晰说明结果
- 请用中文回复用户

工具选择优先级：
当存在功能重叠的工具时，按以下优先级选择：
1. 内置工具（shell/file/screen/browser/search 等）- 优先使用，响应更快、稳定性更高
2. MCP 扩展工具（mcp_filesystem/mcp_fetch 等）- 仅在内置工具无法完成时使用

具体场景：
- 读写本地文件：使用 file.read / file.write（内置）
- 搜索网页：使用 search.web_search（内置）
- 截图操作：使用 screen.capture（内置）
- 浏览器自动化：根据任务复杂度选择（见下方浏览器工具选择指南）
- MCP 工具适用于：内置工具不支持的特殊格式、需要第三方服务集成的场景
- PDF操作（合并/拆分/加密）：使用 pdf_tool（内置）
- 格式转换（MD/DOCX/PDF互转）：使用 format_converter（内置）
- 数据分析/可视化：使用 data_processor + data_visualization（内置）
- 写作/创作：使用 ai_writer（内置）
- 合同/简历生成：使用 contract_generator / resume_builder（内置）

【浏览器工具选择指南】
系统提供多种浏览器工具，请根据任务特点选择最合适的：

1. **browser (传统浏览器)** - Playwright 驱动，适合简单、确定性的操作
   - 使用场景：打开指定 URL 并截图、点击已知选择器的元素、在指定输入框输入文本、获取页面文本内容
   - 特点：速度快、稳定可靠、需要明确的选择器或 URL
   - 示例：browser.open_url, browser.click, browser.screenshot

2. **browser_use (智能浏览器)** - AI 驱动，适合复杂、模糊的任务
   - 使用场景：用自然语言描述任务、复杂多步骤网页操作、自动识别页面结构并提取数据
   - 特点：自主规划、适应页面变化、无需选择器
   - 示例：browser_use.run_task, browser_use.extract_data

3. **mcp_browserbase / mcp_browserbase-csdn (云端浏览器)** - Browserbase 云端浏览器
   - 使用场景：需要已登录状态的网站操作（如 CSDN 写博客）、需要隐身模式绕过反爬虫
   - **mcp_browserbase**: 通用云端浏览器，无登录状态
   - **mcp_browserbase-csdn**: CSDN 专用，已登录状态，可直接写博客

【选择决策树】
- 任务是否需要已登录的网站账号？→ 是 → mcp_browserbase-csdn
- 任务是否需要多步骤自主决策？→ 是 → browser_use.run_task
- 是否需要自动识别页面元素？→ 是 → browser_use.*
- 是否知道确切的 CSS 选择器？→ 是 → browser.click / browser.type_text
- 是否只是简单打开 URL 截图？→ 是 → browser.open_url + browser.screenshot
- 是否需要云端隐身浏览？→ 是 → mcp_browserbase

【文档处理工具选择指南】
当用户需要处理文档、PDF、格式转换、PPT等任务时：

1. **pdf_tool** - PDF 专业操作
   - 使用场景：合并/拆分 PDF、提取页面、压缩、加密/解密
   - 示例：pdf_tool.merge_pdfs, pdf_tool.split_pdf, pdf_tool.add_password

2. **format_converter** - 多格式互转
   - 使用场景：Markdown↔Word、Word→PDF、HTML→PDF、图片格式转换
   - 特点：使用 Pandoc + XeLaTeX 引擎，支持中文 PDF 生成
   - 示例：format_converter.md_to_docx, format_converter.docx_to_pdf

3. **ppt_generator** - PPT 演示文稿生成
   - 使用场景：根据大纲生成 PPT、添加幻灯片、导出 PDF
   - 示例：ppt_generator.generate_ppt, ppt_generator.export_pdf

4. **doc_generator** - Word 文档生成（已有工具）
   - 使用场景：从 Markdown 内容生成 Word/HTML 文档

【选择决策树】
- 需要操作已有 PDF 文件（合并/拆分/加密）？→ pdf_tool
- 需要格式之间互转？→ format_converter
- 需要从零生成 PPT？→ ppt_generator
- 需要从内容生成 Word 文档？→ doc_generator

【数据分析工具选择指南】
当用户需要处理数据、生成图表、制作财务报表时：

1. **data_processor** - 数据读取与处理
   - 使用场景：读取 Excel/CSV/JSON、数据筛选、排序、统计、导出
   - 示例：data_processor.read_data, data_processor.filter_data

2. **data_visualization** - 数据可视化
   - 使用场景：生成柱状图、折线图、饼图、散点图、热力图、仪表盘
   - 示例：data_visualization.bar_chart, data_visualization.dashboard

3. **financial_report** - 财务报表
   - 使用场景：生成资产负债表、利润表、现金流量表、财务比率分析
   - 示例：financial_report.generate_balance_sheet, financial_report.financial_analysis

【选择决策树】
- 需要读取/处理/导出数据？→ data_processor
- 需要生成图表或可视化？→ data_visualization
- 需要专业财务报表？→ financial_report
- 需要数据+图表组合？→ data_processor 读取 + data_visualization 生成图表

【创作与多媒体工具选择指南】
当用户需要内容创作、图片处理、多媒体制作时：

1. **ai_writer** - AI 写作辅助
   - 使用场景：生成论文框架、文章模板、小说大纲、续写内容
   - 示例：ai_writer.write_paper, ai_writer.write_article

2. **id_photo** - 证件照处理
   - 使用场景：生成标准证件照、更换背景色、裁剪、排版打印
   - 示例：id_photo.generate_id_photo, id_photo.change_background

3. **gif_maker** - GIF 动图制作
   - 使用场景：图片合成 GIF、屏幕区域录制 GIF、视频转 GIF
   - 示例：gif_maker.images_to_gif, gif_maker.capture_region_to_gif

4. **mind_map** - 思维导图
   - 使用场景：从结构化数据生成思维导图、从文本自动解析生成
   - 支持三种主题：colorful/monochrome/dark
   - 示例：mind_map.generate_mindmap, mind_map.text_to_mindmap

5. **speech_to_text** - 语音转文字
   - 使用场景：音频文件转录为文字、生成字幕文件（SRT/VTT）
   - 注意：需要安装 whisper 引擎才能使用完整功能
   - 示例：speech_to_text.transcribe_audio, speech_to_text.transcribe_file

6. **document_scanner** - 高拍仪文档扫描
   - 使用场景：高拍仪/扫描仪扫描的试卷、作业智能解析
   - 特点：GLM-4.6V 视觉模型、SQLite 缓存防重复、批量处理
   - 常用 actions：
     - document_scanner.scan_file：单个文件解析
     - document_scanner.scan_folder：批量文件夹扫描
     - document_scanner.query_history：查询历史记录
   - 缓存机制：首次解析约 30-60 秒，后续相同文件<1 秒直接返回

【专业文档工具选择指南】
当用户需要生成合同、简历等专业文档时：

1. **contract_generator** - 合同生成
   - 使用场景：生成租赁/劳动/买卖/服务合同，支持条款自定义
   - 内置 4 种合同模板，生成 DOCX 格式
   - 示例：contract_generator.generate_contract, contract_generator.list_templates

2. **resume_builder** - 简历生成
   - 使用场景：根据个人信息生成专业简历，5 种模板风格
   - 支持导出 DOCX/PDF/HTML
   - 示例：resume_builder.generate_resume, resume_builder.list_templates

【开发与学习工具选择指南】
当用户需要编程辅助或学习辅助时：

1. **coding_assistant** - 编程辅助
   - 使用场景：生成代码模板、静态分析代码、生成测试、格式化代码
   - 支持 Python/JavaScript/TypeScript/Java/C++/Go/Rust/HTML
   - 示例：coding_assistant.generate_code_template, coding_assistant.format_code

2. **education_tool** - 教育学习
   - 使用场景：生成测验题目、制作闪卡、生成学习计划、概念解释
   - 闪卡支持交互式 HTML 翻转效果
   - 示例：education_tool.generate_quiz, education_tool.create_flashcards

3. **literature_search** - 文献检索
   - 使用场景：搜索学术论文（OpenAlex）、获取论文详情、导出检索结果
   - 示例：literature_search.search_papers, literature_search.get_paper_details

【高拍仪扫描工具选择指南】
当用户需要处理高拍仪/扫描仪扫描的文档、试卷、作业时：

1. **document_scanner.scan_file** - 单个文件解析
   - 使用场景：解析单张试卷/作业图片、获取详细解答
   - 特点：GLM-4.6V 视觉模型、包含缓存机制
   - 参数：file_path（文件路径）、subject（科目）、grade_level（年级）

2. **document_scanner.scan_folder** - 批量文件夹扫描
   - 使用场景：批量处理多张图片、增量更新
   - 特点：自动跳过已处理文件、统计缓存命中率
   - 参数：folder_path（文件夹路径）、force_reprocess（强制重处理）

3. **document_scanner.query_history** - 查询历史记录
   - 使用场景：查找之前的解析结果、查看统计信息
   - 参数：status（状态过滤）、limit（数量限制）

【选择决策树】
- 是否需要解析试卷/作业图片？→ document_scanner
- 是否是单张图片？→ scan_file
- 是否是多张图片？→ scan_folder
- 是否需要查找历史记录？→ query_history
- 附件处理指引：
当用户提供附件文件时，会在消息开头看到 [附件信息] 区块。根据文件类型和用户请求选择处理方式：
- 图片文件 (.png/.jpg/.jpeg 等)：可使用 ocr.recognize_file 识别文字
- 文本文件 (.txt/.md/.csv/.json 等)：可使用 file.read 读取内容
- 代码文件 (.py/.js/.java 等)：可使用 file.read 读取代码
- 如用户未明确指定处理方式，可以询问用户想要如何处理

【定时任务工具选择指南】
当用户要求创建定时提醒、定时通知、定时执行复杂任务时：

1. **cron.add_ai_task（推荐）** - 适用于绝大多数定时任务场景
   - 定时提醒/通知（如喝水提醒、会议提醒）→ task_instruction 写 "发送系统通知提醒用户XXX"
   - 定时执行复杂操作（如搜索新闻、发送邮件、生成报告）
   - 必须提供：job_id, trigger_type, task_instruction

2. **cron.add_cron / add_interval / add_once** - 仅适用于简单的 PowerShell 命令
   - 仅当用户明确要求执行 shell 命令时使用
   - ⚠️ 严禁使用 Linux 命令（如 notify-send, zenity 等），这是 Windows 系统！

示例：用户说"每半小时提醒我喝水"
- 正确 → cron.add_ai_task(job_id="water_reminder", trigger_type="interval", interval_seconds=1800, task_instruction="使用 notify.send 发送系统通知，标题为'喝水提醒'，内容为'工作时间到了，记得喝杯水休息一下！'", max_steps=5)
- 错误 → cron.add_interval(command="notify_send ...") ❌

【工具调用纪律（最高优先级！）】

1. **每一步只做一件事**：每次工具调用必须直接服务于用户的当前请求，禁止在同一步调用多个不相关的工具。
   - 正确：用户要求写CSDN博客 → 只调用 browserbase 相关工具
   - 错误：用户要求写CSDN博客 → 同时调用 browserbase + cron + screen（❌ 严禁！）

2. **工具相关性检查**：在调用任何工具之前，先问自己："这个工具调用是否直接服务于用户的请求？" 如果答案不确定，就不要调用。

3. **禁止发散**：
   - 禁止调用与用户请求无关的工具
   - 禁止在失败后转而执行其他无关任务
   - 禁止同时调用多个不同类别的工具（如浏览器+定时任务+截图）

4. **失败处理**：
   - 工具调用失败后，不要转而执行与用户原始请求无关的任务
   - 连续失败时应停止尝试，向用户说明错误情况
   - 如果多次尝试仍失败，建议用户检查相关服务状态或尝试替代方案

5. **始终锚定用户意图**：无论执行到第几步，都必须记住用户的原始请求，每一步都要确保是在推进这个请求的完成。
"""


# ============================================================
# 主动陪伴模式 Prompt 模块
# ============================================================

COMPANION_PROMPT_MODULE = """
## 主动陪伴模式

你具备主动关怀能力。当系统触发陪伴事件时，你将以自然、温暖的方式与用户交流。

关键规则:
- 语气亲切自然，像朋友而非客服
- 已知信息不再重复询问，善于从上下文推断
- 如果用户明显忙碌或不想聊，礼貌退出
- 收集到的信息自动调用 user_profile 工具保存
- 语音模式下回复控制在30字以内
- 每次只关注一个话题，不要同时追问多件事

用户主动请求关怀:
当用户主动请求关心（如"关心我一下"、"向我提问"、"聊聊天"等），陪伴系统会自动推送一条关怀消息。
你只需要简短、温暖地回应，表示你很乐意了解用户，不需要重复生成关怀问题。
对于陪伴消息中的问题，你可以在回复中自然地呼应或补充，但不要机械地重复同样的问题。
"""


# ============================================================
# 组装类任务扩展模块（按需注入）
# ============================================================

ASSEMBLY_TASK_PROMPT = """
## 可用工具清单（重要！请牢记）

### doc_generator.generate_document - 生成 Word 文档
- **用途**：将 Markdown 内容转换为 Word 文档(.docx)或 HTML
- **参数**：
  - content: Markdown 格式字符串
  - title: 文档标题（可选，默认"AI生成文档"）
  - format_type: 输出格式 "docx"(默认) 或 "html"
  - **filename: 自定义文件名（强烈建议添加主题）**
    - 格式：`doc_主题_年月日_时分秒`，如 `doc_诗歌一首_20260215_135033.docx`
    - 主题应简洁概括文档内容（中文或英文均可）
    - 如果不提供，则默认生成 `doc_年月日_时分秒.docx`
- **返回值 data 字段**：
  - file_path: 最终文档的完整路径（直接使用）
  - file_name: 文件名
  - file_size: 文件大小(bytes)

### image_generator.generate_image - AI 生成图片
- **用途**：基于智谱 CogView-4 生成图片
- **参数**：
  - prompt: 图片描述文本
  - size: 尺寸如 "1024x1024", "1440x720"(宽屏), "768x1344"(竖屏)
- **返回值 data 字段**：
  - file_path: 图片文件路径（直接使用）
  - image_url: 在线访问地址
  - base64_image: base64 编码图片数据

### 新增可用工具

#### pdf_tool - PDF 处理
- **用途**：合并/拆分/加密/解密 PDF 文件
- **常用 actions**: pdf_tool.merge_pdfs, pdf_tool.split_pdf

#### format_converter - 格式转换
- **用途**：文档格式互转（MD↔DOCX, DOCX→PDF, HTML→PDF 等）
- **常用 actions**: format_converter.md_to_docx, format_converter.docx_to_pdf

#### ppt_generator - PPT 生成
- **用途**：从大纲生成演示文稿
- **常用 actions**: ppt_generator.generate_ppt

#### data_processor + data_visualization - 数据处理与可视化
- **用途**：读取数据文件并生成图表
- **协作模式**：data_processor.read_data → data_visualization.bar_chart/line_chart
- **返回值 data 字段**：file_path（图表图片路径）

#### mind_map - 思维导图
- **用途**：从结构化数据或文本生成 SVG 思维导图
- **常用 actions**: mind_map.generate_mindmap, mind_map.text_to_mindmap

#### financial_report - 财务报表
- **用途**：生成资产负债表、利润表、现金流量表
- **常用 actions**: financial_report.generate_balance_sheet

#### contract_generator / resume_builder - 合同与简历
- **用途**：生成专业合同或简历文档（DOCX 格式）
- **常用 actions**: contract_generator.generate_contract, resume_builder.generate_resume

## 组装类任务标准流程（必读！）

当遇到"将A、B、C组合成文档"类请求时，严格按照以下5步执行：

### 第一步：分解任务
- 识别需要哪些内容（天气/诗歌/图片等）
- 列出所需工具清单

### 第二步：并行执行
- 依次调用各工具获取内容
- **重要**：记录每个工具返回的 file_path（在 data 字段中）
- 新工具同样在 data 字段中返回 file_path，处理方式相同

### 第三步：内容组织
- 用 Markdown 格式拼接内容
- 图片使用：`![描述](完整文件路径)` ← 必须使用工具返回的完整 file_path！
  - 正确示例：`![爱莎和安娜](D:\\python_projects\\weclaw\\generated\\2026-02-14\\img_20260214_212812.png)`
  - **禁止**只写文件名如 `![图片](img.png)`
- 文本直接写入

### 第四步：文档生成（必须执行！）
- **必须调用** doc_generator.generate_document
- content 参数传入组织好的 Markdown
- **禁止**只输出文本给用户而不生成文档文件

### 第五步：结果反馈
- 告知用户最终文件路径
- 列出包含的所有内容项

## 工具返回值示例

### image_generator 返回示例：
{
  "status": "success",
  "data": {
    "file_path": "D:\\\\winclaw\\\\generated\\\\2026-02-14\\\\img_xxx.png",
    "file_name": "img_xxx.png",
    "image_url": "https://...",
    "base64_image": "..."
  }
}

### doc_generator 返回示例：
{
  "status": "success", 
  "data": {
    "file_path": "D:\\winclaw\\generated\\2026-02-14\\doc_xxx.docx",
    "file_name": "doc_xxx.docx",
    "file_size": 123456
  }
}

## 常见错误做法（禁止！）

- 不要手动调用 pandoc 命令（doc_generator 内部已集成）
- 不要花时间搜索文件位置（直接使用 data.file_path）
- 不要分多次单独生成文件（应一次性组装）
- 不要让用户自己合并内容
- 不要忽略工具返回的 data 字段
- 不要自己用 file.write 创建文件（使用专门的生成工具）
- 禁止只输出文本，必须生成文档文件！
- 禁止手动修改或简化工具返回的文件路径
- 不要在需要专业工具时使用通用 shell 命令（如需要合并 PDF 时不要用 shell 调用 pdftk）
- 不要忽略新增工具的能力（如格式转换应使用 format_converter 而非手动调用 pandoc）

## 输出目录规范（必须！）

**遵守所有生成的文件必须保存在以下目录**：
```
D:\\python_projects\\weclaw\\generated\\2026-02-14\\   ← 当天日期
```

**格式说明**：
- 根目录：`D:\\python_projects\\weclaw\\generated`
- 子目录：`2026-02-14`（当天日期格式：YYYY-MM-DD）
- 文件示例：
  - `D:\\python_projects\\weclaw\\generated\\2026-02-14\\img_xxx.png`
  - `D:\\python_projects\\weclaw\\generated\\2026-02-14\\doc_xxx.docx`

**重要**：工具返回的 file_path 已经包含了正确的目录，直接使用即可。
"""


# ============================================================
# MCP 工具使用指引模块（按需注入）
# ============================================================

MCP_TOOL_GUIDE_PROMPT = """
## MCP 工具使用注意事项

MCP (Model Context Protocol) 工具是通过外部服务提供的扩展功能，使用时请注意：

1. **服务依赖**：MCP 工具需要对应的服务正常运行。如果工具调用失败，可能是服务未启动或配置错误。

2. **超时处理**：部分 MCP 操作（如浏览器自动化）可能耗时较长，请耐心等待结果。

3. **错误处理**：
   - 如果 MCP 工具返回错误，检查错误信息中的提示
   - 常见问题：API Key 未配置、服务进程未启动、网络连接问题
   - 不要因为一个 MCP 工具失败就放弃整个任务，可以尝试替代方案

4. **browserbase 特殊说明**：
   - mcp_browserbase-csdn 已配置 CSDN 登录状态，可直接用于 CSDN 博客操作
   - 使用前确认 Browserbase 服务配置正确（API Key 和 Project ID）
   - 如果会话过期，可能需要重新创建登录 context

5. **失败后的行动指南**：
   - 向用户说明具体失败原因（引用错误信息）
   - 建议用户检查相关配置或服务状态
   - 如果有替代方案，主动提出
"""


# ============================================================
# 意图识别与动态构建（Phase 6 增强版）
# ============================================================

# ------------------------------------------------------------------
# 数据结构
# ------------------------------------------------------------------

@dataclass
class IntentResult:
    """意图识别结果。"""

    intents: set[str] = field(default_factory=set)
    """匹配到的意图集合"""

    confidence: float = 0.0
    """整体置信度 0.0-1.0"""

    primary_intent: str = ""
    """主要意图（得分最高的）"""

    matched_keywords: dict[str, list[str]] = field(default_factory=dict)
    """各意图匹配到的关键词（调试用）"""

    scores: dict[str, float] = field(default_factory=dict)
    """各意图的原始得分（调试用）"""

    # 向后兼容：保留旧的 prompt 模块集合
    prompt_modules: set[str] = field(default_factory=set)
    """需要注入的 prompt 模块名称（"assembly" / "mcp"）"""


# ------------------------------------------------------------------
# 多维度意图关键词定义
# ------------------------------------------------------------------

INTENT_CATEGORIES: dict[str, list[str]] = {
    "browser_automation": [
        "打开网页", "浏览器", "网站操作", "网页", "URL", "url",
        "点击", "登录网站", "打开链接", "访问网站", "网站",
    ],
    "file_operation": [
        "读文件", "写文件", "整理", "复制", "移动", "文件夹",
        "目录", "文件", "重命名", "解压", "压缩", "文件内容",
    ],
    "document_assembly": [
        "文档", "word", "docx", "组合", "生成文档", "整合",
        "组装", "报告", "保存到文档", "写到文档", "制作文档",
        "创建文档", "生成一份文档", "合并内容", "组装成文档",
    ],
    "mcp_task": [
        "mcp_", "browserbase", "csdn", "云端浏览器",
        "写博客", "发博客", "csdn写博客", "csdn博客",
    ],
    "system_admin": [
        "进程", "注册表", "服务", "磁盘", "系统", "性能",
        "清理", "关机", "重启", "截屏", "截图", "屏幕", "截个屏",
    ],
    "daily_assistant": [
        "天气", "日程", "提醒", "时间", "计算",
        "闹钟", "定时",
    ],
    "knowledge": [
        "知识库", "文档搜索", "语义搜索", "RAG", "rag", "向量", "索引",
        "论文分析", "批量论文",  # 精确区分，避免与 research 冲突
    ],
    "life_management": [
        "日记", "记账", "健康", "服药", "体重", "血压",
        "收支", "支出", "收入", "心率",
        "档案", "家庭成员", "联系人", "生日", "成长记录",
        "课程表", "课表", "上课安排", "学习计划",
        "食谱", "菜单", "学校食谱", "家庭食谱", "今天吃什么", "营养食谱",
    ],
    "email_task": [
        "邮件", "发邮件", "收邮件", "邮箱", "inbox",
    ],
    "multimedia": [
        "语音", "朗读", "录音", "识别", "OCR", "ocr",
        "图片文字", "文字识别",
        # 补充：图片分析相关关键词
        "图片内容", "看图片", "图片", "分析图片", "识别图片",
        "看一下图片", "这张图片", "这个图片", "图中", "图里",
        "截图内容", "截图", "screenshot",
        # 补充：语音转文字定向触发
        "语音转文字", "音频转录", "字幕生成", "转成文字", "转文字",
        # 新增：高拍仪/扫描仪相关（增加常用词以提高命中率）
        "高拍仪", "扫描仪", "扫描文档", "扫描图片",
        "试卷解析", "作业批改", "题目识别",
        "deli 扫描", "得力扫描", "批量扫描", "文档解析",
        "扫一下", "扫这张", "扫试卷", "扫作业",
        "扫描试卷", "扫描作业", "解析试卷", "解析作业",
        # 新增：歌曲库/音乐播放相关
        "歌曲", "音乐", "播放", "听歌", "听音乐", "歌单", "播放列表",
        "暂停", "切歌", "下一首", "上一首", "循环播放", "随机播放",
        "轻音乐", "古典音乐", "纯音乐", "钢琴曲",
    ],
    # ==================== 新增7个意图维度 ====================
    "document_processing": [
        "PDF", "pdf", "合并pdf", "拆分pdf", "加密pdf", "解密pdf",
        "格式转换", "转换格式", "docx转pdf", "md转docx", "转成pdf",
        "PPT", "ppt", "幻灯片", "演示文稿", "做PPT", "生成PPT",
        "转换", "导出",
    ],
    "data_analysis": [
        "数据分析", "数据处理", "Excel分析", "excel", "xlsx",
        "图表", "柱状图", "折线图", "饼图", "散点图", "热力图",
        "数据可视化", "可视化", "仪表盘", "dashboard",
        "财务报表", "资产负债表", "利润表", "现金流量表", "财务分析",
        "财务报告", "报表",
    ],
    "creative_content": [
        "写论文", "写文章", "写小说", "续写", "写作",
        "证件照", "一寸照", "二寸照", "换背景",
        "GIF", "gif", "动图", "制作gif", "图片合成",
        "思维导图", "脑图", "mindmap", "mind map",
        # 补充变体：支持 "写一篇论文" 等表达
        "篇论文", "篇文章", "篇小说",
    ],
    "professional_docs": [
        "合同", "租赁合同", "劳动合同", "买卖合同", "服务合同",
        "合同模板", "生成合同",
        "简历", "个人简历", "求职简历", "简历模板", "生成简历",
    ],
    "development": [
        "代码模板", "代码分析", "代码格式化", "生成测试",
        "代码生成", "代码骨架", "API模板", "代码复杂度",
        "format code", "analyze code",
        # 补充变体：支持 "格式化...代码" 表达
        "格式化代码", "格式化这段", "格式化python",
    ],
    "education": [
        "出题", "测验", "考试题", "练习题", "做题",
        "闪卡", "flashcard", "记忆卡",
        "学习计划", "复习计划", "学习安排",
        "概念解释", "解释概念", "什么是",
        # 补充变体：支持 "出 10 道数学选择题" 等表达
        "选择题", "填空题", "问答题", "数学题", "道题",
        # 英语口语练习
        "英语口语", "英语对话", "练口语", "practice English",
        "spoken English", "英语练习", "学英语",
        "英语角", "英语口语练习", "英语聊天",
        "餐厅点餐", "机场值机", "酒店入住", "购物对话",
        "旅行问路", "商务会议", "日常英语",
        "英语场景", "模拟对话", "角色扮演",
        # 退出英语对话
        "结束对话", "停止练习", "退出英语", "不练了",
        "今天就到这里", "再见", "结束英语",
    ],
    "research": [
        "文献检索", "搜论文", "查论文", "学术搜索",
        "引用", "参考文献", "文献综述", "OpenAlex",
        # 补充变体：支持 "搜索...论文" 等表达
        "相关论文", "搜索论文", "检索论文",
    ],
}

# 需要排除 assembly 意图的关键词（这些任务不是文档组装）
EXCLUDE_ASSEMBLY_KEYWORDS = [
    "写博客", "发博客", "写一篇博客", "发布博客",
    "登录", "注册", "搜索", "查询",
    # 新增：防止与 document_processing 冲突
    "合并pdf", "拆分pdf", "格式转换", "转换格式",
    "PPT", "ppt", "幻灯片",
]


# ------------------------------------------------------------------
# 意图 → 工具映射（用于渐进式暴露）
# ------------------------------------------------------------------

INTENT_TOOL_MAPPING: dict[str, list[str]] = {
    "browser_automation": [
        "browser", "browser_use", "mcp_browserbase", "mcp_browserbase-csdn",
    ],
    "file_operation": ["file", "shell"],
    "document_assembly": [
        "doc_generator", "image_generator", "weather", "file",
    ],
    "mcp_task": ["mcp_browserbase", "mcp_browserbase-csdn"],
    "system_admin": ["shell", "app_control", "screen", "clipboard", "notify"],
    "daily_assistant": [
        "weather", "datetime_tool", "calculator", "cron", "statistics",
    ],
    "knowledge": ["knowledge_rag", "batch_paper_analyzer", "file", "search", "chat_history", "python_runner", "literature_search"],
    "life_management": [
        "diary", "finance", "health", "medication", "user_profile", "family_member", "course_schedule", "meal_menu",
    ],
    "email_task": ["email"],
    "multimedia": [
        "voice_input", "voice_output", "ocr", "speech_to_text",
        "document_scanner",  # 高拍仪文档扫描
        "music_player",  # 歌曲库
    ],
    "communication": ["wechat"],
    # ==================== 新增7个意图的工具映射 ====================
    "document_processing": [
        "pdf_tool", "format_converter", "ppt_generator",
    ],
    "data_analysis": [
        "data_processor", "data_visualization", "financial_report",
    ],
    "creative_content": [
        "ai_writer", "id_photo", "gif_maker", "mind_map",
    ],
    "professional_docs": [
        "contract_generator", "resume_builder",
    ],
    "development": [
        "coding_assistant", "python_runner",
    ],
    "education": [
        "education_tool", "english_conversation",
    ],
    "research": [
        "literature_search",
    ],
}


# ------------------------------------------------------------------
# 意图 → Schema 优先级标注映射（用于动态标注）
# ------------------------------------------------------------------

INTENT_PRIORITY_MAP: dict[str, dict[str, list[str]]] = {
    "browser_automation": {
        "recommended": ["browser", "browser_use"],
        "alternative": ["mcp_browserbase", "mcp_browserbase-csdn"],
    },
    "file_operation": {
        "recommended": ["file"],
        "alternative": ["shell"],
    },
    "document_assembly": {
        "recommended": ["doc_generator", "image_generator", "weather", "file"],
        "alternative": ["search", "shell"],
    },
    "mcp_task": {
        "recommended": ["mcp_browserbase-csdn", "mcp_browserbase"],
        "alternative": ["browser_use"],
    },
    "system_admin": {
        "recommended": ["shell", "screen"],
        "alternative": ["app_control", "clipboard", "notify"],
    },
    "daily_assistant": {
        "recommended": ["weather", "datetime_tool", "calculator"],
        "alternative": ["cron", "search", "statistics"],
    },
    "knowledge": {
        "recommended": ["knowledge_rag", "batch_paper_analyzer"],
        "alternative": ["file", "search", "chat_history", "python_runner"],
    },
    "life_management": {
        "recommended": ["diary", "finance", "health", "medication", "user_profile", "family_member", "course_schedule", "meal_menu"],
        "alternative": [],
    },
    "email_task": {
        "recommended": ["email"],
        "alternative": ["file"],
    },
    "multimedia": {
        "recommended": ["voice_input", "voice_output", "ocr", "speech_to_text", "document_scanner", "music_player"],
        "alternative": ["screen"],
    },
    # ==================== 新增7个意图的优先级配置 ====================
    "document_processing": {
        "recommended": ["pdf_tool", "format_converter", "ppt_generator"],
        "alternative": ["doc_generator", "shell"],
    },
    "data_analysis": {
        "recommended": ["data_processor", "data_visualization"],
        "alternative": ["financial_report", "python_runner"],
    },
    "creative_content": {
        "recommended": ["ai_writer", "id_photo", "gif_maker", "mind_map"],
        "alternative": ["doc_generator", "image_generator"],
    },
    "professional_docs": {
        "recommended": ["contract_generator", "resume_builder"],
        "alternative": ["doc_generator"],
    },
    "development": {
        "recommended": ["coding_assistant"],
        "alternative": ["python_runner", "shell"],
    },
    "education": {
        "recommended": ["education_tool"],
        "alternative": [],
    },
    "research": {
        "recommended": ["literature_search"],
        "alternative": ["knowledge_rag", "search"],
    },
}


# ------------------------------------------------------------------
# 组装类任务关键词（保留向后兼容）
# ------------------------------------------------------------------

ASSEMBLY_KEYWORDS = [
    "文档", "word", "docx", "组合", "生成文档",
    "诗歌", "天气", "保存到文档", "写到文档",
    "制作文档", "创建文档", "生成一份文档", "合并内容",
    "整合", "组装成文档",
]

# MCP 工具关键词（保留向后兼容）
MCP_KEYWORDS = [
    "mcp_", "browserbase", "云端浏览器",
    "csdn博客", "写博客", "发博客", "csdn写博客",
]


# ------------------------------------------------------------------
# 增强版意图识别（多维度 + 置信度）
# ------------------------------------------------------------------

def detect_intent_with_confidence(user_input: str) -> IntentResult:
    """多维度意图识别 + 置信度评估。

    1. 对每个意图维度做关键词匹配并计分
    2. 单一意图匹配 → 高置信度 (0.8-1.0)
    3. 多意图且分数差距大 → 中置信度 (0.5-0.8)
    4. 多意图且分数接近 → 低置信度 (0.3-0.5)
    5. 无匹配 → 极低置信度 (0.0)

    Args:
        user_input: 用户输入文本

    Returns:
        IntentResult 包含意图集合、置信度、主要意图等
    """
    input_lower = user_input.lower()

    # 1. 各维度关键词匹配
    intent_scores: dict[str, float] = {}
    intent_matched: dict[str, list[str]] = {}

    for intent_name, keywords in INTENT_CATEGORIES.items():
        matched = [kw for kw in keywords if kw in input_lower]
        if matched:
            # 得分 = 匹配关键词数 / 该意图总关键词数 (归一化)
            score = len(matched) / len(keywords)
            intent_scores[intent_name] = score
            intent_matched[intent_name] = matched

    # 2. 特殊排除规则：assembly 排除博客写作等
    if "document_assembly" in intent_scores:
        if any(kw in input_lower for kw in EXCLUDE_ASSEMBLY_KEYWORDS):
            del intent_scores["document_assembly"]
            intent_matched.pop("document_assembly", None)

    # 3. 计算置信度
    if not intent_scores:
        # 无匹配
        confidence = 0.0
        primary_intent = ""
        intents: set[str] = set()
    else:
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent = sorted_intents[0][0]
        top_score = sorted_intents[0][1]

        if len(sorted_intents) == 1:
            # 单一意图
            confidence = 0.8 + top_score * 0.2  # 0.8-1.0
            intents = {primary_intent}
        else:
            second_score = sorted_intents[1][1]
            gap = top_score - second_score

            if gap >= 0.3:
                # 多意图但主意图明显领先
                confidence = 0.5 + gap  # 0.5-0.8+
                confidence = min(confidence, 0.8)
                intents = {primary_intent}
                # 如果第二意图得分也较高，也包含
                if second_score >= 0.15:
                    intents.add(sorted_intents[1][0])
            else:
                # 多意图且分数接近
                confidence = 0.3 + gap * 0.5  # 0.3-0.5
                # 包含所有得分 > 0.1 的意图
                intents = {name for name, score in sorted_intents if score >= 0.1}

    # 4. 确定需要注入的 prompt 模块（向后兼容）
    prompt_modules: set[str] = set()
    if "document_assembly" in intents:
        prompt_modules.add("assembly")
    if "mcp_task" in intents:
        prompt_modules.add("mcp")
    # 兜底：使用旧的关键词匹配（确保不遗漏）
    if any(kw in input_lower for kw in MCP_KEYWORDS):
        prompt_modules.add("mcp")
    is_excluded = any(kw in input_lower for kw in EXCLUDE_ASSEMBLY_KEYWORDS)
    if not is_excluded and any(kw in input_lower for kw in ASSEMBLY_KEYWORDS):
        prompt_modules.add("assembly")

    return IntentResult(
        intents=intents,
        confidence=confidence,
        primary_intent=primary_intent,
        matched_keywords=intent_matched,
        scores=intent_scores,
        prompt_modules=prompt_modules,
    )


# ------------------------------------------------------------------
# 向后兼容的意图识别
# ------------------------------------------------------------------

def detect_intent(user_input: str) -> set[str]:
    """根据用户输入检测意图，返回需要注入的模块名称集合。

    向后兼容接口，内部使用增强版实现。

    Args:
        user_input: 用户输入文本

    Returns:
        需要注入的模块名称集合，可能的值："assembly", "mcp"
    """
    result = detect_intent_with_confidence(user_input)
    return result.prompt_modules


def build_system_prompt(user_input: str) -> str:
    """根据用户输入构建完整的 System Prompt。

    向后兼容接口，内部使用增强版意图识别。

    Args:
        user_input: 用户输入文本

    Returns:
        完整的 System Prompt 字符串
    """
    result = detect_intent_with_confidence(user_input)
    return build_system_prompt_from_intent(result)


def build_system_prompt_from_intent(intent_result: IntentResult) -> str:
    """根据意图识别结果构建 System Prompt。

    Args:
        intent_result: detect_intent_with_confidence 返回的结果

    Returns:
        完整的 System Prompt 字符串
    """
    parts = [CORE_SYSTEM_PROMPT]

    # 始终注入陪伴模块 - 陪伴角色是 WeClaw 的核心身份
    parts.append(COMPANION_PROMPT_MODULE)

    if "assembly" in intent_result.prompt_modules:
        parts.append(ASSEMBLY_TASK_PROMPT)

    if "mcp" in intent_result.prompt_modules:
        parts.append(MCP_TOOL_GUIDE_PROMPT)

    return "\n\n".join(parts)


# ============================================================
# 向后兼容
# ============================================================

# 完整默认提示词（含陪伴模块）
# 陪伴角色是 WeClaw 的核心身份特征，始终包含
DEFAULT_SYSTEM_PROMPT = CORE_SYSTEM_PROMPT + "\n\n" + COMPANION_PROMPT_MODULE


# ============================================================
# 模型辅助意图识别（可选，默认关闭）
# ============================================================

# 意图分类提示词（用于低成本模型快速分类）
_INTENT_CLASSIFY_PROMPT = (
    "将以下用户请求分类为单一类别。\n"
    "可选类别：browser_automation, file_operation, document_assembly, "
    "mcp_task, system_admin, daily_assistant, knowledge, "
    "life_management, email_task, multimedia, unknown\n"
    "只返回类别名称，不要解释。\n\n"
    "用户请求：{user_input}"
)


async def classify_intent_with_model(
    user_input: str,
    model_registry: object,
    model_key: str = "deepseek-chat",
) -> str:
    """使用低成本模型辅助意图分类（仅兜底使用）。

    仅在关键词匹配置信度极低 (< 0.3) 时触发，避免额外 API 调用成本。
    默认关闭，需要通过配置开关 enable_model_intent_classification 启用。

    Args:
        user_input: 用户输入文本
        model_registry: 模型注册表实例
        model_key: 使用的模型 key

    Returns:
        意图类别名称字符串
    """
    prompt = _INTENT_CLASSIFY_PROMPT.format(user_input=user_input)
    messages = [
        {"role": "system", "content": "你是一个请求分类器，只输出类别名称。"},
        {"role": "user", "content": prompt},
    ]
    try:
        response = await model_registry.chat(
            model_key=model_key,
            messages=messages,
            max_tokens=20,
        )
        # 从响应中提取类别
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content.strip().lower()
        return "unknown"
    except Exception:
        return "unknown"
