import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from deep_research_agent.middleware.implementations import TracingMiddleware
from deep_research_agent.core.state import ResearchAgentState, AgentConfiguration

class MockLangfuseClient:
    def __init__(self, *args, **kwargs):
        self.spans = []
        self.traces = []

    def start_span(self, name, trace_context, input, metadata):
        span = MockSpan(name, input, metadata)
        self.spans.append(span)
        return span
    
    def flush(self):
        pass

class MockSpan:
    def __init__(self, name, input, metadata):
        self.name = name
        self.input = input
        self.metadata = metadata
        self.ended = False
        self.output = None
        self.update_metadata = {}

    def update_trace(self, **kwargs):
        pass

    def update(self, **kwargs):
        if 'metadata' in kwargs:
            self.update_metadata.update(kwargs['metadata'])
        if 'output' in kwargs:
            self.output = kwargs['output']

    def end(self, **kwargs):
        self.ended = True
        if 'output' in kwargs:
            self.output = kwargs['output']

@pytest.mark.asyncio
async def test_tracing_middleware_input_output():
    # Mock Langfuse import and client
    # Patch where it is defined, not where it is imported locally
    with patch('deep_research_agent.utils.config.get_settings') as mock_settings:
        mock_settings.return_value.LANGFUSE_PUBLIC_KEY = "pk-test"
        mock_settings.return_value.LANGFUSE_SECRET_KEY = "sk-test"
        mock_settings.return_value.LANGFUSE_HOST = "https://cloud.langfuse.com"
        
        with patch('langfuse.Langfuse', side_effect=MockLangfuseClient):
            middleware = TracingMiddleware(enable_langfuse=True)
            
            # Create a dummy state
            config = AgentConfiguration(max_search_iterations=1, max_sources_per_step=3)
            state = ResearchAgentState(
                user_query="test query",
                config=config,
                session_id="test-session"
            )
            
            # Test before_node_execution (Input)
            node_name = "test_node"
            await middleware.before_node_execution(node_name, state)
            
            # Verify span created with correct input
            assert len(middleware.langfuse_client.spans) == 1
            span = middleware.langfuse_client.spans[0]
            assert span.name == node_name
            assert span.input is not None
            assert isinstance(span.input, dict)
            assert span.input["user_query"] == "test query"
            
            # Test after_node_execution (Output)
            result = {"result": "success", "data": [1, 2, 3]}
            await middleware.after_node_execution(node_name, state, result)
            
            # Verify span ended with correct output
            assert span.ended is True
            assert span.output == result

if __name__ == "__main__":
    # Manually run the async test function if pytest is not available or for quick check
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_tracing_middleware_input_output())
        print("✅ TracingMiddleware input/output test passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()
