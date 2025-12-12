"""
通用中间件实现
提供常用的中间件，如日志记录、错误处理、性能监控等
"""

import logging
import json
from typing import Any, Dict, Set
from .base import BaseMiddleware, ConditionalMiddleware
from ..core.state import BaseAgentState, AgentStatus
from ..utils.config import get_settings

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    """日志中间件"""
    
    async def before_node_execution(self, node_name: str, state: BaseAgentState) -> BaseAgentState:
        logger.info(f"==> Entering Node: {node_name}")
        return state
    
    async def after_node_execution(self, node_name: str, state: BaseAgentState, result: Any) -> BaseAgentState:
        logger.info(f"<== Exiting Node: {node_name}")
        return state
        
class RecursionCircuitBreaker(BaseMiddleware):
    """递归熔断器 (Recursion Circuit Breaker)"""
    
    def __init__(self, max_depth: int = 5, name: str = None):
        super().__init__(name)
        self.max_depth = max_depth

    async def before_node_execution(self, node_name: str, state: BaseAgentState) -> BaseAgentState:
        # Check if state has 'get_current_step' (Duck typing for ResearchAgentState)
        if hasattr(state, "get_current_step") and callable(state.get_current_step):
            current_step = state.get_current_step()
            if current_step and hasattr(current_step, "depth"):
                if current_step.depth > self.max_depth:
                    msg = f"Recursion Circuit Broken: Step depth {current_step.depth} exceeds limit {self.max_depth}"
                    logger.error(msg)
                    # We can set error or just let it pass (logic node might handle it)
                    # For safety, we enforce it here.
                    raise RuntimeError(msg)
        
        # Also check generic recursion_depth if available
        elif hasattr(state, "recursion_depth") and hasattr(state, "max_recursion_depth"):
             if state.recursion_depth > state.max_recursion_depth:
                msg = f"Recursion limit exceeded: depth {state.recursion_depth}"
                raise RuntimeError(msg)

        return state

    async def after_node_execution(self, node_name: str, state: BaseAgentState, result: Any) -> BaseAgentState:
        return state

class ErrorHandlerMiddleware(BaseMiddleware):
    """错误处理中间件"""
    
    async def on_error(self, node_name: str, state: BaseAgentState, error: Exception) -> BaseAgentState:
        logger.error(f"Captured error in {node_name}: {str(error)}")
        state.set_error(f"Error in {node_name}: {str(error)}")
        return state

try:
    from langfuse import Langfuse
    # Try importing observe from top-level (newer SDK versions) or decorators (older)
    try:
        from langfuse import observe
    except ImportError:
        from langfuse.decorators import observe
    
    class LangfuseMiddleware(BaseMiddleware):
        """
        Langfuse 可观测性中间件
        为每个节点执行创建 Trace Span
        """

        def __init__(self):
            super().__init__()
            try:
                settings = get_settings()
                # 显式传递配置以提高不同环境下的稳定性
                self.langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
                self._spans: Dict[str, Any] = {}
                self._initialized_traces: Set[str] = set()
                logger.info("Langfuse middleware initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.langfuse = None

        def _should_trace(self, state: BaseAgentState) -> bool:
            if not self.langfuse:
                return False

            config = getattr(state, "config", None)
            return bool(getattr(config, "enable_tracing", False))

        def _snapshot_state(self, state: BaseAgentState) -> Dict[str, Any]:
            try:
                return state.dict(exclude={"config", "metadata"})
            except Exception:
                return {
                    "status": getattr(state, "status", None),
                    "current_step": getattr(state, "current_step_index", None),
                }

        def _serialize_result(self, result: Any) -> Any:
            if result is None:
                return None
            if isinstance(result, (str, int, float, bool)):
                return result
            if isinstance(result, (dict, list)):
                return result
            if hasattr(result, "dict"):
                try:
                    return result.dict()
                except Exception:
                    pass
            return repr(result)

        async def before_node_execution(self, node_name: str, state: BaseAgentState) -> BaseAgentState:
            if not self._should_trace(state):
                return state

            try:
                trace_name = f"Agent-Run-{state.session_id}"
                trace_id = state.trace_id or self.langfuse.create_trace_id()

                span = self.langfuse.start_span(
                    trace_context={"trace_id": trace_id},
                    name=f"Node: {node_name}",
                    input=self._snapshot_state(state),
                    metadata={"node": node_name, "session_id": state.session_id},
                )

                state.trace_id = span.trace_id

                if span.trace_id not in self._initialized_traces:
                    span.update_trace(
                        name=trace_name,
                        session_id=state.session_id,
                        user_id=getattr(state, "user_id", None),
                        metadata={"entry_node": node_name},
                    )
                    self._initialized_traces.add(span.trace_id)

                key = f"{state.session_id}_{node_name}"
                self._spans[key] = span

            except Exception as e:
                logger.error(f"Langfuse before_node_execution error: {e}")

            return state

        async def after_node_execution(self, node_name: str, state: BaseAgentState, result: Any) -> BaseAgentState:
            if not self.langfuse:
                return state

            key = f"{state.session_id}_{node_name}"
            span = self._spans.pop(key, None)

            if span:
                try:
                    span.update(
                        output={
                            "state": self._snapshot_state(state),
                            "result": self._serialize_result(result),
                        }
                    )
                    span.end()
                except Exception as e:
                    logger.error(f"Langfuse span end error: {e}")

            return state

        async def on_error(self, node_name: str, state: BaseAgentState, error: Exception) -> BaseAgentState:
            if not self.langfuse:
                return state

            key = f"{state.session_id}_{node_name}"
            span = self._spans.pop(key, None)

            if span:
                try:
                    span.update(
                        level="ERROR",
                        status_message=str(error),
                        metadata={"error": str(error)},
                    )
                    span.end()
                except Exception as e:
                    logger.error(f"Langfuse span error handling failed: {e}")

            return state

except ImportError as e:
    class LangfuseMiddleware(BaseMiddleware):
        """Stub implementation if langfuse is not installed"""
        pass
    logger.warning(f"Langfuse import failed: {e}. Tracing disabled.")
