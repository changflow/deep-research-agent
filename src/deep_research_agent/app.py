"""
FastAPI 应用程序入口
提供 REST API 接口，用于与 Research Agent 交互
"""

import logging
from typing import Dict, Any, Optional
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core.state import create_agent_state, AgentConfiguration, AgentStatus
from .graph import agent_app
from .utils.config import get_settings
from .core.hitl import hitl_manager
from .middleware.implementations import (
    LoggingMiddleware, 
    TracingMiddleware, 
    ErrorHandlerMiddleware,
    PerformanceMiddleware,
    register_global_middlewares
)

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取配置
settings = get_settings()

# 注册全局中间件
register_global_middlewares([
    LoggingMiddleware(),
    TracingMiddleware(),
    ErrorHandlerMiddleware(),
    PerformanceMiddleware()
])

# 创建 FastAPI 应用
app = FastAPI(
    title="Deep Research Agent API",
    description="API for Autonomous Research Agent with Human-in-the-Loop",
    version="0.1.0"
)

# 配置 CORS
# 注意：如果 allow_origins=["*"]，则 allow_credentials 必须为 False
# 如果确实需要 allow_credentials=True，则 allow_origins 不能为 ["*"]，必须指定具体域名或使用 pattern
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,  # 改为 False 以支持 origin="*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 请求/响应模型 ===

class ResearchRequest(BaseModel):
    query: str
    config: Optional[AgentConfiguration] = None

class ResearchResponse(BaseModel):
    session_id: str
    status: str
    message: str

class FeedbackRequest(BaseModel):
    session_id: str
    feedback: Dict[str, Any]

class StatusResponse(BaseModel):
    session_id: str
    status: AgentStatus
    current_step: Optional[str] = None
    plan_summary: Optional[str] = None
    pending_action: Optional[Dict[str, Any]] = None
    final_report: Optional[str] = None  # Changed from result to match frontend expectation
    error: Optional[str] = None
    research_plan: Optional[Dict[str, Any]] = None
    extracted_insights: Optional[Dict[str, Any]] = None
    waiting_for_approval: bool = False


# === 后台任务 ===

async def run_agent_background(session_id: str, state_dict: Dict[str, Any]):
    """后台运行 Agent"""
    try:
        # 这里的 state_dict 只是初始状态，LangGraph 会处理状态流转
        # config 参数用于 checkpointer 配置
        config = {"configurable": {"thread_id": session_id}}
        
        # 运行图直到结束或中断
        async for event in agent_app.astream(state_dict, config=config):
            # event 包含每步的状态更新，这里可以用来推送 WebSocket 消息等
            # 简单起见，我们暂时只记录日志
            pass
            
    except Exception as e:
        logger.error(f"Agent execution failed for session {session_id}: {e}")


# === API 路由 ===

@app.post("/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """开始新的研究任务"""
    import uuid
    import traceback
    session_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Starting research session: {session_id}")
        logger.info(f"Request config: {request.config}")

        # 创建初始状态
        try:
            initial_state = create_agent_state(
                user_query=request.query,
                session_id=session_id,
                config=request.config
            )
            logger.info(f"Initial state created for session: {session_id}")
        except Exception as e:
            logger.error(f"Error creating agent state: {e}")
            raise ValueError(f"Failed to create agent state: {e}")
        
        # 启动后台任务
        try:
            # Ensure state is serializable
            state_dict = initial_state.model_dump()
            background_tasks.add_task(
                run_agent_background,
                session_id,
                state_dict
            )
            logger.info(f"Background task added for session: {session_id}")
        except Exception as e:
            logger.error(f"Error adding background task: {e}")
            raise ValueError(f"Failed to add background task: {e}")
        
        return ResearchResponse(
            session_id=session_id,
            status="started",
            message="Research task started successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to start research: {e}")
        # Include traceback in detail if possible
        err_detail = f"{str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=err_detail)


@app.get("/research/{session_id}/status", response_model=StatusResponse)
async def get_status(session_id: str):
    """获取研究任务状态"""
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # 获取当前状态快照
        snapshot = await agent_app.aget_state(config)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Session not found")
            
        state_data = snapshot.values
        # state_data 可能是 ResearchAgentState 对象或字典，取决于 LangGraph 版本
        # 这里假设是对象，如果不是则转换
        if isinstance(state_data, dict):
            # 注意：这是一个简化的处理，实际可能需要更复杂的解析
            status = state_data.get("status", AgentStatus.PLANNING)
            current_step_idx = state_data.get("current_step_index", 0)
            plan = state_data.get("research_plan")
        else:
            status = state_data.status
            current_step_idx = state_data.current_step_index
            plan = state_data.research_plan
            
        current_step_title = None
        plan_summary = None
        if plan:
            steps = plan.get("steps", []) if isinstance(plan, dict) else plan.steps
            plan_summary = f"{len(steps)} steps planned"
            if 0 <= current_step_idx < len(steps):
                step = steps[current_step_idx]
                current_step_title = step.get("title") if isinstance(step, dict) else step.title

        # 检查是否有挂起的 HITL 事件
        pending_action = None
        if isinstance(state_data, dict):
            pending_event = state_data.get("pending_hitl_event")
            extracted_insights = state_data.get("extracted_insights")
        else:
            pending_event = state_data.pending_hitl_event
            extracted_insights = state_data.extracted_insights
            
        waiting_for_approval = False
        if pending_event:
            event_dict = pending_event.dict() if hasattr(pending_event, "dict") else pending_event
            pending_action = {
                "type": event_dict.get("event_type"),
                "payload": event_dict.get("payload")
            }
            # Simple heuristic for waiting_for_approval based on pending event existence
            # Ideally should check event type
            waiting_for_approval = True
            
        # Convert plan to dict if model
        research_plan_dict = None
        if plan:
            research_plan_dict = plan.dict() if hasattr(plan, "dict") else plan

        return StatusResponse(
            session_id=session_id,
            status=status,
            current_step=current_step_title,
            plan_summary=plan_summary,
            pending_action=pending_action,
            final_report=state_data.get("final_report") if isinstance(state_data, dict) else state_data.final_report,
            error=state_data.get("error_message") if isinstance(state_data, dict) else state_data.error_message,
            research_plan=research_plan_dict,
            extracted_insights=extracted_insights,
            waiting_for_approval=waiting_for_approval
        )
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/{session_id}/feedback")
async def submit_feedback(session_id: str, request: FeedbackRequest):
    """提交用户反馈 (HITL)"""
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # 获取当前状态
        snapshot = await agent_app.aget_state(config)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Session not found")
            
        current_state = snapshot.values
        
        # 使用 HITL 管理器处理反馈
        # 注意：我们需要先恢复状态对象，然后处理，再更新图状态
        # 在 LangGraph 中，我们通常更新状态并继续执行
        
        # 这里我们简单地将反馈注入状态，并更新状态图以继续执行
        
        # 1. 准备全量状态更新
        # 使用全量更新以防止部分更新导致字段（如 research_plan, trace_id）丢失
        if isinstance(current_state, dict):
            new_state = current_state.copy()
        else:
            # 假设是 Pydantic 模型
            new_state = current_state.model_dump()

        # 应用更新
        new_state["human_feedback"] = request.feedback
        new_state["pending_hitl_event"] = None # 清除挂起事件
        
        # 确保 trace_id 存在 (虽然全量复制应该已经包含了，但为了保险再次确认)
        if "trace_id" not in new_state and hasattr(current_state, "trace_id"):
             new_state["trace_id"] = getattr(current_state, "trace_id")

        # 根据反馈类型调整状态逻辑
        action = request.feedback.get("action")
        if action == "approve":
            new_state["status"] = AgentStatus.EXECUTING
        elif action == "modify":
             # 对于 modify，我们也继续执行，并重置步骤索引
             new_state["status"] = AgentStatus.EXECUTING
             new_state["current_step_index"] = 0
             # 注意：实际修改计划的逻辑比较复杂，这里暂不深入实现仅记录反馈
        elif action == "reject":
            new_state["status"] = AgentStatus.ERROR
            new_state["error_message"] = "Rejected by user"
            
        # 更新状态快照
        await agent_app.aupdate_state(config, new_state)
        
        # 继续执行 (Resume)
        # 不等待结果，后台运行
        # 这里创建一个新的后台任务来恢复执行
        import asyncio
        background_task = asyncio.create_task(
            # 传入 None 作为 input 表示继续执行
            _resume_graph(config) 
        )
        
        return {"status": "success", "message": "Feedback received, resuming execution"}
        
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _resume_graph(config):
    """辅助函数：恢复图执行"""
    async for event in agent_app.astream(None, config=config):
        pass


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理工作"""
    logger.info("Shutting down application...")
    
    # 查找并刷新 TracingMiddleware
    from .middleware.base import middleware_manager
    for middleware in middleware_manager.middlewares:
        if isinstance(middleware, TracingMiddleware):
            logger.info("Flushing tracing data...")
            middleware.flush()

# === 静态文件挂载 (放在最后) ===
# 获取 html 目录的绝对路径
# 假设 app.py 在 src/deep_research_agent/app.py
# html 在 deep-research-agent/html
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_DIR = os.path.join(BASE_DIR, "html")

if os.path.exists(HTML_DIR):
    # html=True 允许访问 / 时自动返回 index.html
    app.mount("/", StaticFiles(directory=HTML_DIR, html=True), name="static")
    logger.info(f"Mounted static files from {HTML_DIR}")
else:
    logger.warning(f"HTML directory not found at {HTML_DIR}")

if __name__ == "__main__":
    import uvicorn
    u_settings = get_settings()
    uvicorn.run(app, host=u_settings.HOST, port=u_settings.PORT)
