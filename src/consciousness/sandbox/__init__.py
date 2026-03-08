"""
工具沙箱子包

提供隔离的代码执行环境
"""

from .executor import SandboxExecutor, ExecutionResult

__version__ = "1.0.0"
__all__ = ["SandboxExecutor", "ExecutionResult"]
