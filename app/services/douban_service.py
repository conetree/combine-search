from typing import List, Dict, Any
from fastapi import HTTPException
import requests
from urllib.parse import urlparse
from app.core.logging import logger
from app.utils.web_utils import WebUtils
import concurrent.futures
from app.core.search_config import config
from app.services.search_service import BaseSearch
from app.utils.response_utils import response_success, response_error
from bs4 import BeautifulSoup
from http import HTTPStatus
import time
import random
import re
import json

# 配置常量
MAX_RESULTS = config["MAX_RESULTS"]
MAX_CONTENT_LENGTH = config["MAX_CONTENT_LENGTH"]
DOUBAN_SEARCH_URL = config["DOUBAN_SEARCH_URL"]
ALLOWED_DOMAIN = ["movie.douban.com", "douban.com"]  # 仅允许豆瓣域名


class DoubanService(BaseSearch):
    def __init__(self, http_tool="request", **kwargs):
        super().__init__(**kwargs)
        self.http_tool = http_tool

    def get_client(self):
        return super().get_client(self.http_tool)

    def search(self, query: str, mode="text", links_num=2, headers: dict = None) -> Dict[str, Any]:
        print(f"DoubanService->search({query})")
        return self.search_web(query, mode, links_num, headers)

    def search_web(self, query: str, mode="text", links_num=2, headers: dict = None) -> dict:
        """
        通过豆瓣搜索获取查询结果。
        mode：'text' 模式返回抓取的网页正文，'link' 模式直接返回搜索结果链接
        links_num：返回或抓取的最大链接数
        """
        search_url = f"{DOUBAN_SEARCH_URL}?search_text={query}"
        try:
            # 1. 获取豆瓣搜索结果页面
            headers = WebUtils.get_enhanced_headers(DOUBAN_SEARCH_URL, headers)
            response = self.get_client().fetch(search_url, headers=headers)
            all_links = []
            # 2. 从返回结果中提取链接数据
            linksJsonData = self._get_links_json_data(response)
            # 从 script 里的JSON提取或通过标签匹配链接
            if linksJsonData:
                all_links = self._extract_json_links(linksJsonData)
            else:
                all_links = self._extract_tag_links(response)

            # 3. 过滤有效链接（仅保留指定域名中的链接，可根据需求调整过滤规则）
            filter_links = self._filter_links(all_links)
            if mode == "link":
                return response_success("从搜索结果中过滤出目标链接", filter_links)

            # 4. 根据 links_num 提取需要抓取的 URL
            request_urls = self._extract_request_urls(filter_links, links_num)
            contents_result = self._fetch_contents_concurrently(
                request_urls, headers)

            if mode == "html":
                return response_success("从搜索结果中抓取的源码内容", contents_result)

            # 5. 对返回内容进行文本提取清洗[可选]
            for item in contents_result:
                if item.get("content"):
                    item["content"] = self.extract_content_text_simple(
                        item["content"])
            # logger.info("DoubanService 抓取链接:%s 抓取结果:%s", request_urls, contents_result)
            return response_success("从搜索结果中抓取的链接内容", contents_result)
        except Exception as e:
            return response_error(500, "搜索过程中发生错误", str(e))

    def _get_links_json_data(self, response: str) -> json:
        # 提取 window.__DATA__ 数据
        json_match = re.search(
            r'<script[^>]*>.*?window\.__DATA__\s*=\s*(\{.*?\});.*?</script>', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            # 清理可能多余的逗号
            json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
            try:
                jsonData = json.loads(json_str, strict=False)
                return jsonData
            except json.JSONDecodeError as e:
                print(f"_extract_links_json_data JSON 解码失败: {e}")

    # 根据html标签提取链接
    def _extract_tag_links(self, response):
        all_links = []
        soup = BeautifulSoup(response, "html.parser")
        # 如果是返回的是html，则更加item-root class提取
        item_roots = soup.find_all("div", class_="item-root")
        for item in item_roots:
            title_div = item.find("div", class_="title")
            if title_div:
                a_tag = title_div.find("a")
                if a_tag:
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get("href")
                    all_links.append({"title": title, "href": href})
                    if len(all_links) >= MAX_RESULTS:
                        break
        return all_links

    # 根据json数据提取链接
    def _extract_json_links(self, jsonData):
        all_links = []
        # 遍历 items，从中提取 title 和 url
        for item in jsonData.get('items', []):
            # 如果 item 直接包含 title 和 url，则直接获取
            title = item.get('title')
            url = item.get('url')
            # 否则尝试从嵌套的 urls 列表中提取（例如第一个条目只有 urls 字段）
            if not title or not url:
                urls = item.get('urls', [])
                for u in urls:
                    title = u.get('text')
                    url = u.get('url')
                    if title and url:
                        all_links.append({"title": title, "href": url})
            else:
                all_links.append({"title": title, "href": url})
            if len(all_links) >= MAX_RESULTS:
                break
        return all_links

    def _filter_links(self, links, domains=ALLOWED_DOMAIN):
        """
        根据允许域名对结果链接进行过滤，如链接中包含指定域则视为有效链接
        """
        filtered = []
        for item in links:
            href = item.get("href")
            if href and any(domain in urlparse(href).netloc for domain in domains):
                filtered.append(item)
        return filtered

    def _extract_request_urls(self, urls, links_num=2):
        added_domains = set()
        result = []
        # 保证一个域名只添加 1 个链接，且不超过最大值
        for item in urls:
            if len(result) >= links_num:
                break
            url = item if isinstance(item, str) else item.get("href", None)
            domain = urlparse(url).netloc
            if domain in ALLOWED_DOMAIN and domain not in added_domains:
                result.append(url)
                added_domains.add(domain)
        # 若不够最大值，则补充其他域名的 URL
        if len(result) < links_num:
            for item in urls:
                if len(result) >= links_num:
                    break
                url = item if isinstance(item, str) else item.get("href", None)
                if url not in result:
                    result.append(url)
        return result

    def _fetch_contents_concurrently(self, urls: List[str], headers: dict = None) -> List[Dict]:
        """多线程内容抓取"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(
                self._fetch_single_content, url, headers): url for url in urls}
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

    def extract_content_text_simple(self, html_content: str) -> str:
        """
        利用 BeautifulSoup 提取网页内可见文字，排除脚本、样式、head 等内容
        """
        soup = BeautifulSoup(html_content, "html.parser")
        texts = []
        for element in soup.find_all(text=True):
            if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
                continue
            if element.strip():
                texts.append(element.strip())
        text = " ".join(texts)
        return text[:MAX_CONTENT_LENGTH]
