import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

try:
    import langfuse
    print(f"Langfuse version: {langfuse.__version__}")
    print("Langfuse imported successfully")
except ImportError as e:
    print(f"Failed to import langfuse: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
