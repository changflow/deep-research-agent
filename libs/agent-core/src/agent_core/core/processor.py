"""
通用处理器 (Processor) 实现
"""

import json
from typing import Any, Dict, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel

from .interfaces import Processor, WorkerResult
from ..utils.models import get_chat_model

class LLMProcessor(Processor):
    """
    通用 LLM 处理器
    基于 Prompt Template 处理输入数据
    """
    
    def __init__(self, model_name: str = "gpt-4-turbo", temperature: float = 0.3):
        self.model_name = model_name
        self.temperature = temperature
        self._llm: Optional[BaseChatModel] = None

    @property
    def llm(self) -> BaseChatModel:
        if not self._llm:
            self._llm = get_chat_model(
                temperature=self.temperature,
                model_name=self.model_name
            )
        return self._llm

    async def process(self, data: Any, instructions: str, context: Optional[Dict[str, Any]] = None) -> WorkerResult:
        """
        使用 LLM 处理数据
        
        Args:
            data: 输入数据 (通常是 text 或 search results)
            instructions: Prompt Template (字符串)
            context: 额外的上下文变量 (dict)，用于 format prompt
        """
        try:
            # 1. 准备 Context
            context = context or {}
            
            # 将 data 放入 context 中，key 为 "data" 如果 instructions 中包含 {data}
            # 或者由调用方完全控制 context
            if isinstance(data, str):
                context["data"] = data
            else:
                context["data"] = str(data)

            # 2. 构建 Prompt
            prompt = ChatPromptTemplate.from_template(instructions)
            
            # 3. 检查 Prompt 变量
            # 简单处理：直接用 context format
            messages = prompt.format_messages(**context)
            
            # 4. 调用 LLM
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # 5. 尝试解析 JSON (通用行为)
            # 很多 Process 任务要求 JSON 输出，这里做一个尝试性的解析
            # 如果失败则保留原始文本
            processed_data = content
            try:
                clean_content = content
                if "```json" in content:
                    clean_content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    clean_content = content.split("```")[1].split("```")[0].strip()
                
                processed_data = json.loads(clean_content)
            except Exception:
                pass # Not JSON, keep text

            return WorkerResult(
                success=True,
                data=processed_data,
                metadata={"raw_output": content}
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                data=None,
                error=str(e)
            )
