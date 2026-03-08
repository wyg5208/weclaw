"""
导出功能测试脚本
================
验证 ExperimentExporter 的 JSON/CSV/Markdown 导出功能。
"""
import sys
import os
import tempfile
import shutil
import numpy as np

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'consciousness', 'neuroconscious'))

from manager import NeuroConsciousnessManager
from exporter import ExperimentExporter


def main():
    print("=" * 60)
    print("导出功能测试")
    print("=" * 60)

    # 初始化系统并运行几个周期
    manager = NeuroConsciousnessManager(n_neurons=1000, n_modules=6)
    manager.start()

    # 模拟几次刺激
    stimuli = [
        ("红色闪光", [1.0, 0.0, 0.0]),
        ("蓝色闪光", [0.0, 0.5, 1.0]),
        ("绿色闪光", [0.0, 1.0, 0.0]),
    ]
    for name, color in stimuli:
        sensory_data = {'visual': np.array(color) * 10}
        manager.process_cycle(sensory_data)
        # 存储记忆
        manager.episodic_memory.store(stimulus=f"视觉刺激：{name}", response=f"已处理")
        print(f"  [刺激] {name}")

    # 创建临时目录
    test_dir = tempfile.mkdtemp(prefix='neuro_export_test_')
    print(f"\n测试目录: {test_dir}")

    exporter = ExperimentExporter(manager)

    # ===== 测试 1: JSON 导出 =====
    print(f"\n{'─' * 40}")
    print("测试 1: JSON 导出")
    json_path = os.path.join(test_dir, 'test_export.json')
    exporter.export_json(json_path)
    size = os.path.getsize(json_path)
    print(f"  ✅ 文件: {json_path}")
    print(f"  ✅ 大小: {size:,} bytes")

    # 验证 JSON 可读
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"  ✅ 顶层字段: {list(data.keys())}")
    print(f"  ✅ metadata.total_cycles: {data['metadata']['total_cycles']}")
    print(f"  ✅ memory.short_term_count: {data['memory']['short_term_count']}")
    print(f"  ✅ learning.hebbian.total_updates: {data['learning']['hebbian']['total_updates']}")
    print(f"  ✅ weight_matrix 形状: {len(data['weight_matrix'])}x{len(data['weight_matrix'][0])}")

    # ===== 测试 2: CSV 导出 =====
    print(f"\n{'─' * 40}")
    print("测试 2: CSV 导出")
    csv_dir = os.path.join(test_dir, 'csv')
    files = exporter.export_csv(csv_dir)
    for f in files:
        size = os.path.getsize(f)
        print(f"  ✅ {os.path.basename(f)}: {size:,} bytes")

    # 验证 CSV 可读
    import csv
    with open(os.path.join(csv_dir, 'learning_curve.csv'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f"  ✅ learning_curve.csv: {len(rows)} 行数据, 列={header}")

    with open(os.path.join(csv_dir, 'weight_matrix.csv'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f"  ✅ weight_matrix.csv: {len(rows)} 行 x {len(header)} 列")

    # ===== 测试 3: Markdown 报告 =====
    print(f"\n{'─' * 40}")
    print("测试 3: Markdown 报告")
    md_path = os.path.join(test_dir, 'test_report.md')
    exporter.export_markdown(md_path)
    size = os.path.getsize(md_path)
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    print(f"  ✅ 文件: {md_path}")
    print(f"  ✅ 大小: {size:,} bytes, {len(lines)} 行")
    print(f"  ✅ 标题: {lines[0]}")
    # 检查包含的章节
    sections = [l for l in lines if l.startswith('## ')]
    for s in sections:
        print(f"  ✅ 章节: {s}")

    # ===== 测试 4: 论文数据导出 =====
    print(f"\n{'─' * 40}")
    print("测试 4: 论文数据导出")
    paper_dir = os.path.join(test_dir, 'paper')
    paper_files = exporter.export_for_paper(paper_dir)
    for key, path in paper_files.items():
        size = os.path.getsize(path)
        print(f"  ✅ {key}: {os.path.basename(path)} ({size:,} bytes)")

    # 清理
    manager.stop()
    shutil.rmtree(test_dir)
    print(f"\n{'=' * 60}")
    print("✅ 所有导出测试通过！临时文件已清理。")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
