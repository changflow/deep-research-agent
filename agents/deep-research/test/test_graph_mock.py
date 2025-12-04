import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json

from agent_core.core.state import create_agent_state, AgentConfiguration, ResearchPlan, ResearchStep
from deep_research_agent.graph import agent_app

# Mock data
MOCK_PLAN_JSON = json.dumps({
    "topic": "Test Topic",
    "objective": "Test Objective",
    "steps": [
        {"step_id": "step_1", "title": "Step 1", "description": "Desc 1", "keywords": ["k1"], "expected_output": "Out 1"},
        {"step_id": "step_2", "title": "Step 2", "description": "Desc 2", "keywords": ["k2"], "expected_output": "Out 2"}
    ],
    "estimated_duration_minutes": 10
})

MOCK_SEARCH_RESULTS = [
    {"title": "Res 1", "content": "Content 1", "url": "http://1.com"},
    {"title": "Res 2", "content": "Content 2", "url": "http://2.com"}
]

@pytest.mark.asyncio
async def test_graph_end_to_end():
    """
    Test the full graph execution with mocked LLM and Search.
    """
    
    # 1. Setup Mocks
    
    # Mock LLM for Plan Generation
    # Patching where it is used in the nodes
    
    with patch("deep_research_agent.nodes.plan_generation.get_chat_model") as mock_get_model_plan, \
         patch("deep_research_agent.nodes.search_execution.get_chat_model") as mock_get_model_search, \
         patch("deep_research_agent.nodes.report_generation.get_chat_model") as mock_get_model_report:
        
        mock_llm = AsyncMock()
        mock_get_model_plan.return_value = mock_llm
        mock_get_model_search.return_value = mock_llm
        mock_get_model_report.return_value = mock_llm
        
        # Behavior for Plan Generation
        # First call: Generate Plan
        # Behavior for Search Step 1: Summary/Insight
        # Behavior for Search Step 2: Summary/Insight
        # Behavior for Final Report: Report Content
        
        # We can set side_effect to return different responses based on call count or input
        # Simplified: just return logic based on context or a sequence
        
        # Create JSON strings for insights
        insight_1 = json.dumps({
            "content": "Insight for step 1",
            "sources": ["http://1.com"],
            "confidence": 0.9
        })
        insight_2 = json.dumps({
            "content": "Insight for step 2",
            "sources": ["http://2.com"],
            "confidence": 0.8
        })

        mock_llm.ainvoke.side_effect = [
            MagicMock(content=MOCK_PLAN_JSON), # Plan
            MagicMock(content=insight_1), # Search 1
            MagicMock(content=insight_2), # Search 2
            MagicMock(content="Final Report Content") # Report
        ]
        
        # Mock TavilySearchResults in search_execution
        with patch("deep_research_agent.nodes.search_execution.TavilySearchResults") as mock_tavily_tool_cls:
            mock_tavily_tool = AsyncMock()
            mock_tavily_tool_cls.return_value = mock_tavily_tool
            # ainvoke should return the list of dicts
            mock_tavily_tool.ainvoke.return_value = MOCK_SEARCH_RESULTS
            
            # 2. Setup State
            config = AgentConfiguration(
                max_search_steps=3,
                require_plan_approval=False,
                require_final_approval=False
            )
            initial_state = create_agent_state("Test topic", "test-session-mock", config=config)
            
            # 3. Run Graph
            # Use astream to run until end
            inputs = initial_state # or initial_state.dict() depending on langgraph version usage in graph.py
            
            # Note: agent_app.astream expects dictionary or state object
            # And config for thread_id
            thread_config = {"configurable": {"thread_id": "test-thread"}}
            
            final_state_values = None
            
            # Run step by step
            async for event in agent_app.astream(inputs, config=thread_config):
                # event is a dict of node_name: state_update
                for node, update in event.items():
                    print(f"Executed node: {node}")
                    final_state_values = update # keep updating
            
            # Since astream yields updates, we might need to get the final state using aget_state or accumulate manually.
            # The 'update' in event usually contains the changed fields or the full state depending on StateGraph definition.
            # Our functions return 'state', so update should be the state object (or dict representation).
            
            # 4. Validate
            snapshot = await agent_app.aget_state(thread_config)
            final_state = snapshot.values
            
            # Check Plan
            assert final_state["research_plan"] is not None
            # Pydantic models in dict state might be dicts themselves or objects depending on LangGraph
            # Assuming they are objects if state schema is Pydantic, but let's handle dict just in case
            plan = final_state["research_plan"]
            if isinstance(plan, dict):
                assert len(plan["steps"]) == 2
            else:
                assert len(plan.steps) == 2
            
            # Check Insights (Step 1 and Step 2 executed)
            assert "step_1" in final_state["extracted_insights"]
            insight = final_state["extracted_insights"]["step_1"]
            if isinstance(insight, dict):
                assert insight["content"] == "Insight for step 1"
            else:
                assert insight.content == "Insight for step 1"
            
            # Check Report
            assert final_state["final_report"] == "Final Report Content"
            assert final_state["status"] == "completed"
