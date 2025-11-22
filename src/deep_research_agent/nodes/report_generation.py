"""
报告生成节点 (Report Generation Node)
汇总所有研究洞察，生成最终研究报告
"""

import logging
import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.state import ResearchAgentState, AgentStatus
from ..utils.Models import get_chat_model
from ..middleware.base import middleware_enabled

logger = logging.getLogger(__name__)

# 报告生成提示词
REPORT_GENERATION_TEMPLATE = """
你是一个专业的研究报告撰写专家。请基于以下的研究洞察，为主题 "{topic}" 撰写一份详细的、结构化的研究报告。

当前日期：{current_date}

{user_feedback_section}

=== 提取的研究洞察 ===
{insights}

=== 收集的参考来源链接 ===
{sources_list}

=== 报告要求 ===
1. **基本信息**：必须在报告开头包含报告标题以及生成的当前日期。（注意：不要包含“撰写单位”或“作者”信息）。
2. **目录**：生成一个可点击跳转的 Markdown 目录（Table of Contents），链接到正文的各个章节标题（使用 #anchor 格式）。
3. **正文内容**：
   - 结构清晰，包含摘要、背景、核心分析章节、结论。
   - 深度分析：不仅仅是罗列事实，要进行综合分析和观点阐述。
   - 语言风格：专业、客观、学术化。
4. **引用与参考文献**：
   - 在正文中引用观点时，如果在“参考来源链接”中有对应链接，请尝试关联。
   - **必须**在报告文末包含一个“参考来源”章节，罗列所有使用的 URL，并格式化为 Markdown 链接，例如 `- [网页标题](URL)` 或直接显示 URL。确保链接可点击。

请直接输出 Markdown 格式的报告内容。
"""

@middleware_enabled
async def generate_final_report(state: ResearchAgentState) -> ResearchAgentState:
    """
    生成最终研究报告
    """
    logger.info(f"Generating final report for: {state.user_query}")
    
    try:
        # 1. 准备输入数据
        insights_text = ""
        all_sources = set()
        
        # 按照步骤顺序整理洞察
        if state.research_plan:
            for step in state.research_plan.steps:
                insight = state.extracted_insights.get(step.step_id)
                if insight:
                    insights_text += f"\n\n### 步骤：{step.title}\n"
                    insights_text += f"{insight.content}\n"
                    
                    if insight.sources:
                        all_sources.update(insight.sources)
        
        # 2. 生成报告
        llm = get_chat_model(
            temperature=0.5, 
            model_name=state.config.llm_model
        )
        
        # 格式化来源列表
        sources_text = "\n".join([f"- {s}" for s in all_sources]) if all_sources else "无特定的参考来源链接。"

        # 处理用户反馈
        feedback_section = ""
        if state.human_feedback and isinstance(state.human_feedback, dict):
            notes = state.human_feedback.get("notes")
            if notes:
                feedback_section = f"=== 用户反馈意见 ===\n请务必在撰写报告时考虑以下用户反馈/修改要求：\n{notes}\n"

        prompt = ChatPromptTemplate.from_template(REPORT_GENERATION_TEMPLATE)
        messages = prompt.format_messages(
            topic=state.user_query,
            current_date=datetime.datetime.now().strftime("%Y-%m-%d"),
            user_feedback_section=feedback_section,
            insights=insights_text,
            sources_list=sources_text
        )
        
        response = await llm.ainvoke(messages)
        report_content = response.content
        
        # 3. 更新状态
        state.final_report = report_content
        state.status = AgentStatus.FINAL_REVIEW
        state.complete_research()  # 或者进入最终审批状态
        
        logger.info("Final report generated successfully")
        return state
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        state.set_error(f"Failed to generate final report: {str(e)}")
        return state
