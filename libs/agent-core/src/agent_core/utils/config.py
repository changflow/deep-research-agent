import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings"""
    # Langfuse configuration
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    # OpenAI configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL_NAME: str = Field(default="gpt-4o", validation_alias=AliasChoices("OPENAI_MODEL_NAME", "LLM_MODEL"))
    OPENAI_BASE_URL: Optional[str] = None
    
    # Tavily configuration
    TAVILY_API_KEY: Optional[str] = None

    # CORS configuration
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
