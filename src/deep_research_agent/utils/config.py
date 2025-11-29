"""
配置管理工具
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv

# 计算项目根目录的 .env 路径
# 假设 config.py 在 src/deep_research_agent/utils/config.py
# 项目根目录在 ../../../
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    """全局应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="ignore"
    )
    
    # 环境配置
    ENVIRONMENT: str = Field("development")
    DEBUG: bool = Field(True)
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(None)
    OPENAI_BASE_URL: Optional[str] = Field(None)
    TAVILY_API_KEY: Optional[str] = Field(None)
    
    # 模型配置
    LLM_MODEL: str = Field("gpt-4o")

    # Langfuse 配置
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(None)
    LANGFUSE_SECRET_KEY: Optional[str] = Field(None)
    LANGFUSE_HOST: Optional[str] = Field("https://cloud.langfuse.com")
    
    
    # 服务配置
    HOST: str = Field("0.0.0.0")
    PORT: int = Field(8000)
    CORS_ORIGINS: list = Field(["*"])
    
    # 业务默认配置
    DEFAULT_MAX_SEARCH_ITERATIONS: int = 5
    DEFAULT_MAX_SOURCES_PER_STEP: int = 10

@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()

# 为了兼容旧代码，保留 settings 变量，但建议使用 get_settings()
settings = get_settings()
