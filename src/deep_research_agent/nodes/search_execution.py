"""
搜索与提取节点 (Search Execution Node)
执行研究步骤，调用 Tavily 搜索，提取信息
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.state import ResearchAgentState, SearchResult, ExtractedInsight, ResearchStepStatus, AgentStatus
from ..utils.Models import get_chat_model
from ..utils.config import get_settings
from ..middleware.base import middleware_enabled

logger = logging.getLogger(__name__)

# 信息提取提示词
EXTRACTION_TEMPLATE = """
你是一个专业的研究分析师。请基于提供的搜索结果，提取与当前研究步骤相关的所有关键信息。

研究主题: {topic}
当前步骤: {step_title} - {step_description}
预期输出: {expected_output}

搜索结果:
{search_results}

请提取并总结关键信息，包括数据、事实、观点和引用来源。
请以 JSON 格式输出提取的洞察：
{{
    "content": "综合分析和提取的内容...",
    "sources": ["https://url1.com", "https://url2.com"],
    "confidence": 0.9
}}
"""

@middleware_enabled
async def execute_search_step(state: ResearchAgentState) -> ResearchAgentState:
    """
    执行当前研究步骤的搜索任务
    """
    current_step = state.get_current_step()
    if not current_step:
        logger.warning("No current step found")
        return state
    
    logger.info(f"Executing search for step: {current_step.title}")
    
    # 更新步骤状态
    current_step.status = ResearchStepStatus.EXECUTING
    current_step.start_time = datetime.now()
    state.status = AgentStatus.EXECUTING
    
    try:
        settings = get_settings()
        
        # 1. 执行搜索
        search_query = f"{state.user_query} {' '.join(current_step.keywords)}"
        logger.info(f"Search query: {search_query}")
        
        # 使用 Tavily 搜索工具
        # 注意：这里假设 TavilySearchResults 已经配置好环境变量
        try:
            search_tool = TavilySearchResults(
                max_results=state.config.max_sources_per_step,
                include_answer=True,
                include_raw_content=True
            )
            # TavilySearchResults 返回的是 List[Dict]
            raw_results = await search_tool.ainvoke({"query": search_query})
        except Exception as search_error:
            # 如果搜索工具失败，尝试 mock 或处理错误
            logger.error(f"Search tool error: {search_error}")
            if settings.DEBUG:
                logger.info("Using mock search results in DEBUG mode")
                raw_results = [
                    {"url": "https://example.com", "content": "Mock content for testing", "score": 0.9}
                ]
            else:
                raise search_error

        # 转换搜索结果
        search_results_objects = []
        formatted_results_text = ""
        
        for i, result in enumerate(raw_results):
            # Tavily 返回格式可能不同，做兼容处理
            url = result.get("url", "")
            content = result.get("content", "") or result.get("raw_content", "")
            
            search_result = SearchResult(
                url=url,
                title=result.get("title", f"Source {i+1}"),
                content=content[:1000], # 截断过长内容
                snippet=content[:200],
                score=result.get("score", 0.0),
                source="tavily"
            )
            
            state.add_search_result(current_step.step_id, search_result)
            search_results_objects.append(search_result)
            
            formatted_results_text += f"Source {i+1} ({url}):\n{content[:500]}...\n\n"
        
        # 2. 如果没有搜索结果，标记步骤为失败或跳过
        if not search_results_objects:
            logger.warning(f"No search results found for step: {current_step.step_id}")
            current_step.status = ResearchStepStatus.FAILED
            current_step.error_message = "No search results found"
            current_step.end_time = datetime.now()
            return state
            
        # 3. 信息提取与分析
        llm = get_chat_model(
            temperature=0.3,  # 低温度以获取更准确的事实
            model_name=state.config.llm_model
        )
        
        prompt = ChatPromptTemplate.from_template(EXTRACTION_TEMPLATE)
        messages = prompt.format_messages(
            topic=state.user_query,
            step_title=current_step.title,
            step_description=current_step.description,
            expected_output=current_step.expected_output,
            search_results=formatted_results_text
        )
        
        response = await llm.ainvoke(messages)
        content = response.content
        
        # 解析 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        insight_data = json.loads(content)
        
        insight = ExtractedInsight(
            step_id=current_step.step_id,
            content=insight_data.get("content", ""),
            sources=insight_data.get("sources", []),
            confidence=insight_data.get("confidence", 0.0)
        )
        
        state.add_insight(insight)
        
        # 更新步骤状态
        current_step.status = ResearchStepStatus.COMPLETED
        current_step.end_time = datetime.now()
        
        logger.info(f"Step {current_step.step_id} completed successfully")
        
        # 移动到下一步
        # 注意：这是在 Node 中更新 State，LangGraph 会持久化这个变更
        state.current_step_index += 1
        
        return state
        
    except Exception as e:
        logger.error(f"Error executing search step: {e}")
        if current_step:
            current_step.status = ResearchStepStatus.FAILED
            current_step.error_message = str(e)
            current_step.end_time = datetime.now()
        
        # 即使失败也移动到下一步，防止死循环
        state.current_step_index += 1
        
        # 不中断整个流程，只是当前步骤失败
        return state
