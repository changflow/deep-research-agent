"""
Autonomic Context Middleware
Higher-order optimization for Adaptive Context Management
"""

import logging
import os
from typing import Any

from agent_core.middleware.base import BaseMiddleware
from agent_core.core.state import BaseAgentState
from deep_research_agent.state import ResearchAgentState
from deep_research_agent.utils.context_manager import context_manager

logger = logging.getLogger(__name__)

class ContextManagementMiddleware(BaseMiddleware):
    """
    自适应上下文管理中间件
    1. Pre-processing: 根据当前任务步骤，自动检索相关背景知识并注入 Context Buffer
    2. Post-processing: 监控新产生的 Insight，自动进行向量化存储 (Embedding)
    """
    
    async def before_node_execution(self, node_name: str, state: BaseAgentState) -> BaseAgentState:
        # Check if state is ResearchAgentState (or has get_current_step)
        # Note: We use duck typing or direct type check
        if not isinstance(state, ResearchAgentState):
            return state
            
        # Check configuration for Auto-Context (Default: False to prevent timeouts)
        if os.getenv("ENABLE_AUTO_CONTEXT", "false").lower() != "true":
            return state

        step = state.get_current_step()
        if not step:
            return state
            
        # 1. 自动上下文检索 (Context Retrieval)
        try:
            # Construct query from step metadata
            query = f"{step.title} {step.description}"
            
            # Prepare extraction pool
            all_insights = list(state.extracted_insights.values())
            
            # If no history, no context
            if not all_insights:
                return state

            # Retrieve
            # logger.info(f"Middleware: Auto-retrieving context for step '{step.title}'")
            relevant_insights = await context_manager.retrieve(query, all_insights)
            
            # Format
            context_str = context_manager.format_context_string(relevant_insights)
            
            # Inject into state buffer
            state.context_buffer = context_str
            # logger.info(f"Middleware: Injected {len(relevant_insights)} context nuggets")
            
        except Exception as e:
            logger.error(f"Context Middleware Retrieval Failed: {e}")
            state.context_buffer = "Context retrieval failed."
        
        return state

    async def after_node_execution(self, node_name: str, state: BaseAgentState, result: Any) -> BaseAgentState:
        if not isinstance(state, ResearchAgentState):
            return state

        # Check configuration for Auto-Context (Default: False to prevent timeouts)
        if os.getenv("ENABLE_AUTO_CONTEXT", "false").lower() != "true":
            # If manually disabled, ensure we don't leave hanging insights (though not strictly necessary)
            if state.last_generated_insight:
                state.last_generated_insight = None
            return state
            
        # 2. 自动知识存储 (Auto-Embedding & Storage)
        # Check if the node produced a NEW insight
        if state.last_generated_insight:
            insight = state.last_generated_insight
            
            # Use 'embedding' field as a flag to see if it's already embedded
            # (Though in our new architecture, the node won't embed, so it will be None)
            if not insight.embedding:
                try:
                    # logger.info(f"Middleware: Auto-embedding new insight for Step {insight.step_id}")
                    
                    # Construct text for semantic search
                    text_to_embed = f"{insight.content}\n" + "\n".join(insight.nuggets)
                    
                    # Generate vector
                    embedding = await context_manager.get_embedding(text_to_embed)
                    insight.embedding = embedding
                    
                except Exception as e:
                    logger.error(f"Context Middleware Embedding Failed: {e}")
            
            # Cleanup buffer
            state.last_generated_insight = None
            
        return state
