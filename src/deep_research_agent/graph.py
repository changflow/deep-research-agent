"""
LangGraph 流程定义
构建和编排所有节点的执行流程
"""

import logging
import operator
from typing import Annotated, Sequence, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .core.state import ResearchAgentState, AgentStatus
from .nodes.plan_generation import generate_plan
from .nodes.search_execution import execute_search_step
from .nodes.report_generation import generate_final_report
from .core.hitl import hitl_manager

logger = logging.getLogger(__name__)

# === 条件路由函数 ===

def should_continue_to_execution(state: ResearchAgentState) -> str:
    """判断是否从计划生成继续到执行"""
    if state.status == AgentStatus.ERROR:
        return END
    
    if state.config.require_plan_approval:
        return "create_plan_approval"
    
    return "execute_step"

def check_step_completion(state: ResearchAgentState) -> str:
    """检查当前步骤是否完成，决定下一步"""
    if state.status == AgentStatus.ERROR:
        return END
        
    # 如果计划完成或失败
    if not state.research_plan:
        return END
        
    # 检查是否还有未执行的步骤
    # execute_search_step 节点负责执行后增加 current_step_index
    if state.current_step_index < len(state.research_plan.steps):
        return "execute_step"
    
    # 所有步骤完成（或索引超出范围），生成报告
    return "generate_report"

def check_report_approval(state: ResearchAgentState) -> str:
    """检查报告是否需要审批"""
    if state.status == AgentStatus.ERROR:
        return END
        
    if state.config.require_final_approval:
        return "create_report_approval"
    
    state.complete_research()
    return END

def handle_wait_for_approval(state: ResearchAgentState) -> str:
    """处理等待审批状态，这通常是一个空转或中断点"""
    # 这里的返回值并不重要，因为 graph.compile(interrupt_before=[...]) 会控制中断
    # 但为了图的完整性，我们返回一个虚拟节点
    return "wait_node"


# === 构建图 ===

def build_graph():
    """构建 Research Agent 的 LangGraph"""""
    
    # 创建状态图
    workflow = StateGraph(ResearchAgentState)
    
    # 1. 添加节点
    workflow.add_node("plan_generation", generate_plan)
    workflow.add_node("execute_step", execute_search_step)
    workflow.add_node("generate_report", generate_final_report)
    
    # HITL 节点
    def create_plan_approval_node(state: ResearchAgentState):
        new_state = hitl_manager.create_approval_request(
            state, 
            "plan_approval", 
            {"plan": state.research_plan.dict() if state.research_plan else None}
        )
        # Return full state to ensure persistence of all fields
        return new_state

    def create_report_approval_node(state: ResearchAgentState):
        new_state = hitl_manager.create_approval_request(
            state,
            "final_report_approval",
            {"report_preview": state.final_report[:500] if state.final_report else "No report"}
        )
        # Return full state
        return new_state

    workflow.add_node("create_plan_approval", create_plan_approval_node)
    workflow.add_node("create_report_approval", create_report_approval_node)

    # 添加虚拟等待节点，用于中断
    workflow.add_node("wait_node", lambda x: x)
    
    # 2. 设置入口点
    workflow.set_entry_point("plan_generation")
    
    # 3. 添加边和路由
    
    # 计划生成 -> 条件路由
    workflow.add_conditional_edges(
        "plan_generation",
        should_continue_to_execution,
        {
            "create_plan_approval": "create_plan_approval",
            "execute_step": "execute_step",
            END: END
        }
    )

    # 审批创建节点 -> 等待节点
    workflow.add_edge("create_plan_approval", "wait_node")
    workflow.add_edge("create_report_approval", "wait_node")
    
    # 等待节点 -> 根据状态决定下一步
    # 实际上，这里需要通过外部 update_state 来恢复执行，
    # 但图结构需要连接。恢复时通常直接路由到目标节点。
    # 这里我们简单地连接回检查逻辑
    
    def route_after_wait(state: ResearchAgentState):
        if state.status == AgentStatus.EXECUTING:
            return "execute_step"
        elif state.status == AgentStatus.COMPLETED:
            return END
        elif state.status == AgentStatus.ERROR:
            return END
        return END
        
    workflow.add_conditional_edges(
        "wait_node",
        route_after_wait,
        {
            "execute_step": "execute_step",
            END: END
        }
    )
    
    # 执行步骤 -> 条件路由 (循环或完成)
    workflow.add_conditional_edges(
        "execute_step",
        check_step_completion,
        {
            "execute_step": "execute_step",  # 循环下一在步
            "generate_report": "generate_report",
            END: END
        }
    )
    
    # 生成报告 -> 条件路由 (最终审批)
    workflow.add_conditional_edges(
        "generate_report",
        check_report_approval,
        {
            "create_report_approval": "create_report_approval",
            END: END
        }
    )
    
    # 4. 编译图
    # 使用 MemorySaver 作为简单的检查点存储
    checkpointer = MemorySaver()
    
    # 设置中断点：在进入 'wait_node' 之前中断，等待人工干预
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["wait_node"]
    )
    
    return app

# 提供单例或工厂
agent_app = build_graph()
