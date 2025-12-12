"""
任务执行节点 (Task Execution Node)
通用执行节点，根据步骤分配的 Agent 角色动态调度 Worker
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from deep_research_agent.state import ResearchAgentState, SearchResult, ExtractedInsight, ResearchStepStatus, AgentStatus
from deep_research_agent.registry import WorkerRegistry
from deep_research_agent.utils.context_manager import context_manager
from agent_core.utils.models import get_chat_model
from agent_core.utils.config import get_settings
from agent_core.core.nodes import BaseWorkerNode
from agent_core.core.processor import LLMProcessor
from agent_core.core.interfaces import WorkerResult, VerificationResult

logger = logging.getLogger(__name__)

# 知识蒸馏提示词（Knowledge Distillation Prompt Template）
# 这里充当 Summarizer Node 的核心逻辑，将大量的搜索数据与背景上下文压缩为高密度的 Knowledge Nuggets
# 注意：我们将 {search_results} 替换为通用 {data} 以适配 Processor
DISTILLATION_TEMPLATE = """
你是一个专业的研究分析师。你的任务是进行**知识蒸馏 (Knowledge Distillation)**。
请基于提供的搜索结果以及**相关背景知识**，压缩并提取与当前研究步骤相关的高密度信息。

当前日期: {current_date}
研究主题: {topic}
当前步骤: {step_title} - {step_description}
预期输出: {expected_output}

注意：分析数据时，请务必关注时间效性。当前日期为 {current_date}。

### 相关背景知识 (Historical Context with Similarity Score):
{relevant_context}

### 搜索结果 (New Search Data):
{data}

请提取并总结关键信息，包括数据、事实、观点和引用来源。
**信息压缩要求**:
1. 不要简单的复制粘贴，去除冗余的上下文和废话。
2. 提炼出**原子化的知识点 (Knowledge Nuggets)**，即独立、完整、高密度的信息块。
3. 确保每个 Nugget 包含核心事实和来源。
4. **至关重要**：必须从"搜索结果"中提取**所有**被引用或参考的来源 URL，并放入 `sources` 列表中。

请务必以 **Strict JSON** 格式输出，不要包含任何 Markdown 代码块标记（如 ```json ... ```），只输出纯 JSON 字符串：
{{
    "content": "综合分析和提取的内容，连贯的段落... (在引用具体数据或观点时，必须保留引用标记，如 [Source 1] 或 (Author, Year))",
    "nuggets": [
        "事实1: xxx",
        "事实2: yyy (Source: URL)"
    ],
    "sources": ["https://url1.com", "https://url2.com"],
    "confidence": 0.9
}}
"""

class DeepResearchWorkerNode(BaseWorkerNode):
    """
    特定领域的 Worker Node 实现
    继承自 BaseWorkerNode，实现了 Research Agent 特有的转化逻辑
    """
    
    def get_current_step(self, state: ResearchAgentState) -> Any:
        return state.get_current_step()
        
    def get_search_query(self, state: ResearchAgentState, step: Any) -> str:
        # 优化搜索查询：
        # 1. 组合用户查询与步骤关键词
        # 2. 追加当前年份以确保时效性（针对用户反馈的“2025年”需求）
        # 3. 移除强制的 "report analysis" 后缀，以免过度限制搜索结果
        base_query = f"{state.user_query} {' '.join(step.keywords)}"
        current_year = datetime.now().year
        # 只保留年份，让关键词驱动具体的搜索意图
        return f"{base_query} {current_year}"
        
    def on_gather_complete(self, state: ResearchAgentState, step: Any, result: WorkerResult) -> Any:
        """
        Research 专属: 将 gather 结果转换为 SearchResult 对象并存入 State
        """
        raw_results = result.data or []
        formatted_results_text = ""
        
        for i, item in enumerate(raw_results):
            url = item.get("url", "")
            content = item.get("content", "") or item.get("raw_content", "") or str(item)
            
            search_result = SearchResult(
                url=url,
                title=item.get("title", f"Result {i+1}"),
                content=content[:1000],
                snippet=content[:200],
                score=item.get("score", 0.0),
                source="tavily"
            )
            
            state.add_search_result(step.step_id, search_result)
            formatted_results_text += f"Source {i+1} ({url}):\n{content[:500]}...\n\n"
            
        return formatted_results_text  # 返回给 Processor 使用的数据

    def on_verify_complete(self, state: ResearchAgentState, step: Any, result: VerificationResult):
        """
        Research 专属: 处理验证结果
        即使 Critic 认为结果不合格，为了保证流程畅通和最终报告的生成，我们只记录警告而不中断。
        用户痛点：不要机械地报错，确保护生成最终报告。
        """
        if not result.passed:
            error_msg = f"Critic Rejected Search Results (Ignored to ensure report generation). Score: {result.score}. Feedback: {result.feedback}"
            logger.warning(f"Step {step.step_id} verification failed but proceeding: {error_msg}")
            
            # 记录在 Logs 里供后续参考，但不阻止 Process 阶段
            # 可以在 State 中记录 Quality Warning
            if not hasattr(state, "quality_warnings"):
                state.quality_warnings = []
            state.quality_warnings.append(f"Step {step.step_id}: {error_msg}")
        else:
            logger.info(f"Step {step.step_id} verified successfully. Score: {result.score}")

    def get_process_instruction(self, state: ResearchAgentState, step: Any, gather_data: Any) -> str:
        # Context Management Middleware has already injected context into state.context_buffer
        context_str = state.context_buffer or "No previous context available."
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Inject context into template
        # The resulting string still needs {data}, {topic}, etc. for BaseWorkerNode to format
        return DISTILLATION_TEMPLATE.replace("{relevant_context}", context_str).replace("{current_date}", current_date_str)

    def on_process_complete(self, state: ResearchAgentState, step: Any, result: WorkerResult):
        """
        Research 专属: 将 process 结果转换为 ExtractedInsight 对象
        Note: Auto-embedding is handled by ContextManagementMiddleware
        """
        insight_data = result.data
        if not isinstance(insight_data, dict):
            # Fallback
            insight_data = {"content": str(insight_data), "sources": [], "confidence": 0.5}
            
        # 1. Extract content and nuggets
        content = insight_data.get("content", "")
        
        # Ensure nuggets is a list
        nuggets = insight_data.get("nuggets", [])
        if isinstance(nuggets, str):
            nuggets = [nuggets]
        
        # Handle sources extraction and merging
        extracted_sources = insight_data.get("sources", [])
        # Ensure it's a list (handle potential LLM string output)
        if isinstance(extracted_sources, str):
            extracted_sources = [extracted_sources]
            
        # Get all raw search result URLs for this step
        step_results = state.search_results.get(step.step_id, [])
        raw_urls = [r.url for r in step_results if r.url]
        
        logger.info(f"Step {step.step_id}: LLM extracted {len(extracted_sources)} sources, Raw search has {len(raw_urls)} URLs.")
        
        # Merge sources: Union of extracted and raw URLs to ensure comprehensive citation
        # We prioritize what LLM extracted, but we default to including all valid search hits as 'References'
        # Filter out empty or None
        valid_raw = {u for u in raw_urls if u}
        valid_extracted = {u for u in extracted_sources if u}
        # Use set union properly
        all_sources = list(valid_extracted.union(valid_raw))
        
        # 2. Create Insight (Embedding will be None initially)
        insight = ExtractedInsight(
            step_id=step.step_id,
            content=content,
            nuggets=nuggets,
            embedding=None, # Will be filled by Middleware
            sources=all_sources, # Use the merged list
            confidence=insight_data.get("confidence", 0.0)
        )
        
        # 3. Add to state
        # This sets 'last_generated_insight' which Middleware watches
        state.add_insight(insight)

# 实例化节点
# StateGraph 需要可调用的节点函数；这里提供一个轻量包装，内部实例化真正的 worker。

_node_instance = DeepResearchWorkerNode(
    worker_registry=WorkerRegistry,
    processor=LLMProcessor(model_name="gpt-4-turbo", temperature=0.3) 
    # TODO: Config 注入更好的方式
)

async def execute_task_node(state: ResearchAgentState) -> ResearchAgentState:
    """Wrapper function for DeepResearchWorkerNode to keep middleware working"""
    
    try:
        # 动态注入 Config 中的 LLM Model (如果需要)
        # _node_instance.processor.model_name = state.config.llm_model 
        # 由于 processor 已经初始化，这里暂时忽略动态 config update，或者每次都实例化 Node
        
        # 为了支持 Per-request Config，我们在此处实例化 Node 更好吗？
        # 是的，因为 LLMProcessor 需要 state.config.llm_model
        
        processor = LLMProcessor(model_name=state.config.llm_model, temperature=0.3)
        node = DeepResearchWorkerNode(
            worker_registry=WorkerRegistry,
            processor=processor
        )
        
        return await node(state)
    except Exception as e:
        logger.error(f"Execution Error in execute_task_node: {e}", exc_info=True)
        # 捕获异常并尝试更新当前步骤状态，避免整个 Agent 崩溃
        current_step = state.get_current_step()
        if current_step:
            current_step.status = ResearchStepStatus.FAILED
            current_step.error_message = str(e)
        else:
            state.set_error(str(e))
        return state
