# service/search_service.py
"""
搜索业务处理模块：
    - 负责根据传入的 URL 列表和抓取方式，调用对应的客户端获取页面内容
    - 利用 WebScraper 对抓取到的内容进行解析处理
"""

from app.services.base_search import BaseSearch
from app.utils.web_utils import WebUtils
from app.core.logging import logger
from app.core.search_config import config
from typing import List
import time
import random

class SearchService(BaseSearch):
    def __init__(self, http_tool = "request", **kwargs):
        super().__init__(**kwargs)
        self.http_tool = http_tool

    def search(self, query, headers: dict = None, mode = "html"):
        print(f"SearchService->search({query})")
        # 随机延迟防封禁
        time.sleep(random.uniform(0.3, 1.0))
        headers = WebUtils.get_enhanced_headers(None, headers)
        return self.process_fetch(query, self.http_tool, headers, mode)
    
    def process_fetch(self, url_list: list, http_tool="curl", headers: dict = None, mode="html"):
        print(f"SearchService->process_fetch({url_list}, {http_tool}, {headers}, {mode})")
        return super().process_fetch(url_list, http_tool, headers, mode)