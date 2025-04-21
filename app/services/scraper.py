import random
import string
import subprocess
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.core.logging import logger
from app.services.search_service import SearchService
from app.services.search_engine_factory import DefaultSearchEngineFactory

# --------------------
# 配置与常量
# --------------------
@dataclass(frozen=True)
class ScraperConfig:
    default_retries: int = 5
    default_timeout: int = 5  # seconds
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
    )
    headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "identity",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "TE": "Trailers"
    })

# --------------------
# 工具函数
# --------------------
# 自定义依赖项保持不变

def generate_random_cookie() -> str:
    """生成随机 Cookie 字符串"""
    uid = random.randint(100000, 999999)
    session = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
    token = ''.join(random.choices(string.hexdigits.lower(), k=32))
    return f"__uid={uid}; session_id={session}; token={token}"


def get_enhanced_headers(config: ScraperConfig) -> Dict[str, str]:
    """统一请求头处理方法，生成带随机 Cookie 的请求头"""
    hdrs = {"User-Agent": config.user_agent, **config.headers}
    hdrs["Cookie"] = generate_random_cookie()
    return hdrs


def retry_operation(max_retries: int, delay_factor: float = 1.0):
    """装饰器：带指数退避的重试逻辑"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    wait = delay_factor * (2 ** (attempt - 1))
                    logger.warning(f"{func.__name__} failed (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(wait)
            raise RuntimeError(f"{func.__name__} failed after {max_retries} attempts")
        return wrapper
    return decorator

# --------------------
# 搜索引擎服务工厂
# --------------------
class SearchEngineFactory:
    @staticmethod
    def get(service_name: str, tool: str = "request", force: bool = False) -> SearchService:
        return DefaultSearchEngineFactory.get_service(service_name, tool, force)

# 供随机使用的工具
SEARCH_TOOLS = ["request", "curl", "scrapy", "cloudscraper", "agent"]

def random_bing_service() -> SearchService:
    tool = random.choice(SEARCH_TOOLS)
    return SearchEngineFactory.get("bing", tool)

def random_baidu_service() -> SearchService:
    tool = random.choice(SEARCH_TOOLS)
    return SearchEngineFactory.get("baidu", tool)

def random_search_service() -> SearchService:
    tool = random.choice(SEARCH_TOOLS)
    return SearchService(tool)

# 搜索引擎默认使用cloudscraper工具，反封禁能力略强
default_search = SearchService("cloudscraper")
bing_cloudscraper = SearchEngineFactory.get("bing", "cloudscraper")
baidu_cloudscraper = SearchEngineFactory.get("baidu", "cloudscraper")

# 外网抓取部署到机房需要翻墙，因此需要使用firecrawl，但该工具要收费
duckduckgo_firecrawl = SearchEngineFactory.get("duckduckgo", "firecrawl")
# google_firecrawl = SearchEngineFactory.get("google", "firecrawl")

# --------------------
# 整理抓取的内容，组装数据。默认只返回2条结果。
# --------------------
def wrap_response_result(response: dict, limit_num: int = 2) -> str:
    """整理搜索结果为文本，返回前 N 条"""
    items = response.get("data") or []
    if isinstance(items, str):
        return items

    selected = items[:limit_num]
    lines = []
    for item in selected:
        url = item.get("url", "")
        content = item.get("content", "")
        lines.append(f"链接：{url}\n内容：{content}\n")
    return "".join(lines)

# --------------------
# 提取html文本
# --------------------
def extract_content_text(html: str) -> str:
    """提取 HTML 可见文本"""
    soup = BeautifulSoup(html, "html.parser")
    texts = []
    for tag in soup.find_all(text=True):
        parent = tag.parent
        if parent.name in ["style", "script", "head", "title", "meta"]:
            continue
        style = parent.get("style", "")
        if "display:none" in style:
            continue
        text = tag.strip()
        if text:
            texts.append(text)
    return " ".join(texts)

# --------------------
# 异常定义
# --------------------
class FetchError(Exception):
    pass

# --------------------
# 数据抓取类
# --------------------
class WebScraper:
    def __init__(self, config: ScraperConfig = ScraperConfig()):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    @retry_operation(ScraperConfig.default_retries)
    def fetch_with_curl(self, url: str, timeout: Optional[int] = None) -> str:
        timeout = timeout or self.config.default_timeout
        cmd = ["curl", "-L", "-m", str(timeout), url]
        headers = get_enhanced_headers(self.config)
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout

    def scrape_douban_detail(self, url: str) -> str:
        """抓取单个URL的内容"""
        resp = self.session.get(url, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(strip=True)

    def scrape_urls(self, urls: List[str]) -> List[Dict]:
        """抓取多个URL的内容"""
        results = []
        for url in urls:
            try:
                content = self.scrape_web_url(url)
                results.append({"url": url, "content": content, "success": True})
            except Exception as e:
                results.append({"url": url, "error": str(e), "success": False})
        return results

    def scrape_web_url(self, url: str, headers: Optional[Dict] = None) -> str:
        """抓取单个URL的内容" 
        客户端自动选用随机搜索工具进行fetch"""
        client = default_search.get_client()
        resp = client.fetch(url, headers=headers or {})
        return extract_content_text(resp)

    def duckduckgo_search_web(self, query: str, links_num: int = 1, headers: Optional[Dict] = None) -> str:
        """搜索网页并根据搜索结果抓取网页返回"""
        res = duckduckgo_firecrawl.search_web(query=query, links_num=links_num, headers=headers or {})
        data = wrap_response_result(res)
        return data.strip()

    def baidu_search_web(self, query: str, links_num: int = 1, headers: Optional[Dict] = None) -> str:
        """搜索网页并根据搜索结果抓取网页返回"""
        res = baidu_cloudscraper.search_web(query=query, links_num=links_num, headers=headers or {})
        # res = random_baidu_service.search_web(query=query, links_num=links_num, headers=headers or {})
        data = wrap_response_result(res)
        return data.strip()

    def bing_search_web(self, query: str, links_num: int = 1, headers: Optional[Dict] = None) -> str:
        """搜索网页并根据搜索结果抓取网页返回"""
        # res = bing_cloudscraper().search_web(query=query, links_num=links_num, headers=headers or {})
        res = random_bing_service().search_web(query=query, links_num=links_num, headers=headers or {})
        data = wrap_response_result(res)
        return data.strip()

    def scrape_baike_url(self, url: str) -> str:
        """抓取单个URL的百科内容，优先豆瓣链接"""
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # 寻找豆瓣链接
        for link in soup.select(".sc-link"):
            if "豆瓣" in link.get_text():
                return self.scrape_douban_detail(link["href"])
        raise FetchError("未找到豆瓣链接")

