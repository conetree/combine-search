from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Combine Search Agent"
    PROJECT_DESCRIPTION: str = "组合搜索、网页抓取与大模型内容提炼服务"

    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # Legacy internal gateway (optional — leave empty to use OpenAI-compatible routers only)
    INTERNAL_AI_API_URL: str = ""
    INTERNAL_AI_API_KEY: str = ""

    MAX_CONTEXT_LENGTH: int = 10

    # OpenAI-compatible providers (set the key for the provider you use)
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_DEFAULT_MODEL: str = "deepseek-chat"

    ZHIPU_API_KEY: str = ""
    ZHIPU_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_DEFAULT_MODEL: str = "glm-4-flash"

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_DEFAULT_MODEL: str = "qwen-turbo"

    # Prompt templates: built-in under app/prompts; override with PROMPTS_DIR
    PROMPTS_DIR: str = ""
    PROMPTS_CACHE_ENABLED: bool = False
    PROMPTS_ADMIN_KEY: str = ""

    DEFAULT_SEARCH_ENGINE: str = "bing"
    DEFAULT_FETCH_CHAIN: str = "cloudscraper,request,curl"
    LLM_DEFAULT_PROVIDER: str = "openai"

    MAX_CONTEXT_CHARS: int = 12_000

    # cloudscraper: leave empty for library default (often js2py); set "nodejs" only if Node is installed
    CLOUDSCRAPER_INTERPRETER: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
