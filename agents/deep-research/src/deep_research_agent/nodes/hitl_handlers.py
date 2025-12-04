import logging
from typing import Dict, Any
from agent_core.core.state import BaseAgentState, AgentStatus
from deep_research_agent.state import ResearchAgentState

logger = logging.getLogger(__name__)

def handle_plan_feedback(state: BaseAgentState, feedback_data: Dict[str, Any]) -> BaseAgentState:
    """处理计划审批反馈"""
    # Cast to ResearchAgentState to access domain-specific fields
    # Ideally generic handlers shouldn't cast, but here we know the context
    research_state: ResearchAgentState = state 
    
    action = feedback_data.get("action")
    
    if action == "approve":
        logger.info("Research plan approved")
        research_state.status = AgentStatus.EXECUTING
        research_state.current_step_index = 0
        
    elif action == "modify":
        logger.info("Research plan modified by user")
        # 允许用户修改计划
        modified_plan_data = feedback_data.get("modified_plan")
        if modified_plan_data and research_state.research_plan:
             # 这里简单假设 dictionary update，实际可能需要 validation
             # Pydantic 模型的 update 比较可以直接
             current_plan_dict = research_state.research_plan.dict()
             current_plan_dict.update(modified_plan_data)
             # Re-instantiate or update fields
             for k, v in modified_plan_data.items():
                 if hasattr(research_state.research_plan, k):
                     setattr(research_state.research_plan, k, v)
                     
             research_state.research_plan.user_modified = True
             research_state.research_plan.modification_notes = feedback_data.get("notes")
            
        research_state.status = AgentStatus.EXECUTING
        research_state.current_step_index = 0
        
    else: # reject or other
        logger.info("Research plan rejected")
        research_state.set_error("Research plan rejected by user")
        
    # 清除事件
    research_state.pending_hitl_event = None
    return research_state

def handle_report_feedback(state: BaseAgentState, feedback_data: Dict[str, Any]) -> BaseAgentState:
    """处理报告审批反馈"""
    research_state: ResearchAgentState = state
    action = feedback_data.get("action")
    
    if action == "approve":
        logger.info("Final report approved")
        research_state.complete_research()
        
    elif action == "reject":
        logger.info("Final report rejected")
        research_state.set_error("Final report rejected by user")
        
    research_state.pending_hitl_event = None
    return research_state
