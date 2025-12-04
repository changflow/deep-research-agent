"""
Deep Research Agent specific state definitions.
Inherits from generic agent-core state.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import os

from agent_core.core.state import BaseAgentState, BaseAgentConfiguration, AgentStatus, HITLEvent

class ResearchStepStatus(str, Enum):
    """Research step status enum"""
    PENDING = "pending"
    EXECUTING = "executing" 
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchStep(BaseModel):
    """Research step definition"""
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
    """Research plan"""
    topic: str
    objective: str
    steps: List[ResearchStep]
    estimated_duration_minutes: int
    created_at: datetime = Field(default_factory=datetime.now)
    user_modified: bool = False
    modification_notes: Optional[str] = None
    
    def get_current_step(self, current_index: int) -> Optional[ResearchStep]:
        if 0 <= current_index < len(self.steps):
            return self.steps[current_index]
        return None
    
    def is_completed(self) -> bool:
        return all(step.status == ResearchStepStatus.COMPLETED for step in self.steps)

class ResearchConfig(BaseAgentConfiguration):
    """Deep Research Agent Configuration"""
    # Search config
    max_search_iterations: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_MAX_SEARCH_ITERATIONS", "5")))
    max_sources_per_step: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_MAX_SOURCES_PER_STEP", "10")))
    search_timeout_seconds: int = 30
    
    # Approval config
    require_plan_approval: bool = True
    require_final_approval: bool = False

class SearchResult(BaseModel):
    """Search result"""
    url: str
    title: str
    content: str
    snippet: str
    score: float = 0.0
    source: str = "tavily"
    retrieved_at: datetime = Field(default_factory=datetime.now)

class ExtractedInsight(BaseModel):
    """Extracted insight"""
    step_id: str
    content: str
    sources: List[str]
    confidence: float = 0.0
    extracted_at: datetime = Field(default_factory=datetime.now)

class ResearchAgentState(BaseAgentState):
    """Deep Research Agent State"""
    
    # Configuration override
    config: ResearchConfig
    
    # Research specific fields
    research_plan: Optional[ResearchPlan] = None
    current_step_index: int = 0
    
    search_results: Dict[str, List[SearchResult]] = Field(default_factory=dict)
    extracted_insights: Dict[str, ExtractedInsight] = Field(default_factory=dict)
    
    # Output
    final_report: Optional[str] = None
    
    def add_search_result(self, step_id: str, result: SearchResult) -> None:
        if step_id not in self.search_results:
            self.search_results[step_id] = []
        self.search_results[step_id].append(result)
    
    def add_insight(self, insight: ExtractedInsight) -> None:
        self.extracted_insights[insight.step_id] = insight
    
    def get_current_step(self) -> Optional[ResearchStep]:
        if self.research_plan:
            return self.research_plan.get_current_step(self.current_step_index)
        return None
    
    def move_to_next_step(self) -> bool:
        if self.research_plan and self.current_step_index < len(self.research_plan.steps) - 1:
            self.current_step_index += 1
            return True
        return False
    
    def is_plan_completed(self) -> bool:
        return self.research_plan is not None and self.research_plan.is_completed()
        
    def complete_research(self) -> None:
        self.complete()

# Factory functions

def create_research_state(
    user_query: str,
    session_id: str,
    config: Optional[ResearchConfig] = None,
    user_id: Optional[str] = None
) -> ResearchAgentState:
    """Create new Research Agent State"""
    if config is None:
        config = ResearchConfig(
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
    return ResearchStep(
        step_id=step_id,
        title=title,
        description=description,
        keywords=keywords,
        expected_output=expected_output
    )
