from typing import List, Dict, Any
from fastapi import HTTPException
import requests
from urllib.parse import urlparse, parse_qs
from app.core.logging import logger
from app.utils.web_utils import WebUtils
import concurrent.futures
from app.core.search_config import config
from app.services.search_service import BaseSearch
from app.utils.response_utils import response_success, response_error
from bs4 import BeautifulSoup
import json
from http import HTTPStatus
import time
import random

# 配置常量
MAX_RESULTS = config["MAX_RESULTS"]
MAX_CONTENT_LENGTH = config["MAX_CONTENT_LENGTH"]
GOOGLE_URL = config.get("GOOGLE_URL", "https://www.google.com/search")
ALLOWED_DOMAIN = config["ALLOWED_DOMAIN"]

class GoogleService(BaseSearch):
    def __init__(self, http_tool = "request", **kwargs):
        super().__init__(**kwargs)
        self.http_tool = http_tool

    def get_client(self):
        return super().get_client(self.http_tool)

    def search(self, query: str, mode="text", links_num=2, headers: dict = None) -> Dict[str, Any]:
        print(f"GoogleService->search({query})")
        return self.search_web(query, mode, links_num, headers)

    def search_web(self, query: str, mode="text", links_num=2, headers: dict = None) -> Dict[str, Any]:
        """
        通过 Google 搜索获取查询结果。
        mode：'text' 模式返回抓取的网页正文，'link' 模式直接返回搜索结果链接；
        links_num：返回或抓取的最大链接数。
        """
        # 构造搜索 URL，Google 搜索参数 q 用于查询关键词
        search_url = f"{GOOGLE_URL}?q={query}"
        try:
            # 1. 获取 Google 搜索结果页面
            headers = WebUtils.get_enhanced_headers(GOOGLE_URL, headers)
            response = self.get_client().fetch(search_url, headers=headers or WebUtils.get_enhanced_headers("https://www.google.com"))
            # 2. 使用 BeautifulSoup 解析返回页面，并提取搜索结果
            soup = BeautifulSoup(response, "html.parser")
            # Google 搜索结果通常以 <div class="yuRUbf"> 存在，其中包含结果链接
            result_items = soup.find_all("div", class_="yuRUbf")
            print("GoogleService result_items:", soup.find_all("div"))
            all_links = []
            for item in result_items:
                a_tag = item.find("a")
                if a_tag and a_tag.get("href"):
                    link = a_tag["href"].strip()
                    # 尝试获取 <h3> 标签作为标题
                    h3_tag = a_tag.find("h3")
                    title = h3_tag.get_text(strip=True) if h3_tag else a_tag.get_text(strip=True)
                    all_links.append({"title": title, "href": link})
                    if len(all_links) >= MAX_RESULTS:
                        break

            # 3. 过滤有效链接（仅保留符合 ALLOWED_DOMAIN 规则的链接）
            filter_links = self._filter_web_links(all_links)

            # 4. 根据不同模式处理搜索结果
            if mode == "link":
                # filter_links.append({"origin_content": response})
                return response_success("从搜索结果中过滤出目标链接", filter_links)

            if filter_links:
                request_urls = self._extract_request_urls(filter_links, links_num)
                contents_result = self._fetch_contents_concurrently(request_urls, headers)
                for item in contents_result:
                    if item.get("content"):
                        item["content"] = self.extract_content_text(item["content"])
                # logger.info("GoogleService 抓取链接:%s 抓取结果:%s", request_urls, contents_result)
                return response_success("从搜索结果中抓取的链接内容", contents_result)
            return response_error(500, "没有找到有效内容", None)

        except Exception as e:
            logger.error(f"搜索 Google 时出错: {str(e)}")
            return response_error(500, "搜索过程中发生错误", str(e))

    def _filter_web_links(self, links, domains=ALLOWED_DOMAIN):
        """
        过滤包含指定域名的链接。
        遍历所有搜索结果，保留 href 中包含允许域名的链接
        """
        filtered_results = []
        for item in links:
            href = item.get("href")
            if href and any(domain in urlparse(href).netloc for domain in domains):
                filtered_results.append({
                    "title": item['title'].strip(),
                    "href": href
                })
        return filtered_results

    # 提取过滤请求链接
    def _extract_request_urls(self, urls, links_num=2):
        added_domains = set()
        result = []
        # 每个域名只取一个链接，且不超过 links_num 个
        for item in urls:
            if len(result) >= links_num:
                break
            url = item if isinstance(item, str) else item.get('href', None)
            domain = urlparse(url).netloc
            if domain in ALLOWED_DOMAIN and domain not in added_domains:
                result.append(url)
                added_domains.add(domain)
        # 若不足，则补充其他链接
        if len(result) < links_num:
            for item in urls:
                if len(result) >= links_num:
                    break
                url = item if isinstance(item, str) else item.get('href', None)
                if url not in result:
                    result.append(url)
        return result

    def _fetch_contents_concurrently(self, urls: List[str], headers: dict = None) -> List[Dict]:
        """多线程内容抓取"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._fetch_single_content, url, headers): url for url in urls}
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
        if html_content is not None:
            soup = BeautifulSoup(html_content, "html.parser")
            visible_texts = []
            for element in soup.find_all(text=True):
                if element.parent.name not in ['style', 'script', 'head', 'title', 'meta'] and \
                   not element.parent.has_attr('style') and 'display:none' not in element.parent.get('style', ''):
                    visible_texts.append(element.strip())
            text = ' '.join(visible_texts)
            return text[:MAX_CONTENT_LENGTH]
        return ""
