FROM python:3.13-slim

WORKDIR /app

# Copy libs
COPY libs /app/libs

# Install agent-core
RUN pip install --no-cache-dir /app/libs/agent-core

# Copy agent code
COPY agents/deep-research /app/agents/deep-research

# Install agent dependencies
WORKDIR /app/agents/deep-research
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Set PYTHONPATH to include agent source
ENV PYTHONPATH=/app/agents/deep-research/src

# Start command
CMD ["uvicorn", "deep_research_agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
