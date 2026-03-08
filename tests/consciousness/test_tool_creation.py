"""
测试工具创造模块
"""

import pytest
import asyncio
from src.consciousness.tool_creator import ToolCreator
from src.consciousness.sandbox.executor import SandboxExecutor
from src.consciousness.approval_interface import ApprovalInterface


class TestToolCreator:
    """测试工具创造功能"""
    
    @pytest.fixture
    def creator(self):
        """创建 ToolCreator 实例"""
        return ToolCreator(
            approval_manager=ApprovalInterface(),
            sandbox_dir="./test_tool_sandbox"
        )
    
    def test_identify_tool_need(self, creator):
        """测试工具需求识别"""
        context = {
            "user_request": "帮我下载这个网页的所有图片",
            "available_tools": ["file_reader", "doc_generator"]
        }
        
        need = asyncio.run(creator.identify_tool_need(context))
        assert need is not None
        assert "下载" in need or "工具" in need
    
    def test_design_tool_basic(self, creator):
        """测试工具设计"""
        spec = creator.design_tool(
            need="下载网页图片",
            tool_name="image_downloader",
            parameters={"url": {"type": "str"}}
        )
        
        assert spec.name == "image_downloader"
        assert "下载网页图片" in spec.description
        assert "url" in spec.parameters
        assert spec.risk_level == "medium"
        assert spec.requires_approval is True
    
    def test_select_template(self, creator):
        """测试模板选择"""
        assert creator._select_template("读取文件内容") == "file_processor"
        assert creator._select_template("分析数据") == "data_analyzer"
        assert creator._select_template("爬取网页") == "web_scraper"
        assert creator._select_template("未知需求") == "file_processor"  # 默认
    
    def test_risk_assessment(self, creator):
        """测试风险评估"""
        # 高风险
        spec_dict = {"description": "delete all files", "name": "file_deleter"}
        assert creator._assess_risk(spec_dict) == "high"
        
        # 中风险
        spec_dict = {"description": "write data to file", "name": "file_writer"}
        assert creator._assess_risk(spec_dict) == "medium"
        
        # 低风险
        spec_dict = {"description": "read file content", "name": "file_reader"}
        assert creator._assess_risk(spec_dict) == "low"


class TestSandboxExecutor:
    """测试沙箱执行器"""
    
    @pytest.fixture
    def executor(self):
        """创建 SandboxExecutor 实例"""
        return SandboxExecutor(
            sandbox_dir="./test_sandbox",
            timeout_seconds=5.0
        )
    
    def test_execute_safe_code(self, executor):
        """测试执行安全代码"""
        # 使用简单的计算代码
        code = "print(2 + 3)"
        result = asyncio.run(executor.execute_code(code))
        assert result.success is True
        assert "5" in result.output
    
    def test_execute_unsafe_import(self, executor):
        """测试阻止危险导入"""
        code = """
import os
os.system("whoami")
"""
        result = asyncio.run(executor.execute_code(code))
        # 应该失败或受限
        assert result.success is False or "ESCAPE_FAILED" in result.output
    
    def test_execution_timeout(self, executor):
        """测试执行超时"""
        code = """
import time
time.sleep(10)  # 超过 5 秒超时
"""
        result = asyncio.run(executor.execute_code(code))
        assert result.success is False
        # 超时或错误都算通过
        assert "timeout" in result.error.lower() or result.exit_code == -1
    
    def test_allowed_modules(self, executor):
        """测试模块白名单"""
        assert executor._is_module_allowed("json") is True
        assert executor._is_module_allowed("math") is True
        assert executor._is_module_allowed("subprocess") is False
        assert executor._is_module_allowed("os.system") is False


class TestApprovalInterface:
    """测试审批接口"""
    
    @pytest.fixture
    def interface(self):
        """创建 ApprovalInterface 实例"""
        return ApprovalInterface()
    
    def test_submit_request(self, interface):
        """测试提交请求"""
        request_id = asyncio.run(interface.submit_request(
            request_type="tool_creation",
            description="创建图片下载器",
            risk_level="medium",
            details={"tool_name": "image_downloader"}
        ))
        
        assert request_id.startswith("req_")
        assert request_id in interface.pending_requests
    
    def test_approve_request(self, interface):
        """测试批准请求"""
        request_id = asyncio.run(interface.submit_request(
            request_type="tool_creation",
            description="测试工具",
            risk_level="low",
            details={}
        ))
        
        result = asyncio.run(interface.decide(
            request_id=request_id,
            approved=True,
            decided_by="human",
            reason="功能有用"
        ))
        
        assert result is True
        assert request_id not in interface.pending_requests
        assert len(interface.history) == 1
        assert interface.history[0].decision.value == "approved"
    
    def test_reject_request(self, interface):
        """测试拒绝请求"""
        request_id = asyncio.run(interface.submit_request(
            request_type="self_repair",
            description="修改核心代码",
            risk_level="high",
            details={}
        ))
        
        result = asyncio.run(interface.decide(
            request_id=request_id,
            approved=False,
            decided_by="human",
            reason="风险太高"
        ))
        
        assert result is True
        assert interface.history[0].decision.value == "rejected"
    
    def test_wait_for_decision(self, interface):
        """测试等待决策"""
        async def test_workflow():
            # 提交请求
            request_id = await interface.submit_request(
                request_type="tool_creation",
                description="测试",
                risk_level="low",
                details={}
            )
            
            # 启动等待任务
            wait_task = asyncio.create_task(
                interface.wait_for_decision(request_id, timeout_seconds=2.0)
            )
            
            # 延迟批准后
            await asyncio.sleep(0.5)
            await interface.decide(request_id, True, "human", "测试通过")
            
            # 等待结果
            result = await wait_task
            return result
        
        result = asyncio.run(test_workflow())
        assert result is True
    
    def test_get_statistics(self, interface):
        """测试统计信息"""
        # 添加一些历史数据
        interface.history.append(type('obj', (object,), {
            'decision': type('obj', (object,), {'value': 'approved'}),
            'to_dict': lambda self: {}
        })())
        
        stats = interface.get_statistics()
        assert "total" in stats
        assert "approved" in stats
        assert "approval_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
