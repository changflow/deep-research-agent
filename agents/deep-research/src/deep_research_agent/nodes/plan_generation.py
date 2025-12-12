"""
计划生成节点 (Plan Generation Node)
负责分析用户查询并生成详细的研究计划
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from deep_research_agent.state import ResearchAgentState, ResearchPlan, ResearchStep, AgentStatus, HITLEvent
from agent_core.utils.models import get_chat_model

logger = logging.getLogger(__name__)

# 定义计划生成的提示词模板
PLAN_GENERATION_TEMPLATE = """
你是一个专业的高级研究助手。你的任务是基于用户的研究主题，创建一个详细的、结构化的分步研究计划。

当前日期: {current_date}
用户研究主题: {topic}

{feedback_context}

请生成一个包含 {max_steps} 个关键步骤的研究计划（如果主题较小可以少于此数，但不得超过）。每个步骤应该具体、可执行，并且逻辑连贯。
确保计划涵盖了主题的关键方面，从基础概念到深入分析。
重要：请基于当前日期 ({current_date}) 合理设定时间范围和研究边界。

请严格按照以下 JSON 格式输出（不要输出 markdown 代码块，只输出 JSON）：
{{
    "topic": "研究主题",
    "objective": "研究的总体目标",
    "steps": [
        {{
            "step_id": "step_1",
            "title": "步骤标题",
            "description": "详细的步骤描述，说明要做什么",
            "keywords": ["关键词1", "关键词2", "关键词3"],
            "expected_output": "该步骤预期及其输出结果",
            "assigned_agent": "researcher" 
        }}
    ],
    "estimated_duration_minutes": 15
}}
"""

async def generate_plan(state: ResearchAgentState) -> ResearchAgentState:
    """
    生成研究计划节点
    """
    logger.info(f"Generating research plan for: {state.user_query}")
    
    try:
        # 获取 LLM 模型
        llm = get_chat_model(
            temperature=0.7, 
            model_name=state.config.llm_model
        )
        
        # Check for feedback/modification notes
        feedback_context = ""
        if state.research_plan and state.research_plan.modification_notes:
            logger.info(f"Regenerating plan based on user feedback: {state.research_plan.modification_notes}")
            feedback_context = f"""
!!! CRITICAL INSTRUCTION - USER FEEDBACK OVERRIDE !!!
上一个研究计划已被用户拒绝。你必须生成一个新的计划来解决用户的反馈。
请忽略之前的任何特定时间范围或限制，严格遵循用户的最新反馈。

用户反馈意见: "{state.research_plan.modification_notes}"

你的任务：
1. 仔细阅读用户的反馈意见。
2. 彻底修改原计划中的相关步骤。
3. 如果用户要求增加特定内容，必须显式包含对应的步骤。
4. 如果用户要求删除或修改内容，必须执行。
5. 必须在步骤标题和描述中明确反映用户的修改要求。

请务必执行修改，不要保留被否决的旧计划内容！
"""
        else:
            logger.info("Generating initial plan (no feedback found)")
        
        # 构建提示词
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        # Ensure reasonable bounds for max steps
        max_steps = max(1, min(10, state.config.max_search_iterations))
        
        prompt = ChatPromptTemplate.from_template(PLAN_GENERATION_TEMPLATE)
        messages = prompt.format_messages(
            topic=state.user_query,
            feedback_context=feedback_context,
            current_date=current_date_str,
            max_steps=max_steps
        )
        
        # 调用 LLM
        response = await llm.ainvoke(messages)
        content = response.content
        
        # 解析响应
        # 这里做一个简单的 JSON 清理，防止 LLM 输出 markdown 代码块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        plan_data = json.loads(content)
        
        # 构建 ResearchPlan 对象
        steps = []
        for step_data in plan_data.get("steps", []):
            steps.append(ResearchStep(
                step_id=step_data.get("step_id"),
                title=step_data.get("title"),
                description=step_data.get("description"),
                keywords=step_data.get("keywords", []),
                expected_output=step_data.get("expected_output", ""),
                assigned_agent=step_data.get("assigned_agent", "researcher")
            ))
            
        research_plan = ResearchPlan(
            topic=plan_data.get("topic", state.user_query),
            objective=plan_data.get("objective", ""),
            steps=steps,
            estimated_duration_minutes=plan_data.get("estimated_duration_minutes", 15)
        )
        
        # 更新状态
        state.research_plan = research_plan
        state.current_step_index = 0
        state.status = AgentStatus.PLAN_REVIEW
        
        # 设置 HITL 事件，通知前端需要审批
        state.pending_hitl_event = HITLEvent(
            event_type="plan_approval",
            session_id=state.session_id,
            payload={"plan": research_plan.dict()}
        )
        
        logger.info(f"Plan generated successfully with {len(steps)} steps")
        return state
        
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        state.set_error(f"Failed to generate research plan: {str(e)}")
        return state
