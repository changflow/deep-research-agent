"""
中间件基础定义
实现 AOP 切面编程模式，为 LangGraph 节点提供统一的横切关注点处理
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, List
import functools
import asyncio
import logging
from datetime import datetime

from ..core.state import ResearchAgentState

logger = logging.getLogger(__name__)


class Middleware(ABC):
    """中间件基类"""
    
    @abstractmethod
    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """节点执行前的处理"""
        pass
    
    @abstractmethod
    async def after_node_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        """节点执行后的处理"""
        pass
    
    @abstractmethod
    async def on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """错误处理"""
        pass


class MiddlewareManager:
    """中间件管理器 - AOP 切面编程的核心实现"""
    
    def __init__(self):
        self.middlewares: List[Middleware] = []
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def register(self, middleware: Middleware) -> None:
        """注册中间件"""
        self.middlewares.append(middleware)
        self._logger.info(f"Registered middleware: {middleware.__class__.__name__}")
    
    def register_multiple(self, middlewares: List[Middleware]) -> None:
        """批量注册中间件"""
        for middleware in middlewares:
            self.register(middleware)
    
    def clear(self) -> None:
        """清除所有中间件"""
        self.middlewares = []
        self._logger.info("Cleared all middlewares")

    def wrap_node(self, node_func: Callable) -> Callable:
        """装饰器：为 LangGraph 节点添加中间件支持"""
        
        @functools.wraps(node_func)
        async def wrapped_node(state: ResearchAgentState) -> ResearchAgentState:
            node_name = node_func.__name__
            execution_id = f"{node_name}_{datetime.now().timestamp()}"
            
            self._logger.debug(f"Starting node execution: {node_name} [{execution_id}]")
            
            try:
                # Before 钩子 - 按注册顺序执行
                for middleware in self.middlewares:
                    try:
                        state = await middleware.before_node_execution(node_name, state)
                    except Exception as e:
                        self._logger.error(f"Middleware {middleware.__class__.__name__} before_node_execution failed: {e}")
                        # 中间件错误不应该中断执行，但要记录
                        continue
                
                # 执行原始节点逻辑
                self._logger.debug(f"Executing node logic: {node_name}")
                result_state = await node_func(state)
                
                # After 钩子 - 按注册顺序执行
                for middleware in self.middlewares:
                    try:
                        result_state = await middleware.after_node_execution(node_name, result_state, result_state)
                    except Exception as e:
                        self._logger.error(f"Middleware {middleware.__class__.__name__} after_node_execution failed: {e}")
                        continue
                
                self._logger.debug(f"Node execution completed successfully: {node_name} [{execution_id}]")
                return result_state
                
            except Exception as e:
                self._logger.error(f"Node execution failed: {node_name} [{execution_id}] - {e}")
                
                # Error 钩子 - 按注册顺序执行
                for middleware in self.middlewares:
                    try:
                        state = await middleware.on_error(node_name, state, e)
                    except Exception as middleware_error:
                        self._logger.error(f"Middleware {middleware.__class__.__name__} on_error failed: {middleware_error}")
                        continue
                
                # 重新抛出原始异常
                raise e
        
        return wrapped_node
    
    def wrap_async_function(self, func: Callable) -> Callable:
        """为任意异步函数添加中间件支持"""
        return self.wrap_node(func)


class BaseMiddleware(Middleware):
    """基础中间件实现，提供默认的空实现"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self._logger = logging.getLogger(self.name)
    
    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """默认的前置处理 - 空实现"""
        return state
    
    async def after_node_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        """默认的后置处理 - 空实现"""
        return state
    
    async def on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """默认的错误处理 - 记录错误但不修改状态"""
        self._logger.error(f"Error in node {node_name}: {error}")
        return state


class ConditionalMiddleware(BaseMiddleware):
    """条件中间件 - 根据条件决定是否执行"""
    
    def __init__(self, condition: Callable[[str, ResearchAgentState], bool], name: str = None):
        super().__init__(name)
        self.condition = condition
    
    async def before_node_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        if self.condition(node_name, state):
            return await self._conditional_before_execution(node_name, state)
        return state
    
    async def after_node_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        if self.condition(node_name, state):
            return await self._conditional_after_execution(node_name, state, result)
        return state
    
    async def on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        if self.condition(node_name, state):
            return await self._conditional_on_error(node_name, state, error)
        return state
    
    async def _conditional_before_execution(self, node_name: str, state: ResearchAgentState) -> ResearchAgentState:
        """条件满足时的前置处理"""
        return state
    
    async def _conditional_after_execution(self, node_name: str, state: ResearchAgentState, result: Any) -> ResearchAgentState:
        """条件满足时的后置处理"""
        return state
    
    async def _conditional_on_error(self, node_name: str, state: ResearchAgentState, error: Exception) -> ResearchAgentState:
        """条件满足时的错误处理"""
        return state


# 全局中间件管理器实例
middleware_manager = MiddlewareManager()

# Alias for backward compatibility if needed
global_middleware_manager = middleware_manager


def middleware_enabled(func: Callable) -> Callable:
    """装饰器：为函数启用全局中间件"""
    return middleware_manager.wrap_node(func)


def register_global_middleware(middleware: Middleware) -> None:
    """注册全局中间件"""
    middleware_manager.register(middleware)


def register_global_middlewares_func(middlewares: List[Middleware]) -> None:
    """批量注册全局中间件"""
    middleware_manager.register_multiple(middlewares)
