"""
Human-in-the-Loop (HITL) 管理器
处理需要人工干预的中断点、事件分发和反馈收集
"""

import logging
from typing import Dict, Any, Callable, Optional
from .state import BaseAgentState, AgentStatus, HITLEvent

logger = logging.getLogger(__name__)

HandlerType = Callable[[BaseAgentState, Dict[str, Any]], BaseAgentState]

class HITLManager:
    """HITL 管理器，负责处理断点和用户反馈"""
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._handlers: Dict[str, HandlerType] = {}
    
    def register_handler(self, event_type: str, handler: HandlerType):
        """注册特定事件类型的反馈处理器"""
        self._handlers[event_type] = handler
    
    def create_approval_request(self, state: BaseAgentState, event_type: str, payload: Dict[str, Any]) -> BaseAgentState:
        """创建一个审批请求，并暂停 Agent"""
        
        event = HITLEvent(
            event_type=event_type,
            session_id=state.session_id,
            payload=payload,
            requires_response=True
        )
        
        state.pending_hitl_event = event
        
        # 尝试根据事件设置状态，如果状态枚举中有对应值
        # 这里做一些通用的推断，但具体的状态流转最好由 handler 或 graph 定义
        if event_type == "plan_approval":
            # Check if PLAN_REVIEW exists in AgentStatus (it does in base)
            state.status = AgentStatus.PLAN_REVIEW
        elif event_type == "final_report_approval":
             state.status = AgentStatus.FINAL_REVIEW
            
        self._logger.info(f"Created HITL request: {event_type} for session {state.session_id}")
        return state
    
    def handle_feedback(self, state: BaseAgentState, feedback_data: Dict[str, Any]) -> BaseAgentState:
        """处理用户反馈"""
        event = state.pending_hitl_event
        
        if not event:
            self._logger.warning(f"No pending HITL event for session {state.session_id}")
            return state
            
        handler = self._handlers.get(event.event_type)
        
        if handler:
             self._logger.info(f"Delegating feedback handling for {event.event_type}")
             return handler(state, feedback_data)
            
        # 默认处理：清除挂起的事件并保存反馈
        self._logger.info(f"No specific handler for {event.event_type}, using default handling")
        state.pending_hitl_event = None
        state.human_feedback = feedback_data
        
        return state
    
    def should_interrupt(self, state: BaseAgentState) -> bool:
        """判断是否应该中断以等待人工接入"""
        # 如果有挂起的 HITL 事件，且需要响应，则应该中断
        return state.pending_hitl_event is not None and state.pending_hitl_event.requires_response

# 全局实例
hitl_manager = HITLManager()
