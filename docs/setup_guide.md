# Deep Research Agent - 安装与部署指南

本指南将帮助你在本地环境搭建并运行 Deep Research Agent.

## 环境要求

*   **OS**: Windows, macOS, or Linux
*   **Python**: = 3.13
*   **Git**

## 1. 克隆项目

```bash
git clone <repository-url>
cd deep-research-agent
```

## 2. 创建并激活虚拟环境

**Windows (CMD/PowerShell):**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. 安装依赖

我们使用 `pip` 安装核心依赖。

```bash
# 或者分别安装
pip install fastapi uvicorn langchain-openai langgraph tavily-python python-dotenv langchain_community
```

## 4. 配置环境变量

在项目根目录创建 `.env` 文件，并填入以下 API Keys：

```ini
# OpenAI Models (用于推理、规划和写作)
OPENAI_API_KEY=sk-xxxxxxxxx
OPENAI_BASE_URL=
LLM_MODEL=
# Tavily AI (用于网络搜索)
TAVILY_API_KEY=tvly-xxxxxxxxx


*   获取 **OpenAI API Key**: https://platform.openai.com/
*   获取 **Tavily API Key** (免费 Tier 可用): https://tavily.com/

## 5. 运行服务

项目提供了便捷的启动脚本。

**Windows:**
双击运行 `run_server.bat`，或者在终端执行：
```cmd
run_server.bat
```

**通用方式 (Generic):**
```bash
# 设置 PYTHONPATH 包含 src 目录
export PYTHONPATH=$PYTHONPATH:$(pwd)/src  # Linux/Mac
set PYTHONPATH=%CD%\src                   # Windows CMD

# 启动 Uvicorn Server
python -m uvicorn deep_research_agent.app:app --host 0.0.0.0 --port 8000 --reload
```

服务启动成功后，你会看到类似输出：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 5.1 使用 Docker Compose 运行（推荐）

为了简化部署过程，项目提供了 Docker Compose 配置，可以一键启动所有依赖服务。

1. **构建并启动所有服务**:
```bash
docker compose up -d --build
```

2. **访问服务**:
   - 前端界面: http://localhost:3000
   - 后端 API: http://localhost:8000

3. **查看日志**:
```bash
docker compose logs -f
```

1. **停止服务**:
```bash
docker compose down
```

如果修改了源代码，务必使用 `--build` 标志重新构建镜像以使更改生效。

## 6. 使用 Agent

1.  打开浏览器访问 **http://localhost:8000**。
2.  在输入框中输入研究主题（例如：“量子计算机的最新商业化进展”）。
3.  点击 **"Start Research"**。
4.  Agent 会首先进行规划，生成步骤后会暂停等待你的审批。
5.  在 "Research Plan" 区域查看计划，点击 **"Approve Plan"** (或提供修改建议后点击 **"Request Changes"**)。
6.  Agent 开始自动执行搜索、阅读和整合信息。
7.  完成后，页面会自动显示完整的 Markdown 报告，支持导出 PDF。
