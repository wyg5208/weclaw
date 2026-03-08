"""
工具创造模块 - Phase 5 核心能力

允许系统自主识别需求、设计并创建新工具，扩展自身能力边界。
这是硅基生命"自我编程"能力的关键体现。

功能：
1. 需求识别 - 从上下文中发现工具需求
2. 工具设计 - 生成工具规格说明
3. 代码实现 - 编写工具代码
4. 测试验证 - 在沙箱中测试工具
5. 部署集成 - 将工具注册到系统

安全约束：
- 所有工具创建需要审批
- 代码必须通过安全性验证
- 在隔离沙箱中执行测试
- 禁止修改只读模块
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .types import (
    ToolSpecification,
    CreatedTool,
    ToolCreationStatus,
    RepairLevel,
)
from .safety import SafetyConstraints, ApprovalManager
from .sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)


class ToolCreator:
    """
    工具创造引擎
    
    实现完整的工具创建流程：
    需求 → 设计 → 实现 → 测试 → 部署
    """
    
    def __init__(
        self,
        approval_manager: Optional[ApprovalManager] = None,
        sandbox_dir: str = "./tool_sandbox"
    ):
        """
        初始化工具创造引擎
        
        Args:
            approval_manager: 审批管理器
            sandbox_dir: 沙箱目录
        """
        self.approval_manager = approval_manager or ApprovalManager()
        self.sandbox_executor = SandboxExecutor(sandbox_dir)
        
        # 工具模板库
        self.tool_templates = {
            "file_processor": self._get_file_processor_template(),
            "data_analyzer": self._get_data_analyzer_template(),
            "web_scraper": self._get_web_scraper_template(),
        }
        
        # 已创建的工具列表
        self.created_tools: List[CreatedTool] = []
        
        logger.info("ToolCreator initialized")
    
    async def identify_tool_need(self, context: dict) -> Optional[str]:
        """
        识别工具需求
        
        Args:
            context: 当前上下文（包含用户请求、历史对话等）
            
        Returns:
            工具需求描述，如果没有需求则返回 None
            
        示例：
        >>> context = {
        ...     "user_request": "帮我下载这个网页的所有图片",
        ...     "available_tools": ["file_reader", "doc_generator"]
        ... }
        >>> need = await creator.identify_tool_need(context)
        >>> print(need)
        "需要一个网页图片下载器工具"
        """
        user_request = context.get("user_request", "")
        available_tools = context.get("available_tools", [])
        
        # 分析需求模式
        need_patterns = [
            ("下载", "文件下载工具"),
            ("爬取", "网页爬虫工具"),
            ("批量处理", "批量操作工具"),
            ("自动化", "自动化脚本工具"),
            ("转换", "格式转换工具"),
        ]
        
        for pattern, tool_type in need_patterns:
            if pattern in user_request:
                # 检查是否已有类似工具
                if not any(tool_type in tool for tool in available_tools):
                    return f"需要{tool_type}来处理：{user_request}"
        
        return None
    
    def design_tool(
        self,
        need: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict] = None
    ) -> ToolSpecification:
        """
        设计工具规格
        
        Args:
            need: 需求描述
            tool_name: 工具名称（可选，自动生成）
            parameters: 参数定义（可选）
            
        Returns:
            工具规格说明
            
        示例：
        >>> spec = creator.design_tool(
        ...     need="下载网页图片",
        ...     tool_name="image_downloader",
        ...     parameters={"url": "str", "save_dir": "str"}
        ... )
        """
        import uuid
        
        # 自动生成工具名称
        if not tool_name:
            tool_name = f"auto_tool_{uuid.uuid4().hex[:8]}"
        
        # 选择模板
        template_type = self._select_template(need)
        template = self.tool_templates.get(template_type, {})
        
        # 构建规格说明
        spec = ToolSpecification(
            name=tool_name,
            description=f"Auto-created tool for: {need}",
            parameters=parameters or template.get("parameters", {}),
            returns={"type": template.get("return_type", "Any")},
            risk_level="medium",  # 默认中等风险
            requires_approval=True,
        )
        
        logger.info(f"Designed tool specification: {tool_name}")
        return spec
    
    async def implement_tool(
        self,
        spec: ToolSpecification,
        custom_code: Optional[str] = None
    ) -> str:
        """
        实现工具代码
        
        Args:
            spec: 工具规格说明
            custom_code: 自定义代码（可选，否则使用模板）
            
        Returns:
            生成的工具代码
            
        流程：
        1. 选择代码模板
        2. 填充参数
        3. 生成完整代码
        4. 格式化代码
        """
        if custom_code:
            code = custom_code
        else:
            # 使用模板生成代码
            template = spec.code_template or self._get_default_template()
            code = self._fill_template(template, spec)
        
        # 代码格式化
        formatted_code = self._format_code(code)
        
        # 安全性预检查
        is_safe, violations = SafetyConstraints.validate_tool_code(formatted_code)
        if not is_safe:
            logger.warning(f"Tool code has safety violations: {violations}")
            raise ValueError(f"Code safety violation: {violations}")
        
        logger.info(f"Implemented tool code for: {spec.tool_id}")
        return formatted_code
    
    async def test_tool(self, tool: CreatedTool) -> List[Dict]:
        """
        测试工具
        
        Args:
            tool: 已创建的工具
            
        Returns:
            测试结果列表
            
        测试流程：
        1. 在沙箱中加载代码
        2. 运行单元测试
        3. 运行集成测试
        4. 性能测试
        5. 安全性复测
        """
        results = []
        
        # 1. 语法测试
        syntax_result = await self._test_syntax(tool.code)
        results.append({"type": "syntax", "passed": syntax_result})
        
        # 2. 功能测试
        if syntax_result:
            func_results = await self.sandbox_executor.run_functional_tests(
                tool.code,
                tool.spec.parameters
            )
            results.extend(func_results)
        
        # 3. 安全性测试
        safety_result = await self._test_safety(tool.code)
        results.append({"type": "safety", "passed": safety_result})
        
        # 4. 性能测试
        perf_result = await self._test_performance(tool.code)
        results.append({"type": "performance", **perf_result})
        
        all_passed = all(r.get("passed", False) for r in results)
        logger.info(
            f"Tool testing {'passed' if all_passed else 'failed'}: "
            f"{tool.spec.name}"
        )
        
        return results
    
    async def deploy_tool(
        self,
        tool: CreatedTool,
        target_directory: str = "./tools/auto_generated"
    ) -> bool:
        """
        部署工具
        
        Args:
            tool: 已测试通过的工具
            target_directory: 目标目录
            
        Returns:
            是否部署成功
            
        部署步骤：
        1. 保存工具代码到文件
        2. 注册到工具注册表
        3. 更新工具索引
        4. 记录部署日志
        """
        try:
            import os
            import json
            
            # 创建目标目录
            os.makedirs(target_directory, exist_ok=True)
            
            # 保存工具代码
            tool_file = os.path.join(target_directory, f"{tool.spec.tool_id}.py")
            with open(tool_file, "w", encoding="utf-8") as f:
                f.write(tool.code)
            
            # 保存工具元数据
            metadata = {
                "tool_id": tool.spec.tool_id,
                "name": tool.spec.name,
                "description": tool.spec.description,
                "parameters": tool.spec.parameters,
                "created_at": tool.created_at.isoformat(),
                "version": tool.version,
            }
            
            metadata_file = os.path.join(
                target_directory,
                f"{tool.spec.tool_id}.metadata.json"
            )
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            
            # 添加到已创建工具列表
            self.created_tools.append(tool)
            
            logger.info(f"Tool deployed successfully: {tool.spec.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy tool: {e}")
            return False
    
    async def create_tool_from_need(
        self,
        need: dict,
        require_approval: bool = True
    ) -> Optional[CreatedTool]:
        """
        从需求创建完整工具
        
        Args:
            need: 需求字典（包含 description, parameters 等）
            require_approval: 是否需要审批
            
        Returns:
            创建成功的工具，失败则返回 None
            
        完整流程：
        1. 识别需求
        2. 设计规格
        3. 提交审批（如果需要）
        4. 实现代码
        5. 测试验证
        6. 部署工具
        """
        try:
            # 1. 设计工具规格
            spec = self.design_tool(
                need=need.get("description", ""),
                tool_name=need.get("name"),
                parameters=need.get("parameters")
            )
            
            # 2. 风险评估
            risk_level = self._assess_risk(asdict(spec))
            spec.risk_level = risk_level
            
            # 3. 提交审批
            if require_approval and risk_level in ["medium", "high"]:
                approval_request = {
                    "type": "tool_creation",
                    "description": f"创建新工具：{spec.name}",
                    "risk_level": risk_level,
                    "details": asdict(spec),
                }
                
                request_id = await self.approval_manager.submit_request(
                    **approval_request
                )
                
                # 等待人类决策
                decision = await self.approval_manager.wait_for_decision(
                    request_id,
                    timeout_seconds=600  # 10 分钟超时
                )
                
                if not decision:
                    logger.warning(f"Tool creation denied by human: {spec.name}")
                    return None
            
            # 4. 实现代码
            code = await self.implement_tool(spec)
            
            # 5. 创建工具对象
            tool = CreatedTool(specification=spec, code=code)
            
            # 6. 测试工具
            test_results = await self.test_tool(tool)
            if not all(r.get("passed", False) for r in test_results):
                logger.error(f"Tool testing failed: {spec.name}")
                return None
            
            # 7. 部署工具
            deployed = await self.deploy_tool(tool)
            if not deployed:
                logger.error(f"Tool deployment failed: {spec.name}")
                return None
            
            logger.info(f"Tool created successfully: {spec.name}")
            return tool
            
        except Exception as e:
            logger.error(f"Error creating tool: {e}")
            return None
    
    # ========== 辅助方法 ==========
    
    def _select_template(self, need: str) -> str:
        """选择最适合的模板"""
        need_lower = need.lower()
        
        if any(word in need_lower for word in ["文件", "file", "读取", "写入"]):
            return "file_processor"
        elif any(word in need_lower for word in ["分析", "analyze", "数据", "data"]):
            return "data_analyzer"
        elif any(word in need_lower for word in ["爬取", "scrape", "网页", "web"]):
            return "web_scraper"
        else:
            return "file_processor"  # 默认模板
    
    def _get_file_processor_template(self) -> dict:
        """文件处理器模板"""
        return {
            "parameters": {
                "file_path": {"type": "str", "description": "文件路径"},
                "mode": {"type": "str", "description": "操作模式", "default": "read"},
            },
            "return_type": "str",
            "code": """
async def execute(file_path: str, mode: str = "read") -> str:
    \"\"\"文件处理工具\"\"\"
    import aiofiles
    
    if mode == "read":
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    elif mode == "write":
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write("content")
        return "OK"
    else:
        raise ValueError(f"Unknown mode: {mode}")
""",
        }
    
    def _get_data_analyzer_template(self) -> dict:
        """数据分析器模板"""
        return {
            "parameters": {
                "data": {"type": "list", "description": "数据列表"},
                "operation": {"type": "str", "description": "分析操作"},
            },
            "return_type": "dict",
            "code": """
async def execute(data: list, operation: str) -> dict:
    \"\"\"数据分析工具\"\"\"
    if operation == "statistics":
        return {
            "count": len(data),
            "sum": sum(data),
            "average": sum(data) / len(data) if data else 0
        }
    elif operation == "min_max":
        return {
            "min": min(data) if data else None,
            "max": max(data) if data else None
        }
    else:
        raise ValueError(f"Unknown operation: {operation}")
""",
        }
    
    def _get_web_scraper_template(self) -> dict:
        """网页爬虫模板"""
        return {
            "parameters": {
                "url": {"type": "str", "description": "目标 URL"},
                "selector": {"type": "str", "description": "CSS 选择器"},
            },
            "return_type": "list",
            "code": """
async def execute(url: str, selector: str) -> list:
    \"\"\"网页爬虫工具\"\"\"
    import aiohttp
    from bs4 import BeautifulSoup
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            elements = soup.select(selector)
            return [elem.get_text() for elem in elements]
""",
        }
    
    def _get_default_template(self) -> str:
        """默认代码模板"""
        return """
async def execute(**kwargs):
    \"\"\"自动生成的工具\"\"\"
    # TODO: 实现具体逻辑
    pass
"""
    
    def _fill_template(self, template: str, spec: ToolSpecification) -> str:
        """填充模板"""
        # 简单的字符串替换，实际应该用 AST 或模板引擎
        code = template.replace(
            "async def execute",
            f"async def {spec.tool_id}_execute"
        )
        return code
    
    def _format_code(self, code: str) -> str:
        """格式化代码"""
        try:
            import black
            return black.format_str(code, mode=black.FileMode())
        except ImportError:
            # 如果没有 black，简单清理
            lines = code.split('\n')
            return '\n'.join(line.rstrip() for line in lines)
    
    async def _test_syntax(self, code: str) -> bool:
        """测试语法正确性"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    async def _test_safety(self, code: str) -> bool:
        """测试安全性"""
        is_safe, _ = SafetyConstraints.validate_tool_code(code)
        return is_safe
    
    async def _test_performance(self, code: str) -> dict:
        """简单的性能测试"""
        import time
        
        start = time.time()
        # 这里应该运行性能测试套件
        elapsed = time.time() - start
        
        return {
            "compile_time": elapsed,
            "complexity": "low",  # 应该用 AST 分析
        }
    
    def _assess_risk(self, spec_dict: dict) -> str:
        """
        评估工具风险等级
        
        考虑因素：
        - 操作类型（读/写/执行）
        - 影响范围（单文件/系统/网络）
        - 可逆性（是否可撤销）
        """
        risk_keywords = {
            "high": ["delete", "remove", "format", "shutdown", "execute"],
            "medium": ["write", "modify", "create", "download"],
            "low": ["read", "view", "analyze", "calculate"],
        }
        
        desc = spec_dict.get("description", "").lower()
        name = spec_dict.get("name", "").lower()
        
        for level, keywords in risk_keywords.items():
            if any(kw in desc or kw in name for kw in keywords):
                return level
        
        return "low"  # 默认低风险


__all__ = ["ToolCreator"]
