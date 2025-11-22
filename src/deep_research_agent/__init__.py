"""
Deep Research Agent
基于 LangGraph + LLM 的智能研究助手
"""

from .core.state import ResearchAgentState, AgentConfiguration, AgentStatus
from .graph import agent_app
from .app import app

__version__ = "0.1.0"
__all__ = ["ResearchAgentState", "AgentConfiguration", "AgentStatus", "agent_app", "app"]
