"""
报告生成节点 (Report Generation Node)
汇总所有研究洞察，生成最终研究报告
"""

import logging
import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from deep_research_agent.state import ResearchAgentState, AgentStatus
from agent_core.utils.models import get_chat_model

logger = logging.getLogger(__name__)

# 报告生成提示词
REPORT_GENERATION_TEMPLATE = """
你是一个专业的研究报告撰写专家。请基于以下的研究洞察，为主题 "{topic}" 撰写一份详细的、结构化的研究报告。

当前日期：{current_date}
注意：请在报告中体现当前的时间背景，例如“截至 {current_date} ...”或“最新数据表明...”。

{user_feedback_section}

=== 提取的研究洞察 (Research Insights) ===
{insights}

=== 收集的参考来源链接 (References) ===
{sources_list}

=== 报告要求 ===
1. **基本信息**：必须在报告开头包含报告标题以及生成的当前日期。（注意：不要包含“撰写单位”或“作者”信息）。
2. **目录**：生成一个可点击跳转的 Markdown 目录（Table of Contents），链接到正文的各个章节标题（使用 #anchor 格式）。
3. **正文内容**：
   - 结构清晰，包含摘要、背景、核心分析章节、结论。
   - 深度分析：不仅仅是罗列事实，要进行综合分析和观点阐述。**所有的分析必须基于上述“提取的研究洞察”**。
   - **重要**：如果提供了“收集的参考来源链接”，则**严禁**在报告中声称“无特定参考来源”或“基于行业共识”。你必须将洞察内容与参考来源对应起来。
   - 语言风格：专业、客观、学术化。
4. **引用与参考文献 (Citations)**：
   - **文中引用**：在正文中提到具体数据、事实或观点时，**必须**使用 Markdown 链接格式标注出处，例如 `[1]` 或 `(来源: Title)`。如果输入的洞察中已经包含了 `[Source 1]` 等标记，请务必保留并调整序号以匹配下方的列表。
   - **参考文献列表**：文末**必须**包含“参考来源”章节，罗列所有文中引用的来源。格式：`- [序号] [网页标题](URL)`。
   - 只要有数据来源，就必须展示。

请直接输出 Markdown 格式的报告内容。
"""

async def generate_final_report(state: ResearchAgentState) -> ResearchAgentState:
    """
    生成最终研究报告
    """
    logger.info(f"Generating final report for: {state.user_query}")
    
    try:
        # 1. 准备输入数据
        insights_text = ""
        all_sources = set()
        
        # Build URL to Title map from all search results to provide better citations
        url_to_title = {}
        for step_results in state.search_results.values():
            for res in step_results:
                if res.url:
                    url_to_title[res.url] = res.title

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
        
        # 格式化来源列表 (带标题)
        if all_sources:
            formatted_sources = []
            for i, url in enumerate(sorted(list(all_sources))):
                title = url_to_title.get(url, "Source")
                # Ensure Markdown link format with index for easier citation
                formatted_sources.append(f"{i+1}. [{title}]({url})")
            sources_text = "\n".join(formatted_sources)
        else:
            # 明确告知 LLM 没有来源，避免编造 "行业共识"
            sources_text = "（注意：本次研究未能成功收集到任何外部参考来源链接。请在报告中明确指出：'由于搜索工具限制或网络原因，本次报告未包含外部引用来源，内容仅供参考。' 严禁伪造来源。）"
            logger.warning("No validation sources found for the final report.")
            
        # 若无洞察内容，给出警告
        if not insights_text.strip():
            logger.warning("No insights collected for report generation!")
            insights_text = "（警告：本次研究未收集到有效洞察信息。请检查搜索工具或网络连接。）"

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
