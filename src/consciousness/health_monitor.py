"""
健康监测系统

WinClaw 意识系统 - Phase 3: Health Monitor

功能概述：
- 定期检查系统各组件状态
- 检测性能下降和异常行为
- 生成健康报告
- 触发诊断流程

监测维度：
1. 代码完整性 - 文件是否存在、语法是否正确
2. 运行时状态 - 内存使用、CPU 占用、线程状态
3. 功能可用性 - 关键函数是否可调用
4. 日志分析 - 错误频率、警告模式
5. 配置一致性 - 配置文件是否有效

作者：WinClaw Consciousness Team
版本：v0.3.0 (Phase 3)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
import os
import psutil
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HealthIssue:
    """健康问题"""
    issue_id: str
    component: str
    severity: str  # critical/warning/info
    description: str
    detected_at: datetime
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


@dataclass
class HealthReport:
    """健康报告"""
    report_id: str
    check_time: datetime
    component: str
    status: str  # healthy/degraded/critical
    critical_issues: List[HealthIssue]
    warnings: List[HealthIssue]
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
    
    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return len(self.critical_issues) == 0 and len(self.warnings) == 0


class HealthMonitor:
    """
    健康监测系统
    
    职责：
    1. 执行组件健康检查
    2. 收集性能指标
    3. 检测异常模式
    4. 生成健康报告
    """
    
    def __init__(self, repair_engine=None):
        """
        初始化健康监测器
        
        Args:
            repair_engine: 关联的自我修复引擎实例
        """
        self.repair_engine = repair_engine
        self.system_root = Path(repair_engine.system_root) if repair_engine else Path.cwd()
        
        # 注册的检查器
        self.checkers: Dict[str, callable] = {
            "code_integrity": self._check_code_integrity,
            "runtime_performance": self._check_runtime_performance,
            "file_system": self._check_file_system,
            "memory_usage": self._check_memory_usage,
            "process_health": self._check_process_health
        }
        
        # 历史报告
        self.history: List[HealthReport] = []
        
        logger.info("健康监测系统初始化完成")
    
    async def check_all_components(
        self,
        components: Optional[List[str]] = None
    ) -> HealthReport:
        """
        检查所有组件或指定组件
        
        Args:
            components: 要检查的组件列表，None 表示全部
            
        Returns:
            综合健康报告
        """
        if components is None:
            components = list(self.checkers.keys())
        
        all_issues = []
        all_warnings = []
        aggregated_metrics = {}
        
        # 并行执行所有检查
        tasks = []
        for component in components:
            if component in self.checkers:
                tasks.append(self._run_checker(component))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"检查器执行失败：{result}")
                    continue
                
                if isinstance(result, HealthReport):
                    all_issues.extend(result.critical_issues)
                    all_warnings.extend(result.warnings)
                    aggregated_metrics.update(result.metrics)
        
        # 生成综合报告
        report = HealthReport(
            report_id=f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            check_time=datetime.now(),
            component="all",
            status=self._determine_overall_status(all_issues, all_warnings),
            critical_issues=all_issues,
            warnings=all_warnings,
            metrics=aggregated_metrics
        )
        
        # 保存历史
        self.history.append(report)
        
        return report
    
    async def check_component(self, component: str) -> HealthReport:
        """
        检查单个组件
        
        Args:
            component: 组件名称
            
        Returns:
            组件健康报告
        """
        if component not in self.checkers:
            raise ValueError(f"未知组件：{component}")
        
        return await self._run_checker(component)
    
    async def _run_checker(self, component: str) -> HealthReport:
        """运行单个检查器"""
        try:
            checker = self.checkers[component]
            return await checker()
        except Exception as e:
            logger.error(f"{component} 检查失败：{e}")
            return HealthReport(
                report_id=f"health_{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                check_time=datetime.now(),
                component=component,
                status="critical",
                critical_issues=[
                    HealthIssue(
                        issue_id=f"checker_error_{component}",
                        component=component,
                        severity="critical",
                        description=f"检查器执行失败：{str(e)}",
                        detected_at=datetime.now()
                    )
                ],
                warnings=[]
            )
    
    async def _check_code_integrity(self) -> HealthReport:
        """检查代码完整性"""
        issues = []
        warnings = []
        metrics = {"files_checked": 0, "syntax_errors": 0}
        
        try:
            # 检查核心 Python 文件
            core_dirs = [
                self.system_root / "src" / "consciousness",
                self.system_root / "config"
            ]
            
            for dir_path in core_dirs:
                if not dir_path.exists():
                    continue
                
                py_files = list(dir_path.glob("**/*.py"))
                metrics["files_checked"] += len(py_files)
                
                for py_file in py_files:
                    # 检查语法
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            source = f.read()
                        compile(source, py_file, 'exec')
                    except SyntaxError as e:
                        metrics["syntax_errors"] += 1
                        issues.append(
                            HealthIssue(
                                issue_id=f"syntax_{py_file.name}",
                                component="code_integrity",
                                severity="critical",
                                description=f"语法错误：{py_file}:{e.lineno}",
                                detected_at=datetime.now(),
                                metrics={"file": str(py_file), "error": str(e)}
                            )
                        )
            
            # 检查导入问题
            # TODO: 实现导入检测
            
        except Exception as e:
            logger.error(f"代码完整性检查失败：{e}")
        
        return HealthReport(
            report_id=f"health_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            check_time=datetime.now(),
            component="code_integrity",
            status="critical" if issues else ("warning" if warnings else "healthy"),
            critical_issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    async def _check_runtime_performance(self) -> HealthReport:
        """检查运行时性能"""
        issues = []
        warnings = []
        metrics = {}
        
        try:
            process = psutil.Process(os.getpid())
            
            # CPU 使用率
            cpu_percent = process.cpu_percent(interval=1)
            metrics["cpu_percent"] = cpu_percent
            
            if cpu_percent > 90:
                issues.append(
                    HealthIssue(
                        issue_id="high_cpu",
                        component="runtime_performance",
                        severity="warning",
                        description=f"CPU 使用率过高：{cpu_percent}%",
                        detected_at=datetime.now(),
                        metrics={"cpu_percent": cpu_percent}
                    )
                )
            
            # 内存使用
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            metrics["memory_mb"] = memory_mb
            
            if memory_mb > 1024:  # 1GB 阈值
                warnings.append(
                    HealthIssue(
                        issue_id="high_memory",
                        component="runtime_performance",
                        severity="warning",
                        description=f"内存使用过高：{memory_mb:.1f}MB",
                        detected_at=datetime.now(),
                        metrics={"memory_mb": memory_mb}
                    )
                )
            
            # 线程数
            thread_count = process.num_threads()
            metrics["thread_count"] = thread_count
            
            if thread_count > 50:
                warnings.append(
                    HealthIssue(
                        issue_id="many_threads",
                        component="runtime_performance",
                        severity="info",
                        description=f"线程数过多：{thread_count}",
                        detected_at=datetime.now(),
                        metrics={"thread_count": thread_count}
                    )
                )
            
        except Exception as e:
            logger.error(f"运行时性能检查失败：{e}")
        
        return HealthReport(
            report_id=f"health_runtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            check_time=datetime.now(),
            component="runtime_performance",
            status="critical" if issues else ("warning" if warnings else "healthy"),
            critical_issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    async def _check_file_system(self) -> HealthReport:
        """检查文件系统"""
        issues = []
        warnings = []
        metrics = {}
        
        try:
            # 检查关键目录
            critical_dirs = [
                "src/consciousness",
                "config",
                "generated"
            ]
            
            for dir_name in critical_dirs:
                dir_path = self.system_root / dir_name
                if not dir_path.exists():
                    issues.append(
                        HealthIssue(
                            issue_id=f"missing_dir_{dir_name}",
                            component="file_system",
                            severity="critical",
                            description=f"关键目录缺失：{dir_name}",
                            detected_at=datetime.now(),
                            metrics={"path": str(dir_path)}
                        )
                    )
            
            # 检查磁盘空间
            disk_usage = psutil.disk_usage(str(self.system_root))
            metrics["disk_free_gb"] = disk_usage.free / 1024 / 1024 / 1024
            
            if disk_usage.percent > 90:
                warnings.append(
                    HealthIssue(
                        issue_id="low_disk_space",
                        component="file_system",
                        severity="warning",
                        description=f"磁盘空间不足：剩余 {disk_usage.free / 1024 / 1024 / 1024:.1f}GB",
                        detected_at=datetime.now(),
                        metrics={"disk_percent": disk_usage.percent}
                    )
                )
            
        except Exception as e:
            logger.error(f"文件系统检查失败：{e}")
        
        return HealthReport(
            report_id=f"health_fs_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            check_time=datetime.now(),
            component="file_system",
            status="critical" if issues else ("warning" if warnings else "healthy"),
            critical_issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    async def _check_memory_usage(self) -> HealthReport:
        """检查内存使用情况"""
        issues = []
        warnings = []
        metrics = {}
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # RSS (Resident Set Size)
            rss_mb = memory_info.rss / 1024 / 1024
            metrics["rss_mb"] = rss_mb
            
            # VMS (Virtual Memory Size)
            vms_mb = memory_info.vms / 1024 / 1024
            metrics["vms_mb"] = vms_mb
            
            # 内存百分比
            memory_percent = process.memory_percent()
            metrics["memory_percent"] = memory_percent
            
            if memory_percent > 80:
                warnings.append(
                    HealthIssue(
                        issue_id="high_memory_percent",
                        component="memory_usage",
                        severity="warning",
                        description=f"内存使用率过高：{memory_percent:.1f}%",
                        detected_at=datetime.now(),
                        metrics={"memory_percent": memory_percent}
                    )
                )
            
            # 检测内存泄漏（简单实现）
            # TODO: 实现更复杂的泄漏检测
            if len(self.history) >= 5:
                recent_memory = [
                    h.metrics.get("memory_mb", 0)
                    for h in self.history[-5:]
                    if "memory_mb" in h.metrics
                ]
                
                if len(recent_memory) == 5:
                    # 检查是否持续增长
                    if all(recent_memory[i] < recent_memory[i+1] for i in range(4)):
                        warnings.append(
                            HealthIssue(
                                issue_id="possible_memory_leak",
                                component="memory_usage",
                                severity="warning",
                                description="检测到可能的内存泄漏",
                                detected_at=datetime.now(),
                                metrics={"trend": "increasing"}
                            )
                        )
            
        except Exception as e:
            logger.error(f"内存使用检查失败：{e}")
        
        return HealthReport(
            report_id=f"health_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            check_time=datetime.now(),
            component="memory_usage",
            status="critical" if issues else ("warning" if warnings else "healthy"),
            critical_issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    async def _check_process_health(self) -> HealthReport:
        """检查进程健康状态"""
        issues = []
        warnings = []
        metrics = {}
        
        try:
            process = psutil.Process(os.getpid())
            
            # 进程状态
            status = process.status()
            metrics["status"] = status
            
            if status == psutil.STATUS_ZOMBIE:
                issues.append(
                    HealthIssue(
                        issue_id="zombie_process",
                        component="process_health",
                        severity="critical",
                        description="进程处于僵死状态",
                        detected_at=datetime.now(),
                        metrics={"status": status}
                    )
                )
            
            # 运行时间
            create_time = process.create_time()
            uptime = datetime.now().timestamp() - create_time
            metrics["uptime_hours"] = uptime / 3600
            
            # 文件描述符（仅 Linux/Unix）
            try:
                num_fds = process.num_fds()
                metrics["num_fds"] = num_fds
                
                if num_fds > 1000:
                    warnings.append(
                        HealthIssue(
                            issue_id="many_file_descriptors",
                            component="process_health",
                            severity="warning",
                            description=f"文件描述符过多：{num_fds}",
                            detected_at=datetime.now(),
                            metrics={"num_fds": num_fds}
                        )
                    )
            except (AttributeError, psutil.AccessDenied):
                # Windows 不支持 num_fds
                pass
            
            # 子进程
            try:
                children = process.children()
                metrics["children_count"] = len(children)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                metrics["children_count"] = 0
            
        except Exception as e:
            logger.error(f"进程健康检查失败：{e}")
        
        return HealthReport(
            report_id=f"health_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            check_time=datetime.now(),
            component="process_health",
            status="critical" if issues else ("warning" if warnings else "healthy"),
            critical_issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    def _determine_overall_status(
        self,
        issues: List[HealthIssue],
        warnings: List[HealthIssue]
    ) -> str:
        """确定整体状态"""
        if any(issue.severity == "critical" for issue in issues):
            return "critical"
        elif warnings:
            return "degraded"
        else:
            return "healthy"
    
    def get_history(self, limit: int = 10) -> List[HealthReport]:
        """获取历史记录"""
        return self.history[-limit:]
    
    def clear_history(self):
        """清空历史记录"""
        self.history.clear()
        logger.info("健康检查历史已清空")
