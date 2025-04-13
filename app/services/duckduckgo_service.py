# 安装最新版依赖
# pip install duckduckgo-search>=3.8.8 --upgrade

from duckduckgo_search import DDGS
from typing import List, Dict, Any
from fastapi import HTTPException
import requests
from urllib.parse import urlparse, parse_qs, unquote
from app.core.logging import logger
from app.utils.web_utils import WebUtils
import concurrent.futures
from app.core.search_config import config
from app.services.search_service import BaseSearch
from app.utils.response_utils import response_success, response_error
from bs4 import BeautifulSoup
import json
from typing import List, Dict
from http import HTTPStatus
import time
import random

# 配置常量
MAX_RESULTS = config["MAX_RESULTS"]
MAX_CONTENT_LENGTH = config["MAX_CONTENT_LENGTH"]
DUCKDUCKGO_URL = config["DUCKDUCKGO_URL"]
LITE_DUCKDUCKGO_URL = config["LITE_DUCKDUCKGO_URL"]
DUCKDUCKGO_API = config["DUCKDUCKGO_API"]
ALLOWED_DOMAIN = config["ALLOWED_DOMAIN"]


class DuckduckgoService(BaseSearch):
    def __init__(self, http_tool = "firecrawl", **kwargs):
        super().__init__(**kwargs)
        self.http_tool = http_tool
        """
        初始化搜索服务
        关键修改点：
        - 单次正确初始化DDGS客户端
        - 配置符合反爬要求的请求头
        - 初始化HTTP客户端
        """
        self.ddgs = DDGS(
            # proxy="socks5h://user:password@geo.iproyal.com:32325"
            proxies=None,
            timeout=20,
            headers=WebUtils.get_enhanced_headers("https://duckduckgo.com", None)
        )

    def get_client(self):
        return super().get_client(self.http_tool)

    def search(self, query: str, mode="text", links_num=2, headers: dict = None)-> Dict[str, Any]:
        print(f"DuckduckgoService->search({query})")
        return self.search_web(query, mode, links_num, headers)

    def search_api(self, query: str, mode="text", links_num=2, headers: dict = None)-> Dict[str, Any]:
        """
        同步搜索主方法（兼容新版API）
        """
        try:
            # 1. 获取搜索结果
            raw_results = self._fetch_search_api_results(query, headers)

            # 2. 过滤有效链接
            filter_links = self._filter_api_links(raw_results)
        
            # 3. 处理不同模式
            if mode == "link":
                return response_success("从搜索结果中过滤出目标链接", filter_links)

            if filter_links:
                request_urls = self._extract_request_urls(filter_links, links_num)
                # logger.info("search_web->request_urls:%s", request_urls)
                contents_result = self._fetch_contents_concurrently(request_urls, headers)
                for item in contents_result:
                    if item["content"]:
                        item["content"] = self.extract_content_text(item["content"])
                return response_success("从搜索结果中抓取的链接内容", contents_result)
            return response_error(500, "没有找到有效内容", None)

        except Exception as e:
            logger.error(f"搜索 DuckDuckGo 时出错: {str(e)}")
            return response_error(500, "搜索过程中发生错误", str(e))

    def search_web(self, query: str, mode="text", links_num=2, headers: dict = None)-> Dict[str, Any]:
        """
        使用指定的客户端方法在 DuckDuckGo 上搜索查询，并返回解析后的结果。
        """
        # search_url = f"{DUCKDUCKGO_URL}?q={query}" # 通用版，全面
        search_url = f"{LITE_DUCKDUCKGO_URL}?q={query}&kl=cn-zh" # 轻量版，速度快
        try:
            # 1. 搜索duckduckgo
            headers = WebUtils.get_enhanced_headers(DUCKDUCKGO_URL, headers)
            response = self.get_client().fetch(search_url, headers=headers)

            # 2. 提取需要的链接
            soup = BeautifulSoup(response, "html.parser")
            all_links = [{"href": tag.get("href"), "text": tag.get_text(strip=True)} 
                        for tag in soup.find_all("a")]
            filter_links = self._filter_web_links(all_links)

            # 3. 处理不同模式
            if mode == "link":
                # filter_links.append({"origin_content": response})
                return response_success("从搜索结果中过滤出目标链接", filter_links)

            if filter_links:
                request_urls = self._extract_request_urls(filter_links, links_num)
                contents_result = self._fetch_contents_concurrently(request_urls, headers)
                for item in contents_result:
                    if item["content"]:
                        item["content"] = self.extract_content_text(item["content"])
                # logger.info("DuckduckgoService 抓取链接:%s 抓取结果:%s", request_urls, contents_result)
                return response_success("从搜索结果中抓取的链接内容", contents_result)
            return response_error(500, "没有找到有效内容", None)

        except Exception as e:
            logger.error(f"搜索 DuckDuckGo 时出错: {str(e)}")
            return response_error(500, "搜索过程中发生错误", str(e))

    def search_suggest(self, query: str, headers: dict = None):
        """
        使用DuckDuckGo自动补全API获取搜索建议
        """
        api_url = f"{DUCKDUCKGO_API}?q={query}&type=json"
        try:
            response = self.get_client().fetch(api_url, headers=headers)
            suggestions = json.loads(response)
            return response_success("自动补全建议获取成功", suggestions)

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败：{str(e)}")
            return response_error(500, "数据解析异常", str(e))
        except Exception as e:
            logger.error(f"API请求异常：{str(e)}", exc_info=True)
            return response_error(500, "服务暂时不可用", str(e))

    # 利用DDGS插件抓取，无需指定http_tool
    def _fetch_search_api_results(self, query: str, headers: dict = None) -> List[Dict]:
        """获取原始搜索结果（新版API适配）"""
        try:
            # 更新DDGS实例的headers
            if headers:
                self.ddgs.headers = WebUtils.get_enhanced_headers(None, headers)

            response = self.ddgs.text(
                keywords=query,       # 参数名变更
                region="cn-zh",       # 中文结果
                safesearch="off",     # 必须小写
                timelimit="y",        # 按年过滤
                # backend="auto",       # 指定用哪个接口 html | lite
                max_results=MAX_RESULTS  # 直接设置总数
            )
            return response
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise RuntimeError("搜索服务调用失败")

    def _filter_api_links(self, content, domains=ALLOWED_DOMAIN):
        # 过滤包含指定域名的链接
        filtered_results = []
        for item in content:
            href = item.get('href')
            if href and any(domain in href for domain in domains):
                filtered_results.append(item)
        return filtered_results

    def _filter_web_links(self, content, domains=ALLOWED_DOMAIN):
        # 过滤包含指定域名的链接
        filtered_results = []
        for item in content:
            href = item.get('href')
            if href and any(domain in href for domain in domains):
                # 提取 URL 和查询参数
                # parsed_url = urlparse(href)
                # query_params = parse_qs(parsed_url.query)
                # href = query_params.get('uddg', [None])[0]
                _, _, tail = href.partition("uddg=")
                href = unquote(tail.split("&", 1)[0])
                filtered_results.append({
                    "title": item['text'].strip(),
                    # "origin_url": href.strip(),
                    # "params": query_params
                    "href": href
                })
        return filtered_results

    # 提取html文本
    def extract_content_text_simple(self, content: str):
        if content is not None:
            soup = BeautifulSoup(content, "html.parser")
            visible_texts = []
            for element in soup.find_all(text=True):
                if element.parent.name not in ['style', 'script', 'head', 'title', 'meta'] and \
                        not element.parent.has_attr('style') and 'display:none' not in element.parent.get('style', ''):
                    visible_texts.append(element.strip())
            text = ' '.join(visible_texts)
            return text

    # 提取过滤请求链接
    def _extract_request_urls(self, urls, links_num = 2):
        added_domains = set()
        result = []
        # logger.info("_extract_request_urls[url=%s links_num=%s]", urls, links_num)
        # 一个域名添加1个url，且不超过最大值
        for item in urls:
            if len(result) >= links_num:
                break
            url = item if type(item) is str else item.get('href', None)
            domain = urlparse(url).netloc
            if domain in ALLOWED_DOMAIN and domain not in added_domains:
                result.append(url)
                added_domains.add(domain)

        # 若不够最大值，则补充其他域名的URL
        if len(result) < links_num:
            for item in urls:
                if len(result) >= links_num:
                    break
                url = item if type(item) is str else item.get('href', None)
                if url not in result:
                    result.append(url)

        return result

    def _fetch_contents_concurrently(self, urls: List[str], headers: dict = None) -> List[Dict]:
        """多线程内容抓取"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._fetch_single_content, url, headers): url 
                     for url in urls}
            results = []
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    if result.get("content"):
                        results.append(result)
                except Exception as e:
                    logger.warning(f"内容抓取失败 [{url}]: {str(e)}")
            return results

    def _fetch_single_content(self, url: str, headers: dict = None) -> Dict:
        """单页面内容抓取"""
        try:
            # 随机延迟防封禁
            time.sleep(random.uniform(0.3, 1.0))
            content_data = self.get_client().fetch(url, headers=headers)
            return {"url": url, "content": content_data}
        except Exception as e:
            logger.debug(f"抓取失败详情 [{url}]: {str(e)}")
            return {"url": url, "error": str(e)}

    def _clean_search_content(self, raw_data: List[Dict]) -> str:
        """内容清洗管道"""
        valid_texts = []
        for item in raw_data:
            text = str(item.get("text", "")).strip()
            if len(text) >= 10:
                valid_texts.append(text)
        return "\n".join(valid_texts)[:MAX_CONTENT_LENGTH]
