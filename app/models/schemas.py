from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from datetime import datetime

from app.core.config import settings

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


ScenarioLiteral = Literal["film", "stock", "news", "product"]


class CombineRequest(BaseModel):
    """组合搜索 + 大模型提炼请求"""

    query: str = Field(..., min_length=1, max_length=2000)
    scenario: ScenarioLiteral = Field("news", description="film / stock / news / product")
    search_engine: str = Field(
        "bing",
        description="bing, baidu, duckduckgo, google, sogou, douban, so",
    )
    links_num: int = Field(2, ge=1, le=10)
    http_tool: str = Field(
        "cloudscraper",
        description="request, curl, cloudscraper, playwright, selenium, firecrawl, agent, …",
    )
    fetch_fallback_chain: Optional[List[str]] = Field(
        None,
        description="覆盖默认抓取降级链；正文过短时尝试 link 模式后按链重抓",
    )
    llm_provider: str = Field(
        "openai",
        description="openai, deepseek, zhipu, dashscope（及别名 glm, qwen）",
    )
    model: Optional[str] = Field(None, description="覆盖该厂商默认模型名")
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    system_prompt_override: Optional[str] = None
    include_raw_excerpts: bool = False
    max_context_chars: int = Field(
        default_factory=lambda: settings.MAX_CONTEXT_CHARS,
        ge=500,
        le=100_000,
    )
    locale: Optional[str] = Field(
        None,
        max_length=16,
        description="可选语言短码（如 zh），解析 film.zh.yaml",
    )


class PromptScenarioInfo(BaseModel):
    """单个场景模板解析结果"""

    scenario: str
    source: Literal["builtin", "external", "missing"]
    path: Optional[str] = None
    locale: Optional[str] = None


class PromptCatalogResponse(BaseModel):
    """提示词目录：内置 + 外部 PROMPTS_DIR 扫描"""

    prompts_dir: Optional[str] = None
    locale: Optional[str] = None
    scenarios: List[PromptScenarioInfo] = Field(default_factory=list)


class CombineResponse(BaseModel):
    llm_output: str = ""
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    raw_excerpts: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    timings: Dict[str, int] = Field(default_factory=dict)
    search_engine: str = ""
    scenario: str = ""
    locale: Optional[str] = None