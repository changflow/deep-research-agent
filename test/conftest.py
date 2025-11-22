import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set dummy env vars for testing
os.environ["OPENAI_API_KEY"] = "dummy_key"
os.environ["TAVILY_API_KEY"] = "dummy_key"

from deep_research_agent.core.state import ResearchAgentState, AgentConfiguration, AgentStatus, ResearchPlan, ResearchStep

@pytest.fixture
def mock_llm():
    """Mock the LLM to return predictable responses."""
    mock = MagicMock()
    
    async def async_invoke(inputs):
        return MagicMock(content="Mocked LLM response")
        
    mock.ainvoke = AsyncMock(side_effect=async_invoke)
    mock.invoke = MagicMock(return_value=MagicMock(content="Mocked LLM response"))
    return mock

@pytest.fixture
def mock_tavily():
    """Mock Tavily client."""
    mock = MagicMock()
    mock.search.return_value = [
        {"title": "Test Result 1", "content": "Content 1", "url": "http://test1.com"},
        {"title": "Test Result 2", "content": "Content 2", "url": "http://test2.com"}
    ]
    return mock

@pytest.fixture
def basic_state():
    """Create a basic initial state."""
    config = AgentConfiguration(
        max_search_steps=3,
        require_plan_approval=False, # Default to False for easier testing
        require_final_approval=False
    )
    return ResearchAgentState(
        user_query="Test query",
        config=config,
        session_id="test-session-123",
        status=AgentStatus.PLANNING
    )

@pytest.fixture
def planned_state(basic_state):
    """Create a state that has already been planned."""
    plan = ResearchPlan(
        topic="Test query",
        objective="Test objective",
        estimated_duration_minutes=10,
        steps=[
            ResearchStep(
                step_id="step-1", 
                title="Step 1", 
                description="Description 1", 
                keywords=["k1", "k2"], 
                expected_output="Output 1", 
                status="pending"
            ),
            ResearchStep(
                step_id="step-2", 
                title="Step 2", 
                description="Description 2", 
                keywords=["k3", "k4"], 
                expected_output="Output 2", 
                status="pending"
            )
        ]
    )
    basic_state.research_plan = plan
    basic_state.status = AgentStatus.EXECUTING
    return basic_state
