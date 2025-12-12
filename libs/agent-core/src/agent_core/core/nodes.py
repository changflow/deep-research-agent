"""
通用节点逻辑 (Base Nodes)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Type
from datetime import datetime

from .interfaces import Gatherer, Verifier, Processor, WorkerResult
from .state import BaseAgentState, AgentStatus

logger = logging.getLogger(__name__)

class BaseWorkerNode(ABC):
    """
    通用 Worker 执行节点基类
    实现了 "Gather -> Verify -> Process" 的标准分形流程
    """
    
    def __init__(self, worker_registry: Any, processor: Optional[Processor] = None):
        """
        Args:
            worker_registry: 包含 get_worker_pair(name) -> (GathererCls, VerifierCls) 方法的对象
            processor: 可选的通用处理器，用于深度加工
        """
        self.worker_registry = worker_registry
        self.processor = processor

    @abstractmethod
    def get_current_step(self, state: BaseAgentState) -> Any:
        """从 State 中获取当前步骤对象"""
        pass

    @abstractmethod
    def get_search_query(self, state: BaseAgentState, step: Any) -> str:
        """构建搜索/探索查询"""
        pass

    def on_gather_complete(self, state: BaseAgentState, step: Any, result: WorkerResult) -> Any:
        """Gather 完成后的钩子，用于转换数据或更新 State"""
        return result.data

    def on_verify_complete(self, state: BaseAgentState, step: Any, result: WorkerResult):
        """Verify 完成后的钩子"""
        pass
    
    @abstractmethod
    def get_process_instruction(self, state: BaseAgentState, step: Any, gather_data: Any) -> str:
        """获取 Process 阶段的指令 (Prompt Template)"""
        pass

    def on_process_complete(self, state: BaseAgentState, step: Any, result: WorkerResult):
        """Process 完成后的钩子，用于保存最终洞察"""
        pass

    def update_step_status(self, step: Any, status: str, error: str = None):
        """更新步骤状态"""
        # 默认假设 step 有 status 属性，子类可覆盖
        if hasattr(step, "status"):
            step.status = status
        if error and hasattr(step, "error_message"):
            step.error_message = error
        if status in ["completed", "failed"] and hasattr(step, "end_time"):
            step.end_time = datetime.now()

    async def __call__(self, state: BaseAgentState) -> BaseAgentState:
        """
        执行标准分形步骤
        """
        current_step = self.get_current_step(state)
        if not current_step:
            logger.warning("BaseWorkerNode: No current step found")
            return state
        
        # 1. 准备
        assigned_agent = getattr(current_step, "assigned_agent", None)
        step_id = getattr(current_step, "step_id", "unknown")
        logger.info(f"Executing step: {step_id} (Agent: {assigned_agent})")
        
        self.update_step_status(current_step, "executing")
        if hasattr(state, "status"):
            state.status = AgentStatus.EXECUTING
            
        try:
            # 2. 获取 Worker Implementation
            # 假设 registry 有 get_worker_pair
            GathererCls, VerifierCls = self.worker_registry.get_worker_pair(assigned_agent)
            
            # 3. Gather Phase (广度探索)
            query = self.get_search_query(state, current_step)
            
            try:
                # 尝试传递配置
                gatherer = GathererCls()
                # 如果 Gatherer 支持配置注入，可以在此处优化
            except Exception:
                gatherer = GathererCls()
                
            gather_result = await gatherer.gather(query=query)
            
            if not gather_result.success:
                raise Exception(f"Gather failed: {gather_result.error}")
                
            # 数据转换钩子
            processed_gather_data = self.on_gather_complete(state, current_step, gather_result)
            
            # 4. Verify Phase (证据验证)
            if processed_gather_data and VerifierCls:
                verifier = VerifierCls()
                # 构建简单的验证上下文，实际场景可能更复杂
                content_preview = str(processed_gather_data)[:500]
                verify_criteria = {
                    "relevance": f"Is this relevant to: {query}?",
                    "quality": "Source credibility check"
                }
                verify_result = await verifier.verify(content_preview, verify_criteria)
                self.on_verify_complete(state, current_step, verify_result)
                logger.info(f"Verification: {verify_result.passed}")

            if not processed_gather_data:
                logger.warning(f"No results found for step: {step_id}")
                self.update_step_status(current_step, "failed", "No results found")
                return state

            # 5. Process Phase (深度加工/提取)
            if self.processor:
                instructions = self.get_process_instruction(state, current_step, processed_gather_data)
                
                # Context 构建
                context = {
                    "topic": getattr(state, "user_query", ""),
                    "step_title": getattr(current_step, "title", ""),
                    "step_description": getattr(current_step, "description", ""),
                    "expected_output": getattr(current_step, "expected_output", "")
                }
                
                process_result = await self.processor.process(
                    data=processed_gather_data, # 或者交给 prompt template 处理
                    instructions=instructions,
                    context=context
                )
                
                if process_result.success:
                    self.on_process_complete(state, current_step, process_result)
                    self.update_step_status(current_step, "completed")
                else:
                    raise Exception(f"Processing failed: {process_result.error}")
            else:
                # 如果没有 Processor，默认完成
                self.update_step_status(current_step, "completed")
                
            return state

        except Exception as e:
            logger.error(f"Error executing step {step_id}: {e}")
            self.update_step_status(current_step, "failed", str(e))
            return state
