import sys
import os

# Setup paths identical to how the app runs
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, "src")
sys.path.append(src_path)
libs_path = os.path.join(script_dir, "..", "..", "libs", "agent-core", "src")
sys.path.append(os.path.abspath(libs_path))

from agent_core.utils.config import get_settings

import os
from dotenv import load_dotenv

# Simulate what app.py does: Force load .env to override system envs
# Now using ENV_FILE strategy
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir) # agents/deep-research
env_path = os.path.join(project_root, ".env")

if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    os.environ["ENV_FILE"] = env_path
    print(f"Loaded .env from {env_path} with override=True")
    print(f"Set ENV_FILE to: {env_path}")
else:
    print(f"Warning: .env not found at {env_path}")

print(f"System Env OPENAI_API_KEY starts with: {os.environ.get('OPENAI_API_KEY', '')[:5]}")

settings = get_settings()
print(f"Resolved OPENAI_API_KEY starts with: {settings.OPENAI_API_KEY[:5] if settings.OPENAI_API_KEY else 'None'}")
print(f"OPENAI_BASE_URL: {settings.OPENAI_BASE_URL}")
print(f"OPENAI_MODEL_NAME: {settings.OPENAI_MODEL_NAME}")

from langchain_openai import ChatOpenAI
try:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0
    )
    print("Invoking LLM...")
    resp = llm.invoke("Hello")
    print(f"Success! Response: {resp.content}")
except Exception as e:
    print(f"LLM Invocation Failed: {e}")
