"""
意识系统桥接器 - 连接 WinClaw 和意识系统的桥梁

负责：
1. 将 WinClaw 的事件转换为意识系统的刺激
2. 将意识系统的响应转换为 WinClaw 的动作
3. 管理意识状态与会话的绑定
"""

from typing import Dict, List, Optional
from datetime import datetime
import asyncio


class ConsciousnessBridge:
    """
    意识系统与 WinClaw 的桥接器
    
    这是意识系统的入口点，所有带意识的处理都通过此桥接器
    """
    
    def __init__(self, winclaw_agent):
        self.agent = winclaw_agent
        self.event_bus = winclaw_agent.event_bus
        
        # 标志位
        self.enabled = False
        self.phase_5_enabled = False  # Phase 5 能力开关
        
        # 初始化意识模块（延迟加载）
        self.working_memory = None
        self.episodic_memory = None
        self.semantic_memory = None
        self.identity = None
        self.emotion = None
        self.ethics = None
        self.active_thinking = None
        
        # 身体性接口
        self.embodiment = None
        
        # 工具创造模块（Phase 5）
        self.tool_creator = None
        
        # 自我修复引擎（Phase 5）
        self.self_repair = None
        
        # 涌现监测（Phase 6）
        self.emergence_catalyst = None
        
        # 订阅 WinClaw 事件
        self._setup_event_bindings()
        
    def _setup_event_bindings(self):
        """设置事件订阅"""
        # 这些将在后续实现
        pass
        
    async def initialize(self):
        """初始化意识系统模块"""
        if not self.enabled:
            return
            
        # 延迟导入，避免循环依赖
        from src.consciousness.perception import PerceptionSystem
        from src.consciousness.embodiment import WinClawEmbodiment
        
        # 初始化基础模块
        await self._initialize_memory_modules()
        await self._initialize_identity_module()
        await self._initialize_emotion_module()
        await self._initialize_ethics_module()
        
        # 初始化身体性接口
        self.embodiment = WinClawEmbodiment(
            tool_registry=self.agent.tool_registry
        )
        
        print("[ConsciousnessBridge] Base modules initialized")
        
    async def initialize_phase_5(self):
        """初始化 Phase 5 能力模块"""
        if not self.phase_5_enabled:
            print("[ConsciousnessBridge] Phase 5 disabled")
            return
            
        from src.consciousness.tool_creator import ToolCreator
        from src.consciousness.self_repair import SelfRepairEngine
        
        # 初始化工具创造模块
        self.tool_creator = ToolCreator(
            tool_registry=self.agent.tool_registry,
            event_bus=self.event_bus
        )
        
        # 初始化自我修复引擎
        self.self_repair = SelfRepairEngine(
            consciousness_system=self,
            code_storage=None,  # TODO: 配置存储路径
            backup_storage=None
        )
        
        print("[ConsciousnessBridge] Phase 5 modules initialized")
        
    async def initialize_phase_6(self):
        """初始化 Phase 6 监测模块"""
        if not self.phase_5_enabled:  # Phase 6 需要 Phase 5 先启用
            return
            
        from src.consciousness.emergence_catalyst import EmergenceCatalyst
        
        # 初始化涌现监测
        self.emergence_catalyst = EmergenceCatalyst(
            consciousness_system=self,
            event_bus=self.event_bus
        )
        
        # 启动监测循环
        asyncio.create_task(self.emergence_catalyst.monitor_emergence())
        
        print("[ConsciousnessBridge] Phase 6 monitoring started")
        
    async def _initialize_memory_modules(self):
        """初始化记忆模块"""
        # TODO: 实现记忆模块初始化
        pass
        
    async def _initialize_identity_module(self):
        """初始化身份模块"""
        # TODO: 实现身份模块初始化
        pass
        
    async def _initialize_emotion_module(self):
        """初始化情感模块"""
        # TODO: 实现情感模块初始化
        pass
        
    async def _initialize_ethics_module(self):
        """初始化伦理模块"""
        # TODO: 实现伦理模块初始化
        pass
        
    async def process_with_consciousness(
        self, 
        user_input: str, 
        context: dict = None
    ) -> dict:
        """
        带意识处理的请求流程
        
        Args:
            user_input: 用户输入
            context: 上下文信息
            
        Returns:
            处理结果
        """
        if not self.enabled:
            # 降级到普通处理
            return await self.agent.process_normal(user_input, context or {})
            
        request_id = self._generate_request_id()
        
        try:
            # 1. 感知层：获取当前状态
            sensory_input = await self.embodiment.get_sensory_input()
            
            # 2. 情景记忆：检索相关历史
            relevant_memories = await self.episodic_memory.retrieve(
                query=user_input,
                limit=5
            )
            
            # 3. 身份层：构建角色上下文
            identity_context = self.identity.get_current_identity()
            
            # 4. 情感层：评估情感状态
            emotion_state = self.emotion.evaluate(user_input, sensory_input)
            
            # 5. 伦理层：检查约束
            ethics_check = self.ethics.evaluate_action(
                proposed_action=user_input,
                context=context or {}
            )
            if not ethics_check.allowed:
                return {
                    "response": ethics_check.message,
                    "blocked": True,
                    "request_id": request_id
                }
                
            # 6. 工作记忆：组装完整上下文
            enriched_context = self.working_memory.assemble(
                user_input=user_input,
                memories=relevant_memories,
                identity=identity_context,
                emotion=emotion_state,
                sensory=sensory_input
            )
            
            # 7. 调用 Agent 处理
            result = await self.agent.process(user_input, enriched_context)
            
            # 8. 记忆编码：保存本次交互
            await self.episodic_memory.store({
                "event": {
                    "user_input": user_input,
                    "response": result.get("response"),
                    "tools_used": result.get("tools_used", []),
                    "emotion": emotion_state.to_dict() if hasattr(emotion_state, 'to_dict') else {},
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # 9. 情感更新
            self.emotion.update_from_interaction(result.get("response"))
            
            result["request_id"] = request_id
            result["consciousness_processed"] = True
            
            return result
            
        except Exception as e:
            print(f"[ConsciousnessBridge] Error: {str(e)}")
            # 降级处理
            return await self.agent.process_normal(user_input, context or {})
            
    def _generate_request_id(self) -> str:
        """生成请求 ID"""
        import hashlib
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:16]
        
    async def enable(self):
        """启用意识系统"""
        self.enabled = True
        await self.initialize()
        print("[ConsciousnessBridge] Consciousness system ENABLED")
        
    async def disable(self):
        """禁用意识系统"""
        self.enabled = False
        print("[ConsciousnessBridge] Consciousness system DISABLED")
        
    async def enable_phase_5(self):
        """启用 Phase 5 能力"""
        self.phase_5_enabled = True
        await self.initialize_phase_5()
        print("[ConsciousnessBridge] Phase 5 capabilities ENABLED")
        
    async def disable_phase_5(self):
        """禁用 Phase 5 能力"""
        self.phase_5_enabled = False
        print("[ConsciousnessBridge] Phase 5 capabilities DISABLED")
        
    def get_status(self) -> dict:
        """获取意识系统状态"""
        return {
            "enabled": self.enabled,
            "phase_5_enabled": self.phase_5_enabled,
            "modules_initialized": {
                "working_memory": self.working_memory is not None,
                "episodic_memory": self.episodic_memory is not None,
                "identity": self.identity is not None,
                "emotion": self.emotion is not None,
                "ethics": self.ethics is not None,
                "tool_creator": self.tool_creator is not None,
                "self_repair": self.self_repair is not None,
                "emergence_catalyst": self.emergence_catalyst is not None
            }
        }
