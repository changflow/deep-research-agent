"""
Adaptive Context Management Utilities
Handles embedding generation and vector retrieval for Knowledge Nuggets.
Specific implementation for Deep Research Agent using Agent Core capability.
"""

import os
import logging
from langchain_openai import OpenAIEmbeddings
from agent_core.core.context_manager import ContextManager
from deep_research_agent.state import ExtractedInsight

logger = logging.getLogger(__name__)

def get_embeddings_model():
    """
    获取 Embedding 模型实例。
    优先使用 OpenAI Embeddings，但也支持通过配置切换到本地 HuggingFace 模型。
    
    可以通过设置环境变量 USE_LOCAL_EMBEDDINGS=true 来强制使用本地模型。
    默认本地模型为 'moka-ai/m3e-base' (适合中文)，可通过 LOCAL_EMBEDDING_MODEL 环境变量修改。
    """
    use_local = os.getenv("USE_LOCAL_EMBEDDINGS", "false").lower() == "true"
    
    # 如果指定使用本地模型，或者没有 OpenAI API Key，尝试加载本地模型
    if use_local:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            
            # moka-ai/m3e-base 是一个非常优秀的开源中文 Embedding 模型
            # BAAI/bge-small-zh-v1.5 也是极佳的选择
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "moka-ai/m3e-base")
            logger.info(f"Using local embeddings: {model_name}")
            
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'}, # 默认使用 CPU，如有 CUDA 可改为 cuda
                encode_kwargs={'normalize_embeddings': True}
            )
        except ImportError as e:
            logger.error("Requested local embeddings but dependencies are missing.")
            raise ImportError(
                "To use local embeddings (USE_LOCAL_EMBEDDINGS=true), you must install additional dependencies: "
                "pip install langchain-huggingface sentence-transformers"
            ) from e
    
    # Default to OpenAI
    logger.info("Using OpenAI embeddings")
    return OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

# Instantiate Embeddings Model
_embeddings_model = get_embeddings_model()

# Instantiate Context Manager tailored for ExtractedInsight
# ContextManager is generic, so we can alias it or just instance it.
context_manager = ContextManager[ExtractedInsight](embedding_model=_embeddings_model)
