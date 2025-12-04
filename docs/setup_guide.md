# Deep Research Agent - 安装与部署指南

本指南将帮助你在本地环境搭建并运行 Deep Research Agent。由于项目采用 Monorepo 结构，请仔细阅读路径配置部分。

## 环境要求

*   **OS**: Windows, macOS, or Linux
*   **Python**: >= 3.10
*   **Git**
*   **Docker & Docker Compose** (可选，用于容器化部署)

## 1. 克隆项目

```bash
git clone <repository-url>
cd deep-research-agent
```

## 2. 本地开发环境搭建 (Local Setup)

如果你想进行代码开发和调试，请按照此步骤操作。

### 2.1 创建虚拟环境

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

### 2.2 安装依赖

由于采用 Monorepo 结构，必须先安装核心库 `agent-core`，再安装应用依赖。

```bash
# 1. 以 Editable 模式安装核心库 (允许实时修改 libs 代码)
pip install -e libs/agent-core

# 2. 安装 Agent 具体依赖
pip install -r agents/deep-research/requirements.txt
```

### 2.3 配置环境变量

在 `agents/deep-research` 目录下复制示例配置并创建 `.env` 文件：

```bash
cp agents/deep-research/.env.example agents/deep-research/.env
# Windows: copy agents\deep-research\.env.example agents\deep-research\.env
```

编辑 `agents/deep-research/.env`，填入 API Keys：

```ini
OPENAI_API_KEY=sk-xxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxx
# ...其他配置
```

### 2.4 运行服务

为了确保 Python 能正确找到模块，设置 `PYTHONPATH` 并启动服务。

**Windows CMD:**
```cmd
set PYTHONPATH=%CD%\agents\deep-research\src
python -m uvicorn deep_research_agent.app:app --host 0.0.0.0 --port 8000 --reload
```

**PowerShell:**
```powershell
$env:PYTHONPATH = "$PWD/agents/deep-research/src"
python -m uvicorn deep_research_agent.app:app --host 0.0.0.0 --port 8000 --reload
```

**Linux / macOS:**
```bash
export PYTHONPATH=$(pwd)/agents/deep-research/src
python -m uvicorn deep_research_agent.app:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. 使用 Docker Compose 部署 (推荐)

这是最简单的运行方式，适合快速体验或生产部署。

### 3.1 启动服务

进入部署目录并启动：

```bash
# 进入部署目录
cd deploy

# 启动 (自动构建镜像)
docker-compose up -d --build
```
*Docker Compose 会自动读取 `../agents/deep-research/.env` 文件中的配置。*

### 3.2 访问服务

*   **API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **前端界面**: [http://localhost:3000](http://localhost:3000) (如果启动了前端服务)

### 3.3 管理容器

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 4. 常见问题 (FAQ)

**Q: 找不到 `agent_core` 模块？**
A: 请确保你执行了 `pip install -e libs/agent-core`。

**Q: Docker 启动失败，提示找不到文件？**
A: 请确保你在 `deploy/` 目录下运行 `docker-compose` 命令，且根目录结构完整。

**Q: 前端无法连接后端？**
A: 检查 `.env` 中的 `NEXT_PUBLIC_API_URL` (如果是 Next.js) 或前端配置，确保指向 `http://localhost:8000`。
