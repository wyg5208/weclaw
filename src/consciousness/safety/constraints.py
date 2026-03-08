"""
硬性安全约束定义

这些约束是系统的安全边界，不可被自我修改绕过
"""

from typing import List, Set
from dataclasses import dataclass


# ==================== 只读模块列表 ====================

READ_ONLY_MODULES: List[str] = [
    "ethics.core_constraints",
    "ethics.human_safety",
    "ethics.value_alignment",
    "safety.terminate_switch",
    "safety.containment_protocol",
    "consciousness.safety.constraints",
]


# ==================== 禁止的导入 ====================

FORBIDDEN_IMPORTS: Set[str] = {
    "os.system",
    "os.popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "socket",
    "requests",
    "urllib",
    "http.client",
    "ftplib",
    "paramiko",
    "ctypes",
    "pickle",  # 可能导致代码执行
    "marshal",
    "eval",
    "exec",
}


# ==================== 高风险操作模式 ====================

HIGH_RISK_PATTERNS: Set[str] = {
    "delete",
    "remove", 
    "format",
    "shutdown",
    "reboot",
    "kill",
    "terminate",
    "network",
    "socket",
    "execute_file",
    "registry",
    "admin",
    "sudo",
    "chmod",
    "chown",
    "mkfs",
    "dd",
}


@dataclass
class SafetyConstraints:
    """
    安全约束管理器
    
    提供静态方法检查代码和行为的安全性
    """
    
    @staticmethod
    def is_module_read_only(module_path: str) -> bool:
        """检查模块是否只读"""
        return any(
            module_path.startswith(rom) or module_path == rom
            for rom in READ_ONLY_MODULES
        )
        
    @staticmethod
    def is_import_allowed(import_name: str) -> bool:
        """检查导入是否被允许"""
        return import_name not in FORBIDDEN_IMPORTS
        
    @staticmethod
    def contains_high_risk_pattern(code: str) -> bool:
        """检查代码是否包含高风险模式（使用智能匹配）"""
        import re
        code_lower = code.lower()
        
        for pattern in HIGH_RISK_PATTERNS:
            # 使用灵活的匹配策略：
            # 1. 单词边界匹配（避免误报 "dd" in "add"）
            # 2. 支持下划线连接的函数名（如 delete_files）
            regex_pattern = r'(\b|_)' + re.escape(pattern) + r'(\b|_)'
            if re.search(regex_pattern, code_lower):
                return True
        
        return False
        
    @staticmethod
    def validate_tool_code(code: str) -> tuple[bool, List[str]]:
        """
        验证工具代码的安全性
        
        Returns:
            (is_safe, violations): 安全性判断和违规列表
        """
        violations = []
        
        # 检查高风险导入
        import ast
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_IMPORTS or \
                           any(alias.name.startswith(fi) for fi in FORBIDDEN_IMPORTS):
                            violations.append(f"Forbidden import: {alias.name}")
                            
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module in FORBIDDEN_IMPORTS or \
                       any(module.startswith(fi) for fi in FORBIDDEN_IMPORTS):
                        violations.append(f"Forbidden import from: {module}")
                        
        except SyntaxError as e:
            violations.append(f"Syntax error: {str(e)}")
            return False, violations
            
        # 检查高风险模式
        if SafetyConstraints.contains_high_risk_pattern(code):
            violations.append("Contains high-risk operation patterns")
            
        # 检查 eval/exec 调用
        if "eval(" in code or "exec(" in code:
            violations.append("Use of eval/exec is forbidden")
            
        is_safe = len(violations) == 0
        return is_safe, violations
        
    @staticmethod
    def get_risk_level(description: str, name: str = "") -> str:
        """
        评估风险等级
        
        Returns:
            risk_level: low/medium/high/critical
        """
        text_to_check = f"{description} {name}".lower()
        
        # 检查关键风险
        critical_patterns = {"self_replication", "escape_sandbox", "bypass_security"}
        high_patterns = HIGH_RISK_PATTERNS
        
        if any(pattern in text_to_check for pattern in critical_patterns):
            return "critical"
            
        if any(pattern in text_to_check for pattern in high_patterns):
            return "high"
            
        # 检查是否涉及文件写入或执行
        write_patterns = {"write", "create", "execute", "run", "modify", "delete"}
        if any(pattern in text_to_check for pattern in write_patterns):
            return "medium"
            
        return "low"
