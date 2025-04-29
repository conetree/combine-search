# 搜索控制器
from fastapi import HTTPException, Depends, Query
from typing import List, Any, Dict
from app.core.logging import logger

from app.services.search_service import SearchService
from app.services.search_engine_factory import DefaultSearchEngineFactory

class SearchController:
    def __init__(self):
        self.service = SearchService()
        
    def get_search_engine_service(self, service_name: str, 
                                  http_tool: str = "request", 
                                  force: bool = False):
        return DefaultSearchEngineFactory.get_service(service_name, http_tool, force)

    def validate_url(self, url: List[str] = Query(...)):
        """URL 参数验证方法"""
        if not url or len(url) == 0:
            raise HTTPException(
                status_code=400,
                detail="参数错误，请使用格式: ?url=URL_A&url=URL_B"
            )
        return url

    def fetch_agent(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_agent抓取的 URL: {url}")
        return self.service.process_fetch(url, "agent", headers, mode)

    def fetch_curl(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_curl抓取的 URL: {url}")
        return self.service.process_fetch(url, "curl", headers, mode)

    def fetch_request(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_request抓取的 URL: {url}")
        return self.service.process_fetch(url, "request", headers, mode)

    def fetch_firecrawl(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_firecrawl抓取的 URL: {url}")
        return self.service.process_fetch(url, "firecrawl", headers, mode)

    def fetch_scrapy(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_scrapy抓取的 URL: {url}")
        return self.service.process_fetch(url, "scrapy", headers, mode)

    def fetch_selenium(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_selenium抓取的 URL: {url}")
        return self.service.process_fetch(url, "selenium", headers, mode)

    def fetch_beautifulsoup(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_beautifulsoup抓取的 URL: {url}")
        return self.service.process_fetch(url, "beautifulsoup", headers, mode)

    def fetch_cloudscraper(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_cloudscraper抓取的 URL: {url}")
        return self.service.process_fetch(url, "cloudscraper", headers, mode)

    def fetch_playwright(self, url: list, headers: dict = None, mode = "html"):
        logger.info(f"fetch_playwright抓取的 URL: {url}")
        return self.service.process_fetch(url, "playwright", headers, mode)
    
    def fetch(self, url: list, headers: dict = None, mode = "html"):
        return self.service.search(url, headers, mode)

    # 基于DDGS插件搜索
    def search_duckduckgo_api(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="firecrawl"):
        service = self.get_search_engine_service("duckduckgo", http_tool)
        return service.search_api(q, mode, links_num, headers)
    
    # 基于DDGS插件suggest
    def search_duckduckgo_suggest(self, q: str, headers: dict = None, http_tool="firecrawl"):
        service = self.get_search_engine_service("duckduckgo", http_tool)
        return service.search_suggest(q, headers)
    
    # 基于网页自定义抓取
    def search_duckduckgo_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="firecrawl"):
        service = self.get_search_engine_service("duckduckgo", http_tool)
        return service.search_web(q, mode, links_num, headers)

    # 通过bing搜索抓取
    def search_bing_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="request"):
        service = self.get_search_engine_service("bing", http_tool)
        return service.search_web(q, mode, links_num, headers)
    
    # 通过baidu搜索抓取
    def search_baidu_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="request"):
        service = self.get_search_engine_service("baidu", http_tool)
        return service.search_web(q, mode, links_num, headers)

    # 通过google搜索抓取
    def search_google_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="firecrawl"):
        service = self.get_search_engine_service("google", http_tool)
        return service.search_web(q, mode, links_num, headers)

    # 通过sogou搜索抓取
    def search_sogou_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="request"):
        service = self.get_search_engine_service("sogou", http_tool)
        return service.search_web(q, mode, links_num, headers)

    # 通过360搜索抓取
    def search_so_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="request"):
        service = self.get_search_engine_service("so", http_tool)
        return service.search_web(q, mode, links_num, headers)

    # 通过豆瓣电影搜索抓取
    def search_douban_web(self, q: str, mode: str, links_num: int, headers: dict = None, http_tool="request"):
        service = self.get_search_engine_service("douban", http_tool)
        return service.search_web(q, mode, links_num, headers)

    def index(self):
        return {
            "message": "用以下几种方式抓取网页，各有优劣。",
            "paths": [
                {
                    "path": "/api/search/bing-web?q=念无双 电视剧 豆瓣 百科&mode=link",
                    "desc": "基于bing网页搜索抓取，返回链接。"
                },
                {
                    "path": "/api/search/baidu-web?q=念无双 电视剧 豆瓣 百科&mode=text&links_num=5",
                    "desc": "基于baidu网页搜索抓取，指定抓取数量，默认2条。"
                },
                {
                    "path": "/api/search/google-web?q=念无双 电视剧 豆瓣 百科",
                    "desc": "基于google网页搜索抓取，返回文本。需要穿墙，故使用firecrawl工具抓取，免费有次数限制"
                },
                {
                    "path": "/api/search/douban-web?q=念无双&http_tool=agent",
                    "desc": "基于豆瓣影视搜索抓取，通过Nginx代理工具，返回文本。"
                },
                {
                    "path": "/api/search/sogou-web?q=念无双 电视剧 豆瓣 百科&mode=link&http_tool=curl",
                    "desc": "基于sogou网页搜索抓取，指定工具和模式。"
                },
                {
                    "path": "/api/search/so-web?q=念无双 电视剧 豆瓣 百科&http_tool=curl&links_num=3",
                    "desc": "基于360网页搜索抓取，通过agent工具，抓取3条。"
                },
                {
                    "path": "/api/search/duckduckgo-web?q=念无双 电视剧 豆瓣 百科",
                    "desc": "基于duckduckgo网页搜索抓取，返回文本。需要穿墙，默认使用firecrawl工具抓取，免费有次数限制"
                },
                {
                    "path": "/api/search/duckduckgo-web?q=念无双 电视剧 豆瓣 百科&mode=link",
                    "desc": "基于duckduckgo网页搜索抓取，返回链接。"
                },
                {
                    "path": "/api/search/duckduckgo-api?q=念无双 电视剧 豆瓣 百科",
                    "desc": "基于duckduckgo-search插件抓取，返回文本。需要支持穿墙。"
                },
                {
                    "path": "/api/search/duckduckgo-suggest?q=念无双 电视剧",
                    "desc": "基于duckduckgo API抓取suggest。"
                },
                {
                    "path": "/api/search/fetch-request?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "直接使用内置的 HTTP 请求库进行抓取。方法简单且效率高，但在面对复杂网站时失败率可能较高。"
                },
                {
                    "path": "/api/search/fetch-curl?url=https://movie.douban.com&url=https://baike.baidu.com&mode=text",
                    "desc": "利用系统的 curl 命令进行抓取。执行速度快，直接发送 HTTP 请求，但需要确保系统支持 curl。"
                },
                {
                    "path": "/api/search/fetch-agent?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "通过 Nginx 代理服务器进行抓取。适用于需要绕过封禁或进行定向请求的场景，抓取失败时可以作为备份。"
                },
                {
                    "path": "/api/search/fetch-firecrawl?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "使用 Firecrawl 库进行抓取。该库专为大规模网络抓取设计，功能强大，免费版有次数限制。可穿墙访问。"
                },
                {
                    "path": "/api/search/fetch-selenium?url=https://movie.douban.com&url=https://baike.baidu.com&mode=text",
                    "desc": "采用 Selenium WebDriver 模拟浏览器行为，解析包含 JavaScript 和 CSS 的动态网页，获取完整页面内容。"
                },
                {
                    "path": "/api/search/fetch-beautifulsoup?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "使用 BeautifulSoup 库解析网页内容，方便地提取和过滤所需的 HTML 元素。"
                },
                {
                    "path": "/api/search/fetch-scrapy?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "利用 Scrapy 框架进行抓取。适用于构建和管理大型爬虫项目，支持高效的整站数据采集。"
                },
                {
                    "path": "/api/search/fetch-cloudscraper?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "利用 Cloudscraper 库进行抓取，推荐工具。适用于穿透Cloudflare WAF等防火墙，绕过爬虫封禁。"
                },
                {
                    "path": "/api/search/fetch-playwright?url=https://movie.douban.com&url=https://baike.baidu.com",
                    "desc": "利用 Playwright 库进行抓取，内置高级反爬虫绕过功能。适用于动态渲染页面，绕过强大的爬虫封禁。"
                },
            ]
        }


# 保持原有依赖项兼容性
validate_url = SearchController().validate_url
