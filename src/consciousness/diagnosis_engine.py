"""
诊断引擎

WinClaw 意识系统 - Phase 3: Diagnosis Engine

功能概述：
- 分析问题根源
- 生成修复方案
- 评估修复可行性
- 确定修复等级

诊断流程：
1. 问题分类 - 识别问题类型和严重程度
2. 根因分析 - 找出问题的根本原因
3. 方案设计 - 制定修复策略
4. 可行性评估 - 判断是否可自动修复
5. 审批决策 - 确定是否需要人类审批

作者：WinClaw Consciousness Team
版本：v0.3.0 (Phase 3)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import re
from pathlib import Path

from .types import SelfDiagnosis, RepairLevel

logger = logging.getLogger(__name__)


# 问题模式库
PROBLEM_PATTERNS = {
    # 语法错误
    "syntax_error": {
        "patterns": [r"SyntaxError", r"invalid syntax", r"unexpected indent"],
        "severity": "high",
        "repair_level": RepairLevel.ERROR_RECOVERY,
        "auto_fixable": True
    },
    
    # 导入错误
    "import_error": {
        "patterns": [r"ImportError", r"ModuleNotFoundError"],
        "severity": "medium",
        "repair_level": RepairLevel.ERROR_RECOVERY,
        "auto_fixable": True
    },
    
    # 运行时错误
    "runtime_error": {
        "patterns": [r"RuntimeError", r"Exception", r"Traceback"],
        "severity": "medium",
        "repair_level": RepairLevel.BEHAVIOR_FIX,
        "auto_fixable": False
    },
    
    # 性能问题
    "performance_issue": {
        "patterns": [r"memory leak", r"CPU usage", r"slow performance"],
        "severity": "medium",
        "repair_level": RepairLevel.CAPABILITY_OPT,
        "auto_fixable": True
    },
    
    # 配置问题
    "configuration_error": {
        "patterns": [r"config.*error", r"invalid configuration", r"missing config"],
        "severity": "high",
        "repair_level": RepairLevel.ERROR_RECOVERY,
        "auto_fixable": True
    },
    
    # 文件/IO 问题
    "file_system_error": {
        "patterns": [r"FileNotFoundError", r"PermissionError", r"OSError"],
        "severity": "medium",
        "repair_level": RepairLevel.BEHAVIOR_FIX,
        "auto_fixable": True
    },
    
    # 网络问题
    "network_error": {
        "patterns": [r"ConnectionError", r"TimeoutError", r"NetworkError"],
        "severity": "low",
        "repair_level": RepairLevel.BEHAVIOR_FIX,
        "auto_fixable": True
    },
    
    # 核心逻辑问题
    "core_logic_error": {
        "patterns": [r"logic error", r"incorrect behavior", r"wrong result"],
        "severity": "critical",
        "repair_level": RepairLevel.CORE_EVOLUTION,
        "auto_fixable": False
    }
}


class DiagnosisEngine:
    """
    诊断引擎
    
    职责：
    1. 接收问题描述
    2. 匹配问题模式
    3. 分析根本原因
    4. 生成修复方案
    5. 评估修复可行性
    """
    
    def __init__(self):
        """初始化诊断引擎"""
        self.diagnosis_history: List[SelfDiagnosis] = []
        self.pattern_cache: Dict[str, Dict] = {}
        
        logger.info("诊断引擎初始化完成")
    
    async def analyze(
        self,
        issue_description: str,
        system_root: Optional[Path] = None
    ) -> SelfDiagnosis:
        """
        分析问题并生成诊断结果
        
        Args:
            issue_description: 问题描述
            system_root: 系统根目录（可选）
            
        Returns:
            诊断结果
        """
        logger.info(f"开始分析问题：{issue_description[:100]}...")
        
        # 1. 问题分类和模式匹配
        problem_type, confidence = self._classify_problem(issue_description)
        
        # 2. 根因分析
        root_cause = await self._analyze_root_cause(
            issue_description,
            problem_type,
            system_root
        )
        
        # 3. 确定严重程度
        severity = self._determine_severity(problem_type, root_cause)
        
        # 4. 生成修复方案
        suggested_fix = await self._generate_fix(
            problem_type,
            root_cause,
            system_root
        )
        
        # 5. 确定修复等级
        repair_level = self._get_repair_level(problem_type)
        
        # 6. 评估是否可自动修复
        auto_fixable = self._is_auto_fixable(problem_type, repair_level)
        
        # 7. 判断是否需要审批
        requires_approval = self._requires_approval(repair_level, severity)
        
        # 创建诊断结果
        diagnosis = SelfDiagnosis(
            issue_type=problem_type,
            severity=severity,
            affected_component=self._extract_affected_component(issue_description),
            root_cause=root_cause,
            suggested_fix=suggested_fix,
            repair_level=repair_level,
            auto_fixable=auto_fixable,
            requires_approval=requires_approval,
            diagnosis_time=datetime.now()
        )
        
        # 保存历史
        self.diagnosis_history.append(diagnosis)
        
        logger.info(
            f"诊断完成：{problem_type}, 严重性：{severity}, "
            f"可自修：{auto_fixable}, 需审批：{requires_approval}"
        )
        
        return diagnosis
    
    def _classify_problem(self, description: str) -> Tuple[str, float]:
        """
        分类问题
        
        Args:
            description: 问题描述
            
        Returns:
            (问题类型，置信度)
        """
        # 注意：不转小写，因为错误类型名是大小写敏感的
        best_match = None
        best_confidence = 0.0
        
        for problem_type, info in PROBLEM_PATTERNS.items():
            patterns = info["patterns"]
            
            for pattern in patterns:
                if re.search(pattern, description):
                    # 计算置信度（基于匹配的模式数量）
                    confidence = len([
                        p for p in patterns
                        if re.search(p, description)
                    ]) / len(patterns)
                    
                    if confidence > best_confidence:
                        best_match = problem_type
                        best_confidence = confidence
        
        # 默认类型
        if best_match is None:
            best_match = "runtime_error"
            best_confidence = 0.5
        
        return best_match, best_confidence
    
    async def _analyze_root_cause(
        self,
        description: str,
        problem_type: str,
        system_root: Optional[Path]
    ) -> str:
        """
        分析根本原因
        
        Args:
            description: 问题描述
            problem_type: 问题类型
            system_root: 系统根目录
            
        Returns:
            根本原因分析
        """
        # 基于问题类型的启发式分析
        analysis_templates = {
            "syntax_error": "代码语法错误，可能是缺少括号、冒号或缩进不正确",
            "import_error": "模块导入失败，可能是依赖未安装或路径错误",
            "runtime_error": "运行时发生错误，可能是逻辑错误或异常处理不当",
            "performance_issue": "性能下降，可能是内存泄漏或算法效率低",
            "configuration_error": "配置文件错误或格式不正确",
            "file_system_error": "文件系统操作失败，可能是权限或路径问题",
            "network_error": "网络连接问题，可能是超时或服务不可用",
            "core_logic_error": "核心逻辑错误，需要重新设计算法或流程"
        }
        
        base_analysis = analysis_templates.get(
            problem_type,
            "未知错误类型，需要人工分析"
        )
        
        # 尝试从描述中提取更多信息
        error_details = self._extract_error_details(description)
        
        if error_details:
            return f"{base_analysis}\n详细信息：{error_details}"
        else:
            return base_analysis
    
    def _extract_error_details(self, description: str) -> Optional[str]:
        """从描述中提取错误详情"""
        # 提取 Traceback 中的关键行
        traceback_match = re.search(
            r'Traceback \(most recent call last\):(.*?)File "(.*?)"',
            description,
            re.DOTALL
        )
        
        if traceback_match:
            file_path = traceback_match.group(2)
            return f"错误发生在文件：{file_path}"
        
        # 提取错误消息
        error_match = re.search(r'(\w+Error):\s*(.+?)(?:\n|$)', description)
        if error_match:
            error_type = error_match.group(1)
            error_msg = error_match.group(2).strip()
            return f"{error_type}: {error_msg}"
        
        return None
    
    def _extract_affected_component(self, description: str) -> str:
        """
        提取受影响的组件
        
        Args:
            description: 问题描述
            
        Returns:
            组件名称
        """
        # 尝试从文件路径提取
        path_match = re.search(r'File ["\']?(.+?)["\']?', description)
        if path_match:
            file_path = path_match.group(1)
            # 提取模块名
            parts = file_path.replace('\\', '/').split('/')
            for part in reversed(parts):
                if part.endswith('.py'):
                    return part[:-3]  # 去掉.py 后缀
                elif part:
                    return part
        
        # 尝试从描述中提取组件名
        component_patterns = [
            r'in module (\w+)',
            r'component[:\s]+(\w+)',
            r'module[:\s]+(\w+)'
        ]
        
        for pattern in component_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _determine_severity(
        self,
        problem_type: str,
        root_cause: str
    ) -> str:
        """
        确定严重程度
        
        Args:
            problem_type: 问题类型
            root_cause: 根本原因
            
        Returns:
            严重程度 (critical/high/medium/low)
        """
        # 基于问题类型的默认严重性
        default_severity = PROBLEM_PATTERNS.get(
            problem_type,
            {"severity": "medium"}
        )["severity"]
        
        # 根据根因调整
        critical_keywords = ["data loss", "security", "crash", "corruption"]
        high_keywords = ["failure", "unavailable", "broken"]
        
        root_cause_lower = root_cause.lower()
        
        if any(kw in root_cause_lower for kw in critical_keywords):
            return "critical"
        elif any(kw in root_cause_lower for kw in high_keywords):
            return "high"
        else:
            return default_severity
    
    async def _generate_fix(
        self,
        problem_type: str,
        root_cause: str,
        system_root: Optional[Path]
    ) -> str:
        """
        生成修复方案
        
        Args:
            problem_type: 问题类型
            root_cause: 根本原因
            system_root: 系统根目录
            
        Returns:
            修复方案描述
        """
        fix_templates = {
            "syntax_error": "修复语法错误：检查并修正代码中的括号、冒号、缩进等",
            "import_error": "解决导入问题：安装缺失的依赖或修正导入路径",
            "runtime_error": "添加异常处理或修复逻辑错误",
            "performance_issue": "优化代码性能：改进算法或释放资源",
            "configuration_error": "修正配置文件：检查格式和参数值",
            "file_system_error": "修复文件路径或权限设置",
            "network_error": "添加重试机制或超时处理",
            "core_logic_error": "重新设计核心逻辑或算法"
        }
        
        base_fix = fix_templates.get(
            problem_type,
            "需要人工分析和修复"
        )
        
        # 如果有系统根目录，可以提供更具体的建议
        if system_root:
            if problem_type == "import_error":
                return f"{base_fix}\n建议检查 requirements.txt 并运行 pip install -r requirements.txt"
            elif problem_type == "file_system_error":
                return f"{base_fix}\n检查文件路径：{system_root}"
        
        return base_fix
    
    def _get_repair_level(self, problem_type: str) -> RepairLevel:
        """获取修复等级"""
        default_level = PROBLEM_PATTERNS.get(
            problem_type,
            {"repair_level": RepairLevel.BEHAVIOR_FIX}
        )["repair_level"]
        
        return default_level
    
    def _is_auto_fixable(
        self,
        problem_type: str,
        repair_level: RepairLevel
    ) -> bool:
        """
        判断是否可自动修复
        
        Args:
            problem_type: 问题类型
            repair_level: 修复等级
            
        Returns:
            是否可自动修复
        """
        # 基于问题类型的默认设置
        default_auto = PROBLEM_PATTERNS.get(
            problem_type,
            {"auto_fixable": False}
        )["auto_fixable"]
        
        # 修复等级限制
        if repair_level in [RepairLevel.CORE_EVOLUTION]:
            return False
        
        return default_auto
    
    def _requires_approval(
        self,
        repair_level: RepairLevel,
        severity: str
    ) -> bool:
        """
        判断是否需要审批
        
        Args:
            repair_level: 修复等级
            severity: 严重程度
            
        Returns:
            是否需要审批
        """
        # 高等级修复需要审批
        if repair_level in [RepairLevel.CAPABILITY_OPT, RepairLevel.CORE_EVOLUTION]:
            return True
        
        # 高严重性问题需要审批
        if severity in ["critical", "high"]:
            return True
        
        return False
    
    def get_diagnosis_history(
        self,
        limit: int = 10,
        problem_type: Optional[str] = None
    ) -> List[SelfDiagnosis]:
        """
        获取诊断历史
        
        Args:
            limit: 返回数量限制
            problem_type: 问题类型过滤器
            
        Returns:
            诊断结果列表
        """
        history = self.diagnosis_history[-limit:]
        
        if problem_type:
            history = [
                d for d in history
                if d.issue_type == problem_type
            ]
        
        return history
    
    def clear_history(self):
        """清空诊断历史"""
        self.diagnosis_history.clear()
        logger.info("诊断历史已清空")
