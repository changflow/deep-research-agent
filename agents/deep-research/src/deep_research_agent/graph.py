"""
LangGraph 流程定义
构建和编排所有节点的执行流程
"""

import logging
import operator
from typing import Annotated, Sequence, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from deep_research_agent.state import ResearchAgentState, AgentStatus
from .nodes.plan_generation import generate_plan
from .nodes.search_execution import execute_task_node
from .nodes.result_evaluation import evaluate_task_result
from .nodes.report_generation import generate_final_report
from .nodes.hitl_handlers import handle_plan_feedback, handle_report_feedback
from agent_core.core.hitl import hitl_manager
from agent_core.core.orchestrator import FractalGraphBuilder
from agent_core.middleware.base import register_global_middleware, middleware_manager
from agent_core.middleware.implementations import RecursionCircuitBreaker as CircuitBreakerMiddleware, LangfuseMiddleware
from deep_research_agent.middleware.context import ContextManagementMiddleware

logger = logging.getLogger(__name__)

# Register HITL handlers
hitl_manager.register_handler("plan_approval", handle_plan_feedback)
hitl_manager.register_handler("final_report_approval", handle_report_feedback)

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
    # execute_task_node 节点负责执行后增加 current_step_index
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
    
    # === 初始化中间件 ===
    # 清除旧的中间件防止重复注册
    middleware_manager.clear()
    
    # 注册 Circuit Breaker (防止递归/死循环)
    register_global_middleware(CircuitBreakerMiddleware(max_depth=5)) # 设定最大递归深度
    
    # 注册 Langfuse (可观测性)
    # 这一步依赖环境变量 LANGFUSE_PUBLIC_KEY 等配置，如果未配置会自动跳过记录
    register_global_middleware(LangfuseMiddleware())
    
    # 注册自适应上下文中间件 (Adaptive Context)
    register_global_middleware(ContextManagementMiddleware(name="DeepContextMiddleware"))
    
    logger.info("Global middlewares registered: CircuitBreaker, Langfuse, ContextMiddleware")

    # 使用 FractalGraphBuilder 构建分形图
    # 这确保了代理遵循标准的 P-E-E (Plan-Execute-Evaluate) 架构范式
    builder = FractalGraphBuilder(ResearchAgentState)
    
    # 1. 添加核心节点 (Plan, Execute, Evaluate)
    builder.add_plan_node(generate_plan, "plan_generation")
    builder.add_execute_node(execute_task_node, "execute_step")
    builder.add_evaluate_node(evaluate_task_result, "evaluate_step")
    
    # 获取底层 workflow 以添加自定义节点和边缘
    workflow = builder.workflow
    
    # 添加自定义节点 (需要手动 wrap 以启用中间件)
    workflow.add_node("generate_report", middleware_manager.wrap_node(generate_final_report))
    
    # HITL 节点
    async def create_plan_approval_node(state: ResearchAgentState):
        new_state = hitl_manager.create_approval_request(
            state, 
            "plan_approval", 
            {"plan": state.research_plan.dict() if state.research_plan else None}
        )
        # Return full state to ensure persistence of all fields
        return new_state

    async def create_report_approval_node(state: ResearchAgentState):
        new_state = hitl_manager.create_approval_request(
            state,
            "final_report_approval",
            {"report_preview": state.final_report[:500] if state.final_report else "No report"}
        )
        # Return full state
        return new_state

    # 包装 HITL 节点
    workflow.add_node("create_plan_approval", middleware_manager.wrap_node(create_plan_approval_node))
    workflow.add_node("create_report_approval", middleware_manager.wrap_node(create_report_approval_node))

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
        try:
            logger.info(f"Routing after wait. Current status: {state.status}")
            if state.status == AgentStatus.EXECUTING:
                logger.info("Routing to: execute_step")
                return "execute_step"
            elif state.status == AgentStatus.PLANNING:
                logger.info("Routing to: plan_generation")
                return "plan_generation"
            elif state.status == AgentStatus.COMPLETED:
                return END
            elif state.status == AgentStatus.ERROR:
                return END
            return END
        except Exception as e:
            logger.error(f"Error in route_after_wait: {e}")
            return END
        
    workflow.add_conditional_edges(
        "wait_node",
        route_after_wait,
        {
            "execute_step": "execute_step",
            "plan_generation": "plan_generation",
            END: END
        }
    )
    
    # 执行步骤 -> 结果评估
    workflow.add_edge("execute_step", "evaluate_step")

    # 结果评估 -> 条件路由 (循环或完成)
    # evaluate_step 负责决定是否添加新步骤，并增加 current_step_index
    workflow.add_conditional_edges(
        "evaluate_step",
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
