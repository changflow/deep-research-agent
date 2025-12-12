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
    OPENAI_API_KEY: Optional[str] = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "DASHSCOPE_API_KEY"))
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

    def __init__(self, **values: any):
        super().__init__(**values)
        # If a .env file is specified, load it.
        # Pydantic-settings by default will NOT override existing env vars.
        # We want to override them, so we do it manually.
        env_file = self.model_config.get('env_file')
        if env_file and os.path.exists(env_file):
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
            # Re-initialize settings to pick up the new env vars
            super().__init__(**values)  


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
