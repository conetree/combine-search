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

# 配置常量
MAX_RESULTS = config["MAX_RESULTS"]
MAX_CONTENT_LENGTH = config["MAX_CONTENT_LENGTH"]
SO_URL = config["SO_URL"]
ALLOWED_DOMAIN = config["ALLOWED_DOMAIN"]


class SoService(BaseSearch):
    def __init__(self, http_tool="request", **kwargs):
        super().__init__(**kwargs)
        self.http_tool = http_tool

    def get_client(self):
        return super().get_client(self.http_tool)

    def search(self, query: str, mode="text", links_num=2, headers: dict = None) -> Dict[str, Any]:
        """
        搜索接口，根据查询关键词调用搜索并返回结果。
        mode: 'text' 返回页面内容；'link' 直接返回搜索结果链接
        """
        print(f"SoService->search({query})")
        return self.search_web(query, mode, links_num, headers)

    def search_web(self, query: str, mode="text", links_num=2, headers: dict = None) -> dict:
        """
        通过360搜索获取查询结果。
        mode：'text' 模式返回抓取的网页正文；'link' 模式直接返回搜索结果链接
        links_num：返回或抓取的最大链接数
        """
        # 构造查询 URL，360 搜索使用参数 q
        search_url = f"{SO_URL}?q={query}"
        try:
            # 1. 获取 360 搜索结果页面
            enhanced_headers = WebUtils.get_enhanced_headers(SO_URL, headers)
            response = self.get_client().fetch(search_url, headers=enhanced_headers)

            # 2. 使用 BeautifulSoup 解析返回页面，并提取搜索结果
            soup = BeautifulSoup(response, "html.parser")
            # 360 搜索结果通常位于 <h3 class="res-title"> 内部
            # result_items = soup.find_all("h3", class_="res-title ")
            result_items = soup.find_all("h3")
            all_links = []
            for item in result_items:
                a_tag = item.find("a")
                if a_tag and a_tag.get("href"):
                    link = a_tag["href"].strip()
                    title = a_tag.get_text(strip=True)
                    real_url = self._get_real_url(link)
                    all_links.append({"title": title, "href": real_url})
                    if len(all_links) >= MAX_RESULTS:
                        break

            # 3. 过滤有效链接（仅保留指定域名的链接，可根据需求调整过滤规则）
            filter_links = self._filter_links(all_links)
            # 若模式为返回链接，则直接返回过滤后的链接
            if mode == "link":
                # filter_links.append({"origin_content": response})
                return response_success("从搜索结果中过滤出目标链接", filter_links)

            # 4. 根据 links_num 提取需要抓取的 URL
            request_urls = self._extract_request_urls(filter_links, links_num)
            contents_result = self._fetch_contents_concurrently(
                request_urls, enhanced_headers)
            # 对返回内容进行文本提取清洗
            for item in contents_result:
                if item.get("content"):
                    item["content"] = self.extract_content_text(
                        item["content"])
            # 打印日志记录抓取情况
            logger.info("SoService 抓取链接:%s 抓取结果:%s",
                        request_urls, contents_result)
            return response_success("从搜索结果中抓取的链接内容", contents_result)
        except Exception as e:
            return response_error(500, "搜索过程中发生错误", str(e))

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

    def _get_real_url(self, url: str) -> str:
        try:
            response = requests.head(url, allow_redirects=True)
            return response.url
        except requests.RequestException as e:
            logger.warning(f"解析真实URL失败 [{url}]: {str(e)}")
            return url

    def _extract_request_urls(self, urls, links_num=2):
        """
        提取过滤后的请求链接，确保同一域名仅抓取一个链接，若不足则补充其他链接
        """
        added_domains = set()
        result = []
        # 保证一个域名只添加 1 个链接，且不超过最大值
        for item in urls:
            if len(result) >= links_num:
                break
            url = item if isinstance(item, str) else item.get('href', None)
            domain = urlparse(url).netloc
            if domain in ALLOWED_DOMAIN and domain not in added_domains:
                result.append(url)
                added_domains.add(domain)

        # 若不够最大值，则补充其他域名的 URL
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

    # def _fetch_single_content(self, url: str, headers: dict) -> Dict:
    #     """单页面内容抓取"""
    #     try:
    #         # 随机延迟防封禁
    #         time.sleep(random.uniform(0.3, 1.0))

    #         response = self.session.get(
    #             url,
    #             headers=headers,
    #             timeout=10,
    #             allow_redirects=True,
    #             verify=False  # 忽略SSL验证
    #         )

    #         # 内容有效性检查
    #         if response.status_code != 200:
    #             raise ValueError(f"无效状态码: {response.status_code}")

    #         if len(response.text) < 1000:
    #             raise ValueError("内容过短")

    #         return {
    #             "status": "success",
    #             "url": response.url,
    #             "content": response.text
    #         }
    #     except Exception as e:
    #         return {
    #             "status": "error",
    #             "url": url,
    #             "message": str(e)
    #         }

    def extract_content_text_simple(self, html_content: str) -> str:
        """
        利用 BeautifulSoup 提取网页内可见文字，排除脚本、样式、head 等内容
        """
        soup = BeautifulSoup(html_content, "html.parser")
        texts = []
        for element in soup.find_all(text=True):
            # 排除不可见区域
            if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
                continue
            if element.strip():
                texts.append(element.strip())
        text = " ".join(texts)
        return text[:MAX_CONTENT_LENGTH]
