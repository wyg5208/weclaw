"""
意识系统 Web 监控界面

功能：
1. 实时显示意识状态
2. 手动触发行为记录
3. 查看涌现指标变化
4. 测试提示词上下文生成

启动方式：
    python consciousness_web.py

访问地址：
    http://localhost:8765
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 意识系统导入
from src.consciousness.consciousness_manager import ConsciousnessManager

# 创建 FastAPI 应用
app = FastAPI(title="WinClaw 意识系统监控")

# 全局意识系统实例
consciousness: Optional[ConsciousnessManager] = None


# ==================== HTML 页面 ====================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WinClaw 意识系统监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #00d4ff;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 16px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-running { background: #00c853; color: #fff; }
        .status-stopped { background: #ff5252; color: #fff; }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #aaa; }
        .metric-value {
            font-weight: bold;
            font-family: 'Consolas', monospace;
        }
        .metric-value.high { color: #00e676; }
        .metric-value.medium { color: #ffeb3b; }
        .metric-value.low { color: #ff9800; }
        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        .btn {
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: transform 0.2s, box-shadow 0.2s;
            margin: 4px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.4);
        }
        .btn:active { transform: translateY(0); }
        .btn-danger {
            background: linear-gradient(135deg, #ff5252, #cc0000);
        }
        .btn-success {
            background: linear-gradient(135deg, #00c853, #009624);
        }
        .context-box {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 16px;
            font-family: 'Consolas', monospace;
            font-size: 13px;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 16px;
        }
        .history-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            font-size: 13px;
        }
        .history-item .time { color: #888; font-size: 11px; }
        .log-container {
            background: #0a0a0a;
            border-radius: 8px;
            padding: 16px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-entry { margin: 4px 0; }
        .log-info { color: #00d4ff; }
        .log-success { color: #00e676; }
        .log-error { color: #ff5252; }
        .log-warning { color: #ffeb3b; }
        .refresh-info {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
        .phase-icon {
            font-size: 24px;
            margin-right: 8px;
        }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 WinClaw 意识系统监控</h1>
        
        <div class="grid">
            <!-- 状态卡片 -->
            <div class="card">
                <h2><span class="phase-icon" id="phase-icon">○</span> 系统状态</h2>
                <div class="metric">
                    <span class="metric-label">运行状态</span>
                    <span class="metric-value" id="status">检查中...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">涌现阶段</span>
                    <span class="metric-value" id="phase">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">涌现分数</span>
                    <span class="metric-value" id="score">0.000</span>
                </div>
                <div class="metric">
                    <span class="metric-label">运行时长</span>
                    <span class="metric-value" id="uptime">-</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="score-bar" style="width: 0%; background: #00d4ff;"></div>
                </div>
                <div class="controls">
                    <button class="btn btn-success" onclick="startConsciousness()">▶ 启动</button>
                    <button class="btn btn-danger" onclick="stopConsciousness()">⏹ 停止</button>
                    <button class="btn" onclick="refreshStatus()">🔄 刷新</button>
                </div>
            </div>
            
            <!-- 实时指标 -->
            <div class="card">
                <h2>📊 实时指标</h2>
                <div class="metric">
                    <span class="metric-label">自主性 (Autonomy)</span>
                    <span class="metric-value" id="autonomy">0.000</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="autonomy-bar" style="width: 0%; background: #00e676;"></div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">创造性 (Creativity)</span>
                    <span class="metric-value" id="creativity">0.000</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="creativity-bar" style="width: 0%; background: #ffeb3b;"></div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">目标对齐 (Goal Alignment)</span>
                    <span class="metric-value" id="goal-alignment">0.000</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="goal-bar" style="width: 0%; background: #00d4ff;"></div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">新颖性 (Novelty)</span>
                    <span class="metric-value" id="novelty">0.000</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="novelty-bar" style="width: 0%; background: #ff9800;"></div>
                </div>
            </div>
            
            <!-- 统计信息 -->
            <div class="card">
                <h2>📈 统计信息</h2>
                <div class="metric">
                    <span class="metric-label">行为记录总数</span>
                    <span class="metric-value" id="total-behaviors">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">成功任务</span>
                    <span class="metric-value high" id="success-count">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">失败任务</span>
                    <span class="metric-value low" id="fail-count">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">干预次数</span>
                    <span class="metric-value" id="interventions">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">进化代数</span>
                    <span class="metric-value" id="generation">0</span>
                </div>
            </div>
            
            <!-- 行为注入 -->
            <div class="card">
                <h2>⚡ 行为注入测试</h2>
                <p style="color: #888; margin-bottom: 12px;">手动注入行为记录以测试意识系统</p>
                <div class="controls">
                    <button class="btn" onclick="injectBehavior('model_reasoning', 0.7, 0.5, 0.8, 0.4)">🤔 模型推理</button>
                    <button class="btn" onclick="injectBehavior('tool_usage:test', 0.8, 0.5, 0.9, 0.3)">🔧 工具调用</button>
                    <button class="btn" onclick="injectBehavior('creative_action', 0.6, 0.9, 0.7, 0.8)">💡 创造性行为</button>
                </div>
                <div class="controls">
                    <button class="btn btn-success" onclick="injectBatch()">📥 批量注入 5 条</button>
                    <button class="btn btn-danger" onclick="clearHistory()">🗑 清空历史</button>
                </div>
            </div>
            
            <!-- 提示词上下文 -->
            <div class="card" style="grid-column: span 2;">
                <h2>📝 提示词上下文</h2>
                <button class="btn" onclick="generateContext()" style="margin-bottom: 12px;">生成上下文</button>
                <div class="context-box" id="context-output">点击按钮生成意识上下文...</div>
            </div>
            
            <!-- 行为历史 -->
            <div class="card" style="grid-column: span 2;">
                <h2>📜 最近行为记录</h2>
                <div id="history-list">
                    <p style="color: #666;">暂无行为记录</p>
                </div>
            </div>
        </div>
        
        <p class="refresh-info">页面每 3 秒自动刷新 | 最后更新: <span id="last-update">-</span></p>
    </div>
    
    <script>
        // 自动刷新
        setInterval(refreshStatus, 3000);
        
        // 页面加载时刷新
        document.addEventListener('DOMContentLoaded', refreshStatus);
        
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // 更新状态
                const statusEl = document.getElementById('status');
                if (data.is_running) {
                    statusEl.innerHTML = '<span class="status-badge status-running">运行中</span>';
                } else {
                    statusEl.innerHTML = '<span class="status-badge status-stopped">已停止</span>';
                }
                
                // 更新涌现阶段
                const phase = data.emergence?.phase || 'pre_emergence';
                const phaseNames = {
                    'pre_emergence': '前涌现期',
                    'approaching': '接近临界点',
                    'critical': '临界状态',
                    'emerged': '已涌现',
                    'unstable': '不稳定'
                };
                const phaseIcons = {
                    'pre_emergence': '○',
                    'approaching': '◐',
                    'critical': '●',
                    'emerged': '◎',
                    'unstable': '◑'
                };
                document.getElementById('phase').textContent = phaseNames[phase] || phase;
                document.getElementById('phase-icon').textContent = phaseIcons[phase] || '○';
                
                // 更新涌现分数
                const score = data.emergence?.score || 0;
                document.getElementById('score').textContent = score.toFixed(3);
                document.getElementById('score-bar').style.width = (score * 100) + '%';
                
                // 更新运行时长
                document.getElementById('uptime').textContent = data.uptime_hours?.toFixed(2) + ' 小时' || '-';
                
                // 更新指标
                const indicators = data.emergence?.indicators || {};
                updateMetric('autonomy', indicators.autonomy_level || 0);
                updateMetric('creativity', indicators.creativity_metric || 0);
                updateMetric('goal-alignment', indicators.goal_alignment || 0);
                updateMetric('novelty', indicators.novelty || 0);
                
                // 更新统计
                const stats = data.stats || {};
                document.getElementById('total-behaviors').textContent = stats.total_tasks || 0;
                document.getElementById('success-count').textContent = stats.successful_tasks || 0;
                document.getElementById('fail-count').textContent = stats.failed_tasks || 0;
                document.getElementById('interventions').textContent = stats.interventions_applied || 0;
                document.getElementById('generation').textContent = data.evolution?.generation || 0;
                
                // 更新最后更新时间
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                
            } catch (error) {
                console.error('刷新状态失败:', error);
            }
        }
        
        function updateMetric(id, value) {
            document.getElementById(id).textContent = value.toFixed(3);
            document.getElementById(id + '-bar').style.width = (value * 100) + '%';
            
            // 设置颜色
            const el = document.getElementById(id);
            if (value >= 0.7) {
                el.className = 'metric-value high';
            } else if (value >= 0.4) {
                el.className = 'metric-value medium';
            } else {
                el.className = 'metric-value low';
            }
        }
        
        async function startConsciousness() {
            try {
                const response = await fetch('/api/start', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                refreshStatus();
            } catch (error) {
                alert('启动失败: ' + error);
            }
        }
        
        async function stopConsciousness() {
            try {
                const response = await fetch('/api/stop', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                refreshStatus();
            } catch (error) {
                alert('停止失败: ' + error);
            }
        }
        
        async function injectBehavior(actionType, autonomy, creativity, goal, novelty) {
            try {
                const response = await fetch('/api/inject', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action_type: actionType,
                        autonomy_level: autonomy,
                        creativity_score: creativity,
                        goal_relevance: goal,
                        novelty_score: novelty
                    })
                });
                const data = await response.json();
                refreshStatus();
                refreshHistory();
            } catch (error) {
                alert('注入失败: ' + error);
            }
        }
        
        async function injectBatch() {
            for (let i = 0; i < 5; i++) {
                await injectBehavior(
                    'test_action_' + i,
                    0.5 + Math.random() * 0.4,
                    0.3 + Math.random() * 0.5,
                    0.6 + Math.random() * 0.3,
                    0.2 + Math.random() * 0.4
                );
                await new Promise(r => setTimeout(r, 100));
            }
            alert('批量注入完成！');
        }
        
        async function clearHistory() {
            try {
                const response = await fetch('/api/clear', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                refreshStatus();
                refreshHistory();
            } catch (error) {
                alert('清空失败: ' + error);
            }
        }
        
        async function generateContext() {
            try {
                const response = await fetch('/api/context');
                const data = await response.json();
                document.getElementById('context-output').textContent = data.context || '[空]';
            } catch (error) {
                document.getElementById('context-output').textContent = '生成失败: ' + error;
            }
        }
        
        async function refreshHistory() {
            try {
                const response = await fetch('/api/history');
                const data = await response.json();
                const historyEl = document.getElementById('history-list');
                
                if (!data.history || data.history.length === 0) {
                    historyEl.innerHTML = '<p style="color: #666;">暂无行为记录</p>';
                    return;
                }
                
                let html = '';
                data.history.slice(-10).reverse().forEach(item => {
                    html += `
                        <div class="history-item">
                            <div class="time">${item.time}</div>
                            <div><strong>${item.action_type}</strong></div>
                            <div style="color: #888; font-size: 11px;">
                                自主性: ${item.autonomy_level.toFixed(2)} | 
                                创造性: ${item.creativity_score.toFixed(2)} | 
                                目标: ${item.goal_relevance.toFixed(2)}
                            </div>
                        </div>
                    `;
                });
                historyEl.innerHTML = html;
            } catch (error) {
                console.error('刷新历史失败:', error);
            }
        }
        
        // 初始加载历史
        refreshHistory();
    </script>
</body>
</html>
"""


# ==================== API 路由 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回监控页面"""
    return HTML_TEMPLATE


@app.get("/api/status")
async def get_status():
    """获取意识系统状态"""
    global consciousness
    
    if consciousness is None:
        return {"is_running": False, "error": "意识系统未初始化"}
    
    try:
        state = consciousness.get_consciousness_state()
        return state
    except Exception as e:
        return {"is_running": False, "error": str(e)}


@app.post("/api/start")
async def start_consciousness():
    """启动意识系统"""
    global consciousness
    
    if consciousness is None:
        # 创建意识系统
        consciousness = ConsciousnessManager(
            system_root='.',
            config={'enable_active_thinking': False},
            auto_start=False
        )
    
    if consciousness.is_running:
        return {"success": True, "message": "意识系统已在运行中"}
    
    try:
        await consciousness.start()
        return {"success": True, "message": "意识系统启动成功！"}
    except Exception as e:
        return {"success": False, "message": f"启动失败: {str(e)}"}


@app.post("/api/stop")
async def stop_consciousness():
    """停止意识系统"""
    global consciousness
    
    if consciousness is None or not consciousness.is_running:
        return {"success": True, "message": "意识系统未运行"}
    
    try:
        await consciousness.stop()
        return {"success": True, "message": "意识系统已停止"}
    except Exception as e:
        return {"success": False, "message": f"停止失败: {str(e)}"}


@app.post("/api/inject")
async def inject_behavior(request: Request):
    """注入行为记录"""
    global consciousness
    
    if consciousness is None or not consciousness.is_running:
        # 自动启动
        await start_consciousness()
    
    try:
        data = await request.json()
        consciousness.record_behavior(
            action_type=data.get("action_type", "test_action"),
            autonomy_level=data.get("autonomy_level", 0.5),
            creativity_score=data.get("creativity_score", 0.5),
            goal_relevance=data.get("goal_relevance", 0.5),
            novelty_score=data.get("novelty_score", 0.5)
        )
        
        count = len(consciousness.emergence_metrics.behavior_history)
        return {
            "success": True,
            "message": f"行为已记录，总记录数: {count}"
        }
    except Exception as e:
        return {"success": False, "message": f"注入失败: {str(e)}"}


@app.post("/api/clear")
async def clear_history():
    """清空行为历史"""
    global consciousness
    
    if consciousness is None:
        return {"success": True, "message": "无需清空"}
    
    try:
        consciousness.emergence_metrics.behavior_history.clear()
        consciousness.emergence_metrics._cached_indicators = None
        return {"success": True, "message": "行为历史已清空"}
    except Exception as e:
        return {"success": False, "message": f"清空失败: {str(e)}"}


@app.get("/api/context")
async def get_context():
    """生成提示词上下文"""
    global consciousness
    
    if consciousness is None or not consciousness.is_running:
        return {"context": "[意识系统未启动]"}
    
    try:
        context = consciousness.get_context_for_prompt()
        return {"context": context or "[空]"}
    except Exception as e:
        return {"context": f"[错误: {str(e)}]"}


@app.get("/api/history")
async def get_history():
    """获取行为历史"""
    global consciousness
    
    if consciousness is None:
        return {"history": []}
    
    try:
        history = []
        for record in consciousness.emergence_metrics.behavior_history[-20:]:
            history.append({
                "time": record.timestamp.strftime("%H:%M:%S"),
                "action_type": record.action_type,
                "autonomy_level": record.autonomy_level,
                "creativity_score": record.creativity_score,
                "goal_relevance": record.goal_relevance,
                "novelty_score": record.novelty_score
            })
        return {"history": history}
    except Exception as e:
        return {"history": [], "error": str(e)}


# ==================== 启动入口 ====================

def run_server():
    """启动 Web 服务器"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              WinClaw 意识系统 Web 监控界面                  ║
║                                                              ║
║  访问地址: http://localhost:8765                            ║
║                                                              ║
║  功能:                                                       ║
║  • 实时监控意识状态                                         ║
║  • 手动注入行为记录                                         ║
║  • 查看涌现指标变化                                         ║
║  • 生成提示词上下文                                         ║
║                                                              ║
║  按 Ctrl+C 停止服务器                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    run_server()
