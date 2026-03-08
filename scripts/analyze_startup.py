"""启动性能分析脚本 - 诊断 WinClaw 启动慢的问题。

使用方法：
    python scripts/analyze_startup.py
    
输出：
    - 各模块导入时间
    - 各组件初始化时间
    - 性能瓶颈分析建议
"""

import time
from pathlib import Path
from datetime import datetime


class Timer:
    """上下文管理器，用于测量代码块执行时间。"""
    
    def __init__(self, label: str):
        self.label = label
        self.start = None
        self.end = None
        self.elapsed = None
    
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed = (self.end - self.start) * 1000  # 毫秒
        print(f"[{self.elapsed:8.2f} ms] {self.label}")


def analyze_imports():
    """分析各模块导入时间。"""
    print("\n" + "="*60)
    print("模块导入性能分析")
    print("="*60 + "\n")
    
    imports_to_test = [
        ("PyQt5/PySide6", "try:\n    from PySide6.QtWidgets import QApplication\nexcept ImportError:\n    pass"),
        ("src.core.agent", "from src.core.agent import Agent"),
        ("src.models.registry", "from src.models.registry import ModelRegistry"),
        ("src.tools.registry", "from src.tools.registry import create_default_registry"),
        ("src.ui.main_window", "from src.ui.main_window import MainWindow"),
        ("src.consciousness", "try:\n    from src.consciousness import ConsciousnessAgent\nexcept ImportError:\n    pass"),
        ("src.neuroconscious", "try:\n    from src.neuroconscious import NeuroConsciousnessSystem\nexcept ImportError:\n    pass"),
        ("src.remote_client", "from src.remote_client import RemoteBridgeClient"),
        ("src.core.mcp_client", "from src.core.mcp_client import MCPClientManager"),
        ("src.workflow", "try:\n    from src.workflow import WorkflowEngine\nexcept ImportError:\n    pass"),
    ]
    
    results = []
    for module_name, import_stmt in imports_to_test:
        with Timer(f"导入 {module_name}") as timer:
            exec(import_stmt)
        results.append((module_name, timer.elapsed))
    
    # 排序并显示最慢的模块
    print("\n" + "-"*60)
    print("按耗时排序（最慢的在前）:")
    print("-"*60)
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    for module_name, elapsed in sorted_results:
        percentage = (elapsed / sum(r[1] for r in results)) * 100
        print(f"  {module_name:30s} {elapsed:8.2f} ms ({percentage:5.1f}%)")
    
    return results


def analyze_component_init():
    """分析组件初始化时间。"""
    print("\n" + "="*60)
    print("组件初始化性能分析")
    print("="*60 + "\n")
    
    from src.models.registry import ModelRegistry
    from src.tools.registry import ToolRegistry
    
    results = []
    
    # 测试 ModelRegistry 初始化
    with Timer("ModelRegistry 初始化（含 Ollama 检测）") as timer:
        model_reg = ModelRegistry()
    results.append(("ModelRegistry", timer.elapsed))
    
    # 测试 ToolRegistry 初始化
    with Timer("ToolRegistry 初始化") as timer:
        tool_reg = ToolRegistry()
    results.append(("ToolRegistry", timer.elapsed))
    
    # 测试工具配置加载
    with Timer("加载 tools.json 配置") as timer:
        tool_reg.load_config()
    results.append(("tools.json 加载", timer.elapsed))
    
    # 测试工具自动发现
    with Timer("工具自动发现（懒加载）") as timer:
        tool_reg.auto_discover(lazy=True)
    results.append(("工具自动发现", timer.elapsed))
    
    # 排序并显示
    print("\n" + "-"*60)
    print("按耗时排序（最慢的在前）:")
    print("-"*60)
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    for comp_name, elapsed in sorted_results:
        percentage = (elapsed / sum(r[1] for r in results)) * 100
        print(f"  {comp_name:30s} {elapsed:8.2f} ms ({percentage:5.1f}%)")
    
    return results


def generate_report(all_results: dict):
    """生成性能分析报告。"""
    print("\n" + "="*60)
    print("性能瓶颈分析与优化建议")
    print("="*60 + "\n")
    
    # 找出最慢的前 3 个组件
    all_components = []
    for category, results in all_results.items():
        all_components.extend([(category, name, elapsed) for name, elapsed in results])
    
    top_slow = sorted(all_components, key=lambda x: x[2], reverse=True)[:5]
    
    print("🐢 最慢的前 5 个组件:")
    print("-"*60)
    for i, (category, name, elapsed) in enumerate(top_slow, 1):
        print(f"  {i}. [{category}] {name}: {elapsed:.2f} ms")
    
    print("\n💡 优化建议:")
    print("-"*60)
    
    # 根据分析结果给出建议
    has_ollama = any("Ollama" in name for _, name, _ in all_components)
    has_consciousness = any("Consciousness" in name or "Neuro" in name for _, name, _ in all_components)
    has_mcp = any("MCP" in name for _, name, _ in all_components)
    
    if has_ollama:
        print("""
1. Ollama 服务检测超时问题
   - 现象：Ollama 检测可能因网络超时而延迟
   - 建议：降低 Ollama 检测超时时间（从 30s 改为 5s）
   - 或：将 Ollama 检测改为异步后台任务，不阻塞启动""")
    
    if has_consciousness:
        print("""
2. 意识模块加载优化
   - 现象：意识/神经科学模块可能加载了大量模型或配置
   - 建议：使用懒加载模式，仅在需要时才初始化
   - 或：预加载简化版模型，完整版后台加载""")
    
    if has_mcp:
        print("""
3. MCP 客户端连接优化
   - 现象：MCP Server 连接可能超时或等待响应
   - 建议：设置合理的连接超时时间
   - 或：将 MCP 连接改为异步后台任务""")
    
    print("""
4. 通用优化策略
   - 懒加载：所有非关键组件都采用懒加载
   - 并行初始化：多个独立组件可并行初始化
   - 缓存：对配置文件、模型元数据等进行缓存
   - 按需加载：用户请求时才加载特定功能模块""")
    
    print("\n")


def main():
    """主函数。"""
    print("\n" + "="*60)
    print("WinClaw 启动性能分析")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # 分析导入性能
    import_results = analyze_imports()
    
    # 分析组件初始化性能
    init_results = analyze_component_init()
    
    # 生成报告
    generate_report({
        "模块导入": import_results,
        "组件初始化": init_results,
    })
    
    print("分析报告已生成，请查看上述输出。")


if __name__ == "__main__":
    main()
