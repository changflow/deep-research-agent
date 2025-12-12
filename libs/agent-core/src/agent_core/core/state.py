"""
核心状态模型定义
定义了 Agent 框架的基础状态对象和数据模型 (Generic Core)
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from enum import Enum
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root relative to this file
env_path = Path(__file__).parents[3] / ".env"
load_dotenv(dotenv_path=env_path, override=True)


class AgentStatus(str, Enum):
    """Agent 状态枚举"""
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    EXECUTING = "executing"
    FINAL_REVIEW = "final_review"
    COMPLETED = "completed"
    ERROR = "error"


class BaseAgentConfiguration(BaseModel):
    """基础 Agent 运行时配置"""
    # 系统配置
    auto_save_checkpoints: bool = True
    max_retry_attempts: int = 3
    
    # 集成配置
    langfuse_project: str = Field(default_factory=lambda: os.getenv("LANGFUSE_PROJECT", "default-project"))
    enable_tracing: bool = True
    
    # LLM 配置
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4"))
    llm_temperature: float = 0.7
    max_tokens: int = 4000


class HITLEvent(BaseModel):
    """Human-in-the-Loop 事件"""
    event_type: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: Dict[str, Any]
    requires_response: bool = True


class BaseAgentState(BaseModel):
    """LangGraph 基础状态对象"""
    
    # === 输入与配置 ===
    user_query: str
    config: BaseAgentConfiguration
    session_id: str
    user_id: Optional[str] = None
    
    # === 状态控制 ===
    status: AgentStatus = AgentStatus.PLANNING
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # === 递归控制 ===
    recursion_depth: int = 0
    max_recursion_depth: int = 5  # 默认最大递归深度
    visited_states: List[str] = Field(default_factory=list) # 用于循环检测

    # === 人工交互 ===
    human_feedback: Optional[Dict[str, Any]] = None
    pending_hitl_event: Optional[HITLEvent] = None
    
    # === 元数据和追踪 ===
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
    
    def set_error(self, error_message: str) -> None:
        """设置错误状态"""
        self.status = AgentStatus.ERROR
        self.error_message = error_message
        self.end_time = datetime.now()
    
    def complete(self) -> None:
        """完成任务"""
        self.status = AgentStatus.COMPLETED
        self.end_time = datetime.now()
