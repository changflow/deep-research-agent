"""
Core Context Management Module
Provides generic capability for vector embedding and similarity search over state objects.
"""

import math
import logging
import asyncio
from typing import List, Any, Tuple, Optional, Protocol, TypeVar, Generic
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

class Vectorizable(Protocol):
    """Protocol for objects that can be indexed/retrieved via vector search"""
    embedding: Optional[List[float]]
    content: str
    # metadata: Optional[dict]

T = TypeVar("T", bound=Vectorizable)

class ContextManager(Generic[T]):
    """
    Generic Context Manager using in-memory vector similarity.
    Can be used with any object adhering to Vectorizable protocol.
    """
    
    def __init__(self, embedding_model: Optional[Embeddings] = None):
        self.embedding_model = embedding_model

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single string asynchronously with retry"""
        if not self.embedding_model:
            logger.warning("No embedding model configured for ContextManager.")
            return []
            
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Check if model supports async
                if hasattr(self.embedding_model, 'aembed_query'):
                    return await self.embedding_model.aembed_query(text)
                else:
                    return self.embedding_model.embed_query(text)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error generating embedding after {max_retries} attempts: {e}")
                    return []
                else:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Error generating embedding (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    async def retrieve(
        self, 
        query: str, 
        items: List[T], 
        top_k: int = 3,
        threshold: float = 0.4
    ) -> List[Tuple[T, float]]:
        """
        Retrieve top-k items relevant to the query from the provided list.
        Returns list of (item, score) tuples.
        """
        if not items:
            return []
            
        # Generate query embedding
        query_vec = await self.get_embedding(query)
        if not query_vec:
            return []
            
        scored_items = []
        
        for item in items:
            # Skip if no embedding available
            if not item.embedding:
                continue
                
            score = self._cosine_similarity(query_vec, item.embedding)
            
            if score >= threshold:
                scored_items.append((item, score))
                
        # Sort by score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        return scored_items[:top_k]

    def format_context_string(self, items: List[Tuple[T, float]], content_extractor: Optional[Any] = None) -> str:
        """
        Format retrieved items into a context string.
        content_extractor: optional callable to extract string from item, defaults to item.content
        """
        if not items:
            return "No relevant context found."
            
        context_parts = []
        for i, (item, score) in enumerate(items):
            if content_extractor:
                text = content_extractor(item)
            else:
                # Default behavior: try to use nuggets if available (DeepResearch specific convention but harmless to check generic attr), else content
                if hasattr(item, 'nuggets') and item.nuggets:
                    # Specific Logic for Research Agent moved to generic: 
                    # ideally we pass a lambda for this. But for now, let's keep it simple.
                    text = "\n- ".join(item.nuggets)
                else:
                    text = item.content[:500] + "..." if len(item.content) > 500 else item.content
            
            context_parts.append(f"[Context {i+1} | Score: {score:.2f}]:\n{text}")
            
        return "\n\n".join(context_parts)
