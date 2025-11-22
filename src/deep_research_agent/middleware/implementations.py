"""
中间件具体实现
包含日志、追踪、错误处理、监控等具体的中间件实现
"""

import logging
import time
import json
import hashlib
from typing import Any, Dict, Optional, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..core.state import ResearchAgentState, AgentStatus
from .base import BaseMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """日志中间件 - 记录节点执行的详细日志"""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__("LoggingMiddleware")
        self.log_level = getattr(logging, log_level.upper())
        self._logger.setLevel(self.log_level)
    
    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """记录节点开始执行的日志"""
        self._logger.info(f"🚀 Starting node: {node_name}")
        self._logger.info(f"📊 Session: {state.session_id}, Status: {state.status}")
        
        if state.research_plan:
            current_step = state.get_current_step()
            if current_step:
                self._logger.info(f"📋 Current step: {current_step.title} ({state.current_step_index + 1}/{len(state.research_plan.steps)})")
        
        # 记录执行开始时间到状态中
        state.metadata[f"{node_name}_start_time"] = time.time()
        return state
    
    async def after_node_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        """记录节点执行完成的日志"""
        start_time = state.metadata.get(f"{node_name}_start_time")
        duration = time.time() - start_time if start_time else 0
        
        self._logger.info(f"✅ Completed node: {node_name} (Duration: {duration:.2f}s)")
        self._logger.info(f"📊 New status: {state.status}")
        
        # 记录性能指标
        state.metadata[f"{node_name}_duration"] = duration
        state.metadata[f"{node_name}_completed_at"] = datetime.now().isoformat()
        
        return state
    
    async def on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """记录错误日志"""
        self._logger.error(f"❌ Error in node {node_name}: {type(error).__name__}: {error}")
        
        # 记录错误详情到状态中
        error_info = {
            "node": node_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        if "errors" not in state.metadata:
            state.metadata["errors"] = []
        state.metadata["errors"].append(error_info)
        
        return state


class TracingMiddleware(BaseMiddleware):
    """链路追踪中间件 - 集成 Langfuse 或其他追踪系统"""
    
    def __init__(self, settings=None):
        super().__init__("TracingMiddleware")
        self.langfuse_client = None
        self.enable_langfuse = False
        self.spans = {}  # 存储活跃的 span
        
        try:
            from langfuse import Langfuse
            from ..utils.config import get_settings
            
            self.settings = settings or get_settings()
            
            # 打印配置信息以便调试
            print(f"DEBUG: TracingMiddleware init. PK={self.settings.LANGFUSE_PUBLIC_KEY[:5]}... SK={self.settings.LANGFUSE_SECRET_KEY[:5]}... Host={self.settings.LANGFUSE_HOST}")
            
            # 显式传入配置，确保即使环境变量未设置也能工作
            if self.settings.LANGFUSE_PUBLIC_KEY and self.settings.LANGFUSE_SECRET_KEY:
                self.langfuse_client = Langfuse(
                    public_key=self.settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=self.settings.LANGFUSE_SECRET_KEY,
                    host=self.settings.LANGFUSE_HOST
                )
                # 验证连接
                if self.langfuse_client.auth_check():
                    self._logger.info("Langfuse tracing enabled and authenticated")
                    print("DEBUG: Langfuse authenticated successfully")
                    self.enable_langfuse = True
                else:
                    self._logger.warning("Langfuse authentication failed")
                    print("DEBUG: Langfuse authentication failed")
                    self.enable_langfuse = False
            else:
                self._logger.warning("Langfuse credentials not found in settings, tracing disabled")
                print("DEBUG: Langfuse credentials missing")
                self.enable_langfuse = False
                
        except ImportError:
            self._logger.warning("Langfuse package not installed, tracing disabled")
            print("DEBUG: Langfuse package missing")
            self.enable_langfuse = False
        except Exception as e:
            self._logger.warning(f"Failed to initialize Langfuse: {e}")
            print(f"DEBUG: Langfuse init error: {e}")
            self.enable_langfuse = False
    
    def _get_valid_trace_id(self, trace_id: str) -> str:
        """确保 trace_id 是有效的 32 字符 hex"""
        if not trace_id:
            return hashlib.sha256(str(time.time()).encode()).hexdigest()[:32]
            
        if len(trace_id) == 32 and all(c in '0123456789abcdef' for c in trace_id):
            return trace_id
            
        return hashlib.sha256(trace_id.encode()).hexdigest()[:32]

    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """开始追踪节点执行"""
        # Helper to get attribute from dict or object
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Helper to set attribute to dict or object
        def set_attr(obj, key, value):
            if isinstance(obj, dict):
                obj[key] = value
            else:
                setattr(obj, key, value)

        trace_id = get_attr(state, "trace_id")
        session_id = get_attr(state, "session_id", "unknown")

        if not trace_id:
            self._logger.warning(f"Trace ID missing in state for node {node_name}, generating new one.")
            trace_id = f"research_{session_id}_{int(time.time())}"
            set_attr(state, "trace_id", trace_id)
        else:
            self._logger.debug(f"Using existing trace ID: {trace_id} for node {node_name}")
        
        if self.enable_langfuse and self.langfuse_client:
            try:
                print(f"DEBUG: Creating span for {node_name}")
                # 确保 trace_id 格式正确
                valid_trace_id = self._get_valid_trace_id(trace_id)
                
                # 准备 input 数据
                input_data = None
                try:
                    # 尝试获取 state 的字典表示作为输入
                    if hasattr(state, "dict"):
                        input_data = state.dict()
                    elif hasattr(state, "model_dump"):
                        input_data = state.model_dump()
                    else:
                        input_data = str(state)
                except Exception as e:
                    self._logger.warning(f"Failed to serialize state for input: {e}")
                    input_data = str(state)

                # 创建节点 span (v3 API)
                span = self.langfuse_client.start_span(
                    name=node_name,
                    trace_context={"trace_id": valid_trace_id},
                    input=input_data,
                    metadata={
                        "node_type": "langgraph_node",
                        "status": get_attr(state, "status"),
                        "current_step": get_attr(state, "current_step_index"),
                        "research_query": get_attr(state, "user_query"),
                        "session_id": session_id
                    }
                )
                
                # 更新 trace 信息
                try:
                    config = get_attr(state, "config")
                    config_dict = {}
                    if config:
                        if hasattr(config, "dict"):
                            config_dict = config.dict()
                        elif hasattr(config, "model_dump"):
                            config_dict = config.model_dump()
                        else:
                            config_dict = str(config)

                    span.update_trace(
                        name=f"research_session_{session_id}",
                        user_id=get_attr(state, "user_id"),
                        session_id=session_id,
                        metadata={
                            "config": config_dict
                        }
                    )
                except Exception as e:
                    print(f"DEBUG: Failed to update trace: {e}")
                
                # 保存 span 对象到临时字典
                if not hasattr(self, "_active_spans"):
                    self._active_spans = {}
                
                span_key = f"{session_id}_{node_name}"
                self._active_spans[span_key] = span
                
                # 确保 metadata 存在
                metadata = get_attr(state, "metadata")
                if metadata is None:
                    metadata = {}
                    set_attr(state, "metadata", metadata)
                
                metadata[f"{node_name}_span_key"] = span_key
                # If state is object, we might need to re-assign metadata if it was None
                if not isinstance(state, dict) and get_attr(state, "metadata") is None:
                     set_attr(state, "metadata", metadata)
                
            except Exception as e:
                self._logger.warning(f"Failed to create Langfuse span: {e}")
                print(f"DEBUG: Create span error: {e}")
        
        return state
    
    async def after_node_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        """完成节点追踪"""
        # Helper to get attribute from dict or object
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        if self.enable_langfuse and self.langfuse_client:
            try:
                print(f"DEBUG: Ending span for {node_name}")
                metadata = get_attr(state, "metadata", {})
                span_key = metadata.get(f"{node_name}_span_key")
                
                if span_key and hasattr(self, "_active_spans") and span_key in self._active_spans:
                    span = self._active_spans.pop(span_key)
                    
                    duration = metadata.get(f"{node_name}_duration", 0)
                    
                    # 准备 output 数据
                    output_data = None
                    try:
                        if hasattr(result, "dict"):
                            output_data = result.dict()
                        elif hasattr(result, "model_dump"):
                            output_data = result.model_dump()
                        elif isinstance(result, (dict, list, str, int, float, bool)):
                            output_data = result
                        else:
                            output_data = str(result)
                    except Exception:
                        output_data = str(result)

                    # 更新并结束 span
                    span.update(
                        output=output_data,
                        metadata={
                            "duration": duration,
                            "output_status": get_attr(state, "status"),
                            "success": True
                        }
                    )
                    span.end()
                    
                    # 强制 flush 以确保数据发送 (调试用)
                    self.langfuse_client.flush()
                    print(f"DEBUG: Span ended and flushed for {node_name}")
                else:
                    print(f"DEBUG: Span key not found for {node_name}")
                    
            except Exception as e:
                self._logger.warning(f"Failed to update Langfuse span: {e}")
                print(f"DEBUG: End span error: {e}")
        
        return state
    
    async def on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """记录错误到追踪系统"""
        # Helper to get attribute from dict or object
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        if self.enable_langfuse and self.langfuse_client:
            try:
                metadata = get_attr(state, "metadata", {})
                span_key = metadata.get(f"{node_name}_span_key")
                if span_key and hasattr(self, "_active_spans") and span_key in self._active_spans:
                    span = self._active_spans.pop(span_key)
                    
                    span.update(
                        level="ERROR",
                        status_message=str(error),
                        metadata={
                            "error": True,
                            "error_type": type(error).__name__,
                            "error_message": str(error)
                        }
                    )
                    span.end()
                    self.langfuse_client.flush()
                    
            except Exception as e:
                self._logger.warning(f"Failed to record error in Langfuse: {e}")
        
        return state

    def flush(self):
        """强制发送所有追踪数据"""
        if self.enable_langfuse and self.langfuse_client:
            try:
                self._logger.info("Flushing Langfuse traces...")
                self.langfuse_client.flush()
                self._logger.info("Langfuse traces flushed")
            except Exception as e:
                self._logger.warning(f"Failed to flush Langfuse traces: {e}")


class ErrorHandlerMiddleware(BaseMiddleware):
    """错误处理中间件 - 统一异常处理和重试机制"""
    
    def __init__(self, max_retries: int = 3, enable_recovery: bool = True):
        super().__init__("ErrorHandlerMiddleware")
        self.max_retries = max_retries
        self.enable_recovery = enable_recovery
    
    async def on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """处理节点执行错误"""
        self._logger.error(f"Handling error in {node_name}: {error}")
        
        error_category = self._classify_error(error)
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        if error_category == "retryable" and state["retry_count"] <= self.max_retries:
            self._logger.info(f"Error is retryable, attempt {state['retry_count']}/{self.max_retries}")
            # 不设置错误状态，让系统重试
            return state
        elif error_category == "recoverable" and self.enable_recovery:
            self._logger.info(f"Attempting error recovery for {node_name}")
            return await self._attempt_recovery(node_name, state, error)
        else:
            # 致命错误或重试次数超限
            self._logger.error(f"Fatal error or max retries exceeded in {node_name}")
            # state.set_error(f"Node {node_name} failed: {error}") # ResearchAgentState is TypedDict, no methods
            state["error"] = f"Node {node_name} failed: {error}"
            return state
    
    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        # 网络相关错误 - 可重试
        if isinstance(error, (ConnectionError, TimeoutError)):
            return "retryable"
        
        # API 限流错误 - 可重试
        if "rate limit" in str(error).lower() or "429" in str(error):
            return "retryable"
        
        # 临时服务不可用 - 可重试
        if "502" in str(error) or "503" in str(error) or "504" in str(error):
            return "retryable"
        
        # 数据格式错误等 - 可恢复
        if isinstance(error, (ValueError, KeyError, AttributeError)):
            return "recoverable"
        
        # 其他错误 - 致命
        return "fatal"
    
    async def _attempt_recovery(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """尝试从错误中恢复"""
        self._logger.info(f"Attempting recovery for {node_name}")
        
        # 根据不同的节点类型实施不同的恢复策略
        if node_name == "search_execution":
            # 搜索失败：跳过当前搜索，使用缓存结果或继续下一步
            self._logger.info("Search failed, attempting to continue with cached results")
            # current_step = state.get_current_step() # TypedDict has no methods
            # if current_step:
            #     current_step.error_message = str(error)
            #     # 不标记为失败，而是部分完成
            #     return state
            pass
        
        elif node_name == "plan_generation":
            # 计划生成失败：使用默认模板
            self._logger.info("Plan generation failed, using fallback template")
            # 这里可以实现默认计划逻辑
            pass
        
        # 默认恢复：记录错误但继续执行
        if "metadata" not in state:
            state["metadata"] = {}
        
        if "recovery_attempts" not in state["metadata"]:
            state["metadata"]["recovery_attempts"] = []
            
        state["metadata"]["recovery_attempts"].append({
            "node": node_name,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        })
        
        return state


class PerformanceMiddleware(BaseMiddleware):
    """性能监控中间件 - 收集性能指标"""
    
    def __init__(self):
        super().__init__("PerformanceMiddleware")
        self.metrics = {}
    
    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """开始性能监控"""
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"][f"{node_name}_perf_start"] = time.perf_counter()
        state["metadata"][f"{node_name}_memory_before"] = self._get_memory_usage()
        return state
    
    async def after_node_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        """收集性能指标"""
        start_time = state.get("metadata", {}).get(f"{node_name}_perf_start")
        if start_time:
            duration = time.perf_counter() - start_time
            memory_after = self._get_memory_usage()
            memory_before = state.get("metadata", {}).get(f"{node_name}_memory_before", 0)
            
            # 记录指标
            metrics = {
                "node": node_name,
                "duration_ms": duration * 1000,
                "memory_delta_mb": memory_after - memory_before,
                "timestamp": datetime.now().isoformat()
            }
            
            # 保存到状态
            if "performance_metrics" not in state["metadata"]:
                state["metadata"]["performance_metrics"] = []
            state["metadata"]["performance_metrics"].append(metrics)
            
            # 记录到类实例（可选，用于聚合分析）
            if node_name not in self.metrics:
                self.metrics[node_name] = []
            self.metrics[node_name].append(metrics)
            
            self._logger.info(f"⚡ {node_name} performance: {duration*1000:.1f}ms, Memory: {memory_after - memory_before:.1f}MB")
        
        return state
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {}
        for node_name, metrics_list in self.metrics.items():
            if metrics_list:
                durations = [m["duration_ms"] for m in metrics_list]
                summary[node_name] = {
                    "count": len(durations),
                    "avg_duration_ms": sum(durations) / len(durations),
                    "max_duration_ms": max(durations),
                    "min_duration_ms": min(durations)
                }
        return summary


class ContextMiddleware(BaseMiddleware):
    """上下文中间件 - 注入和管理执行上下文"""
    
    def __init__(self, context_data: Dict[str, Any] = None):
        super().__init__("ContextMiddleware")
        self.context_data = context_data or {}
    
    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """注入执行上下文"""
        # 添加全局上下文
        context = {
            "execution_id": f"{node_name}_{int(time.time())}",
            "node_name": node_name,
            "session_id": state.get("session_id"),
            "timestamp": datetime.now().isoformat(),
            **self.context_data
        }
        
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"][f"{node_name}_context"] = context
        return state
    
    def set_context(self, key: str, value: Any) -> None:
        """设置上下文数据"""
        self.context_data[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self.context_data.get(key, default)

def register_global_middlewares(middlewares: List[BaseMiddleware] = None):
    """Register global middleware"""
    from .base import middleware_manager
    
    # Clear existing to avoid duplicates on reload
    middleware_manager.clear()
    
    if middlewares:
        for mw in middlewares:
            middleware_manager.register(mw)
    else:
        # Default middlewares if none provided
        middleware_manager.register(LoggingMiddleware())
        middleware_manager.register(ErrorHandlerMiddleware())
        middleware_manager.register(PerformanceMiddleware())
