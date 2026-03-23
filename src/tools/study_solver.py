"""试卷作业解答工具 — 基于 GLM-4.6V 的智能题目识别与解答。

本工具专门处理高拍仪扫描的试卷和作业图片，支持：
- 图片格式：JPG, PNG, BMP 等（使用 GLM-4.6V 视觉理解）
- PDF 格式：使用 pymupdf4llm 提取后调用 LLM 解答
- 题目类型：数学、物理、化学等理科题目
- 输出格式：Markdown 详细解答 + JSON 结构化数据
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class StudySolverTool(BaseTool):
    """试卷作业解答工具。
    
    使用 GLM-4.6V 视觉模型识别图片中的题目并提供详细解答。
    支持单题和多题混合试卷的智能分析。
    """
    
    name = "study_solver"
    emoji = "📝"
    title = "试卷解答"
    description = "试卷作业智能解答工具，支持图片识别和详细解析"
    timeout = 180  # 3 分钟超时
    
    def __init__(self, output_dir: str = None) -> None:
        """初始化解答工具。
        
        Args:
            output_dir: 输出目录，默认为项目的 generated/日期/ 目录
        """
        super().__init__()
        self.output_dir = (
            Path(output_dir) if output_dir
            else Path(__file__).parent.parent.parent / "generated" / datetime.now().strftime("%Y-%m-%d")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载 .env 文件获取 API Key
        load_dotenv()
        self.api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    
    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="solve_from_image",
                description="从图片文件识别试卷/作业题目并解答（支持 JPG/PNG/BMP 等格式）",
                parameters={
                    "image_path": {
                        "type": "string",
                        "description": "图片文件路径（高拍仪扫描的试卷或作业照片）",
                    },
                    "subject": {
                        "type": "string",
                        "description": "科目类型，如：数学、物理、化学、生物",
                        "default": "数学",
                    },
                    "grade_level": {
                        "type": "string",
                        "description": "年级水平，如：小学、初中、高中、大学",
                        "default": "高中",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                    "include_steps": {
                        "type": "boolean",
                        "description": "是否包含详细解题步骤，默认 true",
                        "default": True,
                    },
                    "extract_formulas": {
                        "type": "boolean",
                        "description": "是否提取公式为 LaTeX 格式，默认 true",
                        "default": True,
                    },
                },
                required_params=["image_path"],
            ),
            ActionDef(
                name="solve_from_pdf",
                description="从 PDF 文件提取试卷题目并解答（使用 pymupdf4llm）",
                parameters={
                    "pdf_path": {
                        "type": "string",
                        "description": "PDF 文件路径",
                    },
                    "subject": {
                        "type": "string",
                        "description": "科目类型",
                        "default": "数学",
                    },
                    "grade_level": {
                        "type": "string",
                        "description": "年级水平",
                        "default": "高中",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                    "pages": {
                        "type": "string",
                        "description": "页码范围，如 '1-3' 或 '1,3,5'，默认全部",
                    },
                },
                required_params=["pdf_path"],
            ),
            ActionDef(
                name="batch_solve",
                description="批量处理文件夹中的所有图片/PDF 文件",
                parameters={
                    "folder_path": {
                        "type": "string",
                        "description": "包含试卷图片的文件夹路径",
                    },
                    "subject": {
                        "type": "string",
                        "description": "科目类型",
                        "default": "数学",
                    },
                    "grade_level": {
                        "type": "string",
                        "description": "年级水平",
                        "default": "高中",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "文件匹配模式，如 '*.jpg' 或 '*.png'",
                        "default": "*.*",
                    },
                },
                required_params=["folder_path"],
            ),
        ]
    
    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的解答动作。"""
        action_map = {
            "solve_from_image": self._solve_from_image,
            "solve_from_pdf": self._solve_from_pdf,
            "batch_sell": self._batch_solve,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作：{action}，支持的动作：{list(action_map.keys())}",
            )
        
        try:
            return await handler(params)
        except Exception as e:
            logger.error("试卷解答工具执行失败：%s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"试卷解答失败：{e}",
            )
    
    async def _solve_from_image(self, params: dict[str, Any]) -> ToolResult:
        """从图片识别并解答题目。"""
        image_path_str = params.get("image_path", "").strip()
        subject = params.get("subject", "数学").strip()
        grade_level = params.get("grade_level", "高中").strip()
        output_filename = params.get("output_filename", "").strip()
        include_steps = params.get("include_steps", True)
        extract_formulas = params.get("extract_formulas", True)
        
        # 参数验证
        if not image_path_str:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少必需参数：image_path",
            )
        
        image_path = Path(image_path_str).expanduser().resolve()
        if not image_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"图片文件不存在：{image_path}",
            )
        
        # 检查文件大小（限制 20MB）
        file_size_mb = image_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 20:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"图片过大：{file_size_mb:.1f}MB（限制 20MB）",
            )
        
        # 检查 API Key
        if not self.api_key:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="未配置 GLM_API_KEY，请在 .env 文件中设置智谱 API 密钥",
            )
        
        logger.info("开始识别图片：%s (科目：%s, 年级：%s)", image_path, subject, grade_level)
        
        try:
            # 读取图片并转换为 base64
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            img_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # 调用 GLM-4.6V 进行视觉理解和解答
            result_text = await self._call_glm_vision(img_base64, subject, grade_level, include_steps, extract_formulas)
            
            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{image_path.stem}_解答_{timestamp}"
            
            # 保存 Markdown 文件
            md_path = self.output_dir / f"{output_filename}.md"
            md_path.write_text(result_text, encoding="utf-8")
            
            # 尝试提取 JSON 数据
            json_data = self._extract_json_from_result(result_text)
            if json_data:
                json_path = self.output_dir / f"{output_filename}.json"
                json_path.write_text(
                    __import__("json").dumps(json_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            
            logger.info("图片解答完成：%s", md_path)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 试卷解答完成\n📁 图片：{image_path.name}\n📖 科目：{subject}\n🎓 年级：{grade_level}\n📄 输出：{md_path.name}",
                data={
                    "md_file_path": str(md_path),
                    "json_file_path": str(json_path) if json_data else None,
                    "source_image": str(image_path),
                    "subject": subject,
                    "grade_level": grade_level,
                },
            )
            
        except Exception as e:
            logger.exception("图片解答失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"图片解答失败：{e}",
            )
    
    async def _solve_from_pdf(self, params: dict[str, Any]) -> ToolResult:
        """从 PDF 提取并解答题目。"""
        pdf_path_str = params.get("pdf_path", "").strip()
        subject = params.get("subject", "数学").strip()
        grade_level = params.get("grade_level", "高中").strip()
        output_filename = params.get("output_filename", "").strip()
        pages = params.get("pages", "")
        
        # 参数验证
        if not pdf_path_str:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少必需参数：pdf_path",
            )
        
        pdf_path = Path(pdf_path_str).expanduser().resolve()
        if not pdf_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"PDF 文件不存在：{pdf_path}",
            )
        
        logger.info("开始处理 PDF：%s", pdf_path)
        
        try:
            # 使用 pymupdf4llm 提取 PDF 内容为 Markdown
            import pymupdf4llm
            
            markdown_content = pymupdf4llm.to_markdown(str(pdf_path))
            
            if not markdown_content or len(markdown_content) < 100:
                logger.warning("pymupdf4llm 提取结果为空，可能不是文本型 PDF")
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="PDF 内容提取失败，可能是扫描版 PDF（需要使用图片识别方式）",
                )
            
            # 调用 LLM 进行分析解答
            result_text = await self._call_llm_for_pdf(markdown_content, subject, grade_level)
            
            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{pdf_path.stem}_解答_{timestamp}"
            
            # 保存 Markdown 文件
            md_path = self.output_dir / f"{output_filename}.md"
            md_path.write_text(result_text, encoding="utf-8")
            
            logger.info("PDF 解答完成：%s", md_path)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF 试卷解答完成\n📁 PDF: {pdf_path.name}\n📖 科目：{subject}\n📄 输出：{md_path.name}",
                data={
                    "md_file_path": str(md_path),
                    "source_pdf": str(pdf_path),
                    "subject": subject,
                },
            )
            
        except ImportError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="pymupdf4llm 未安装，请运行：pip install pymupdf4llm",
            )
        except Exception as e:
            logger.exception("PDF 解答失败")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"PDF 解答失败：{e}",
            )
    
    async def _batch_solve(self, params: dict[str, Any]) -> ToolResult:
        """批量处理文件夹中的文件。"""
        folder_path_str = params.get("folder_path", "").strip()
        subject = params.get("subject", "数学").strip()
        grade_level = params.get("grade_level", "高中").strip()
        file_pattern = params.get("file_pattern", "*.*").strip()
        
        if not folder_path_str:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少必需参数：folder_path",
            )
        
        folder_path = Path(folder_path_str).expanduser().resolve()
        if not folder_path.exists() or not folder_path.is_dir():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件夹不存在：{folder_path}",
            )
        
        # 查找所有匹配的文件
        files = list(folder_path.glob(file_pattern))
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        pdf_extensions = {".pdf"}
        
        image_files = [f for f in files if f.suffix.lower() in image_extensions]
        pdf_files = [f for f in files if f.suffix.lower() in pdf_extensions]
        
        if not image_files and not pdf_files:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到符合条件的图片/PDF 文件",
            )
        
        logger.info("找到 %d 个图片文件和 %d 个 PDF 文件", len(image_files), len(pdf_files))
        
        results = []
        success_count = 0
        error_count = 0
        
        # 处理图片文件
        for img_file in image_files:
            try:
                result = await self._solve_from_image({
                    "image_path": str(img_file),
                    "subject": subject,
                    "grade_level": grade_level,
                })
                results.append({"file": str(img_file), "status": result.status.value})
                if result.is_success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error("处理文件 %s 失败：%s", img_file, e)
                results.append({"file": str(img_file), "status": "error", "error": str(e)})
                error_count += 1
        
        # 处理 PDF 文件
        for pdf_file in pdf_files:
            try:
                result = await self._solve_from_pdf({
                    "pdf_path": str(pdf_file),
                    "subject": subject,
                    "grade_level": grade_level,
                })
                results.append({"file": str(pdf_file), "status": result.status.value})
                if result.is_success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error("处理文件 %s 失败：%s", pdf_file, e)
                results.append({"file": str(pdf_file), "status": "error", "error": str(e)})
                error_count += 1
        
        # 生成汇总报告
        summary_md = f"""# 批量处理汇总报告

**处理时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**科目**: {subject}
**年级**: {grade_level}
**文件夹**: {folder_path}

## 统计信息
- ✅ 成功：{success_count} 个文件
- ❌ 失败：{error_count} 个文件
- 📊 总计：{len(image_files) + len(pdf_files)} 个文件

## 处理结果

| 文件 | 状态 |
|------|------|
"""
        for r in results:
            status_icon = "✅" if r["status"] == "success" else "❌"
            summary_md += f"| {Path(r['file']).name} | {status_icon} {r['status']} |\n"
        
        summary_path = self.output_dir / f"批量处理汇总_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        summary_path.write_text(summary_md, encoding="utf-8")
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 批量处理完成\n📊 成功：{success_count}/{len(image_files) + len(pdf_files)}\n📄 汇总报告：{summary_path.name}",
            data={
                "total_files": len(image_files) + len(pdf_files),
                "success_count": success_count,
                "error_count": error_count,
                "summary_path": str(summary_path),
                "results": results,
            },
        )
    
    async def _call_glm_vision(self, img_base64: str, subject: str, grade_level: str, 
                               include_steps: bool, extract_formulas: bool) -> str:
        """调用 GLM-4.6V 视觉模型进行题目识别和解答。
        
        Args:
            img_base64: Base64 编码的图片
            subject: 科目
            grade_level: 年级水平
            include_steps: 是否包含详细步骤
            extract_formulas: 是否提取 LaTeX 公式
        
        Returns:
            解答文本（Markdown 格式）
        """
        from zai import ZhipuAiClient
        import tenacity
        from tenacity import stop_after_attempt, wait_exponential
        
        client = ZhipuAiClient(api_key=self.api_key)
        
        # 构建提示词
        prompt = f"""你是一位专业的{subject}教师，请仔细分析这张试卷/作业图片中的题目。

要求：
1. **题目识别**：准确识别图片中的所有题目内容
2. **详细解答**：为每道题目提供详细的解答过程
3. **步骤清晰**：解答步骤要条理清晰，逻辑严密
4. **公式规范**：数学公式请使用 LaTeX 格式（用 $...$ 包裹）
5. **难度适配**：根据{grade_level}学生的理解水平调整解答深度
6. **知识点标注**：在每道题后标注涉及的核心知识点

输出格式：
```markdown
# {subject} 试卷解答

## 第 1 题
**题目**：[完整复述题目内容]
**解答**：
[详细解答过程，包含必要的公式推导]
**知识点**：[核心知识点名称]

## 第 2 题
...
```

{"3. **JSON 数据**：在最后以 JSON 格式总结所有题目（包含题号、题目、答案、知识点）" if extract_formulas else ""}
"""
        
        # 使用重试机制处理超时
        @tenacity.retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=10, max=60),
            reraise=True
        )
        def call_with_retry():
            try:
                # 调用 GLM-4.6V，增加超时时间
                response = client.chat.completions.create(
                    model="glm-4.6v",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    thinking={"type": "enabled"},  # 启用深度思考模式
                    timeout=120.0  # 设置 2 分钟超时
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"GLM 调用失败（将重试）: {e}")
                raise
        
        try:
            result_text = call_with_retry()
            return result_text
        except Exception as e:
            logger.error(f"GLM 调用最终失败：{e}")
            raise
    
    async def _call_llm_for_pdf(self, markdown_content: str, subject: str, grade_level: str) -> str:
        """调用 LLM 分析 PDF 提取的内容。
        
        Args:
            markdown_content: pymupdf4llm 提取的 Markdown 内容
            subject: 科目
            grade_level: 年级水平
        
        Returns:
            解答文本
        """
        from litellm import completion
        
        # 使用 LiteLLM 统一接口调用
        response = await completion(
            model="zhipu/glm-4.6v",  # 通过 LiteLLM 调用
            messages=[
                {
                    "role": "system",
                    "content": f"你是一位专业的{subject}教师，负责解答{grade_level}水平的试卷题目。"
                },
                {
                    "role": "user",
                    "content": f"""请分析以下试卷内容并提供详细解答：

{markdown_content[:50000]}  # 限制长度避免超出上下文

要求：
1. 识别所有题目并编号
2. 为每道题提供详细解答步骤
3. 标注涉及的知识点
4. 公式使用 LaTeX 格式

请按 Markdown 格式输出。"""
                }
            ],
            api_key=self.api_key,
            api_base="https://open.bigmodel.cn/api/paas/v4",
        )
        
        result_text = response.choices[0].message.content.strip()
        return result_text
    
    def _extract_json_from_result(self, result_text: str) -> dict | None:
        """从结果文本中提取 JSON 数据。
        
        Args:
            result_text: 模型返回的文本
        
        Returns:
            JSON 数据字典，如果提取失败返回 None
        """
        import json
        import re
        
        # 尝试查找 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试查找裸 JSON 对象
        json_objects = re.findall(r'\{[^{}]*"problems"[^{}]*\}', result_text, re.DOTALL)
        for json_str in json_objects:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
        
        return None
