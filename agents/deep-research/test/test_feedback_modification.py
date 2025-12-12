import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import logging

from agent_core.core.state import AgentStatus
from deep_research_agent.graph import agent_app
from deep_research_agent.state import ResearchConfig, create_research_state

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Data
INITIAL_PLAN_JSON = json.dumps({
    "topic": "Future Trends",
    "objective": "Predict 5 years",
    "steps": [
        {"step_id": "step_1", "title": "Analyze 2020-2025", "description": "Look back", "keywords": ["k1"]}
    ],
    "estimated_duration_minutes": 5
})

MODIFIED_PLAN_JSON = json.dumps({
    "topic": "Future Trends",
    "objective": "Predict 1 year",
    "steps": [
        {"step_id": "step_1_new", "title": "Analyze 2024-2025", "description": "Short term focus", "keywords": ["k1"]}
    ],
    "estimated_duration_minutes": 5
})

@pytest.mark.asyncio
async def test_feedback_plan_modification():
    """
    Test that providing 'modify' feedback triggers plan regeneration.
    """
    
    with patch("deep_research_agent.nodes.plan_generation.get_chat_model") as mock_get_model_plan:
        
        # Setup LLM Mock for Plan Generation
        mock_llm_plan = AsyncMock()
        mock_get_model_plan.return_value = mock_llm_plan
        
        # First call returns initial plan (5 years)
        # Second call returns modified plan (1 year)
        mock_llm_plan.ainvoke.side_effect = [
            MagicMock(content=INITIAL_PLAN_JSON),
            MagicMock(content=MODIFIED_PLAN_JSON)
        ]
        
        # Setup Config & State
        config = ResearchConfig(
            max_search_iterations=5,
            require_plan_approval=True, # Critical: Enable approval
            require_final_approval=False
        )
        initial_state = create_research_state("Predict Trends", "test-feedback-thread", config=config)
        thread_config = {"configurable": {"thread_id": "test-feedback-thread"}}
        
        # 1. Run until Plan Approval Interrupt
        logger.info("--- Starting Run 1 (Initial Plan) ---")
        async for event in agent_app.astream(initial_state, config=thread_config):
             pass
             
        # Check state at interrupt
        snapshot = await agent_app.aget_state(thread_config)
        state = snapshot.values
        
        assert state["status"] == AgentStatus.PLAN_REVIEW
        assert state["research_plan"].objective == "Predict 5 years"
        
        # 2. Simulate User Feedback (Modify)
        # This mirrors the logic we added to app.py
        logger.info("--- Simulating Feedback (Modify) ---")
        
        # Prepare state update
        new_state = state.copy() if isinstance(state, dict) else state.model_dump()
        new_state["status"] = AgentStatus.PLANNING # The Fix
        
        # Determine if plan is dict or object and set notes accordingly
        plan = new_state["research_plan"]
        if isinstance(plan, dict):
            plan["modification_notes"] = "Change duration to 1 year"
        else:
            plan.modification_notes = "Change duration to 1 year"
            
        new_state["pending_hitl_event"] = None
        
        # Update state
        await agent_app.aupdate_state(thread_config, new_state)
        
        # 3. Resume Execution
        logger.info("--- Resuming Execution (Regenerate Plan) ---")
        # Resume (input=None)
        # Should route: wait_node -> (via conditional edge + PLANNING status) -> plan_generation
        
        # We need to run it again until next interrupt (Plan Approval again for new plan)
        async for event in agent_app.astream(None, config=thread_config):
            pass
            
        # 4. Verify New Plan
        snapshot = await agent_app.aget_state(thread_config)
        final_state = snapshot.values
        
        # Should be back in Plan Review
        assert final_state["status"] == AgentStatus.PLAN_REVIEW
        
        # Should have NEW plan content
        new_plan = final_state["research_plan"]
        logger.info(f"New Plan Objective: {new_plan.objective}")
        
        assert new_plan.objective == "Predict 1 year"
        assert new_plan.steps[0].title == "Analyze 2024-2025"
        
        # Verify LLM was called twice
        assert mock_llm_plan.ainvoke.call_count == 2
        
        # Verify second call Prompt contained the feedback
        call_args = mock_llm_plan.ainvoke.call_args_list[1]
        # langchain PromptValue is passed, we check its string representation
        prompt_str = str(call_args[0][0]) 
        assert "Change duration to 1 year" in prompt_str
        assert "USER FEEDBACK OVERRIDE" in prompt_str

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_feedback_plan_modification())
