# Deep Research Agent

> 🤖 一个基于 LangGraph、LangChain 和 FastAPI 构建的自主研究智能体。

Deep Research Agent 能够根据用户给定的复杂主题，自主制定研究计划，执行多步骤网络搜索，提取关键信息，并最终生成结构化的深度研究报告。它集成了 Human-in-the-Loop (HITL) 机制，允许用户干预计划制定和报告生成过程。

## 💡 设计理念与初衷

本项目基于最新的 **LangChain V1.0** 生态进行开发。与直接使用 LangChain 现成的 Middleware 或开箱即用的 Deep Agents 不同，本项目特意选择了 **LangGraph + 自研 HITL (Human-in-the-Loop) + 自研 Middleware** 的技术路线。

**为什么这样做？**

*   **展现底层原理**: 通过从头构建核心组件（如状态管理、中间件机制），旨在深入剖析 Agent 系统的内部运作机制，而非仅仅停留在 API 调用层面。
*   **更高的定制化能力**: 自研的中间件架构和 HITL 流程提供了比标准库更灵活的控制力，能够满足复杂的业务逻辑需求。
*   **面向深度学习**: 本项目主要面向希望深入研究 LangChain 家族架构、探索 Agent 设计模式以及追求高可控性 AI 应用的开发者和研究人员。

## 📚 文档

- [**详细设计文档 (Design Specification)**](docs/design_specification.md): 了解系统的架构设计、技术选型和核心模块。

## 👀 效果演示

### 💻 Web 界面功能

Deep Research Agent 提供了一个直观的 Web 界面，支持以下核心交互：

*   **⚙️ 参数配置**: 用户可自定义研究主题及**最大搜索步骤**，灵活控制研究深度。
*   **📝 计划审批 (HITL)**: 在执行搜索前，Agent 会生成研究计划。用户可以**审查、修改或批准**该计划，确保研究方向准确。
*   **📊 实时进度**: 界面实时展示 Agent 的当前状态（规划中、搜索中、分析中等）及执行日志，让过程透明化。
*   **📄 报告导出**: 研究完成后，支持一键将最终报告**下载为 PDF 格式**，便于分享和存档。

### 📸 界面截图

#### 1. 页面初始化
![页面初始化](res/init.png)

#### 2. Human-in-the-Loop (HITL) 审批
![HITL状态](res/hitl.png)

#### 3. 任务执行中
![执行中](res/executing.png)

#### 4. 任务完成与报告生成
![执行完成](res/completed.png)


### 📊 Langfuse Trace 示例
查看完整的 Agent 执行链路追踪，包括规划、搜索、反思和报告生成过程：
[👉 点击查看 Langfuse Trace](https://cloud.langfuse.com/project/cmhkk7puw01cnad08uwnxugs9/traces/15f6ba4c96f0d22baa439c858342349b?observation=53db5328b8a22151&timestamp=2025-11-22T08:54:01.003Z)

## ✨ 核心特性

- **🧠 自主规划**: 利用 LLM 将模糊的研究目标拆解为可执行的具体搜索步骤。
- **🕸️ 深度搜索**: 集成 Tavily API，针对每个步骤进行精准搜索和内容抓取。
- **🔍 智能提取**: 自动从搜索结果中分析并提取关键数据、事实和引用。
- **🤝 Human-in-the-Loop**: 支持人工审核机制，可随时介入调整研究方向。
- **🔌 中间件架构**: 内置日志、Tracing (Langfuse)、性能监控和错误处理中间件，生产级健壮性。
- **⚡ 异步 API**: 基于 FastAPI 提供高性能的异步 REST 接口。

## 🚀 快速开始

### 前置要求

- Python 3.10+（本项目使用Python 3.13开发）
- OpenAI API Key
- Tavily API Key
- (可选) Langfuse 公钥/私钥 (用于追踪)

### 安装

```bash
# 克隆项目
git clone https://github.com/changflow/deep-research-agent.git
cd deep-research-agent

# 设置虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -e .[all]
```

### 配置

复制 `.env.example` (如果不存在，请参考下方) 创建 `.env` 文件：

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

### 运行

启动 API 服务器：

```bash
python -m deep_research_agent.app
```

服务将在 `http://0.0.0.0:8000` 启动。

### 使用示例

1. **启动研究任务**:

```bash
curl -X POST "http://localhost:8000/research/start" \
     -H "Content-Type: application/json" \
     -d '{"query": "2025年生成式AI在医疗领域的应用趋势", "max_steps": 3}'
```

2. **检查状态**:

```bash
# 使用返回的 thread_id
curl "http://localhost:8000/research/{thread_id}/status"
```

## 🛠️ 开发与测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest test/test_graph_mock.py
```

## 🏗️项目结构

```
deep-research-agent/
├── docs/                   # 文档
│   └── design_specification.md
├── src/
│   └── deep_research_agent/
│       ├── core/           # 核心逻辑 (State, HITL)
│       ├── nodes/          # 图节点 (Plan, Search, Report)
│       ├── middleware/     # 中间件系统
│       ├── utils/          # 工具函数
│       ├── graph.py        # LangGraph 图定义
│       └── app.py          # FastAPI 应用入口
└── test/                   # 测试用例
```

## License

MIT
