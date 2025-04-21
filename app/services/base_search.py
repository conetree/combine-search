# service/search_service.py
"""
搜索业务处理模块：
    - 负责根据传入的 URL 列表和抓取方式，调用对应的客户端获取页面内容
    - 利用 WebScraper 对抓取到的内容进行解析处理
"""
from abc import ABC, abstractmethod
from fastapi import HTTPException
# from firecrawl import FirecrawlApp
# from duckduckgo_search import DDGS
# from app.services.scraper import WebScraper
from app.core.logging import logger
from app.core.search_config import config
from app.utils.response_utils import response_success, response_error
from bs4 import BeautifulSoup, Comment
import re
# 从工具层导入各个抓取客户端
from app.tools.http_clients import (
    AgentClient, CurlClient, SimpleHTTPClient,
    ScrapyClient, FirecrawlClient, SeleniumClient,
    CloudscraperClient, BeautifulSoupClient, PlaywrightClient)
from typing import List

# 配置常量
DEFAULT_RETRIES = config["DEFAULT_RETRIES"]
DEFAULT_TIMEOUT = config["DEFAULT_TIMEOUT"]
AGENT_URL = config["AGENT_URL"]
FIRECRAWL_API_KEY = config["FIRECRAWL_API_KEY"]
ALLOWED_DOMAIN = config["ALLOWED_DOMAIN"]

class BaseSearch(ABC):
    def __init__(self):
        # 初始化各抓取客户端，并传入相应的配置参数
        self.http_tool = None
        self.simple_client = SimpleHTTPClient(
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.curl_client = CurlClient(
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.agent_client = AgentClient(
            agent_url=AGENT_URL, retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.firecrawl_client = FirecrawlClient(
            retries=DEFAULT_RETRIES, api_key=FIRECRAWL_API_KEY, timeout=DEFAULT_TIMEOUT)
        self.beautifulsoup_client = BeautifulSoupClient(
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.scrapy_client = ScrapyClient(
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.selenium_client = SeleniumClient(
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.cloudscraper_client = CloudscraperClient(
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        self.playwright_client = PlaywrightClient(config = None,
            retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT)
        
        # 构建客户端映射，根据请求方式选择对应的客户端
        self.clients = {
            "agent": self.agent_client,
            "curl": self.curl_client,
            "request": self.simple_client,
            "firecrawl": self.firecrawl_client,
            "beautifulsoup": self.beautifulsoup_client,
            "scrapy": self.scrapy_client,
            "selenium": self.selenium_client,
            "cloudscraper": self.cloudscraper_client,
            "playwright": self.playwright_client,
        }

    def set_http_tool(self, http_tool: str):
        self.http_tool = http_tool

    @abstractmethod
    def search(self, query, headers: dict = None):
        pass

    # 默认使用 curl 模式
    def get_client(self, http_tool = "request"):
        client = self.clients.get(http_tool)
        if client is None:
            raise HTTPException(status_code=502, detail="获取client失败")
        return client
    
    def process_fetch(self, url_list: list, http_tool="curl", headers: dict = None, mode="html"):
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
            raise HTTPException(status_code=400, detail="url_list 长度不能大于 10")
    
        results = []

        # 获取客户端
        client = self.get_client(http_tool)
        if client is None:
            raise HTTPException(status_code=502, detail="请求方法失败")

        for url in url_list:
            try:
                # 调用客户端 fetch 方法获取页面内容，传入 headers
                content = client.fetch(url, headers=headers)
                # 根据 mode 选择处理方式
                if mode.lower() == "text":
                    data = self.extract_content_text(content)
                else:
                    data = content
                results.append({"url": url, "data": data})
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                results.append({"url": url, "error": str(e), "headers": headers})
                return response_error(502, "请求失败", results)
        return response_success(f"成功获取 {len(results)} 个搜索结果", results)

    def extract_content_text(self, html_content: str) -> str:
        """
        高级HTML净化引擎
        功能：
        1. 移除所有不可见内容（脚本/样式/元标签等）
        2. 保留语义段落结构
        3. 智能空格处理
        4. 清除隐藏注释
        """
        # 启用更快的lxml解析器（需要安装）
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 预清洗：移除所有需要排除的标签
        excluded_tags = [
            'script', 'style', 'head', 'title', 'meta',
            'nav', 'footer', 'header', 'iframe', 'noscript',
            'svg', 'button', 'input', 'textarea', 'select',
            'link', 'img', 'figure', 'aside',
            # 'form', 
        ]
        
        # 批量移除指定标签
        for tag in excluded_tags:
            for element in soup(tag):
                element.decompose()
        
        # 移除HTML注释
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # 智能文本提取（保留换行结构）
        text = soup.get_text(separator='\n', strip=True)
        
        # 高级空白处理
        clean_rules = [
            (r'\n{3,}', '\n\n'),  # 合并多个换行
            (r'[ \t]{2,}', ' '),   # 合并空格
            (r'\s+([.!?])', r'\1'),# 清理标点前空格
            (r'\n\s+\n', '\n\n')   # 清理空行中的空格
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
        for element in soup.find_all(text=True):
            # 排除不可见区域
            if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
                continue
            if element.strip():
                texts.append(element.strip())
        return " ".join(texts)

    def _filter_result_links(self, content, domains = ALLOWED_DOMAIN):

        # 过滤包含指定域名的链接
        filtered_results = []
        for item in content:
            href = item.get('href')
            if href and any(domain in href for domain in domains):
                filtered_results.append(item)
        return filtered_results
    
    