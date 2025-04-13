from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CombineSearch智能服务"
    PROJECT_DESCRIPTION: str = "基于搜索引擎抓取和大模型的智能分析系统"
    
    # CORS设置
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # AI模型配置
    INTERNAL_AI_API_URL: Optional[str] = None
    INTERNAL_AI_API_KEY: Optional[str] = None
    
    # 会话配置
    MAX_CONTEXT_LENGTH: int = 10
    
    class Config:
        env_file = ".env"

settings = Settings() 