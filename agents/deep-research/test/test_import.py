try:
    from langfuse import observe
    print(f"Imported observe from langfuse (top-level): {observe}")
except Exception as e:
    print(f"Failed top-level import: {e}")

try:
    from langfuse.decorators import observe
    print(f"Imported observe from decorators: {observe}")
except Exception as e:
    print(f"Failed decorators import: {e}")
