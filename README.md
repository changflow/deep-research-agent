# AgentCore Framework

> 🏗️ A production-ready, multi-agent collaboration framework built on top of LangGraph.

[中文文档](README-zh.md)

**AgentCore** provides a robust infrastructure for building controllable, observable, and human-collaborative AI agents. Designed as a monorepo, it decouples the core agent framework from specific implementations, allowing developers to rapidly build and deploy diverse vertical agents while reusing a unified foundation.

## 🌟 Vision

Originally starting as a single "Deep Research Agent", this project has evolved into a comprehensive framework. Our goal is to solve the common challenges in building production-grade agents:

*   **Observability**: How to trace complex agent reasoning steps? (Built-in Middleware & Langfuse)
*   **Controllability**: How to prevent agents from hallucinating or going off-track? (First-class Human-in-the-Loop support)
*   **Reusability**: How to share state management, configuration, and tools across different agents? (Shared Core Library)

## 🧩 Architecture

The project follows a Monorepo structure:

```
deep-research-agent/
├── libs/
│   └── agent-core/         # 🧠 The Framework Core
│       ├── State Management
│       ├── Middleware System (Logging, Tracing, Metrics)
│       └── HITL Protocals
│
├── agents/                 # 🤖 Agent Implementations
│   └── deep-research/      # Reference Implementation: Autonomous Research Agent
│
└── deploy/                 # 🐳 Deployment Configurations (Docker Compose)
```

## 🚀 Core Capabilities (`libs/agent-core`)

1.  **Middleware Architecture**: A flexible, interceptor-based system that wraps every agent node execution with logging, tracing (Langfuse), and error handling without polluting business logic.
2.  **Unified State Management**: Pydantic-based state definitions that ensure type safety and data validation across the graph.
3.  **Human-in-the-Loop (HITL)**: Abstracted pause-resume mechanisms, making it easy to integrate "Human Approval" steps into any workflow.

## 🤖 Built-in Agents

### [Deep Research Agent](agents/deep-research/README.md)

A powerful autonomous research assistant that can:
*   Plan research steps based on user queries.
*   Execute multi-step searches using Tavily API.
*   Synthesize comprehensive reports.

[👉 Learn more about Deep Research Agent](agents/deep-research/README.md)

*(More agents like Coding Assistant, Data Analyst coming soon...)*

## 🚦 Quick Start

### Installation

For detailed setup instructions, please refer to the [Setup Guide](docs/setup_guide.md).

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/changflow/deep-research-agent.git
    cd deep-research-agent
    ```

2.  **Install the Framework Core**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e libs/agent-core
    ```

3.  **Run the Deep Research Agent**:
    ```bash
    # Install agent dependencies
    pip install -r agents/deep-research/requirements.txt
    
    # Configure environment
    cp agents/deep-research/.env.example agents/deep-research/.env
    # Edit .env with your API Keys
    
    # Run
    cd agents/deep-research
    python -m deep_research_agent.app
    ```

### Docker Deployment

To launch the full stack (multiple agents + frontend + observability):

```bash
cd deploy
docker compose up -d --build
```

Access the dashboard at `http://localhost:3000`.

## 📚 Documentation

*   [**Setup Guide**](docs/setup_guide.md): Environment setup and installation.
*   [**Architecture Design**](docs/architecture.md): Deep dive into the framework design.
*   [**Design Specification**](docs/design_specification.md): Technical specs and decisions.

## 📝 Related Blogs (Chinese)

- [Step-by-Step Guide to Replicate Deep Research Agent](https://blog.csdn.net/roseey/article/details/155312929)
- [Why I Built My Own Middleware Layer on Top of LangChain](https://zhuanlan.zhihu.com/p/1977352285798552066)
- [Implementing Frontend-Friendly HITL in LangGraph](https://juejin.cn/post/7576969229984923688)

## License

MIT
