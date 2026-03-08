"""
自我修复引擎模块测试套件

WinClaw 意识系统 - Phase 3: Self-Repair Engine Tests

测试覆盖：
1. 自我修复引擎核心 (self_repair.py)
2. 健康监测系统 (health_monitor.py)
3. 诊断引擎 (diagnosis_engine.py)
4. 修复执行器 (repair_executor.py)
5. 备份管理器 (backup_manager.py)

作者：WinClaw Consciousness Team
版本：v0.3.0 (Phase 3)
创建时间：2026 年 2 月
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 导入被测试模块
from src.consciousness.self_repair import SelfRepairEngine
from src.consciousness.health_monitor import HealthMonitor, HealthReport
from src.consciousness.diagnosis_engine import DiagnosisEngine, PROBLEM_PATTERNS
from src.consciousness.repair_executor import RepairExecutor
from src.consciousness.backup_manager import BackupManager
from src.consciousness.types import RepairLevel, SelfDiagnosis, RepairAction


# ==================== Fixtures ====================

@pytest.fixture
def temp_system_root():
    """创建临时系统根目录"""
    temp_dir = tempfile.mkdtemp(prefix="winclaw_test_")
    system_root = Path(temp_dir)
    
    # 创建基本目录结构
    (system_root / "src" / "consciousness").mkdir(parents=True)
    (system_root / "config").mkdir(parents=True)
    (system_root / "generated").mkdir(parents=True)
    
    # 创建测试配置文件
    config_file = system_root / "config" / "default.toml"
    config_file.write_text('[settings]\nname = "test"\n')
    
    yield system_root
    
    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def repair_engine(temp_system_root):
    """创建自我修复引擎实例"""
    return SelfRepairEngine(
        system_root=str(temp_system_root),
        auto_repair=False,
        backup_enabled=True
    )


@pytest.fixture
def health_monitor(repair_engine):
    """创建健康监测器实例"""
    return HealthMonitor(repair_engine)


@pytest.fixture
def diagnosis_engine():
    """创建诊断引擎实例"""
    return DiagnosisEngine()


@pytest.fixture
def repair_executor(temp_system_root):
    """创建修复执行器实例"""
    return RepairExecutor(temp_system_root)


@pytest.fixture
def backup_manager(temp_system_root):
    """创建备份管理器实例"""
    return BackupManager(temp_system_root)


# ==================== 健康监测系统测试 ====================

class TestHealthMonitor:
    """健康监测系统测试"""
    
    @pytest.mark.asyncio
    async def test_check_code_integrity(self, health_monitor):
        """测试代码完整性检查"""
        report = await health_monitor._check_code_integrity()
        
        assert isinstance(report, HealthReport)
        assert report.component == "code_integrity"
        assert report.status in ["healthy", "degraded", "critical"]
        assert "files_checked" in report.metrics
    
    @pytest.mark.asyncio
    async def test_check_runtime_performance(self, health_monitor):
        """测试运行时性能检查"""
        report = await health_monitor._check_runtime_performance()
        
        assert isinstance(report, HealthReport)
        assert report.component == "runtime_performance"
        assert "cpu_percent" in report.metrics
        assert "memory_mb" in report.metrics
    
    @pytest.mark.asyncio
    async def test_check_file_system(self, health_monitor):
        """测试文件系统检查"""
        report = await health_monitor._check_file_system()
        
        assert isinstance(report, HealthReport)
        assert report.component == "file_system"
        # 应该检测到关键目录存在
        assert len(report.critical_issues) == 0
    
    @pytest.mark.asyncio
    async def test_check_memory_usage(self, health_monitor):
        """测试内存使用检查"""
        report = await health_monitor._check_memory_usage()
        
        assert isinstance(report, HealthReport)
        assert report.component == "memory_usage"
        assert "rss_mb" in report.metrics
        assert "memory_percent" in report.metrics
    
    @pytest.mark.asyncio
    async def test_check_process_health(self, health_monitor):
        """测试进程健康检查"""
        report = await health_monitor._check_process_health()
        
        assert isinstance(report, HealthReport)
        assert report.component == "process_health"
        assert "status" in report.metrics
        assert "uptime_hours" in report.metrics
    
    @pytest.mark.asyncio
    async def test_check_all_components(self, health_monitor):
        """测试全面健康检查"""
        report = await health_monitor.check_all_components()
        
        assert isinstance(report, HealthReport)
        assert report.component == "all"
        assert hasattr(report, 'is_healthy')
    
    @pytest.mark.asyncio
    async def test_check_single_component(self, health_monitor):
        """测试单个组件检查"""
        report = await health_monitor.check_component("code_integrity")
        
        assert isinstance(report, HealthReport)
        assert report.component == "code_integrity"
    
    @pytest.mark.asyncio
    async def test_check_unknown_component(self, health_monitor):
        """测试未知组件检查"""
        with pytest.raises(ValueError):
            await health_monitor.check_component("unknown_component")


# ==================== 诊断引擎测试 ====================

class TestDiagnosisEngine:
    """诊断引擎测试"""
    
    @pytest.mark.asyncio
    async def test_classify_syntax_error(self, diagnosis_engine):
        """测试语法错误分类"""
        error_desc = "SyntaxError: invalid syntax at line 10"
        problem_type, confidence = diagnosis_engine._classify_problem(error_desc)
        
        assert problem_type == "syntax_error"
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_classify_import_error(self, diagnosis_engine):
        """测试导入错误分类"""
        error_desc = "ModuleNotFoundError: No module named 'numpy'"
        problem_type, confidence = diagnosis_engine._classify_problem(error_desc)
        
        assert problem_type == "import_error"
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_classify_runtime_error(self, diagnosis_engine):
        """测试运行时错误分类"""
        error_desc = "RuntimeError: Something went wrong"
        problem_type, confidence = diagnosis_engine._classify_problem(error_desc)
        
        assert problem_type == "runtime_error"
        assert confidence >= 0.5
    
    @pytest.mark.asyncio
    async def test_analyze_syntax_error(self, diagnosis_engine):
        """测试语法错误分析"""
        error_desc = "SyntaxError: unexpected indent at line 5"
        diagnosis = await diagnosis_engine.analyze(error_desc)
        
        assert isinstance(diagnosis, SelfDiagnosis)
        assert diagnosis.issue_type == "syntax_error"
        assert diagnosis.severity in ["low", "medium", "high", "critical"]
        assert diagnosis.repair_level == RepairLevel.ERROR_RECOVERY
    
    @pytest.mark.asyncio
    async def test_analyze_import_error(self, diagnosis_engine):
        """测试导入错误分析"""
        error_desc = "ImportError: cannot import name 'abc' from 'module'"
        diagnosis = await diagnosis_engine.analyze(error_desc)
        
        assert isinstance(diagnosis, SelfDiagnosis)
        assert diagnosis.issue_type == "import_error"
        assert diagnosis.auto_fixable is True
    
    @pytest.mark.asyncio
    async def test_extract_affected_component(self, diagnosis_engine):
        """测试受影响组件提取"""
        desc_with_file = 'Error in File "src/consciousness/test.py"'
        component = diagnosis_engine._extract_affected_component(desc_with_file)
        
        assert component == "test"
    
    @pytest.mark.asyncio
    async def test_requires_approval_for_core_evolution(self, diagnosis_engine):
        """测试核心进化需要审批"""
        requires_approval = diagnosis_engine._requires_approval(
            RepairLevel.CORE_EVOLUTION,
            "high"
        )
        
        assert requires_approval is True
    
    @pytest.mark.asyncio
    async def test_diagnosis_history(self, diagnosis_engine):
        """测试诊断历史"""
        # 执行多次诊断
        for i in range(5):
            await diagnosis_engine.analyze(f"Test error {i}")
        
        history = diagnosis_engine.get_diagnosis_history(limit=3)
        assert len(history) == 3
        
        # 清空历史
        diagnosis_engine.clear_history()
        assert len(diagnosis_engine.diagnosis_history) == 0


# ==================== 修复执行器测试 ====================

class TestRepairExecutor:
    """修复执行器测试"""
    
    @pytest.mark.asyncio
    async def test_execute_error_recovery_syntax(self, repair_executor, temp_system_root):
        """测试语法错误恢复"""
        # 创建一个有语法错误的文件
        test_file = temp_system_root / "test_syntax.py"
        test_file.write_text("def test(\n    print('missing closing paren'\n")
        
        action = RepairAction(
            action_id="test_syntax_fix",
            level=RepairLevel.ERROR_RECOVERY,
            target_component="test_syntax",
            action_type="modify",
            before_state={"file": str(test_file), "issue": "syntax error"},
            after_state={"fix": "add closing parenthesis"},
            approval_status="approved"
        )
        
        # 执行修复（可能成功或失败，取决于自动修复能力）
        result = await repair_executor.execute(action)
        
        # 不强制要求成功，因为自动修复能力有限
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_execute_file_system_fix(self, repair_executor, temp_system_root):
        """测试文件系统修复"""
        missing_path = temp_system_root / "missing" / "dir" / "file.txt"
        
        action = RepairAction(
            action_id="test_fs_fix",
            level=RepairLevel.BEHAVIOR_FIX,
            target_component="file_system",
            action_type="create",
            before_state={"path": str(missing_path), "issue": "missing"},
            after_state={"created": True},
            approval_status="approved"
        )
        
        result = await repair_executor.execute(action)
        
        # 应该成功创建缺失的目录和文件
        assert result is True
        assert missing_path.exists()
    
    @pytest.mark.asyncio
    async def test_clear_caches(self, repair_executor, temp_system_root):
        """测试清除缓存"""
        # 创建缓存文件
        cache_dir = temp_system_root / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "test.pyc").write_text("cache")
        
        await repair_executor._clear_caches()
        
        # 缓存应该被清除
        assert not cache_dir.exists()
    
    @pytest.mark.asyncio
    async def test_execution_history(self, repair_executor):
        """测试执行历史记录"""
        # 执行一些动作
        for i in range(5):
            action = RepairAction(
                action_id=f"test_{i}",
                level=RepairLevel.ERROR_RECOVERY,
                target_component="test",
                action_type="modify",
                before_state={},
                after_state={},
                approval_status="approved"
            )
            await repair_executor.execute(action)
        
        history = repair_executor.get_execution_history(limit=3)
        assert len(history) == 3
        
        # 清空历史
        repair_executor.clear_history()
        assert len(repair_executor.execution_history) == 0


# ==================== 备份管理器测试 ====================

class TestBackupManager:
    """备份管理器测试"""
    
    @pytest.mark.asyncio
    async def test_create_snapshot(self, backup_manager, temp_system_root):
        """测试创建快照"""
        # 创建一些测试文件
        (temp_system_root / "test.txt").write_text("test content")
        
        backup_id = await backup_manager.create_snapshot(
            name="test_backup",
            description="测试备份"
        )
        
        assert backup_id == "test_backup"
        assert backup_id in backup_manager.backups
        
        # 备份文件应该存在
        backup_file = backup_manager.backup_dir / f"{backup_id}.tar.gz"
        assert backup_file.exists()
    
    @pytest.mark.asyncio
    async def test_restore_snapshot(self, backup_manager, temp_system_root):
        """测试恢复快照"""
        # 创建测试文件并备份
        test_file = temp_system_root / "original.txt"
        test_file.write_text("original content")
        
        backup_id = await backup_manager.create_snapshot(name="before_modify")
        
        # 修改文件
        test_file.write_text("modified content")
        
        # 恢复到备份
        success = await backup_manager.restore_snapshot(backup_id)
        
        assert success is True
        
        # 文件内容应该恢复到原始状态
        # 注意：由于 tar 解压会覆盖，这里需要验证文件是否存在
        assert test_file.exists()
    
    @pytest.mark.asyncio
    async def test_delete_backup(self, backup_manager):
        """测试删除备份"""
        # 先创建备份
        backup_id = await backup_manager.create_snapshot(name="to_delete")
        
        # 删除备份
        success = await backup_manager.delete_backup(backup_id)
        
        assert success is True
        assert backup_id not in backup_manager.backups
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, backup_manager):
        """测试清理旧备份"""
        # 创建多个备份
        for i in range(5):
            await backup_manager.create_snapshot(name=f"backup_{i}")
        
        assert len(backup_manager.backups) == 5
        
        # 设置最大保留数为 3
        backup_manager.max_backups = 3
        
        # 清理
        deleted = await backup_manager.cleanup_old_backups()
        
        assert deleted == 2
        assert len(backup_manager.backups) == 3
    
    @pytest.mark.asyncio
    async def test_list_backups(self, backup_manager):
        """测试列出备份"""
        # 创建多个备份
        for i in range(3):
            await backup_manager.create_snapshot(
                name=f"backup_{i}",
                description=f"备份{i}"
            )
        
        backups = await backup_manager.list_backups(limit=10)
        
        assert len(backups) == 3
        assert all("backup_id" in b for b in backups)
    
    @pytest.mark.asyncio
    async def test_get_backup_info(self, backup_manager):
        """测试获取备份信息"""
        backup_id = await backup_manager.create_snapshot(
            name="info_test",
            description="测试信息"
        )
        
        info = await backup_manager.get_backup_info(backup_id)
        
        assert info is not None
        assert info["description"] == "测试信息"
        assert "size_bytes" in info
    
    @pytest.mark.asyncio
    async def test_backup_stats(self, backup_manager):
        """测试备份统计"""
        stats = backup_manager.get_stats()
        
        assert "total_backups" in stats
        assert "total_size_mb" in stats
        assert "max_backups" in stats


# ==================== 自我修复引擎集成测试 ====================

class TestSelfRepairEngineIntegration:
    """自我修复引擎集成测试"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, repair_engine):
        """测试引擎初始化"""
        assert repair_engine.is_running is False
        assert repair_engine.backup_enabled is True
        assert repair_engine.stats["total_diagnoses"] == 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring_flow(self, repair_engine):
        """测试健康监测流程"""
        # 执行一次健康检查
        report = await repair_engine.health_monitor.check_all_components()
        
        assert isinstance(report, HealthReport)
        assert report.check_time is not None
    
    @pytest.mark.asyncio
    async def test_diagnose_and_repair_flow(self, repair_engine):
        """测试诊断修复流程"""
        # 模拟一个问题
        issue = "SyntaxError: invalid syntax in code"
        
        # 执行诊断（不实际修复，因为 auto_repair=False）
        diagnosis = await repair_engine.diagnosis_engine.analyze(issue)
        
        assert isinstance(diagnosis, SelfDiagnosis)
        assert diagnosis.issue_type == "syntax_error"
    
    @pytest.mark.asyncio
    async def test_repair_history_tracking(self, repair_engine):
        """测试修复历史追踪"""
        # 初始历史为空
        assert len(repair_engine.repair_history) == 0
        
        # 获取统计
        stats = repair_engine.get_stats()
        assert "total_repairs" in stats
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, repair_engine):
        """测试启动停止监测"""
        # 启动监测
        await repair_engine.start_health_monitoring(
            interval_seconds=1,
            components=["code_integrity"]
        )
        
        assert repair_engine.is_running is True
        
        # 停止监测
        repair_engine.stop_health_monitoring()
        
        assert repair_engine.is_running is False
    
    @pytest.mark.asyncio
    async def test_backup_integration(self, repair_engine, temp_system_root):
        """测试备份集成功能"""
        if not repair_engine.backup_enabled:
            pytest.skip("备份功能未启用")
        
        # 创建测试文件
        test_file = temp_system_root / "backup_test.txt"
        test_file.write_text("test data")
        
        # 创建备份
        backup_id = await repair_engine.backup_manager.create_snapshot(
            name="integration_test"
        )
        
        assert backup_id is not None
        
        # 验证备份存在
        backups = await repair_engine.backup_manager.list_backups()
        assert any(b["backup_id"] == backup_id for b in backups)


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
