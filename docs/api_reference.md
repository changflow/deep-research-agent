# Deep Research Agent - API 接口文档

本文档描述了 Agent 对外提供的 HTTP REST API。所有接口默认基于 `http://localhost:8000`。

## Base Request/Response
所有接口均返回 JSON 格式数据。

---

## 1. 创建研究任务

**Endpoint**: `POST /research`

**描述**: 初始化一个新的研究会话。这会启动 LangGraph 引擎并生成初始计划。

**Request Body**:
```json
{
    "query": "2025年人工智能在医疗领域的最新应用",
    "config": {
        "max_search_iterations": 5,
        "require_plan_approval": true
    }
}
```
*   `query` (string, required): 研究主题。
*   `config` (object, optional): 配置项，如最大搜索步长或是否需要人工审批。

**Response (200 OK)**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "started"
}
```

---

## 2. 查询任务状态

**Endpoint**: `GET /research/{session_id}/status`

**描述**: 轮询当前会话的执行状态、计划详情和最终报告。

**Request Params**:
*   `session_id` (path, required): 任务 ID。

**Response (200 OK)**:
```json
{
    "status": "plan_review",  // 或 "planning", "executing", "completed", "failed"
    "waiting_for_approval": true,
    "research_plan": {
        "objective": "Research Report on AI in Healthcare",
        "steps": [
            {"title": "Analyze Market", "description": "..."}
        ]
    },
    "extracted_insights": { ... },
    "final_report": null // 仅在 status="completed" 时有值
}
```
**Status 状态说明**:
*   `pending`: 初始化中。
*   `planning`: 正在生成研究计划。
*   `plan_review`: 计划已生成，等待人工审批（如果配置了 require_approval）。
*   `executing`: 正在执行搜索和提取信息。
*   `completed`: 报告已生成。
*   `failed`: 发生系统错误。

---

## 3. 提交反馈

**Endpoint**: `POST /research/{session_id}/feedback`

**描述**: 在 `plan_review` 阶段提交用户决策。

**Request Body**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "feedback": {
        "action": "approve", 
        "notes": "Looks good!" 
    }
}
```
*   `action`:
    *   `approve`: 同意计划，Agent 将进入 `executing` 阶段。
    *   `modify`: 拒绝并要求修改，需在 `notes` 中提供修改意见，Agent 将返回 `planning` 阶段。
*   `notes`: 附加说明或修改需求。

**Response (200 OK)**:
```json
{
    "status": "feedback_received",
    "message": "Resuming graph execution..."
}
