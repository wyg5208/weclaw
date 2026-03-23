"""高拍仪文档扫描工具 - 支持试卷/作业智能解析与缓存。

功能特性:
- 自动扫描指定文件夹的图片
- 使用 GLM-4.6V 进行智能题目识别和解答
- SQLite 数据库存储解析结果
- 文件指纹缓存，避免重复解析
- 批量处理和增量更新
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class DocumentScannerTool(BaseTool):
    """高拍仪文档扫描工具。
    
    专门用于处理高拍仪扫描的试卷、作业等文档，提供：
    1. 智能题目识别（GLM-4.6V）
    2. 详细解答生成
    3. 数据库持久化存储
    4. 文件指纹缓存机制
    """
    
    name = "document_scanner"
    emoji = "📷"
    title = "高拍仪扫描"
    description = "高拍仪文档智能扫描与解析工具，支持试卷作业批改"
    timeout = 300  # 5 分钟超时
    
    def __init__(self, db_path: str | None = None, scan_folder: str | None = None):
        """初始化高拍仪工具。
        
        Args:
            db_path: 数据库路径，默认 ~/.weclaw/scanner.db
            scan_folder: 扫描文件夹，默认 D:/python_projects/weclaw/docs/deli_scan_image
        """
        super().__init__()
        
        # 加载环境变量
        load_dotenv()
        self.api_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
        
        # 数据库路径
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / ".weclaw" / "scanner.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 扫描文件夹
        if scan_folder:
            self.scan_folder = Path(scan_folder)
        else:
            self.scan_folder = Path("D:/python_projects/weclaw/docs/deli_scan_image")
        
        # 数据库连接
        self._conn = None
        self._initialized = False
    
    async def _ensure_db(self):
        """确保数据库已初始化。"""
        if self._initialized:
            return
        
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as conn:
            # 创建扫描记录表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    subject TEXT DEFAULT '数学',
                    grade_level TEXT DEFAULT '高中',
                    status TEXT NOT NULL,
                    md_file_path TEXT,
                    json_file_path TEXT,
                    problem_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                )
            """)
            
            # 创建索引
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_hash ON scan_records(file_hash)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON scan_records(status)
            """)
            
            await conn.commit()
        
        self._initialized = True
    
    async def _get_file_hash(self, file_path: Path) -> str:
        """计算文件的 SHA256 哈希值。
        
        Args:
            file_path: 文件路径
            
        Returns:
            SHA256 哈希值（十六进制字符串）
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def _check_cache(self, file_hash: str) -> dict | None:
        """检查缓存中是否已有该文件的解析结果。
        
        Args:
            file_hash: 文件哈希值
            
        Returns:
            如果存在返回记录字典，否则返回 None
        """
        await self._ensure_db()
        
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM scan_records 
                WHERE file_hash = ? AND status = 'success'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (file_hash,)
            )
            row = await cursor.fetchone()
            
            if row:
                return dict(row)
        return None
    
    async def _save_result(
        self,
        file_path: Path,
        file_hash: str,
        result_data: dict,
        subject: str = "数学",
        grade_level: str = "高中"
    ):
        """保存解析结果到数据库。
        
        Args:
            file_path: 文件路径
            file_hash: 文件哈希值
            result_data: 解析结果数据
            subject: 科目
            grade_level: 年级水平
        """
        await self._ensure_db()
        
        import aiosqlite
        
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO scan_records 
                (file_path, file_hash, file_name, file_size, subject, grade_level, 
                 status, md_file_path, json_file_path, problem_count, 
                 created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(file_path),
                    file_hash,
                    file_path.name,
                    file_path.stat().st_size,
                    subject,
                    grade_level,
                    result_data.get("status", "success"),
                    result_data.get("md_file_path"),
                    result_data.get("json_file_path"),
                    result_data.get("problem_count", 0),
                    now,
                    now,
                    json.dumps(result_data.get("metadata", {}))
                )
            )
            await conn.commit()
    
    async def _call_glm_vision(self, img_base64: str, subject: str, grade_level: str) -> str:
        """调用 GLM-4.6V 进行题目识别和解答。
        
        Args:
            img_base64: Base64 编码的图片
            subject: 科目
            grade_level: 年级水平
            
        Returns:
            解答文本（Markdown 格式）
        """
        from zai import ZhipuAiClient
        import tenacity
        from tenacity import stop_after_attempt, wait_exponential
        
        if not self.api_key:
            raise ValueError("未配置 GLM_API_KEY")
        
        client = ZhipuAiClient(api_key=self.api_key)
        
        prompt = f"""你是一位专业的{subject}教师，请仔细分析这张试卷/作业图片中的题目。

要求：
1. **题目识别**：准确识别图片中的所有题目内容
2. **详细解答**：为每道题目提供详细的解答过程
3. **步骤清晰**：解答步骤要条理清晰，逻辑严密
4. **公式规范**：数学公式请使用 LaTeX 格式（用 $...$ 包裹）
5. **难度适配**：根据{grade_level}学生的理解水平调整解答深度
6. **知识点标注**：在每道题后标注涉及的核心知识点
7. **批改建议**：如果是学生作业，请给出批改意见和改进建议

输出格式：
```markdown
# {subject} 试卷/作业解析

**基本信息**:
- 科目：{subject}
- 年级：{grade_level}
- 解析时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 第 1 题
**题目**：[完整复述题目内容]
**解答**：
[详细解答过程，包含必要的公式推导]
**知识点**：[核心知识点名称]
**批改建议**：[如果是作业，给出批改意见]

## 第 2 题
...

---

## 总结
**总题数**：X 题
**主要知识点**：[列出所有涉及的知识点]
**学习建议**：[针对性的学习建议]
```

请在最后以 JSON 格式总结：
```json
{{
    "subject": "{subject}",
    "grade_level": "{grade_level}",
    "problem_count": X,
    "problems": [
        {{
            "id": 1,
            "title": "题目简述",
            "type": "题目类型",
            "answer": "答案",
            "knowledge_points": ["知识点 1", "知识点 2"]
        }}
    ],
    "total_score": 100,
    "suggestions": ["建议 1", "建议 2"]
}}
```
"""
        
        # 使用 asyncio.to_thread 在后台线程中执行同步 API 调用
        async def call_api():
            try:
                response = await asyncio.to_thread(
                    client.chat.completions.create,
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
                    thinking={"type": "enabled"},
                    timeout=180.0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"GLM 调用失败：{e}")
                raise
        
        # 重试机制
        last_error = None
        for attempt in range(3):
            try:
                return await call_api()
            except Exception as e:
                last_error = e
                if attempt < 2:  # 最后一次不等待
                    wait_time = min(10 * (2 ** attempt), 60)  # 指数退避：10s, 20s, 40s
                    logger.warning(f"GLM 调用失败（将重试，等待{wait_time}秒）: {e}")
                    await asyncio.sleep(wait_time)
        
        raise last_error
    
    async def _process_single_file(
        self,
        file_path: Path,
        subject: str = "数学",
        grade_level: str = "高中"
    ) -> ToolResult:
        """处理单个文件。
        
        Args:
            file_path: 文件路径
            subject: 科目
            grade_level: 年级水平
            
        Returns:
            工具执行结果
        """
        try:
            # 检查文件是否存在
            if not file_path.exists():
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"文件不存在：{file_path}"
                )
            
            # 检查文件大小（限制 20MB）
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 20:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"文件过大：{file_size_mb:.2f}MB（限制 20MB）"
                )
            
            # 计算文件哈希
            file_hash = await self._get_file_hash(file_path)
            
            # 检查缓存
            cached_result = await self._check_cache(file_hash)
            if cached_result:
                logger.info(f"使用缓存结果：{file_path.name}")
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=f"✅ 使用缓存结果：{cached_result['file_name']}\n📄 MD: {cached_result['md_file_path']}\n📊 题目数：{cached_result['problem_count']}",
                    data={
                        "cached": True,
                        "md_file_path": cached_result["md_file_path"],
                        "json_file_path": cached_result.get("json_file_path"),
                        "problem_count": cached_result["problem_count"]
                    }
                )
            
            # 读取图片并转换为 base64
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            import base64
            img_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            logger.info(f"开始解析：{file_path.name} ({file_size_mb:.2f} MB)")
            
            # 调用 GLM-4.6V 进行解析
            result_text = await self._call_glm_vision(
                img_base64,
                subject,
                grade_level
            )
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{file_path.stem}_解析_{timestamp}"
            
            # 确定输出目录
            output_dir = Path.home() / ".weclaw" / "scanner_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存 Markdown 文件
            md_path = output_dir / f"{output_filename}.md"
            md_path.write_text(result_text, encoding="utf-8")
            
            # 提取 JSON 数据
            json_data = self._extract_json_from_result(result_text)
            json_path = None
            problem_count = 0
            
            if json_data:
                json_path = output_dir / f"{output_filename}.json"
                json_path.write_text(
                    json.dumps(json_data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                problem_count = json_data.get("problem_count", 0)
            
            # 保存到数据库
            result_data = {
                "status": "success",
                "md_file_path": str(md_path),
                "json_file_path": str(json_path) if json_path else None,
                "problem_count": problem_count,
                "metadata": {
                    "original_file": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "processing_time": datetime.now().isoformat()
                }
            }
            
            await self._save_result(
                file_path,
                file_hash,
                result_data,
                subject,
                grade_level
            )
            
            logger.info(f"解析完成：{file_path.name} (题目数：{problem_count})")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 解析完成：{file_path.name}\n📄 MD: {md_path.name}\n📊 题目数：{problem_count}",
                data={
                    "cached": False,
                    "md_file_path": str(md_path),
                    "json_file_path": str(json_path) if json_path else None,
                    "problem_count": problem_count,
                    "file_hash": file_hash
                }
            )
        
        except Exception as e:
            logger.exception(f"文件解析失败：{file_path}")
            
            # 保存失败记录
            try:
                file_hash = await self._get_file_hash(file_path)
                await self._save_result(
                    file_path,
                    file_hash,
                    {"status": "failed", "error": str(e)},
                    subject,
                    grade_level
                )
            except:
                pass
            
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"解析失败：{e}"
            )
    
    def _extract_json_from_result(self, result_text: str) -> dict | None:
        """从结果文本中提取 JSON 数据。
        
        Args:
            result_text: 模型返回的文本
            
        Returns:
            JSON 数据字典，如果提取失败返回 None
        """
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
    
    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="scan_file",
                description="扫描并解析单个文件（图片/PDF）",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
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
                },
                required_params=["file_path"],
            ),
            ActionDef(
                name="scan_folder",
                description="批量扫描文件夹中的所有图片",
                parameters={
                    "folder_path": {
                        "type": "string",
                        "description": "文件夹路径，默认使用配置的扫描文件夹",
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
                        "description": "文件匹配模式",
                        "default": "*.jpg,*.png,*.bmp",
                    },
                    "force_reprocess": {
                        "type": "boolean",
                        "description": "是否强制重新处理（忽略缓存）",
                        "default": False,
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="query_history",
                description="查询历史扫描记录",
                parameters={
                    "file_hash": {
                        "type": "string",
                        "description": "文件哈希值（可选）",
                    },
                    "status": {
                        "type": "string",
                        "description": "状态过滤",
                        "enum": ["all", "success", "failed"],
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 20,
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="clear_cache",
                description="清除缓存记录",
                parameters={
                    "older_than_days": {
                        "type": "integer",
                        "description": "清除多少天前的记录",
                        "default": 30,
                    },
                },
                required_params=[],
            ),
        ]
    
    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的动作。"""
        action_map = {
            "scan_file": self._scan_file,
            "scan_folder": self._scan_folder,
            "query_history": self._query_history,
            "clear_cache": self._clear_cache,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作：{action}"
            )
        
        try:
            return await handler(params)
        except Exception as e:
            logger.error(f"工具执行失败：{e}", exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"执行失败：{e}"
            )
    
    async def _scan_file(self, params: dict[str, Any]) -> ToolResult:
        """扫描单个文件。"""
        file_path_str = params.get("file_path", "").strip()
        subject = params.get("subject", "数学").strip()
        grade_level = params.get("grade_level", "高中").strip()
        
        if not file_path_str:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少必需参数：file_path"
            )
        
        file_path = Path(file_path_str).expanduser().resolve()
        
        return await self._process_single_file(file_path, subject, grade_level)
    
    async def _scan_folder(self, params: dict[str, Any]) -> ToolResult:
        """批量扫描文件夹。"""
        folder_path_str = params.get("folder_path", "")
        subject = params.get("subject", "数学").strip()
        grade_level = params.get("grade_level", "高中").strip()
        file_pattern = params.get("file_pattern", "*.jpg,*.png,*.bmp").strip()
        force_reprocess = params.get("force_reprocess", False)
        
        # 确定扫描文件夹
        if folder_path_str:
            folder_path = Path(folder_path_str).expanduser().resolve()
        else:
            folder_path = self.scan_folder
        
        if not folder_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件夹不存在：{folder_path}"
            )
        
        # 解析文件模式
        patterns = [p.strip() for p in file_pattern.split(",")]
        
        # 查找所有匹配的文件
        files = []
        for pattern in patterns:
            files.extend(folder_path.glob(pattern))
        
        if not files:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到符合条件的文件：{folder_path}"
            )
        
        logger.info(f"找到 {len(files)} 个文件")
        
        # 处理每个文件
        results = []
        success_count = 0
        error_count = 0
        cache_hit_count = 0
        
        start_time = datetime.now()
        
        for i, file_path in enumerate(files, 1):
            logger.info(f"[{i}/{len(files)}] 处理：{file_path.name}")
            
            # 如果强制重新处理，先删除缓存记录
            if force_reprocess:
                file_hash = await self._get_file_hash(file_path)
                await self._delete_cache_record(file_hash)
            
            result = await self._process_single_file(file_path, subject, grade_level)
            
            if result.is_success:
                success_count += 1
                if result.data.get("cached"):
                    cache_hit_count += 1
            else:
                error_count += 1
            
            results.append({
                "file": file_path.name,
                "status": result.status.value,
                "cached": result.data.get("cached", False) if result.data else False
            })
        
        duration = datetime.now() - start_time
        
        # 生成汇总报告
        summary = f"""✅ 批量扫描完成

📊 统计信息:
- 总文件数：{len(files)}
- 成功：{success_count}
- 失败：{error_count}
- 缓存命中：{cache_hit_count}
- 耗时：{duration}

📋 详细结果:
"""
        
        for r in results:
            status_icon = "✅" if r["status"] == "success" else "❌"
            cache_mark = " (缓存)" if r["cached"] else ""
            summary += f"{status_icon} {r['file']}{cache_mark}\n"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=summary,
            data={
                "total_files": len(files),
                "success_count": success_count,
                "error_count": error_count,
                "cache_hit_count": cache_hit_count,
                "duration": str(duration),
                "results": results
            }
        )
    
    async def _query_history(self, params: dict[str, Any]) -> ToolResult:
        """查询历史记录。"""
        file_hash = params.get("file_hash")
        status = params.get("status", "all")
        limit = params.get("limit", 20)
        
        await self._ensure_db()
        
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            if file_hash:
                cursor = await conn.execute(
                    "SELECT * FROM scan_records WHERE file_hash = ? ORDER BY updated_at DESC",
                    (file_hash,)
                )
            elif status != "all":
                cursor = await conn.execute(
                    "SELECT * FROM scan_records WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM scan_records ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                )
            
            rows = await cursor.fetchall()
            records = [dict(row) for row in rows]
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"查询到 {len(records)} 条记录",
            data={"records": records}
        )
    
    async def _clear_cache(self, params: dict[str, Any]) -> ToolResult:
        """清除缓存。"""
        older_than_days = params.get("older_than_days", 30)
        
        await self._ensure_db()
        
        import aiosqlite
        from datetime import timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM scan_records WHERE updated_at < ?",
                (cutoff_date,)
            )
            deleted_count = cursor.rowcount
            await conn.commit()
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已清除 {deleted_count} 条 {older_than_days} 天前的记录",
            data={"deleted_count": deleted_count}
        )
    
    async def _delete_cache_record(self, file_hash: str):
        """删除指定哈希值的缓存记录。
        
        Args:
            file_hash: 文件哈希值
        """
        await self._ensure_db()
        
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "DELETE FROM scan_records WHERE file_hash = ?",
                (file_hash,)
            )
            await conn.commit()
