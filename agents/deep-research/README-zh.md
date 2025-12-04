# Deep Research Agent

> 🤖 一个基于 **AgentCore 框架** 构建的自主研究智能体实现。

Deep Research Agent 是本项目框架的一个参考实现 (Reference Implementation)。它能够根据用户给定的复杂主题，自主制定研究计划，执行多步骤网络搜索，提取关键信息，并最终生成结构化的深度研究报告。

## 💡 功能亮点

*   **🧠 自主规划**: 利用 LLM 将模糊的研究目标拆解为可执行的具体搜索步骤。
*   **🕸️ 深度搜索**: 集成 Tavily API，针对每个步骤进行精准搜索和内容抓取。
*   **🔍 智能提取**: 自动从搜索结果中分析并提取关键数据、事实和引用。
*   **🤝 Human-in-the-Loop**: 集成了框架提供的 HITL 机制，允许用户在 Web 界面上干预计划制定。
*   **📄 报告生成**: 自动汇总是所有信息并生成 Markdown/PDF 报告。

## 👀 效果演示

### 💻 Web 界面

Deep Research Agent 提供了一个直观的 Web 界面（位于根目录的 `Dockerfile.frontend` 构建）：

*   **⚙️ 参数配置**: 自定义研究主题及最大搜索步骤。
*   **📝 计划审批**: 在执行搜索前审查、修改或批准计划。
*   **📊 实时进度**: 实时展示 Agent 的当前状态及执行日志。

### 📸 截图展示

| 页面初始化 | 计划审批 (HITL) |
| :---: | :---: |
| ![Init](../../res/init.png) | ![HITL](../../res/hitl.png) |

| 任务执行中 | 报告生成完成 |
| :---: | :---: |
| ![Executing](../../res/executing.png) | ![Completed](../../res/completed.png) |

## 🚀 快速开始

### 前置要求

确保你已经安装了核心库 `agent-core` (请参考根目录说明)。

### 安装依赖

```bash
cd agents/deep-research
pip install -r requirements.txt
```

### 配置

在 `agents/deep-research/` 目录下创建 `.env` 文件：

```ini
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
# 可选：Langfuse 用于追踪
LANGFUSE_PUBLIC_KEY=...
```

### 运行

```bash
# 确保在根目录下设置了 PYTHONPATH，或者在当前目录运行：
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python -m deep_research_agent.app
```

### 查看 Trace

完整执行链路可参考 [Langfuse Trace 示例](https://cloud.langfuse.com/project/cmhkk7puw01cnad08uwnxugs9/traces/15f6ba4c96f0d22baa439c858342349b?observation=53db5328b8a22151&timestamp=2025-11-22T08:54:01.003Z)。
