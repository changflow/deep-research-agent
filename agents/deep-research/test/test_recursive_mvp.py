import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import logging

from agent_core.core.state import AgentStatus
from deep_research_agent.graph import agent_app
from deep_research_agent.state import ResearchAgentState, ResearchConfig, ResearchPlan, ResearchStep, create_research_state

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Data
MOCK_PLAN_JSON = json.dumps({
    "topic": "Recursive Test",
    "objective": "Test Recursion",
    "steps": [
        {"step_id": "step_1", "title": "Step 1", "description": "Initial Step", "keywords": ["k1"]}
    ],
    "estimated_duration_minutes": 5
})

# Mock Responses
# 1. Plan Generation -> Returns MOCK_PLAN_JSON
# 2. Search Execute (Step 1) -> Returns some search results
# 3. Evaluate Result (Step 1) -> Returns decision "more_info" with sub-steps
# 4. Search Execute (Step 1.sub1) -> Returns results
# 5. Evaluate Result (Step 1.sub1) -> Returns decision "satisfied" (sufficient)
# 6. Report Generation -> Returns "Final Report"

DECISION_MORE_INFO = json.dumps({
    "status": "NEEDS_MORE_INFO",
    "reasoning": "Need details",
    "new_steps": [
        {"title": "Sub Step 1", "description": "Deep dive"}
    ]
})

DECISION_SATISFIED = json.dumps({
    "status": "APPROVED",
    "reasoning": "Good enough"
})

MOCK_SEARCH_RESULTS = [{"title": "Res", "content": "Content", "url": "http://test"}]

@pytest.mark.asyncio
async def test_recursive_planning_flow():
    """
    Test the recursive planning flow:
    Plan -> Step 1 -> Eval (More Info) -> Step 1.sub1 -> Eval (Satisfied) -> Report
    """
    
    with patch("deep_research_agent.nodes.plan_generation.get_chat_model") as mock_get_model_plan, \
         patch("deep_research_agent.nodes.search_execution.get_chat_model") as mock_get_model_search, \
         patch("agent_core.core.processor.get_chat_model") as mock_get_model_processor, \
         patch("deep_research_agent.nodes.result_evaluation.get_chat_model") as mock_get_model_eval, \
         patch("deep_research_agent.nodes.report_generation.get_chat_model") as mock_get_model_report, \
         patch("deep_research_agent.workers.TavilySearchResults") as mock_tavily_cls, \
         patch("deep_research_agent.workers.get_chat_model") as mock_get_model_worker:
        
        # Setup LLMs
        mock_llm_plan = AsyncMock()
        mock_llm_eval = AsyncMock()
        mock_llm_report = AsyncMock()
        mock_llm_search = AsyncMock() # For search_execution node's extraction phase
        mock_llm_worker = AsyncMock() # For Critic inside Worker

        mock_get_model_plan.return_value = mock_llm_plan
        mock_get_model_search.return_value = mock_llm_search
        mock_get_model_processor.return_value = mock_llm_search # Bind processor mock to same search logic
        mock_get_model_eval.return_value = mock_llm_eval
        mock_get_model_report.return_value = mock_llm_report
        mock_get_model_worker.return_value = mock_llm_worker

        # Configure Search/Extraction LLM Mock
        # Must return valid JSON or string for ExtractedInsight
        mock_llm_search.ainvoke.return_value.content = json.dumps({
            "content": "Extracted search content",
            "sources": ["http://test.com"],
            "confidence": 0.9
        })

        # Configure Worker/Critic LLM Mock
        # Must return valid JSON for VerificationResult
        mock_llm_worker.ainvoke.return_value.content = json.dumps({
            "score": 0.9,
            "passed": True,
            "feedback": "LGTM"
        })
        
        # Setup Tavily
        mock_tavily = AsyncMock()
        mock_tavily_cls.return_value = mock_tavily
        mock_tavily.ainvoke.return_value = MOCK_SEARCH_RESULTS
        
        # 1. Plan Generation Response
        mock_llm_plan.ainvoke.return_value.content = MOCK_PLAN_JSON
        
        # 2. Evaluation Responses
        # First call (for Step 1): Return "more_info" -> Triggers recursion
        # Second call (for Step 1.sub1): Return "sufficient" -> Continues
        # Note: Depending on logic, Step 1 might be re-evaluated or marked as done after sub-steps?
        # In our logic: 
        # - Step 1 executed.
        # - Eval checks. Returns "more_info" -> Adds Step 1.sub1. Step 1 index NOT incremented? 
        #   Actually, insert_steps_after_current adds them AFTER current. 
        #   So next definition is `1.sub1`. 
        #   Current step `1` is marked completed or stays?
        #   If `more_info`, usually we might want to re-evaluate parent or just consider children enough.
        #   Let's check `result_evaluation.py` logic.
        #   If `more_info`, it inserts steps. DOES IT increment index?
        #   Our `evaluate_task_result` returns `return {"current_step_index": ...}`?
        #   If we use standard flow, `result_evaluation` usually returns nothing implies state update is handled.
        #   Wait, `graph.py` edge logic?
        #   Let's assume for this test:
        #   1. Eval(Step 1) -> more_info -> Adds 1.sub1 -> Index + 1 (to 1.sub1)
        #   2. Eval(Step 1.sub1) -> sufficient -> Index + 1 (End of list) -> Final Report
        
        mock_llm_eval.ainvoke.side_effect = [
            MagicMock(content=DECISION_MORE_INFO), # For Step 1
            MagicMock(content=DECISION_SATISFIED)  # For Step 1.sub1
        ]
        
        # 3. Report Response
        mock_llm_report.ainvoke.return_value.content = "Final Report with Recursion"

        # Setup Config & State
        config = ResearchConfig(
            max_search_iterations=10,
            require_plan_approval=False,
            require_final_approval=False
        )
        initial_state = create_research_state("Recursion Test", "test-recursion", config=config)
        
        # Run
        thread_config = {"configurable": {"thread_id": "test-rec-thread"}}
        
        last_snapshot = None
        async for event in agent_app.astream(initial_state, config=thread_config):
             for node, update in event.items():
                 # print(f"Node: {node}")
                 pass
        
        # Validate Final State
        snapshot = await agent_app.aget_state(thread_config)
        final_state = snapshot.values
        
        # Check Plan has expanded
        steps = final_state["research_plan"].steps
        # Original Step 1 + Sub Step 1 = 2 steps total?
        # Or effectively 2 steps in flat list.
        assert len(steps) >= 2 
        
        # Check IDs
        # We expect "step_1" and "step_1.sub1" (or similar generated ID)
        ids = [s.step_id for s in steps]
        print(f"Step IDs: {ids}")
        assert any("sub" in pid for pid in ids)
        
        # Check Depth
        depths = [s.depth for s in steps]
        print(f"Depths: {depths}")
        assert 2 in depths # Sub step should have depth 2 (1+1)
        
        # Check Status
        assert final_state["status"] == "completed"
        assert final_state["final_report"] == "Final Report with Recursion"

if __name__ == "__main__":
    # If run directly
    import asyncio
    asyncio.run(test_recursive_planning_flow())
