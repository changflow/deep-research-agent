
import os
import sys

# Add src directories to sys.path to mimic run_server.bat
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
libs_path = os.path.abspath(os.path.join(current_dir, "../../libs/agent-core/src"))

sys.path.append(src_path)
sys.path.append(libs_path)

# Set ENV_FILE environment variable as run_server.bat does
env_file_path = os.path.join(current_dir, ".env")
os.environ["ENV_FILE"] = env_file_path

print(f"ENV_FILE set to: {os.environ['ENV_FILE']}")

try:
    from agent_core.utils.config import get_settings
    settings = get_settings()
    
    print("--- Settings Loaded ---")
    print(f"OPENAI_API_KEY: {settings.OPENAI_API_KEY[:8] if settings.OPENAI_API_KEY else 'None'}...")
    print(f"OPENAI_MODEL_NAME: {settings.OPENAI_MODEL_NAME}")
    print(f"OPENAI_BASE_URL: {settings.OPENAI_BASE_URL}")
    
    if settings.OPENAI_API_KEY == "sk-806d2e03d2524be2bc162e58afa969b4":
         print("SUCCESS: API Key matches the expected value in .env")
    else:
         print("FAILURE: API Key does NOT match. Please check .env loading.")

except Exception as e:
    print(f"Error loading settings: {e}")
    import traceback
    traceback.print_exc()
