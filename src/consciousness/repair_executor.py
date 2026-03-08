"""
修复执行器

WinClaw 意识系统 - Phase 3: Repair Executor

功能概述：
- 执行具体的修复操作
- 修改代码文件
- 更新配置文件
- 重启服务或组件
- 验证修复效果

修复类型：
1. 代码修改 - 修正语法错误、逻辑错误
2. 配置更新 - 修改配置参数
3. 依赖管理 - 安装/卸载包
4. 文件操作 - 创建/删除/移动文件
5. 进程管理 - 重启服务

作者：WinClaw Consciousness Team
版本：v0.3.0 (Phase 3)
创建时间：2026 年 2 月
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

from .types import RepairAction, RepairLevel

logger = logging.getLogger(__name__)


class RepairExecutor:
    """
    修复执行器
    
    职责：
    1. 接收修复动作
    2. 执行具体修复操作
    3. 报告执行结果
    4. 清理临时文件
    """
    
    def __init__(self, system_root: Path):
        """
        初始化修复执行器
        
        Args:
            system_root: 系统根目录
        """
        self.system_root = system_root
        self.execution_history: List[Dict] = []
        
        logger.info("修复执行器初始化完成")
    
    async def execute(self, action: RepairAction) -> bool:
        """
        执行修复动作
        
        Args:
            action: 修复动作
            
        Returns:
            执行是否成功
        """
        logger.info(f"开始执行修复：{action.action_id}, 类型：{action.action_type}")
        
        try:
            # 根据修复等级和类型选择执行策略
            if action.level == RepairLevel.ERROR_RECOVERY:
                success = await self._execute_error_recovery(action)
            elif action.level == RepairLevel.BEHAVIOR_FIX:
                success = await self._execute_behavior_fix(action)
            elif action.level == RepairLevel.CAPABILITY_OPT:
                success = await self._execute_capability_optimization(action)
            elif action.level == RepairLevel.CORE_EVOLUTION:
                success = await self._execute_core_evolution(action)
            else:
                logger.error(f"未知修复等级：{action.level}")
                success = False
            
            # 记录执行历史
            self._record_execution(action, success)
            
            return success
            
        except Exception as e:
            logger.error(f"修复执行失败：{e}")
            self._record_execution(action, False, str(e))
            return False
    
    async def _execute_error_recovery(self, action: RepairAction) -> bool:
        """
        执行错误恢复
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        logger.info("执行错误恢复...")
        
        try:
            # 尝试重新编译有语法错误的文件
            if "syntax" in str(action.before_state).lower():
                file_path = self._extract_file_path(action)
                if file_path and file_path.exists():
                    # 读取并尝试编译
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    # 如果编译失败，尝试自动修复常见错误
                    fixed_source = self._fix_common_syntax_errors(source)
                    
                    if fixed_source != source:
                        # 保存修复后的代码
                        backup_path = file_path.with_suffix('.py.bak')
                        shutil.copy2(file_path, backup_path)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_source)
                        
                        logger.info(f"已修复语法错误：{file_path}")
                        return True
            
            # 处理导入错误
            if "import" in str(action.before_state).lower():
                return await self._fix_import_errors(action)
            
            # 默认返回 False，表示需要人工干预
            logger.warning("无法自动恢复错误，需要人工干预")
            return False
            
        except Exception as e:
            logger.error(f"错误恢复失败：{e}")
            return False
    
    async def _execute_behavior_fix(self, action: RepairAction) -> bool:
        """
        执行行为修复
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        logger.info("执行行为修复...")
        
        try:
            # 修改配置文件
            if "config" in action.target_component.lower():
                return await self._update_configuration(action)
            
            # 修改代码逻辑
            if "code" in action.target_component.lower() or "module" in action.target_component.lower():
                return await self._modify_code_logic(action)
            
            # 文件系统修复
            if "file" in action.target_component.lower():
                return await self._fix_file_system_issue(action)
            
            logger.warning("未知的行为修复类型")
            return False
            
        except Exception as e:
            logger.error(f"行为修复失败：{e}")
            return False
    
    async def _execute_capability_optimization(self, action: RepairAction) -> bool:
        """
        执行能力优化
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        logger.info("执行能力优化...")
        
        try:
            # 性能优化通常需要代码重写，这里只处理简单情况
            # 例如：清除缓存、释放资源
            
            if "cache" in action.target_component.lower():
                await self._clear_caches()
                return True
            
            if "memory" in action.target_component.lower():
                await self._optimize_memory()
                return True
            
            logger.warning("能力优化需要更复杂的处理")
            return False
            
        except Exception as e:
            logger.error(f"能力优化失败：{e}")
            return False
    
    async def _execute_core_evolution(self, action: RepairAction) -> bool:
        """
        执行核心进化
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        logger.warning("核心进化需要人工审批和实施")
        
        # 核心进化通常涉及重大改动，不应该自动执行
        # 这里只记录建议
        
        logger.info(f"进化建议已记录：{action.after_state}")
        return False  # 返回 False 表示需要人工处理
    
    async def _fix_import_errors(self, action: RepairAction) -> bool:
        """
        修复导入错误
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        try:
            # 提取缺失的模块名
            error_info = str(action.before_state)
            module_match = self._extract_module_name(error_info)
            
            if module_match:
                module_name = module_match.group(1)
                logger.info(f"尝试安装缺失模块：{module_name}")
                
                # 执行 pip install
                result = await asyncio.create_subprocess_exec(
                    'pip', 'install', module_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    logger.info(f"成功安装模块：{module_name}")
                    return True
                else:
                    logger.error(f"安装失败：{stderr.decode()}")
            
            return False
            
        except Exception as e:
            logger.error(f"修复导入错误失败：{e}")
            return False
    
    async def _update_configuration(self, action: RepairAction) -> bool:
        """
        更新配置文件
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        try:
            config_path = self.system_root / "config" / "default.toml"
            
            if not config_path.exists():
                logger.error(f"配置文件不存在：{config_path}")
                return False
            
            # TODO: 实现 TOML 配置更新
            # 目前只支持简单的键值对替换
            
            logger.info("配置更新功能尚未完全实现")
            return False
            
        except Exception as e:
            logger.error(f"配置更新失败：{e}")
            return False
    
    async def _modify_code_logic(self, action: RepairAction) -> bool:
        """
        修改代码逻辑
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        try:
            # 提取目标文件和修改内容
            after_state = action.after_state
            
            if "fix" in after_state:
                fix_description = after_state["fix"]
                logger.info(f"代码修改建议：{fix_description}")
                
                # TODO: 实现代码自动生成和替换
                # 这需要集成代码生成工具
                
                logger.warning("代码逻辑修改需要代码生成能力")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"代码修改失败：{e}")
            return False
    
    async def _fix_file_system_issue(self, action: RepairAction) -> bool:
        """
        修复文件系统问题
        
        Args:
            action: 修复动作
            
        Returns:
            执行结果
        """
        try:
            before_state = action.before_state
            
            # 如果是文件缺失
            if "missing" in str(before_state).lower() or "not found" in str(before_state).lower():
                # 创建缺失的目录或文件
                path_str = before_state.get("path", "")
                if path_str:
                    target_path = Path(path_str)
                    
                    if not target_path.parent.exists():
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        logger.info(f"创建目录：{target_path.parent}")
                    
                    if not target_path.exists():
                        target_path.touch()
                        logger.info(f"创建文件：{target_path}")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"文件系统修复失败：{e}")
            return False
    
    async def _clear_caches(self):
        """清除缓存"""
        try:
            cache_dir = self.system_root / "__pycache__"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.info("已清除 Python 缓存")
            
            # 清除其他缓存
            for pattern in ["*.pyc", "*.pyo"]:
                for pyc_file in self.system_root.rglob(pattern):
                    pyc_file.unlink()
            
            logger.info("缓存清理完成")
            
        except Exception as e:
            logger.error(f"缓存清理失败：{e}")
    
    async def _optimize_memory(self):
        """优化内存使用"""
        try:
            # 触发垃圾回收
            import gc
            gc.collect()
            
            logger.info("内存优化完成")
            
        except Exception as e:
            logger.error(f"内存优化失败：{e}")
    
    def _fix_common_syntax_errors(self, source: str) -> str:
        """
        修复常见语法错误
        
        Args:
            source: 源代码
            
        Returns:
            修复后的代码
        """
        lines = source.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_line = line
            
            # 检查常见的缩进错误
            if line.startswith(' ') and not line.startswith('    '):
                # 将空格缩进转换为制表符缩进（如果需要）
                pass
            
            # 检查缺少冒号
            stripped = line.strip()
            if (stripped.endswith(')') or 
                stripped.endswith(':') is False and 
                (stripped.startswith('if ') or 
                 stripped.startswith('for ') or 
                 stripped.startswith('while ') or 
                 stripped.startswith('def ') or 
                 stripped.startswith('class '))):
                
                if not stripped.endswith(':'):
                    fixed_line = line.rstrip() + ':'
                    logger.debug(f"第{i+1}行：添加缺少的冒号")
            
            fixed_lines.append(fixed_line)
        
        return '\n'.join(fixed_lines)
    
    def _extract_file_path(self, action: RepairAction) -> Optional[Path]:
        """从修复动作中提取文件路径"""
        before_state = action.before_state
        
        if "file" in before_state:
            return Path(before_state["file"])
        
        if "path" in before_state:
            return Path(before_state["path"])
        
        return None
    
    def _extract_module_name(self, error_info: str) -> Optional[Any]:
        """从错误信息中提取模块名"""
        import re
        
        patterns = [
            r"No module named ['\"]?(\w+)['\"]?",
            r"ModuleNotFoundError: No module named ['\"]?(\w+)['\"]?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_info)
            if match:
                return match
        
        return None
    
    def _record_execution(
        self,
        action: RepairAction,
        success: bool,
        error: Optional[str] = None
    ):
        """记录执行历史"""
        record = {
            "action_id": action.action_id,
            "timestamp": datetime.now(),
            "success": success,
            "error": error,
            "level": action.level.name,
            "component": action.target_component
        }
        
        self.execution_history.append(record)
        
        # 限制历史记录大小
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    def clear_history(self):
        """清空执行历史"""
        self.execution_history.clear()
        logger.info("执行历史已清空")
