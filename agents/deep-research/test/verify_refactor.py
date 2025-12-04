import sys
import os
import traceback

# Setup paths similar to app running context
current_dir = os.path.dirname(os.path.abspath(__file__))
# deep-research-agent/agents/deep-research/src
agent_src_path = os.path.abspath(os.path.join(current_dir, "..", "src"))
# deep-research-agent/libs/agent-core/src
lib_src_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "libs", "agent-core", "src"))

print(f"Adding to sys.path: {agent_src_path}")
sys.path.append(agent_src_path)
print(f"Adding to sys.path: {lib_src_path}")
sys.path.append(lib_src_path)

def test_imports():
    print("\n=== Testing Imports ===")
    
    print("Attempting to import generic state from agent_core...")
    try:
        from agent_core.core.state import BaseAgentState, BaseAgentConfiguration, AgentStatus
        print("✅ Successfully imported BaseAgentState, BaseAgentConfiguration, AgentStatus from agent_core.core.state")
    except Exception as e:
        print(f"❌ Failed to import from agent_core.core.state: {e}")
        traceback.print_exc()
        return False

    print("Attempting to import specific state from deep_research_agent...")
    try:
        from deep_research_agent.state import ResearchAgentState, ResearchConfig, ResearchPlan
        print("✅ Successfully imported ResearchAgentState, ResearchConfig, ResearchPlan from deep_research_agent.state")
    except Exception as e:
        print(f"❌ Failed to import from deep_research_agent.state: {e}")
        traceback.print_exc()
        return False

    print("Attempting to instantiate ResearchAgentState...")
    try:
        config = ResearchConfig()
        state = ResearchAgentState(
            user_query="Test Query",
            session_id="test-123",
            config=config,
            status=AgentStatus.PLANNING
        )
        print("✅ Successfully instantiated ResearchAgentState")
        print(f"State keys: {state.dict().keys()}")
    except Exception as e:
        print(f"❌ Failed to instantiate ResearchAgentState: {e}")
        traceback.print_exc()
        return False
        
    print("Attempting to import app (triggers graph and nodes)...")
    try:
        from deep_research_agent.app import app
        print("✅ Successfully imported app module")
    except Exception as e:
        print(f"❌ Failed to import deep_research_agent.app: {e}")
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    if test_imports():
        print("\n✨ Verification Successful! Refactoring seems correct.")
        sys.exit(0)
    else:
        print("\n💀 Verification Failed.")
        sys.exit(1)
