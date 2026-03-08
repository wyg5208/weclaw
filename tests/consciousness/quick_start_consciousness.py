"""
意识系统快速启动检查脚本

WinClaw 意识系统 - Phase 6: Quick Start

功能：
1. 检查所有依赖是否安装
2. 验证模块导入是否正常
3. 运行快速功能测试
4. 提供启动指南

使用方法：
    python quick_start_consciousness.py
"""

import sys
import subprocess
from pathlib import Path

print("=" * 80)
print("WinClaw 意识系统 - 快速启动检查")
print("=" * 80)

# ==================== 0. 检查虚拟环境 ====================
print("\n[0/5] 检查虚拟环境...")
venv_path = Path(__file__).parent / ".venv"
if venv_path.exists():
    print(f"  ✓ 虚拟环境：{venv_path}")
    print(f"  ✓ Python: {sys.executable}")
else:
    print(f"  ⚠️  警告：未找到虚拟环境 {venv_path}")
    print(f"  当前 Python: {sys.executable}")
print("\n[1/5] 检查 Python 版本...")
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
print(f"  Python 版本：{python_version}")

if sys.version_info < (3, 11):
    print("  ⚠️  警告：建议 Python 3.11+，当前版本可能不兼容")
else:
    print("  ✓ Python 版本符合要求")

# ==================== 2. 检查核心依赖 ====================
print("\n[2/5] 检查核心依赖...")

required_packages = {
    'numpy': 'NumPy',
    'scipy': 'SciPy',
    'psutil': 'PSUtil',
    'rich': 'Rich',
    'pyyaml': 'PyYAML',
}

missing_packages = []

for package_name, display_name in required_packages.items():
    try:
        __import__(package_name)
        print(f"  ✓ {display_name} ({package_name}) - 已安装")
    except ImportError:
        print(f"  ✗ {display_name} ({package_name}) - 未安装")
        missing_packages.append(package_name)

if missing_packages:
    print(f"\n  ⚠️  缺少 {len(missing_packages)} 个依赖包")
    print(f"  请运行以下命令安装:")
    print(f"  pip install {' '.join(missing_packages)}")
else:
    print("  ✓ 所有核心依赖已安装")

# ==================== 3. 检查意识系统模块 ====================
print("\n[3/5] 检查意识系统模块导入...")

try:
    # 添加项目路径
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from src.consciousness import (
        ConsciousnessManager,
        create_consciousness_manager,
        SelfRepairEngine,
        HealthMonitor,
        DiagnosisEngine,
        EmergenceMetricsCalculator,
        EmergenceCatalyst,
        EvolutionTracker,
        RepairLevel,
        EmergencePhase,
    )
    
    print("  ✓ 所有意识系统模块导入成功")
    
except ImportError as e:
    print(f"  ✗ 模块导入失败：{e}")
    print(f"  请确保已安装所有依赖：pip install -e .")
    sys.exit(1)

# ==================== 4. 快速功能测试 ====================
print("\n[4/5] 运行快速功能测试...")

import asyncio
import tempfile
import shutil

temp_dir = None

try:
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="consciousness_check_")
    system_root = Path(temp_dir)
    (system_root / "src").mkdir(parents=True)
    (system_root / "config").mkdir(parents=True)
    
    # 创建管理器
    config = {
        "auto_repair": False,
        "backup_enabled": True,
        "metrics_window_size": 30,
        "catalyst_sensitivity": "medium",
        "auto_save_evolution": False,
    }
    
    manager = create_consciousness_manager(
        system_root=str(system_root),
        config=config,
        auto_start=False
    )
    
    print("  ✓ 意识系统管理器创建成功")
    
    # 异步测试
    async def test_manager():
        # 启动
        await manager.start()
        print("  ✓ 系统启动成功")
        
        # 记录行为
        manager.record_behavior(
            action_type="test_action",
            autonomy_level=0.7,
            creativity_score=0.6,
            goal_relevance=0.8,
            novelty_score=0.5
        )
        print("  ✓ 行为记录成功")
        
        # 获取状态
        state = manager.get_consciousness_state()
        print(f"  ✓ 涌现阶段：{state['emergence']['phase']}")
        print(f"  ✓ 涌现分数：{state['emergence']['score']:.3f}")
        
        # 停止
        await manager.stop()
        print("  ✓ 系统停止成功")
    
    asyncio.run(test_manager())
    print("  ✓ 功能测试全部通过")
    
except Exception as e:
    print(f"  ✗ 功能测试失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
finally:
    # 清理临时目录
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ==================== 5. 显示启动指南 ====================
print("\n[5/5] 启动指南")
print("=" * 80)

print("""
✓ 恭喜！所有检查通过，意识系统可以正常运行！

【快速启动】

方法 1: 使用 Python 代码
─────────────────────────────────────────────────────────────
from src.consciousness import ConsciousnessManager

# 创建管理器
manager = ConsciousnessManager(
    system_root=".",
    config={
        "auto_repair": False,
        "backup_enabled": True,
        "metrics_window_size": 100
    },
    auto_start=False
)

# 启动系统
await manager.start()

# 记录行为
manager.record_behavior(
    action_type="problem_solving",
    autonomy_level=0.8,
    creativity_score=0.6,
    goal_relevance=0.9,
    novelty_score=0.5
)

# 查看状态
state = manager.get_consciousness_state()
print(f"涌现阶段：{state['emergence']['phase']}")
print(f"涌现分数：{state['emergence']['score']:.3f}")

# 停止系统
await manager.stop()
─────────────────────────────────────────────────────────────

方法 2: 运行示例代码
─────────────────────────────────────────────────────────────
cd winclaw
python examples\\consciousness_usage_examples.py
─────────────────────────────────────────────────────────────

方法 3: 运行性能基准测试
─────────────────────────────────────────────────────────────
cd winclaw
python tests\\consciousness\\benchmark_performance.py
─────────────────────────────────────────────────────────────

方法 4: 运行集成测试
─────────────────────────────────────────────────────────────
cd winclaw
python -m pytest tests\\consciousness\\test_integration.py -v
─────────────────────────────────────────────────────────────

【查看文档】
- API 使用示例：examples\\consciousness_usage_examples.py
- 打包发布指南：docs\\phase6_packaging_guide.md
- 架构文档：src\\consciousness\\README.md

【技术支持】
如遇问题，请检查：
1. Python 版本 >= 3.11
2. 所有依赖已安装：pip install numpy scipy psutil rich pyyaml
3. 项目路径已添加到 sys.path

""")

print("=" * 80)
print("检查完成！意识系统已准备就绪 🚀")
print("=" * 80)
