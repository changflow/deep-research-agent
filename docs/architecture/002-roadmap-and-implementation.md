# 002 - Next-Gen Architecture Blueprint: Intelligent Reasoning Framework

**Status:** Draft
**Date:** 2025-12-04
**Audience:** Architects, Developers, System Integrators

## 1. 战略愿景 (Strategic Vision)

本项目的目标是构建一个**具备深度推理能力与企业级治理特性的智能体框架**。

区别于传统的线性工作流（Chain-of-Thought），本框架采用**分形编排（Fractal Orchestration）**架构，通过递归式的任务分解与自我修正，实现对复杂问题的深度探究。同时，架构内置了**协议化互操作标准（MCP）**与**全链路可观测性治理**，确保系统在具备强认知能力的同时，依然保持可控、透明与安全。

## 2. 核心架构支柱 (Core Architectural Pillars)

### 2.1 分形认知编排系统 (Fractal Cognitive Orchestration)
系统摒弃了单一 Agent 大包大揽的模式，采用 "Orchestrator-Workers" 的层级协作结构，模拟人类专家团队的研究方法。

*   **Recursive Planning (递归规划)**: 主智能体 (Lead Orchestrator) 具备动态规划能力。它不直接执行任务，而是定义目标接口与验收标准，根据 Workers 返回的初步结果，实时调整后续的研究路径（Re-planning），避免无效路径依赖。
*   **Specialized Executors (专业执行者)**:
    *   **Research Worker**: 专注于广度信息检索与交叉验证。
    *   **Data Analyst (Code Execution)**: 利用 MCP 连接安全沙箱，编写并执行 Python 代码来处理检索到的数据（如清洗 CSV、统计频次），而非依赖 LLM 进行不可靠的数值计算。
    *   **Critic Worker**: 运行在独立沙箱中，负责对结论进行逻辑漏洞审查与事实核查 (Fact-Checking)。

### 2.2 自适应上下文管理 (Adaptive Context Management)
针对大模型固有的上下文窗口限制与 "Lost-in-the-Middle" 现象，引入**信息密度控制引擎**。

*   **Knowledge Distillation (知识蒸馏)**: 在层级传递中，强制执行“信息压缩”。子任务完成时，通过 `Summarizer Node` 将冗余的思维链（Chain of Thought）提炼为高密度的知识块 (Knowledge Nuggets) 上报，确保上层决策者始终拥有清晰、专注的上下文视野。
*   **Dynamic Loading (动态加载)**: 支持基于相关性的按需加载机制，仅将当前推理步骤最关心的事实调入显存，大幅提升推理精度与响应速度。

### 2.3 协议化互操作层 (Protocol-Agnostic Interoperability)
全面采用 **Model Context Protocol (MCP)** 标准，实现工具层与核心逻辑的彻底解耦。

*   **Universal Connectivity**: 通过标准化的 MCP Client，系统能够以统一接口连接本地文件系统、企业数据库或云端搜索服务。这意味着同一套业务逻辑可以无缝迁移于本地隐私环境与云原生环境之间。
*   **Tooling Abstraction**: 开发者无需编写特定的 API Adapter，仅需配置 MCP Server 端点即可扩展新能力。

### 2.4 企业级治理与可观测性 (Enterprise Governance & Observability)
虽然追求认知的深度，但我们绝不妥协系统的可控性。通过轻量级的中间件架构，实现企业级治理能力。

*   **Policy Middleware (策略中间件)**: 基于拦截器模式（Interceptor Pattern），在每一个 Action 执行前进行合规性检查（如敏感数据过滤、指令注入防御）。
*   **Token Budgeting (预算熔断)**: 集成基于 Langfuse 的实时消耗追踪。支持为每个 Request ID 设定 Token 预算上限，一旦触发阈值自动熔断，防止 Agent 陷入死循环造成的资源浪费。
*   **Full-Link Tracing (全链路追踪)**: 提供从用户查询到底层 Tool Call 的完整执行轨迹透视，让每一次“思考”都可回溯、可审计。

## 3. 演进路线图与迭代计划 (Roadmap & Iteration Plan)

本项目采用 **"MVP First"** 的迭代策略，在早期阶段**外包**非核心基础设施（如使用 Langfuse Cloud SaaS 和社区 MCP 工具），集中火力攻克**核心认知架构**。

### Phase 1: 核心认知智能 (Core Intelligence) - Weeks 1-2
**目标**: 构建 **Fractal Orchestrator** 能够完成复杂的递归搜索任务，暂不关注自定义工具与复杂治理。
*   [ ] **Logic First**: 集中精力编写 `Orchestrator` 的 Prompt Engineering 和 `Graph` 的状态流转逻辑。
*   [ ] **SaaS Observability**: 直接集成 **Langfuse Cloud** (Free Tier)，一行代码实现 Trace 和 Token 统计，跳过本地日志系统开发。
*   [ ] **Community Tools**: 仅使用社区成熟的 MCP Server (如 `brave-search`, `filesystem`)，不编写任何自定义 Tool 代码。

### Phase 2: 深度能力构建 (Deep Capabilities) - Weeks 3-4
**目标**: 引入 **Code Execution** 与 **Context Distillation**，提升解决问题的深度。
*   [ ] **Docker Sandbox**: 实现 `Data Analyst` 节点，基于 Docker 容器运行 Python 代码，替代 LLM 的数值计算。
*   [ ] **Context Summarizer**: 实现“知识蒸馏”节点，在父子任务传递间压缩上下文。
*   [ ] **MVP Release**: 此时可发布 v0.1.0 版本，具备完整的深度研究能力。

### Phase 3: 企业级增强 (Enterprise Enhancement) - Future
**目标**: 仅在需求明确时，投资开发自定义中间件与私有化工具。
*   [ ] **Custom Tools**: 在 `servers/` 目录中开发专用的 MCP Server (如内部 API Connector)。
*   [ ] **Middleware**: 替换 Langfuse Cloud 为私有化中间件，实现复杂的 Token 熔断策略。
*   [ ] **MicroVM**: 升级 Docker Sandbox 为 Firecracker MicroVM 以满足多租户隔离需求。

## 4. 全局项目结构预览 (Project Structure Preview)

采用 Monorepo 结构，其中 `servers/` 目录专门用于储备未来 Phase 3 需要的自定义 MCP 服务能力。

```text
changflow-root/
├── libs/                 # 公共库层
│   └── agent-core/       # 核心框架 (State, Orchestrator, Middleware)
├── agents/               # 应用层 (Consumers of MCP)
│   ├── deep-research/    # 深度研究智能体 (Python)
│   └── ...
├── servers/              # 协议层 (Providers of MCP) - [Phase 3 Focus]
│   ├── knowledge-graph/  # [Custom] 知识图谱读写服务
│   ├── local-analyzer/   # [Custom] 本地数据分析服务
│   └── ...               # 其他自定义 MCP Server
├── deploy/               # 部署层 (Docker Compose)
└── docs/                 # 文档层
```

## 5. 总结

本项目旨在通过**分形编排**与**自适应上下文**技术突破现有 Agent 的能力天花板，同时通过**MCP 标准**与**治理中间件**确保系统的落地可行性与安全性。


---
此文档将随着项目的演进持续更新。