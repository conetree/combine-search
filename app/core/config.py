from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Agent Service"
    PROJECT_DESCRIPTION: str = "基于FastAPI和LangChain的智能助手服务"
    
    # CORS设置
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # AI模型配置
    INTERNAL_AI_API_URL: str
    INTERNAL_AI_API_KEY: str
    
    # 会话配置
    MAX_CONTEXT_LENGTH: int = 10
    
    class Config:
        env_file = ".env"

settings = Settings() 