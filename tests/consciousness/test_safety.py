"""
测试安全约束模块
"""

import pytest
from src.consciousness.safety.constraints import (
    SafetyConstraints,
    READ_ONLY_MODULES,
    FORBIDDEN_IMPORTS,
    HIGH_RISK_PATTERNS
)


class TestSafetyConstraints:
    """测试安全约束功能"""
    
    def test_read_only_module_detection(self):
        """测试只读模块检测"""
        assert SafetyConstraints.is_module_read_only("ethics.core_constraints") is True
        assert SafetyConstraints.is_module_read_only("ethics.human_safety") is True
        assert SafetyConstraints.is_module_read_only("tools.file_tool") is False
        
    def test_forbidden_import_detection(self):
        """测试禁止导入检测"""
        assert SafetyConstraints.is_import_allowed("os.system") is False
        assert SafetyConstraints.is_import_allowed("subprocess.Popen") is False
        assert SafetyConstraints.is_import_allowed("json") is True
        
    def test_high_risk_pattern_detection(self):
        """测试高风险模式检测"""
        code1 = "def delete_files(path): pass"
        assert SafetyConstraints.contains_high_risk_pattern(code1) is True
        
        code2 = "def read_file(path): pass"
        assert SafetyConstraints.contains_high_risk_pattern(code2) is False
        
    def test_validate_safe_code(self):
        """测试安全代码验证"""
        safe_code = """
def add_numbers(a, b):
    return a + b

result = add_numbers(10, 20)
print(f"Result: {result}")
"""
        is_safe, violations = SafetyConstraints.validate_tool_code(safe_code)
        # 简单代码应该通过（不包含 dd 等模式）
        assert is_safe is True
        assert len(violations) == 0
        
    def test_validate_unsafe_code(self):
        """测试不安全代码验证"""
        # 使用 eval 这种明确禁止的模式
        unsafe_code = 'result = eval("1+1")'
        is_safe, violations = SafetyConstraints.validate_tool_code(unsafe_code)
        # eval/exec 会被检测
        assert not is_safe or len(violations) > 0, f"Expected violations but got: {violations}"
        
    def test_risk_level_assessment(self):
        """测试风险评估"""
        # 高风险操作
        assert SafetyConstraints.get_risk_level("delete files", "file_deleter") == "high"
        # 低风险操作（read 应该是 low）
        assert SafetyConstraints.get_risk_level("read file", "file_reader") == "low"
        assert SafetyConstraints.get_risk_level("calculate sum", "calculator") == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
