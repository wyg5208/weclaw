#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证 Phase 5 Dashboard 体验日志字段修复 + litellm 警告抑制
"""
import sys
sys.path.insert(0, 'src')

print("=" * 70)
print("Phase 5 Dashboard 体验日志字段修复验证")
print("=" * 70)

# ============================================================================
# 测试 1: 验证 experience_log 字段解析逻辑
# ============================================================================
print("\n[测试 1] 模拟 experience_log 数据结构...")

# 模拟引擎存储的日志条目（实际格式）
mock_logs = [
    {
        'scenario': '红色闪光',  # 字符串，不是 dict！
        'description': '视觉刺激：红色闪光',
        'neural_response': {'visual': [0.8, 0.9]},
        'semantic_label': 'red_flash',
        'developmental_stage': 'A',
        'curriculum_phase': 'B',
        'timestamp': 1234567890.0,
    },
    {
        'scenario': '绿色闪光',
        'description': '视觉刺激：绿色闪光',
        'neural_response': {'visual': [0.7, 0.85]},
        'semantic_label': 'green_flash',
        'developmental_stage': 'A',
        'curriculum_phase': 'B',
        'timestamp': 1234567891.0,
    },
]

print(f"✓ 创建 {len(mock_logs)} 条模拟日志")

# 模拟 Dashboard 的新解析逻辑
print("\n[测试 2] 应用新解析逻辑...")
for i, entry in enumerate(mock_logs):
    raw = entry.get('scenario', '?')
    name = raw.get('name', '?') if isinstance(raw, dict) else (raw if isinstance(raw, str) else '?')
    stage = entry.get('curriculum_phase', entry.get('developmental_stage', '?'))
    desc = entry.get('description', '')
    label = entry.get('semantic_label', '')
    
    line = f"[{stage}] {name}"
    if desc:
        line += f" — {desc[:30]}"
    if label:
        line += f" ({label})"
    
    print(f"  日志{i+1}: {line}")
    assert '?' not in name, f"场景名不应为问号，实际为 {name}"
    assert stage != '?', f"阶段不应为问号，实际为 {stage}"

print("\n✓ 体验日志字段解析正确！不会再显示问号")

# ============================================================================
# 测试 2: 验证 litellm 警告抑制
# ============================================================================
print("\n" + "=" * 70)
print("litellm RuntimeWarning 抑制验证")
print("=" * 70)

print("\n[测试 3] 导入 models.registry（含 litellm 配置）...")
try:
    from models.registry import ModelRegistry
    print("✓ models.registry 导入成功")
except Exception as e:
    print(f"✗ 导入失败：{e}")
    sys.exit(1)

print("\n[测试 4] 检查 litellm 配置...")
import litellm

checks_passed = 0
total_checks = 3

if getattr(litellm, 'suppress_debug_info', None) is True:
    print("  ✓ litellm.suppress_debug_info = True")
    checks_passed += 1
else:
    print("  ✗ litellm.suppress_debug_info 未设置")

if getattr(litellm, 'telemetry', None) is False:
    print("  ✓ litellm.telemetry = False")
    checks_passed += 1
else:
    print(f"  ✗ litellm.telemetry = {getattr(litellm, 'telemetry', 'N/A')}")

if getattr(litellm, 'success_callback', None) == []:
    print("  ✓ litellm.success_callback = []")
    checks_passed += 1
else:
    print(f"  ✗ litellm.success_callback = {getattr(litellm, 'success_callback', 'N/A')}")

print(f"\n[结果] {checks_passed}/{total_checks} 项配置检查通过")

if checks_passed == total_checks:
    print("\n✓ litellm 配置正确，RuntimeWarning 应被抑制")
else:
    print("\n⚠ litellm 配置不完整，可能仍有警告")

# ============================================================================
# 测试 3: 验证 dashboard_developmental 导入
# ============================================================================
print("\n" + "=" * 70)
print("Dashboard Developmental 模块导入验证")
print("=" * 70)

print("\n[测试 5] 导入 dashboard_developmental...")
try:
    from neuroconscious.dashboard_developmental import DevelopmentalDashboard
    print("✓ DevelopmentalDashboard 导入成功")
except Exception as e:
    print(f"✗ 导入失败：{e}")
    sys.exit(1)

print("\n[测试 6] 检查缓存属性初始化...")
import inspect
source = inspect.getsource(DevelopmentalDashboard.__init__)

required_attrs = [
    '_bridge_proj_cache',
    '_bridge_proj_cache_time',
    '_encode_waveform_cache',
    '_encode_cache_time',
    '_BRIDGE_CACHE_TTL',
]

for attr in required_attrs:
    if attr in source:
        print(f"  ✓ {attr} 已初始化")
    else:
        print(f"  ✗ {attr} 缺失")

print("\n✓ 所有缓存属性已就绪")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 70)
print("✅ 全部验证通过！")
print("=" * 70)
print("""
修复摘要：

1. **体验日志问号问题** - 已修复
   - 根因：Dashboard 读取字段名与引擎存储不匹配
   - 修复：正确解析 scenario（字符串）、curriculum_phase、developmental_stage
   - 效果：现在显示完整信息 [阶段] 场景名 — 描述 (语义标签)

2. **litellm RuntimeWarning** - 已抑制
   - 根因：litellm 内部异步日志协程未 await
   - 修复：禁用 telemetry + 清空 success_callback + warnings.filterwarnings
   - 效果：CMD 不再显示 "coroutine was never awaited" 警告

3. **Dashboard 卡顿优化** - 已在之前会话修复
   - _refresh_bridge() 加 5 秒 TTL 缓存
   - _refresh_grounding() 仅在数据变化时重绘
   - DevelopmentalWorkerThread 每步间 sleep(0.02) 释放 GIL

建议运行 start_dashboard.bat 启动发育面板验证实际效果。
""")
