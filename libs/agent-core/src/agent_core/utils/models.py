from typing import Optional
from langchain_openai import ChatOpenAI
from .config import get_settings

def get_chat_model(
    model_name: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    temperature: float = 0
) -> ChatOpenAI:
    """Get configured ChatOpenAI instance"""
    settings = get_settings()
    
    return ChatOpenAI(
        model=model_name or settings.OPENAI_MODEL_NAME,
        api_key=openai_api_key or settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature
    )
