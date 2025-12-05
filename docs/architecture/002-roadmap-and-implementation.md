# 002 - Architecture Blueprint: FractalMind (Next-Gen Reasoning Framework)

**Status:** Draft
**Date:** 2025-12-05
**Audience:** Architects, Developers, System Integrators

## 1. 战略愿景 (Strategic Vision)

本项目的目标是构建一个**通用的、具备深度推理能力与多场景适配性的智能体协作框架**。

区别于传统的线性任务执行（Chain-of-Thought）或单一场景的垂直 Agent，FractalMind 采用**分形编排（Fractal Orchestration）**架构，通过**“动态分解 → 并行探索 → 证据验证 → 迭代修正”**的通用认知范式，解决具有高模糊性与多维度的复杂问题。这一范式不仅适用于深度研究，通过切换“策略配置”，它同样能胜任**复杂系统编程**、**创意内容创作**或**商业情报分析**等场景。

同时，架构内置了**协议化互操作标准（MCP）**与**全链路可观测性治理**，确保这一强大的通用认知引擎时刻处于可控、透明与安全的状态。

## 2. 核心架构支柱 (Core Architectural Pillars)

### 2.1 分形认知编排系统 (Fractal Cognitive Orchestration)
系统摒弃了单一 Agent “一把抓”的模式，构建了一个通用的 **Orchestrator-Workers** 协作网络。

*   **Recursive Planning (通用递归规划)**:
    主智能体 (Lead Orchestrator) 是一个通用的问题拆解引擎。它不直接执行具体工作，而是负责定义目标接口与验收标准，并根据“子任务”反馈的中间结果，实时动态调整后续的路径（Re-planning）。
    *   **Safety Guards**: 为了确保这种强大的递归能力不失控，系统内置了 **Recursion Circuit Breaker**（递归熔断器），通过深度限制与循环检测机制，防止 Agent 陷入死循环。

*   **Adaptive Worker System (场景自适应执行者)**:
    Worker 并非硬编码的角色，而是根据场景（Domain）动态加载的**“能力角色包” (Persona Packs)**。
    *   **Gatherer (信息获取者)**: 负责广度探索。在研究场景下是 *Research Worker*（查资料），在编程场景下则是 *Repo Scanner*（读代码）。
    *   **Processor (逻辑处理者)**: 负责深度加工。在研究场景下是 *Data Analyst*（清洗数据），在编程场景下则是 *Code Implementer*（写函数）。均通过 MCP 连接安全沙箱进行确定性计算。
    *   **Verifier (质量把关者)**: 负责证据验证。在研究场景下是 *Critic*（查来源），在编程场景下则是 *Test Runner*（跑测试）。

### 2.2 自适应上下文管理 (Adaptive Context Management)
针对大模型固有的上下文窗口限制与 "Lost-in-the-Middle" 现象，引入**信息密度控制引擎**。

*   **Knowledge Distillation (知识蒸馏)**: 在层级传递中，强制执行“信息压缩”。子任务完成时，通过 `Summarizer Node` 将冗余的思维链（Chain of Thought）提炼为高密度的知识块 (Knowledge Nuggets) 上报。
*   **Dynamic Loading (动态加载)**: 并非一次性加载所有 Nuggets，而是为每个 Nugget 生成 **Vector Embedding**。在推理该步骤时，仅加载与当前 Thought 语义相似度 (Cosine Similarity) 最高的 Top-K Nuggets，实现“显存即缓存”的高效管理。

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

### Phase 1: 核心框架与 MVP 验证 (Core Framework & MVP)
**目标**: 确立 **通用编排器 (Orchestrator)** 的核心逻辑，并以 **"深度研究"** 为首个参考实现（Reference Implementation）来验证架构基础。
*   [ ] **Interface Definition (Level 1)**: 定义 `Gatherer` (信息采集) 和 `Verifier` (核心验证) 的基础接口标准。优先实现 `Research Worker` 和 `Critic` 作为首批实现类。
*   [ ] **Orchestrator Logic**: 实现具备递归与熔断（Circuit Breaker）能力的通用编排引擎。
*   [ ] **Dev Observability**: 集成 **Langfuse Cloud**，为每个 Worker 节点配置标准化的 Trace Span，用于调试。
*   [ ] **Process Visualization**: 开发实时前端 UI，将分形编排的“递归思维树”可视化展示给最终用户。

### Phase 2: 架构解耦与能力深化 (Abstraction & Deepening)
**目标**: 完成所有 Worker 角色的完全解耦，并引入深度计算能力。
*   [ ] **Processor Abstraction**: 定义 `Processor` (逻辑处理) 的通用接口。实现 **"Universal Sandbox"** (基于 Docker) 作为其默认执行环境，支持代码执行与数据清洗。
*   [ ] **Strategy Engine**: 完成策略配置化引擎，支持通过 YAML 动态组装 `Gatherer` / `Processor` / `Verifier` 的不同实现。
*   [ ] **Dynamic Context**: 实现基于 Embedding 的动态上下文加载机制。

### Phase 3: 领域扩展与企业治理 (Domain Extension & Governance) - Future
**目标**: 针对特定领域构建专用的基础设施，并增强治理能力。
*   **Multi-Tenant Quota**: 实现按 Team/Project 粒度的 Token 配额管理策略。
*   **MicroVM**: 升级 Docker Sandbox 为 Firecracker MicroVM 以满足多租户隔离需求。
*   待续......


## 4. 总结

本项目旨在通过**分形编排**与**自适应上下文**技术突破现有 Agent 的能力天花板，同时通过**MCP 标准**与**治理中间件**确保系统的落地可行性与安全性。


---
此文档将随着项目的演进持续更新。
