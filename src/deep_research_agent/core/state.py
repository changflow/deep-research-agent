"""
核心状态模型定义
定义了 LangGraph 状态机的所有状态对象和数据模型
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


class ResearchStepStatus(str, Enum):
    """研究步骤状态枚举"""
    PENDING = "pending"
    EXECUTING = "executing" 
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, Enum):
    """Agent 状态枚举"""
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    EXECUTING = "executing"
    FINAL_REVIEW = "final_review"
    COMPLETED = "completed"
    ERROR = "error"


class ResearchStep(BaseModel):
    """研究步骤定义"""
    step_id: str
    title: str
    description: str
    keywords: List[str]
    expected_output: str
    status: ResearchStepStatus = ResearchStepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        use_enum_values = True


class ResearchPlan(BaseModel):
    """研究计划"""
    topic: str
    objective: str
    steps: List[ResearchStep]
    estimated_duration_minutes: int
    created_at: datetime = Field(default_factory=datetime.now)
    user_modified: bool = False
    modification_notes: Optional[str] = None
    
    def get_current_step(self, current_index: int) -> Optional[ResearchStep]:
        """获取当前执行的步骤"""
        if 0 <= current_index < len(self.steps):
            return self.steps[current_index]
        return None
    
    def is_completed(self) -> bool:
        """检查所有步骤是否已完成"""
        return all(step.status == ResearchStepStatus.COMPLETED for step in self.steps)


class AgentConfiguration(BaseModel):
    """Agent 运行时配置"""
    # 搜索配置
    max_search_iterations: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_MAX_SEARCH_ITERATIONS", "5")))
    max_sources_per_step: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_MAX_SOURCES_PER_STEP", "10")))
    search_timeout_seconds: int = 30
    
    # 审批配置
    require_plan_approval: bool = True
    require_final_approval: bool = False
    
    # 系统配置
    auto_save_checkpoints: bool = True
    max_retry_attempts: int = 3
    
    # 集成配置
    langfuse_project: str = Field(default_factory=lambda: os.getenv("LANGFUSE_PROJECT", "deep-research-agent"))
    enable_tracing: bool = True
    
    # LLM 配置
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4"))
    llm_temperature: float = 0.7
    max_tokens: int = 4000


class SearchResult(BaseModel):
    """搜索结果"""
    url: str
    title: str
    content: str
    snippet: str
    score: float = 0.0
    source: str = "tavily"  # 搜索源
    retrieved_at: datetime = Field(default_factory=datetime.now)


class ExtractedInsight(BaseModel):
    """提取的洞察"""
    step_id: str
    content: str
    sources: List[str]
    confidence: float = 0.0
    extracted_at: datetime = Field(default_factory=datetime.now)


class HITLEvent(BaseModel):
    """Human-in-the-Loop 事件"""
    event_type: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: Dict[str, Any]
    requires_response: bool = True


class ResearchAgentState(BaseModel):
    """LangGraph 状态对象 - 系统的核心状态"""
    
    # === 输入与配置 ===
    user_query: str
    config: AgentConfiguration
    session_id: str
    user_id: Optional[str] = None
    
    # === 计划与执行 ===
    research_plan: Optional[ResearchPlan] = None
    current_step_index: int = 0
    
    # === 搜索和分析结果 ===
    search_results: Dict[str, List[SearchResult]] = Field(default_factory=dict)
    extracted_insights: Dict[str, ExtractedInsight] = Field(default_factory=dict)
    
    # === 状态控制 ===
    status: AgentStatus = AgentStatus.PLANNING
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # === 人工交互 ===
    human_feedback: Optional[Dict[str, Any]] = None
    pending_hitl_event: Optional[HITLEvent] = None
    
    # === 输出 ===
    final_report: Optional[str] = None
    
    # === 元数据和追踪 ===
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
    
    def add_search_result(self, step_id: str, result: SearchResult) -> None:
        """添加搜索结果"""
        if step_id not in self.search_results:
            self.search_results[step_id] = []
        self.search_results[step_id].append(result)
    
    def add_insight(self, insight: ExtractedInsight) -> None:
        """添加提取的洞察"""
        self.extracted_insights[insight.step_id] = insight
    
    def get_current_step(self) -> Optional[ResearchStep]:
        """获取当前执行的研究步骤"""
        if self.research_plan:
            return self.research_plan.get_current_step(self.current_step_index)
        return None
    
    def move_to_next_step(self) -> bool:
        """移动到下一个研究步骤"""
        if self.research_plan and self.current_step_index < len(self.research_plan.steps) - 1:
            self.current_step_index += 1
            return True
        return False
    
    def is_plan_completed(self) -> bool:
        """检查研究计划是否已完成"""
        return self.research_plan is not None and self.research_plan.is_completed()
    
    def set_error(self, error_message: str) -> None:
        """设置错误状态"""
        self.status = AgentStatus.ERROR
        self.error_message = error_message
        self.end_time = datetime.now()
    
    def complete_research(self) -> None:
        """完成研究"""
        self.status = AgentStatus.COMPLETED
        self.end_time = datetime.now()


# === 工厂函数 ===

def create_agent_state(
    user_query: str,
    session_id: str,
    config: Optional[AgentConfiguration] = None,
    user_id: Optional[str] = None
) -> ResearchAgentState:
    """创建新的 Agent 状态"""
    if config is None:
        # Load defaults from environment variables
        config = AgentConfiguration(
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            max_search_iterations=int(os.getenv("MAX_SEARCH_ITERATIONS", "5")),
            max_sources_per_step=int(os.getenv("MAX_SOURCES_PER_STEP", "10")),
            langfuse_project=os.getenv("LANGFUSE_PROJECT", "deep-research-agent"),
            enable_tracing=os.getenv("ENABLE_TRACING", "True").lower() == "true",
        )
    
    return ResearchAgentState(
        user_query=user_query,
        session_id=session_id,
        config=config,
        user_id=user_id,
        trace_id=f"research_{session_id}_{int(datetime.now().timestamp())}",
        search_results={},
        extracted_insights={}
    )


def create_research_step(
    step_id: str,
    title: str,
    description: str,
    keywords: List[str],
    expected_output: str
) -> ResearchStep:
    """创建研究步骤"""
    return ResearchStep(
        step_id=step_id,
        title=title,
        description=description,
        keywords=keywords,
        expected_output=expected_output
    )
