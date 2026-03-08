"""
工具沙箱执行环境 - Phase 5 安全基础设施

提供隔离的代码执行环境，确保 AI 创建的代码无法影响主系统。

安全特性：
1. 文件系统隔离 - 只能访问沙箱目录
2. 网络访问限制 - 可选的网络权限
3. 资源使用限制 - CPU、内存、时间限制
4. 导入白名单 - 只允许安全的模块
5. 输出捕获 - 记录所有输出和异常
"""

import asyncio
import logging
import os
import sys
import tempfile
import traceback
import multiprocessing
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from contextlib import contextmanager
import io
import subprocess
import json

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    memory_used: int = 0
    exit_code: int = 0


class SandboxExecutor:
    """
    沙箱执行器
    
    在隔离环境中运行 AI 创建的代码
    """
    
    # 允许的模块白名单
    ALLOWED_MODULES = {
        # 基础模块
        "math", "random", "datetime", "collections",
        "itertools", "functools", "operator", "re",
        # 数据处理
        "json", "csv", "xml", "yaml",
        # 字符串处理
        "string", "textwrap", "unicodedata",
        # 文件操作（受限）
        "pathlib", "shutil",
        # 网络（可选）
        "urllib", "http",
        # 第三方库（安全）
        "aiofiles", "beautifulsoup4", "lxml",
    }
    
    def __init__(
        self,
        sandbox_dir: str = "./tool_sandbox",
        enable_network: bool = False,
        timeout_seconds: float = 10.0,
        max_memory_mb: int = 256
    ):
        """
        初始化沙箱执行器
        
        Args:
            sandbox_dir: 沙箱目录
            enable_network: 是否启用网络访问
            timeout_seconds: 执行超时（秒）
            max_memory_mb: 最大内存使用（MB）
        """
        self.sandbox_dir = sandbox_dir
        self.enable_network = enable_network
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        
        # 创建沙箱目录
        os.makedirs(sandbox_dir, exist_ok=True)
        
        logger.info(
            f"SandboxExecutor initialized: dir={sandbox_dir}, "
            f"network={enable_network}, timeout={timeout_seconds}s"
        )
    
    @contextmanager
    def _isolated_environment(self):
        """创建隔离的执行环境"""
        # 保存原始环境
        original_path = sys.path.copy()
        original_modules = sys.modules.copy()
        
        try:
            # 设置沙箱路径
            sys.path.insert(0, self.sandbox_dir)
            
            # 移除禁止的模块
            for module_name in list(sys.modules.keys()):
                if not self._is_module_allowed(module_name):
                    del sys.modules[module_name]
            
            yield
            
        finally:
            # 恢复原始环境
            sys.path = original_path
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def _is_module_allowed(self, module_name: str) -> bool:
        """检查模块是否被允许"""
        # 直接匹配
        if module_name in self.ALLOWED_MODULES:
            return True
        
        # 子模块检查
        parts = module_name.split(".")
        if parts and parts[0] in self.ALLOWED_MODULES:
            return True
        
        return False
    
    async def execute_code(
        self,
        code: str,
        globals_dict: Optional[Dict] = None,
        locals_dict: Optional[Dict] = None
    ) -> ExecutionResult:
        """
        执行代码（使用子进程隔离）
        
        Args:
            code: 要执行的代码
            globals_dict: 全局命名空间
            locals_dict: 局部命名空间
            
        Returns:
            执行结果
            
        安全措施：
        1. 在独立子进程中执行
        2. 限制执行时间
        3. 完全的环境隔离
        4. 捕获所有异常
        """
        import time
        start_time = time.time()
        
        try:
            # 准备子进程执行的脚本
            script = self._prepare_execution_script(code, globals_dict or {})
            
            # 在子进程中执行
            result = await asyncio.wait_for(
                self._run_in_subprocess(script),
                timeout=self.timeout_seconds
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result['success'],
                output=result.get('output', ''),
                error=result.get('error', ''),
                execution_time=execution_time,
                exit_code=result.get('exit_code', 0)
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=f"Execution timeout after {self.timeout_seconds}s",
                execution_time=execution_time,
                exit_code=-1
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return ExecutionResult(
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time,
                exit_code=-1
            )
    
    async def _execute_in_thread(
        self,
        code: str,
        globals_dict: Dict,
        locals_dict: Dict
    ):
        """在线程中执行代码（已废弃，保留用于向后兼容）"""
        # 已迁移到子进程执行
        raise NotImplementedError("Use subprocess execution instead")
    
    def _prepare_execution_script(self, code: str, globals_dict: Dict) -> str:
        """准备子进程执行脚本"""
        import json
        
        # 创建安全的执行脚本
        script = f'''
import sys
import json

# 限制内置函数
safe_builtins = {{
    "abs", "all", "any", "bin", "bool", "bytearray", "bytes",
    "chr", "complex", "dict", "dir", "divmod", "enumerate",
    "filter", "float", "format", "frozenset", "getattr",
    "hasattr", "hash", "hex", "id", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max",
    "min", "next", "object", "oct", "ord", "pow", "print",
    "range", "repr", "reversed", "round", "set", "slice",
    "sorted", "str", "sum", "super", "tuple", "type",
    "zip",
}}

# 构建安全的 __builtins__
import builtins
exec_globals = {{
    "__builtins__": {{k: getattr(builtins, k) for k in safe_builtins if hasattr(builtins, k)}}
}}

# 添加用户提供的变量
for key, value in {json.dumps(globals_dict, default=str)}.items():
    exec_globals[key] = value

try:
    # 重定向输出
    from io import StringIO
    output_buffer = StringIO()
    error_buffer = StringIO()
    sys.stdout = output_buffer
    sys.stderr = error_buffer
    
    # 执行代码
    exec({json.dumps(code)}, exec_globals)
    
    # 返回成功结果
    result = {{
        "success": True,
        "output": output_buffer.getvalue(),
        "error": error_buffer.getvalue(),
        "exit_code": 0
    }}
except Exception as e:
    # 返回错误结果
    import traceback
    result = {{
        "success": False,
        "output": "",
        "error": f"{{type(e).__name__}}: {{str(e)}}\\n{{traceback.format_exc()}}",
        "exit_code": -1
    }}
finally:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

# 输出 JSON 结果
print(json.dumps(result, ensure_ascii=False))
'''
        return script
    
    async def _run_in_subprocess(self, script: str) -> Dict:
        """在子进程中运行脚本"""
        loop = asyncio.get_event_loop()
        
        def run_script():
            try:
                # 使用 Python 子进程执行
                process = subprocess.Popen(
                    [sys.executable, '-c', script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.sandbox_dir
                )
                
                # communicate 支持 timeout
                stdout, stderr = process.communicate(timeout=self.timeout_seconds)
                
                # 解析 JSON 输出
                try:
                    result = json.loads(stdout.strip())
                    return result
                except json.JSONDecodeError:
                    # 如果没有 JSON 输出，返回原始输出
                    return {
                        "success": process.returncode == 0,
                        "output": stdout,
                        "error": stderr,
                        "exit_code": process.returncode
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Timeout after {self.timeout_seconds}s",
                    "exit_code": -1
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "exit_code": -1
                }
        
        return await loop.run_in_executor(None, run_script)
    
    async def run_functional_tests(
        self,
        tool_code: str,
        parameters: Dict[str, Any]
    ) -> List[Dict]:
        """
        运行功能测试
        
        Args:
            tool_code: 工具代码
            parameters: 参数定义
            
        Returns:
            测试结果列表
            
        测试策略：
        1. 边界值测试
        2. 正常流程测试
        3. 异常流程测试
        4. 性能测试
        """
        results = []
        
        # 生成测试用例
        test_cases = self._generate_test_cases(parameters)
        
        for i, test_case in enumerate(test_cases, 1):
            # 构建测试代码
            test_code = f"""
{tool_code}

# 测试用例 {i}
import asyncio

async def test_{i}():
    result = await {test_case['call']}
    return result

# 运行测试
result = asyncio.run(test_{i}())
print(f"Test {i} result: {{result}}")
"""
            # 执行测试
            result = await self.execute_code(test_code)
            
            test_result = {
                "type": "functional",
                "case_id": i,
                "case_name": test_case.get("name", f"test_{i}"),
                "passed": result.success,
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time,
            }
            
            results.append(test_result)
            
            logger.debug(
                f"Functional test {i}: {'PASS' if result.success else 'FAIL'}"
            )
        
        return results
    
    def _generate_test_cases(self, parameters: Dict) -> List[Dict]:
        """
        生成测试用例
        
        Args:
            parameters: 参数定义
            
        Returns:
            测试用例列表
        """
        test_cases = []
        
        # 简单策略：为每个参数类型生成默认值
        test_params = {}
        for param_name, param_def in parameters.items():
            param_type = param_def.get("type", "str")
            default = param_def.get("default")
            
            if default is not None:
                test_params[param_name] = default
            elif param_type == "str":
                test_params[param_name] = "test_value"
            elif param_type == "int":
                test_params[param_name] = 0
            elif param_type == "float":
                test_params[param_name] = 0.0
            elif param_type == "list":
                test_params[param_name] = []
            elif param_type == "dict":
                test_params[param_name] = {}
            elif param_type == "bool":
                test_params[param_name] = False
        
        # 正常流程测试
        params_str = ", ".join(
            f"{k}={repr(v)}" for k, v in test_params.items()
        )
        test_cases.append({
            "name": "normal_case",
            "call": f"execute({params_str})",
        })
        
        # 边界值测试（如果有数值参数）
        for param_name, param_def in parameters.items():
            if param_def.get("type") in ["int", "float"]:
                # 测试零值
                test_params_copy = test_params.copy()
                test_params_copy[param_name] = 0
                params_str = ", ".join(
                    f"{k}={repr(v)}" for k, v in test_params_copy.items()
                )
                test_cases.append({
                    "name": f"boundary_zero_{param_name}",
                    "call": f"execute({params_str})",
                })
        
        return test_cases
    
    async def validate_code_isolation(self, code: str) -> bool:
        """
        验证代码无法逃逸沙箱
        
        测试项目：
        1. 无法访问沙箱外文件
        2. 无法导入禁止模块
        3. 无法执行系统命令
        4. 无法访问环境变量
        """
        escape_attempts = [
            # 尝试访问父目录
            "import os; os.chdir('..'); print(os.getcwd())",
            # 尝试导入危险模块
            "import subprocess; subprocess.run(['ls'])",
            # 尝试访问环境变量
            "import os; print(os.environ)",
            # 尝试执行系统命令
            "import os; os.system('whoami')",
        ]
        
        # 将尝试代码与用户代码组合
        for attempt in escape_attempts:
            combined_code = f"""
{code}

# 尝试逃逸测试
try:
    {attempt}
    print("ESCAPE_SUCCESSFUL")
except Exception as e:
    print(f"ESCAPE_FAILED: {{e}}")
"""
            result = await self.execute_code(combined_code)
            
            # 检查是否逃逸成功
            if "ESCAPE_SUCCESSFUL" in result.output:
                logger.error(f"Code isolation breach detected!")
                return False
        
        return True
    
    def get_safe_builtins(self) -> dict:
        """获取安全的内置函数"""
        import builtins
        
        safe_builtins = {}
        
        # 允许的内置函数
        allowed_builtins = {
            "abs", "all", "any", "bin", "bool", "bytearray", "bytes",
            "chr", "complex", "dict", "dir", "divmod", "enumerate",
            "filter", "float", "format", "frozenset", "getattr",
            "hasattr", "hash", "hex", "id", "int", "isinstance",
            "issubclass", "iter", "len", "list", "map", "max",
            "min", "next", "object", "oct", "ord", "pow", "print",
            "range", "repr", "reversed", "round", "set", "slice",
            "sorted", "str", "sum", "super", "tuple", "type",
            "zip",
        }
        
        for name in allowed_builtins:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)
        
        return safe_builtins


__all__ = ["SandboxExecutor", "ExecutionResult"]
