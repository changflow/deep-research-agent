import sys
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add the local src directory to path
src_path = os.path.join(script_dir, "src")
sys.path.append(src_path)

# Add agent-core to path (relative to this script: ../../libs/agent-core/src)
# This assumes the standard directory structure we just created
libs_path = os.path.join(script_dir, "..", "..", "libs", "agent-core", "src")
sys.path.append(os.path.abspath(libs_path))

print(f"Added paths: \n- {src_path}\n- {os.path.abspath(libs_path)}")

try:
    print("Attempting to import deep_research_agent.app...")
    from deep_research_agent import app
    print("Successfully imported app.")
    
    print("Attempting to import deep_research_agent.graph...")
    from deep_research_agent import graph
    print("Successfully imported graph.")
    
    print("Attempting to import agent_core...")
    import agent_core
    print(f"Successfully imported agent_core from {agent_core.__file__}")

    print("Setup verification successful!")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
