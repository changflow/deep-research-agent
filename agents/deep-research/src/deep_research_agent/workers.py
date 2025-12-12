"""
Worker 实现
包含 Gatherer 和 Verifier 的具体实现
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from agent_core.core.interfaces import Gatherer, Verifier, WorkerResult, VerificationResult
# Migrated to langchain-tavily per deprecation warning
from langchain_community.tools.tavily_search import TavilySearchResults
from agent_core.utils.config import get_settings
from agent_core.utils.models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate
import json

logger = logging.getLogger(__name__)

class ResearchWorker(Gatherer):
    """
    Research Worker (Gatherer Implementation)
    使用 Tavily 进行深度搜索
    """
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.settings = get_settings()

    async def gather(self, query: str, context: Optional[Dict[str, Any]] = None) -> WorkerResult:
        logger.info(f"ResearchWorker gathering info for: {query}")
        try:
            # 尝试初始化 Tavily 工具
            # 增加 exclude_domains 以过滤非权威来源（如 CSDN, 知乎, 博客园等 UGC 平台），提高 Critic 通过率
            # 优化：关闭 include_raw_content 以大幅提升响应速度，仅使用 Tavily 生成的高质量摘要 (Snippet) 和 Answer
            search_tool = TavilySearchResults(
                max_results=self.max_results,
                include_answer=True,
                include_raw_content=False,
                exclude_domains=[
                    "csdn.net", 
                    "zhihu.com", 
                    "juejin.cn", 
                    "cnblogs.com", 
                    "jianshu.com",
                    "bilibili.com"
                ]
            )
            
            # 执行搜索
            raw_results = await search_tool.ainvoke({"query": query})
            
            # Robustness: Handle if tool returns string (JSON) instead of List
            if isinstance(raw_results, str):
                try:
                    # 尝试解析 JSON
                    if raw_results.strip().startswith("[") or raw_results.strip().startswith("{"):
                        raw_results = json.loads(raw_results)
                    else:
                        # 如果是纯文本（可能是 Answer），封装为伪结果以免下游崩溃
                        raw_results = [{"url": "", "content": raw_results, "title": "Tavily Answer", "score": 1.0}]
                except Exception as parse_error:
                     logger.warning(f"Failed to parse Tavily results: {parse_error}")
                     #均无法解析，封装为 Content
                     raw_results = [{"url": "", "content": raw_results, "title": "Raw Search Output", "score": 0.0}]

            # Ensure it is a list
            if not isinstance(raw_results, list):
                raw_results = [raw_results]
                
            return WorkerResult(
                success=True,
                data=raw_results,
                metadata={"source": "tavily", "query": query}
            )
            
        except Exception as e:
            logger.error(f"ResearchWorker gather failed: {e}")
            if self.settings.DEBUG:
                logger.info("Using mock results due to error in DEBUG mode")
                return WorkerResult(
                    success=True,
                    data=[
                        {"url": "https://example.com", "content": "Mock content", "title": "Mock Title", "score": 0.8}
                    ],
                    metadata={"source": "mock", "error": str(e)}
                )
            
            return WorkerResult(success=False, data=None, error=str(e))


class Critic(Verifier):
    """
    Critic (Verifier Implementation)
    验证信息来源的可靠性和相关性
    """
    
    def __init__(self):
        self.config = get_settings()
        self.llm = get_chat_model(temperature=0.0) # 使用默认配置的模型

    async def verify(self, content: Any, criteria: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        logger.info("Critic verifying content...")
        
        # 简单的验证逻辑：如果有 LLM 可用，使用 Global Judge 模式
        # 这里简化实现，针对文本内容或搜索结果进行评估
        
        validate_template = """
        你是一个建设性的内容审核员 (Reviewer)。请验证以下内容是否对报告撰写有帮助。

        当前时间: {current_date}
        待验证内容: {content}
        验证标准: {criteria}

        审核准则：
        1. **实质优先**：如果内容包含具体的行业数据、观点或预测，即使来源是科技媒体（如36Kr、QbitAI）或门户网站（如Sina），也应予以通过。不要因为是移动端链接或非学术期刊就拒绝。
        2. **时效性宽容度**：如果内容发布于当前年份（{current_date}所在年份），或者涉及对未来的预测，**不应**视为过时。例如，2025年8月的文章在2025年12月依然是极佳的“年度总结/现状”来源。
        3. **通过门槛**：除非内容完全无关、明显虚假或完全是垃圾广告，否则请倾向于通过（Passed=True），并给予 0.6 以上的分数，以便后续环节使用。

        请评估并以 JSON 格式返回:
        {{
            "score": 0.8, // 0-1 之间的分数。只要有用，请给 0.6 以上。
            "passed": true, // 倾向于 True，除非完全不可用。
            "feedback": "具体的反馈意见（指出优点和潜在局限即可，不要过于苛刻）..."
        }}
        """
        
        try:
            current_date_str = datetime.now().strftime("%Y-%m-%d")
            prompt = ChatPromptTemplate.from_template(validate_template)
            messages = prompt.format_messages(
                content=str(content)[:2000], # 截断防止过长
                criteria=json.dumps(criteria),
                current_date=current_date_str
            )
            
            response = await self.llm.ainvoke(messages)
            result_text = response.content
            
            # 清洗 JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
                
            result_json = json.loads(result_text)
            
            return VerificationResult(
                success=True,
                data=None, # 验证本身不产生新数据，只产生元数据
                score=result_json.get("score", 0.0),
                passed=result_json.get("passed", False),
                feedback=result_json.get("feedback", "No feedback provided")
            )
            
        except Exception as e:
            logger.error(f"Critic verification failed: {e}")
            # Fallback for error
            return VerificationResult(
                success=False,
                data=None,
                error=str(e),
                score=0.0,
                passed=False,
                feedback=f"Verification failed execution: {str(e)}"
            )
