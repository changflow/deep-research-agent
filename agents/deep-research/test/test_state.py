import pytest
from datetime import datetime
from deep_research_agent.core.state import create_agent_state, AgentStatus, ResearchStep, ExtractedInsight, ResearchStepStatus

def test_state_initialization():
    """Test creating initial state."""
    user_query = "Deep learning trends"
    session_id = "test-session-1"
    state = create_agent_state(user_query, session_id)
    
    assert state.user_query == user_query
    assert state.session_id == session_id
    assert state.status == AgentStatus.PLANNING
    assert state.research_plan is None
    assert len(state.extracted_insights) == 0
    assert state.current_step_index == 0

def test_state_step_progress(planned_state):
    """Test moving through steps."""
    state = planned_state
    
    # Initially at step 0
    assert state.current_step_index == 0
    current_step = state.get_current_step()
    assert current_step.step_id == "step-1"
    
    # Mark complete and move next (simulate node behavior)
    current_step.status = ResearchStepStatus.COMPLETED
    insight = ExtractedInsight(
        step_id="step-1",
        content="Found some insights",
        sources=["url1"]
    )
    state.add_insight(insight)
    
    assert state.research_plan.steps[0].status == ResearchStepStatus.COMPLETED
    assert "step-1" in state.extracted_insights
    assert state.extracted_insights["step-1"].content == "Found some insights"
    
    # Move to next step
    has_next = state.move_to_next_step()
    assert has_next is True
    assert state.current_step_index == 1
    assert state.get_current_step().step_id == "step-2"
    
    # Complete last step
    state.get_current_step().status = ResearchStepStatus.COMPLETED
    has_next = state.move_to_next_step()
    assert has_next is False # No more steps
    assert state.is_plan_completed() is True

def test_agent_completion(planned_state):
    """Test completing the research."""
    state = planned_state
    state.final_report = "Final Report Content"
    state.complete_research()
    
    assert state.status == AgentStatus.COMPLETED
    assert state.end_time is not None
