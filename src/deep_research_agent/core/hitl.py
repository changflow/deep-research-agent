"""
Human-in-the-Loop (HITL) 管理器
处理需要人工干预的中断点、事件分发和反馈收集
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Awaitable
from langchain_core.runnables import RunnableConfig

from .state import ResearchAgentState, AgentStatus, HITLEvent, ResearchPlan, ResearchStepStatus

logger = logging.getLogger(__name__)

class HITLManager:
    """HITL 管理器，负责处理断点和用户反馈"""
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def create_approval_request(self, state: ResearchAgentState, event_type: str, payload: Dict[str, Any]) -> ResearchAgentState:
        """创建一个审批请求，并暂停 Agent"""
        
        event = HITLEvent(
            event_type=event_type,
            session_id=state.session_id,
            payload=payload,
            requires_response=True
        )
        
        state.pending_hitl_event = event
        
        # 根据不同事件类型设置状态
        if event_type == "plan_approval":
            state.status = AgentStatus.PLAN_REVIEW
        elif event_type == "final_report_approval":
            state.status = AgentStatus.FINAL_REVIEW
            
        self._logger.info(f"Created HITL request: {event_type} for session {state.session_id}")
        return state
    
    def handle_feedback(self, state: ResearchAgentState, feedback_data: Dict[str, Any]) -> ResearchAgentState:
        """处理用户反馈"""
        event = state.pending_hitl_event
        
        if not event:
            self._logger.warning(f"No pending HITL event for session {state.session_id}")
            return state
            
        action = feedback_data.get("action")  # "approve", "reject", "modify"
        
        if event.event_type == "plan_approval":
            return self._handle_plan_feedback(state, feedback_data)
        elif event.event_type == "final_report_approval":
            return self._handle_report_feedback(state, feedback_data)
            
        # 清除挂起的事件
        state.pending_hitl_event = None
        state.human_feedback = feedback_data
        
        return state
        
    def _handle_plan_feedback(self, state: ResearchAgentState, feedback_data: Dict[str, Any]) -> ResearchAgentState:
        """处理计划审批反馈"""
        action = feedback_data.get("action")
        
        if action == "approve":
            self._logger.info("Research plan approved")
            state.status = AgentStatus.EXECUTING
            state.current_step_index = 0
            
        elif action == "modify":
            self._logger.info("Research plan modified by user")
            # 允许用户修改计划
            modified_plan_data = feedback_data.get("modified_plan")
            if modified_plan_data and state.research_plan:
                self._update_plan_from_dict(state.research_plan, modified_plan_data)
                state.research_plan.user_modified = True
                state.research_plan.modification_notes = feedback_data.get("notes")
                
            state.status = AgentStatus.EXECUTING
            state.current_step_index = 0
            
        else: # reject or other
            self._logger.info("Research plan rejected")
            state.set_error("Research plan rejected by user")
            
        # 清除事件
        state.pending_hitl_event = None
        return state
        
    def _handle_report_feedback(self, state: ResearchAgentState, feedback_data: Dict[str, Any]) -> ResearchAgentState:
        """处理报告审批反馈"""
        action = feedback_data.get("action")
        
        if action == "approve":
            self._logger.info("Final report approved")
            state.complete_research()
            
        elif action == "reject":
            self._logger.info("Final report rejected")
            # 这里的逻辑可以是结束，或者要求重写
            state.set_error("Final report rejected by user")
            
        state.pending_hitl_event = None
        return state
        
    def _update_plan_from_dict(self, current_plan: ResearchPlan, new_data: Dict[str, Any]) -> None:
        """从字典更新计划对象"""
        # 这是一个简化的实现，实际逻辑可能更复杂
        if "topic" in new_data:
            current_plan.topic = new_data["topic"]
        if "objective" in new_data:
            current_plan.objective = new_data["objective"]
            
        # 步骤更新逻辑略...
        
    def should_interrupt(self, state: ResearchAgentState) -> bool:
        """判断是否应该中断以等待人工接入"""
        # 如果有挂起的 HITL 事件，且需要响应，则应该中断
        return state.pending_hitl_event is not None and state.pending_hitl_event.requires_response

# 全局实例
hitl_manager = HITLManager()
