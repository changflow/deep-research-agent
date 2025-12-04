import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from deep_research_agent.app import app

client = TestClient(app)

@pytest.fixture
def mock_graph_methods():
    """Mock LangGraph methods used in API."""
    with patch("deep_research_agent.app.agent_app") as mock_app:
        # Mock astream for background task
        mock_app.astream = AsyncMock()
        mock_app.astream.return_value.__aiter__.return_value = []
        
        # Mock aget_state
        mock_state_snapshot = AsyncMock()
        mock_state_snapshot.values = {"status": "planning", "current_step_index": 0, "research_plan": None, "pending_hitl_event": None, "final_report": None, "error_message": None}
        mock_app.aget_state = AsyncMock(return_value=mock_state_snapshot)
        
        yield mock_app

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_start_research(mock_graph_methods):
    response = client.post("/research", json={"query": "Test Query"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "started"

def test_get_status(mock_graph_methods):
    # Assuming 'mock_graph_methods' setup a default return for aget_state
    session_id = "test-session"
    response = client.get(f"/research/{session_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "planning"

def test_submit_feedback(mock_graph_methods):
    session_id = "test-session"
    
    # Setup mock for update_state
    mock_graph_methods.aupdate_state = AsyncMock()
    
    response = client.post(
        f"/research/{session_id}/feedback",
        json={"session_id": session_id, "feedback": {"action": "approve"}}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
