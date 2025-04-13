from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class ChatMessage(BaseModel):
    """聊天消息模型"""
    content: str = Field(..., description="消息内容")
    role: str = Field(default="user", description="消息角色: user/assistant")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户输入的消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    context: Optional[Dict] = Field(default={}, description="额外上下文信息")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str = Field(..., description="AI响应内容")
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="响应状态: success/error")

class ScrapeRequest(BaseModel):
    """网页抓取请求模型"""
    urls: List[str] = Field(..., description="待抓取的URL列表")
    max_retries: int = Field(default=3, description="最大重试次数")

class ScrapeResult(BaseModel):
    """单个URL抓取结果"""
    url: str = Field(..., description="抓取的URL")
    content: Optional[str] = Field(None, description="抓取的内容")
    success: bool = Field(..., description="是否抓取成功")
    error: Optional[str] = Field(None, description="错误信息")

class ScrapeResponse(BaseModel):
    """网页抓取响应模型"""
    results: List[ScrapeResult] = Field(..., description="抓取结果列表")
    total: int = Field(..., description="总URL数")
    success_count: int = Field(..., description="成功数量") 