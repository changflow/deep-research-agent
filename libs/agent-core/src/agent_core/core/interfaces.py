"""
核心接口定义
定义 Gatherer, Processor, Verifier 的基础契约
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class WorkerResult(BaseModel):
    """Worker 执行结果基类"""
    success: bool
    data: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class Gatherer(ABC):
    """
    Gatherer (信息获取者)
    负责广度探索，如搜索网页、读取代码库等。
    """
    
    @abstractmethod
    async def gather(self, query: str, context: Optional[Dict[str, Any]] = None) -> WorkerResult:
        """
        执行信息收集
        Args:
            query: 收集目标/查询语句
            context: 上下文信息
        Returns:
            WorkerResult: 包含收集到的数据
        """
        pass

class Processor(ABC):
    """
    Processor (逻辑处理者)
    负责深度加工，如数据分析、代码实现等。
    """
    
    @abstractmethod
    async def process(self, data: Any, instructions: str, context: Optional[Dict[str, Any]] = None) -> WorkerResult:
        """
        执行数据处理
        Args:
            data: 输入数据
            instructions: 处理指令
            context: 上下文
        Returns:
            WorkerResult: 处理后的结果
        """
        pass

class VerificationResult(WorkerResult):
    """验证结果"""
    score: float = Field(0.0, description="验证分数 0-1")
    feedback: str = Field("", description="详细反馈")
    passed: bool = Field(False, description="是否通过验证")

class Verifier(ABC):
    """
    Verifier (质量把关者)
    负责证据验证，如来源核查、代码测试等。
    """
    
    @abstractmethod
    async def verify(self, content: Any, criteria: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        执行验证
        Args:
            content: 待验证内容
            criteria: 验证标准
            context: 上下文
        Returns:
            VerificationResult: 验证结果
        """
        pass
