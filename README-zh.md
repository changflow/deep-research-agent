# AgentCore Framework

> 🏗️ 一个基于 LangGraph 构建的生产级多智能体协同框架。

**AgentCore** 提供了一套健壮的基础设施，用于构建可控 (Controllable)、可观察 (Observable) 且支持人类协同 (Human-Collaborative) 的 AI 智能体。本项目采用 Monorepo 结构，将核心框架与具体业务实现解耦，允许开发者基于统一的底层快速构建、复用和部署各种垂直领域的智能体。

## 🌟 愿景

本项目最初是作为单一的 "Deep Research Agent" 开始的，现已演变为通用的 Agent 开发框架。我们的目标是解决构建生产级 Agent 时的共性挑战：

*   **可观测性 (Observability)**: 如何追踪复杂的 Agent 推理步骤？(内置中间件系统 & Langfuse 集成)
*   **可控性 (Controllability)**: 如何防止 Agent 产生幻觉或偏离轨道？(原生 Human-in-the-Loop 支持)
*   **复用性 (Reusability)**: 如何在不同 Agent 间共享状态管理和工具？(共享 Core 库)

## 🧩 架构设计

项目遵循 Monorepo 结构：

```
deep-research-agent/
├── libs/
│   └── agent-core/         # 🧠 框架核心库
│       ├── 状态管理 (State Management)
│       ├── 中间件系统 (Logging, Tracing, Metrics)
│       └── HITL 协议抽象
│
├── agents/                 # 🤖 具体智能体实现
│   └── deep-research/      # 参考实现：自主深度研究智能体
│
└── deploy/                 # 🐳 部署配置 (Docker Compose)
```

## 🚀 核心能力 (`libs/agent-core`)

1.  **中间件架构 (Middleware Architecture)**: 灵活的拦截器系统，自动为每个节点执行注入日志、追踪和错误处理，保持业务逻辑纯净。
2.  **统一状态管理**: 基于 Pydantic 的状态定义，确保跨图传递的数据类型安全。
3.  **Human-in-the-Loop (HITL)**: 抽象化的暂停-恢复机制，轻松将"人工审批"步骤集成到任何工作流中。

## 🤖 内置智能体

### [Deep Research Agent (深度研究智能体)](agents/deep-research/README-zh.md)

一个强大的自主研究助手，能够：
*   根据用户查询自动规划研究步骤。
*   使用 Tavily API 执行多步深度搜索。
*   合成结构化的长文报告。

[👉 了解 Deep Research Agent 详情](agents/deep-research/README-zh.md)

*(更多智能体如 Coding Assistant, Data Analyst 即将推出...)*

## 🚦 快速开始

### 安装

详细安装步骤请参考 [安装指南](docs/setup_guide.md)。

1.  **克隆项目**:
    ```bash
    git clone https://github.com/changflow/deep-research-agent.git
    cd deep-research-agent
    ```

2.  **安装核心框架**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e libs/agent-core
    ```

3.  **运行 Deep Research Agent**:
    ```bash
    # 安装依赖
    pip install -r agents/deep-research/requirements.txt
    
    # 配置环境
    cp agents/deep-research/.env.example agents/deep-research/.env
    # 编辑 .env 填入 API Keys
    
    # 运行
    cd agents/deep-research
    python -m deep_research_agent.app
    ```

### Docker 部署

一键启动全栈环境（多 Agent + 前端 + 可观测性平台）：

```bash
cd deploy
docker compose up -d --build
```

访问控制台：`http://localhost:3000`。

## 📚 文档资源

*   [**安装指南**](docs/setup_guide.md): 环境配置与安装。
*   [**架构设计**](docs/architecture.md): 深入了解框架设计理念。
*   [**设计规范**](docs/design_specification.md): 技术规范与决策。

## 📝 相关博客

- [【Python 教程】手把手教你用 LangGraph 复刻 Deep Research 智能体](https://blog.csdn.net/roseey/article/details/155312929)
- [LangChain 1.0 终于来了！为何我还在坚持手写“执行层”中间件？](https://zhuanlan.zhihu.com/p/1977352285798552066)
- [告别“黑盒”等待：如何在 LangGraph 中优雅地实现前端友好的 Human-in-the-Loop？](https://juejin.cn/post/7576969229984923688)

## License

MIT
