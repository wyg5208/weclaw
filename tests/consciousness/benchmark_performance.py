"""
意识系统性能基准测试工具

WinClaw 意识系统 - Phase 6: Performance Benchmark

测试维度：
1. 启动/停止性能
2. 行为记录延迟
3. 内存占用趋势
4. CPU 使用率
5. 长时间运行稳定性
6. 并发性能

性能目标：
- 启动时间 < 2 秒
- 单次行为记录延迟 < 10ms
- 内存占用 < 200MB
- CPU 使用率 < 5%（空闲）
- 7x24 小时稳定运行

作者：WinClaw Consciousness Team
版本：v0.6.0 (Phase 6)
创建时间：2026 年 2 月
"""

import asyncio
import time
import tracemalloc
import psutil
import statistics
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import logging

from src.consciousness.consciousness_manager import ConsciousnessManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """性能基准测试器"""
    
    def __init__(self):
        """初始化基准测试器"""
        self.results: Dict[str, Any] = {}
        self.temp_dir = None
        self.manager = None
        
    def setup(self):
        """准备测试环境"""
        self.temp_dir = tempfile.mkdtemp(prefix="winclaw_benchmark_")
        system_root = Path(self.temp_dir)
        (system_root / "src" / "consciousness").mkdir(parents=True)
        (system_root / "config").mkdir(parents=True)
        
        config = {
            "auto_repair": False,
            "backup_enabled": True,
            "metrics_window_size": 100,
            "catalyst_sensitivity": "medium",
            "auto_save_evolution": False,
            "health_check_interval": 3600  # 禁用自动健康检查
        }
        
        self.manager = ConsciousnessManager(
            system_root=str(system_root),
            config=config,
            auto_start=False
        )
        
        logger.info("测试环境准备完成")
    
    def teardown(self):
        """清理测试环境"""
        if self.manager and self.manager.is_running:
            # 在异步上下文中停止
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.manager.stop())
            finally:
                loop.close()
        
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        logger.info("测试环境已清理")
    
    async def benchmark_startup(self) -> Dict[str, float]:
        """测试启动性能"""
        logger.info("开始启动性能测试...")
        
        start_time = time.perf_counter()
        await self.manager.start()
        end_time = time.perf_counter()
        
        startup_time = (end_time - start_time) * 1000  # 毫秒
        
        result = {
            "startup_time_ms": startup_time,
            "passed": startup_time < 2000,  # < 2 秒
            "target_ms": 2000
        }
        
        logger.info(f"启动时间：{startup_time:.2f}ms {'✓' if result['passed'] else '✗'}")
        
        return result
    
    async def benchmark_behavior_recording(self, iterations: int = 100) -> Dict[str, float]:
        """测试行为记录延迟"""
        logger.info(f"开始行为记录延迟测试 ({iterations}次)...")
        
        latencies = []
        
        for i in range(iterations):
            start = time.perf_counter()
            
            self.manager.record_behavior(
                action_type=f"action_{i}",
                autonomy_level=0.6,
                creativity_score=0.5,
                goal_relevance=0.7,
                novelty_score=0.4
            )
            
            end = time.perf_counter()
            latency = (end - start) * 1000  # 毫秒
            latencies.append(latency)
        
        # 统计结果
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        max_latency = max(latencies)
        
        result = {
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "max_latency_ms": max_latency,
            "iterations": iterations,
            "passed": avg_latency < 10,  # < 10ms
            "target_ms": 10
        }
        
        logger.info(
            f"平均延迟：{avg_latency:.3f}ms, "
            f"P95: {p95_latency:.3f}ms, "
            f"Max: {max_latency:.3f}ms "
            f"{'✓' if result['passed'] else '✗'}"
        )
        
        return result
    
    def benchmark_memory_usage(self, duration_seconds: int = 10) -> Dict[str, float]:
        """测试内存占用"""
        logger.info(f"开始内存占用测试 ({duration_seconds}秒)...")
        
        process = psutil.Process()
        memory_samples = []
        
        # 初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 采样
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            time.sleep(0.5)
        
        # 统计
        avg_memory = statistics.mean(memory_samples)
        max_memory = max(memory_samples)
        memory_growth = max_memory - initial_memory
        
        result = {
            "initial_memory_mb": initial_memory,
            "avg_memory_mb": avg_memory,
            "max_memory_mb": max_memory,
            "memory_growth_mb": memory_growth,
            "passed": avg_memory < 200,  # < 200MB
            "target_mb": 200
        }
        
        logger.info(
            f"初始：{initial_memory:.1f}MB, "
            f"平均：{avg_memory:.1f}MB, "
            f"最大：{max_memory:.1f}MB, "
            f"增长：{memory_growth:.1f}MB "
            f"{'✓' if result['passed'] else '✗'}"
        )
        
        return result
    
    def benchmark_cpu_usage(self, duration_seconds: int = 10) -> Dict[str, float]:
        """测试 CPU 使用率"""
        logger.info(f"开始 CPU 使用率测试 ({duration_seconds}秒)...")
        
        process = psutil.Process()
        cpu_samples = []
        
        # 预热
        process.cpu_percent(interval=None)
        
        # 采样
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            time.sleep(1)
            cpu_percent = process.cpu_percent()
            cpu_samples.append(cpu_percent)
        
        # 统计
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)
        
        result = {
            "avg_cpu_percent": avg_cpu,
            "max_cpu_percent": max_cpu,
            "passed": avg_cpu < 5,  # < 5%
            "target_percent": 5
        }
        
        logger.info(
            f"平均 CPU: {avg_cpu:.1f}%, "
            f"最大 CPU: {max_cpu:.1f}% "
            f"{'✓' if result['passed'] else '✗'}"
        )
        
        return result
    
    async def benchmark_long_running(self, hours: int = 1) -> Dict[str, Any]:
        """长时间运行稳定性测试（简化版，默认 1 分钟）"""
        actual_minutes = min(hours * 60, 1)  # 最多测试 1 分钟
        
        logger.info(f"开始长时间运行测试 ({actual_minutes}分钟)...")
        
        start_time = datetime.now()
        error_count = 0
        action_count = 0
        
        # 持续记录行为
        while (datetime.now() - start_time).total_seconds() < actual_minutes * 60:
            try:
                self.manager.record_behavior(
                    action_type=f"stress_test_{action_count}",
                    autonomy_level=0.5,
                    creativity_score=0.5,
                    goal_relevance=0.5,
                    novelty_score=0.5
                )
                action_count += 1
                
                # 每秒 10 次
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"运行错误：{e}")
                error_count += 1
        
        # 最终状态检查
        final_state = self.manager.get_consciousness_state()
        
        result = {
            "duration_minutes": actual_minutes,
            "total_actions": action_count,
            "error_count": error_count,
            "final_state_ok": final_state is not None,
            "actions_per_minute": action_count / actual_minutes if actual_minutes > 0 else 0,
            "passed": error_count == 0 and final_state is not None
        }
        
        logger.info(
            f"运行时长：{actual_minutes}分钟，"
            f"总行为数：{action_count}，"
            f"错误数：{error_count}，"
            f"吞吐：{result['actions_per_minute']:.1f} 次/分钟 "
            f"{'✓' if result['passed'] else '✗'}"
        )
        
        return result
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        logger.info("=" * 60)
        logger.info("开始完整性能基准测试")
        logger.info("=" * 60)
        
        # 准备环境
        self.setup()
        
        try:
            # 启动测试
            startup_result = await self.benchmark_startup()
            self.results["startup"] = startup_result
            
            # 行为记录延迟
            recording_result = await self.benchmark_behavior_recording(100)
            self.results["recording_latency"] = recording_result
            
            # 内存占用
            memory_result = self.benchmark_memory_usage(10)
            self.results["memory_usage"] = memory_result
            
            # CPU 使用率
            cpu_result = self.benchmark_cpu_usage(10)
            self.results["cpu_usage"] = cpu_result
            
            # 长时间运行
            stability_result = await self.benchmark_long_running(1)
            self.results["stability"] = stability_result
            
            # 总体评估
            all_passed = all(
                result.get("passed", False)
                for result in self.results.values()
            )
            
            self.results["overall_passed"] = all_passed
            
            # 打印总结
            self._print_summary()
            
            return self.results
            
        finally:
            # 清理环境
            self.teardown()
    
    def _print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("性能基准测试总结")
        print("=" * 60)
        
        tests = [
            ("启动时间", "startup", "startup_time_ms", "ms"),
            ("记录延迟", "recording_latency", "avg_latency_ms", "ms"),
            ("内存占用", "memory_usage", "avg_memory_mb", "MB"),
            ("CPU 使用率", "cpu_usage", "avg_cpu_percent", "%"),
            ("稳定性", "stability", "actions_per_minute", "次/分钟"),
        ]
        
        for name, key, metric, unit in tests:
            if key in self.results:
                value = self.results[key].get(metric, 0)
                passed = self.results[key].get("passed", False)
                status = "✓" if passed else "✗"
                print(f"{status} {name}: {value:.2f}{unit}")
        
        overall = "✓ 全部通过" if self.results.get("overall_passed", False) else "✗ 部分失败"
        print(f"\n总体结果：{overall}")
        print("=" * 60)


async def main():
    """主函数"""
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()
    
    # 返回是否全部通过
    return results.get("overall_passed", False)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
