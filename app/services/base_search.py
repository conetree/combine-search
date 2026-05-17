# service/search_service.py
"""
搜索业务处理模块：
    - 负责根据传入的 URL 列表和抓取方式，调用对应的客户端获取页面内容
    - 利用 WebScraper 对抓取到的内容进行解析处理
    - HTTP 客户端按需懒创建，避免 import 时初始化 Selenium/Playwright 等重资源
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Set

from bs4 import BeautifulSoup, Comment
from fastapi import HTTPException

from app.core.logging import logger
from app.core.search_config import config
from app.tools.http_clients import (
    AgentClient,
    BeautifulSoupClient,
    CloudscraperClient,
    CurlClient,
    FirecrawlClient,
    PlaywrightClient,
    ScrapyClient,
    SeleniumClient,
    SimpleHTTPClient,
)
from app.utils.response_utils import response_error, response_success

DEFAULT_RETRIES = config["DEFAULT_RETRIES"]
DEFAULT_TIMEOUT = config["DEFAULT_TIMEOUT"]
AGENT_URL = config["AGENT_URL"]
FIRECRAWL_API_KEY = config["FIRECRAWL_API_KEY"]
ALLOWED_DOMAIN = config["ALLOWED_DOMAIN"]

_CLIENT_KEYS: Set[str] = {
    "agent",
    "curl",
    "request",
    "firecrawl",
    "beautifulsoup",
    "scrapy",
    "selenium",
    "cloudscraper",
    "playwright",
}


class BaseSearch(ABC):
    def __init__(self) -> None:
        self.http_tool: str | None = None
        self._client_cache: Dict[str, object] = {}

    def _build_client(self, http_tool: str):
        if http_tool == "agent":
            return AgentClient(
                agent_url=AGENT_URL, retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT
            )
        if http_tool == "curl":
            return CurlClient(retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        if http_tool == "request":
            return SimpleHTTPClient(retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        if http_tool == "firecrawl":
            return FirecrawlClient(
                retries=DEFAULT_RETRIES,
                api_key=FIRECRAWL_API_KEY,
                timeout=DEFAULT_TIMEOUT,
            )
        if http_tool == "beautifulsoup":
            return BeautifulSoupClient(
                retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT
            )
        if http_tool == "scrapy":
            return ScrapyClient(retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        if http_tool == "selenium":
            return SeleniumClient(retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        if http_tool == "cloudscraper":
            return CloudscraperClient(
                retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT
            )
        if http_tool == "playwright":
            return PlaywrightClient(
                config=None, retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT
            )
        raise HTTPException(status_code=502, detail=f"未知 http_tool: {http_tool}")

    def set_http_tool(self, http_tool: str) -> None:
        self.http_tool = http_tool

    @abstractmethod
    def search(self, query, headers: dict = None):
        pass

    def get_client(self, http_tool: str = "request"):
        if http_tool not in _CLIENT_KEYS:
            raise HTTPException(status_code=502, detail="获取client失败")
        if http_tool not in self._client_cache:
            self._client_cache[http_tool] = self._build_client(http_tool)
        return self._client_cache[http_tool]

    def process_fetch(
        self, url_list: list, http_tool="curl", headers: dict = None, mode="html"
    ):
        """
        统一处理抓取请求：
            1. 根据传入的抓取方式，选择对应的客户端
            2. 遍历 URL 列表，对每个 URL 进行抓取
            3. 返回抓取结果列表，包含成功抓取的数据或错误信息
            4. 根据 mode 选择返回模式:
                - mode="html": 返回原始抓取内容
                - mode="text": 返回调用 extract_content_text 后的文本内容

        :param url_list: 要抓取的 URL 列表，列表长度不能超过 20
        :param http_tool: 抓取方式，默认为 "curl"
        :param headers: 自定义请求头，可选
        :param mode: 返回内容模式[html|text]，默认为 html
        :return: 包含抓取结果的响应
        """
        if len(url_list) > 20:
            raise HTTPException(
                status_code=400, detail="url_list 长度不能大于 20"
            )

        results = []

        client = self.get_client(http_tool)

        for url in url_list:
            try:
                content = client.fetch(url, headers=headers)
                if mode.lower() == "text":
                    data = self.extract_content_text(content)
                else:
                    data = content
                results.append({"url": url, "data": data, "success": True})
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                results.append({"url": url, "error": str(e), "success": False})
        ok = [r for r in results if r.get("success")]
        if not ok:
            return response_error(502, "全部 URL 抓取失败", results)
        return response_success(f"成功 {len(ok)}/{len(results)} 个 URL", results)

    def extract_content_text(self, html_content: str) -> str:
        """
        高级HTML净化引擎
        功能：
        1. 移除所有不可见内容（脚本/样式/元标签等）
        2. 保留语义段落结构
        3. 智能空格处理
        4. 清除隐藏注释
        """
        soup = BeautifulSoup(html_content, "lxml")

        excluded_tags = [
            "script",
            "style",
            "head",
            "title",
            "meta",
            "nav",
            "footer",
            "header",
            "iframe",
            "noscript",
            "svg",
            "button",
            "input",
            "textarea",
            "select",
            "link",
            "img",
            "figure",
            "aside",
        ]

        for tag in excluded_tags:
            for element in soup(tag):
                element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        text = soup.get_text(separator="\n", strip=True)

        clean_rules = [
            (r"\n{3,}", "\n\n"),
            (r"[ \t]{2,}", " "),
            (r"\s+([.!?])", r"\1"),
            (r"\n\s+\n", "\n\n"),
        ]

        for pattern, replacement in clean_rules:
            text = re.sub(pattern, replacement, text)

        return text.strip()

    def extract_content_text_simple(self, html_content: str) -> str:
        """
        利用 BeautifulSoup 提取网页内可见文字，排除脚本、样式、head 等内容

        :param html_content: 原始 HTML 内容
        :return: 处理后的纯文本内容
        """
        soup = BeautifulSoup(html_content, "html.parser")
        texts = []
        for element in soup.find_all(string=True):
            if not getattr(element, "parent", None):
                continue
            if element.parent.name in [
                "style",
                "script",
                "head",
                "title",
                "meta",
                "[document]",
            ]:
                continue
            if element.strip():
                texts.append(element.strip())
        return " ".join(texts)

    def _filter_result_links(self, content, domains=ALLOWED_DOMAIN):
        filtered_results = []
        for item in content:
            href = item.get("href")
            if href and any(domain in href for domain in domains):
                filtered_results.append(item)
        return filtered_results
