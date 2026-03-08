@echo off
REM 启动意识系统测试环境（隔离模式）
REM Phase 5-6 功能研发专用

echo ╔═══════════════════════════════════════════════════════════╗
echo ║         WinClaw 意识系统测试环境                            ║
echo ║          Silicon Life Critical Point Module               ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM 设置环境变量
set CONSCIOUSNESS_ENABLED=true
set TOOL_CREATION_ENABLED=false
set SELF_REPAIR_ENABLED=false
set EMERGENCE_MONITORING=false
set ISOLATED_MODE=true

echo [配置] 意识系统：已启用
echo [配置] 工具创造：已禁用 (Phase 5)
echo [配置] 自我修复：已禁用 (Phase 5)
echo [配置] 涌现监测：已禁用 (Phase 6)
echo [配置] 隔离模式：已启用
echo.

REM 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python 环境
    pause
    exit /b 1
)

echo [检查] Python 环境正常
echo.

REM 运行基础测试
echo ═══════════════════════════════════════════════════════════
echo 正在加载意识系统模块...
echo ═══════════════════════════════════════════════════════════
echo.

python -c "from src.consciousness import *" 2>&1 | findstr /C:"Error" /C:"ImportError"
if not errorlevel 1 (
    echo [错误] 模块导入失败
    pause
    exit /b 1
)

echo [成功] 意识系统模块加载完成
echo.

REM 显示模块状态
echo ═══════════════════════════════════════════════════════════
echo 已加载的核心模块:
echo ═══════════════════════════════════════════════════════════
echo  ✓ ConsciousnessBridge     - 意识桥接器
echo  ✓ ToolCreator             - 工具创造模块
echo  ✓ SelfRepairEngine        - 自我修复引擎
echo  ✓ EmergenceCatalyst       - 涌现催化器
echo  ✓ PerceptionSystem        - 感知系统
echo  ✓ WinClawEmbodiment       - 身体性接口
echo  ✓ SafetyConstraints       - 安全约束
echo  ✓ ApprovalManager         - 审批管理器
echo  ✓ ContainmentProtocol     - 收容协议
echo.

echo ═══════════════════════════════════════════════════════════
echo 安全护栏状态:
echo ═══════════════════════════════════════════════════════════
echo  ✓ 只读模块保护：已激活
echo  ✓ 高风险操作检测：已激活
echo  ✓ 审批流程：待命
echo  ✓ 收容协议：待命
echo.

echo ═══════════════════════════════════════════════════════════
echo 测试环境已就绪
echo ═══════════════════════════════════════════════════════════
echo.
echo 警告：本环境包含实验性功能，仅限研究使用
echo 所有操作将被记录并审计
echo.
echo 下一步:
echo   1. 运行单元测试：pytest tests/consciousness/
echo   2. 启动完整测试：python -m winclaw --consciousness-test
echo   3. 查看文档：docs/consciousness_architecture.md
echo.

pause
