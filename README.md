# Deep Research Agent

> 🤖 An autonomous research agent built with LangGraph, LangChain, and FastAPI.

[中文文档](README-zh.md)

Deep Research Agent is capable of autonomously formulating research plans, executing multi-step web searches, extracting key information, and ultimately generating structured deep research reports based on complex topics provided by users. It integrates a Human-in-the-Loop (HITL) mechanism, allowing users to intervene in the planning and report generation processes.

## 💡 Design Philosophy & Motivation

This project is developed based on the latest **LangChain V1.0** ecosystem. Unlike using ready-made Middleware from LangChain or out-of-the-box Deep Agents, this project deliberately chooses the technical route of **LangGraph + Custom HITL (Human-in-the-Loop) + Custom Middleware**.

**Why do this?**

*   **Reveal Underlying Principles**: By building core components (such as state management and middleware mechanisms) from scratch, it aims to deeply analyze the internal working mechanisms of Agent systems, rather than just staying at the API call level.
*   **Higher Customization Capability**: The self-developed middleware architecture and HITL process provide more flexible control than standard libraries, capable of meeting complex business logic requirements.
*   **Oriented for Deep Learning**: This project is mainly aimed at developers and researchers who wish to deeply study the LangChain family architecture, explore Agent design patterns, and pursue highly controllable AI applications.

## 📚 Documentation

- [**Design Specification**](docs/design_specification.md): Understand the system's architectural design, technology selection, and core modules.

## 👀 Demo

### 💻 Web Interface Features

Deep Research Agent provides an intuitive Web interface supporting the following core interactions:

*   **⚙️ Configuration**: Users can customize the research topic and **max search steps** to flexibly control research depth.
*   **📝 Plan Approval (HITL)**: Before executing searches, the Agent generates a research plan. Users can **review, modify, or approve** this plan to ensure accuracy.
*   **📊 Real-time Progress**: The interface displays the Agent's current status (planning, searching, analyzing, etc.) and execution logs in real-time, making the process transparent.
*   **📄 Report Export**: Upon completion, the final report can be **downloaded as PDF** with one click for easy sharing and archiving.

### 📸 Screenshots

#### 1. Page Initialization
![Page Initialization](res/init.png)

#### 2. Human-in-the-Loop (HITL) Approval
![HITL Status](res/hitl.png)

#### 3. Task Execution
![Executing](res/executing.png)

#### 4. Task Completion & Report Generation
![Completed](res/completed.png)


### 📊 Langfuse Trace Example
View the complete Agent execution trace, including planning, searching, reflection, and report generation processes:
[👉 Click to view Langfuse Trace](https://cloud.langfuse.com/project/cmhkk7puw01cnad08uwnxugs9/traces/15f6ba4c96f0d22baa439c858342349b?observation=53db5328b8a22151&timestamp=2025-11-22T08:54:01.003Z)

## ✨ Core Features

- **🧠 Autonomous Planning**: Utilizes LLM to break down vague research goals into executable specific search steps.
- **🕸️ Deep Search**: Integrates Tavily API to perform precise searches and content scraping for each step.
- **🔍 Intelligent Extraction**: Automatically analyzes and extracts key data, facts, and citations from search results.
- **🤝 Human-in-the-Loop**: Supports manual review mechanisms, allowing intervention to adjust research direction at any time.
- **🔌 Middleware Architecture**: Built-in logging, Tracing (Langfuse), performance monitoring, and error handling middleware for production-grade robustness.
- **⚡ Asynchronous API**: Provides high-performance asynchronous REST interfaces based on FastAPI.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (This project is developed using Python 3.13)
- OpenAI API Key
- Tavily API Key
- (Optional) Langfuse Public/Secret Key (for tracing)

### Installation

```bash
# Clone the project
git clone https://github.com/changflow/deep-research-agent.git
cd deep-research-agent

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e .[all]
```

### Configuration

Copy `.env.example` (if it doesn't exist, refer below) to create a `.env` file:

```ini
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=
LLM_MODEL=

TAVILY_API_KEY=tvly-...

# Optional: Langfuse Tracing
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional: System Configuration
DEBUG=True
ENVIRONMENT=development
```

### Running

Start the API server:

```bash
python -m deep_research_agent.app
```

The service will start at `http://0.0.0.0:8000`.

### Usage Example

1. **Start a Research Task**:

```bash
curl -X POST "http://localhost:8000/research/start" \
     -H "Content-Type: application/json" \
     -d '{"query": "Trends in Generative AI applications in healthcare in 2025", "max_steps": 3}'
```

2. **Check Status**:

```bash
# Use the returned thread_id
curl "http://localhost:8000/research/{thread_id}/status"
```

## 🛠️ Development & Testing

```bash
# Run all tests
pytest

# Run specific tests
pytest test/test_graph_mock.py
```

## 🏗️ Project Structure

```
deep-research-agent/
├── docs/                   # Documentation
│   └── design_specification.md
├── src/
│   └── deep_research_agent/
│       ├── core/           # Core Logic (State, HITL)
│       ├── nodes/          # Graph Nodes (Plan, Search, Report)
│       ├── middleware/     # Middleware System
│       ├── utils/          # Utility Functions
│       ├── graph.py        # LangGraph Definition
│       └── app.py          # FastAPI Application Entry
└── test/                   # Test Cases
```

## License

MIT
