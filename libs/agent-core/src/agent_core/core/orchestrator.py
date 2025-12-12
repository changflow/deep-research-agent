"""
分形编排器构建工具 (Fractal Orchestrator)
"""

from typing import Callable, Type, Optional, Any
from langgraph.graph import StateGraph, END
from .state import BaseAgentState, AgentStatus
from ..middleware.base import middleware_manager

class FractalGraphBuilder:
    """
    分形图构建器
    构建标准的 Plan -> Execute -> Evaluate 递归循环
    """
    
    def __init__(self, state_schema: Type[BaseAgentState]):
        self.workflow = StateGraph(state_schema)
        self._nodes = {}

    def add_plan_node(self, node_func: Callable, name: str = "plan_node"):
        wrapped_func = middleware_manager.wrap_node(node_func)
        self.workflow.add_node(name, wrapped_func)
        self._nodes["plan"] = name
        return self

    def add_execute_node(self, node_func: Callable, name: str = "execute_node"):
        wrapped_func = middleware_manager.wrap_node(node_func)
        self.workflow.add_node(name, wrapped_func)
        self._nodes["execute"] = name
        return self

    def add_evaluate_node(self, node_func: Callable, name: str = "evaluate_node"):
        wrapped_func = middleware_manager.wrap_node(node_func)
        self.workflow.add_node(name, wrapped_func)
        self._nodes["evaluate"] = name
        return self
        
    def add_hitl_node(self, node_func: Callable, name: str = "hitl_node"):
        wrapped_func = middleware_manager.wrap_node(node_func)
        self.workflow.add_node(name, wrapped_func)
        self._nodes["hitl"] = name
        return self

    def compile(self, checkpointer: Optional[Any] = None) -> Any:
        # 定义标准边
        plan = self._nodes.get("plan")
        execute = self._nodes.get("execute")
        evaluate = self._nodes.get("evaluate")
        hitl = self._nodes.get("hitl")
        
        if not (plan and execute and evaluate):
            raise ValueError("Must provide at least plan, execute, and evaluate nodes")

        # 入口
        if hitl:
            self.workflow.set_entry_point(hitl)
            # HITL -> Plan (Initial) or HITL -> Execute or HITL -> END
            # 这里需要一个路由逻辑，通常 HITL 后面是 Plan Review
            # 简化版：我们假设 HITL 只在 Plan 生成后起作用，或者初始需要确认
            # 但实际上 Deep Research 的图比较复杂。
            # 为了通用性，我们先不强制连线，而是要求用户自己 define edges?
            # 不，Builder 的目的是标准化 Edge。
            
            # 标准循环：
            # Start -> Plan -> HITL(Review) -> Execute -> Evaluate -> (Loop back to Plan or End)
            pass
        else:
            self.workflow.set_entry_point(plan)

        # 默认使用 Conditional Edges 的逻辑需要在 Node 内部处理，
        # 或者在这里提供 standardized router
        
        # 由于 LangGraph 的 Edge 逻辑通常依赖于 State 的具体值，
        # 通用的 Builder 很难替用户写 router。
        # 所以这个 Builder 目前主要作为 Node 容器。
        # 我们可以提供一个 helper method `build_standard_loop`
        return self.workflow

    def build_standard_loop(
        self, 
        plan_node: str, 
        execute_node: str, 
        evaluate_node: str, 
        router_func: Callable,
        hitl_node: Optional[str] = None
    ):
        """
        构建标准的 P-E-E 循环
        Plan -> (HITL) -> Execute -> Evaluate -> (Router) -> [Plan, End]
        """
        self.workflow.set_entry_point(plan_node)
        
        if hitl_node:
            self.workflow.add_edge(plan_node, hitl_node)
            self.workflow.add_edge(hitl_node, execute_node)
        else:
            self.workflow.add_edge(plan_node, execute_node)
            
        self.workflow.add_edge(execute_node, evaluate_node)
        
        self.workflow.add_conditional_edges(
            evaluate_node,
            router_func,
            {
                "continue": plan_node,
                "end": END,
                "loop": execute_node # 此处逻辑视 Evaluate 结果而定
            }
        )
        
        return self.workflow
