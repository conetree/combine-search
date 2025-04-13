# utils/web_utils.py
"""
工具方法模块：
    提供生成随机 Cookie、获取默认请求头以及增强请求头的方法
"""

import random
import string
import secrets
from urllib.parse import urlparse
from app.core.logging import logger

# 可选：定义一组随机 User-Agent 列表
RANDOM_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
]

class WebUtils:
    @staticmethod
    def generate_random_cookie():
        """
        生成随机 Cookie（纯工具方法）：
            - 生成包含 __uid、session_id 和 token 的随机 Cookie 字符串
        """
        components = [
            f"__uid={random.randint(100000, 999999)}",
            f"BAIDUID={WebUtils.generate_BAIDUID_value()}",
            f"session_id={''.join(random.choices(string.ascii_letters + string.digits, k=24))}",
            f"token={''.join(random.choices(string.hexdigits.lower(), k=32))}"
        ]
        return "; ".join(components)

    @staticmethod
    def get_default_headers():
        """
        获取默认请求头（无业务参数）：
            - 返回包含常见 HTTP 请求头的字典
        """
        return {
            "User-Agent": random.choice(RANDOM_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;application/json;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Accept-Language": random.choice(['en-US,en;q=0.9', 'zh-CN,zh;q=0.8', "zh-CN,zh;q=0.9,en;q=0.8"]),
            "Connection": "keep-alive",
            "Cookie": WebUtils.generate_random_cookie(),
            # "Upgrade-Insecure-Requests": "1", # 是否将 不安全的HTTP 请求升级到 HTTPS
            # "TE": "Trailers"   # "TE" 是一个请求头，代表 "Transfer Encoding"（传输编码）
        }

    @staticmethod
    def generate_BAIDUID_value():
        """
        每次调用生成**完全随机**的许可证密钥（符合历史格式）
        格式：32位随机十六进制:SL=X:NR=Y:FG=Z（X∈{0,1}, Y≥1, Z∈{0,1}）
        """
        # 1. 32位安全随机十六进制（128位熵）
        hex_part = secrets.token_hex(16).upper()
        sl = secrets.choice([0, 1])
        nr = secrets.randbelow(999) + 1
        fg = secrets.choice([0, 1])
        return f"{hex_part}:SL={sl}:NR={nr}:FG={fg}"

    @staticmethod
    def get_enhanced_headers(url=None, user_headers=None):
        """
        获取增强的请求头，可以基于传入的user_headers进行扩展
        """
        headers = WebUtils.get_default_headers()

        # 合并传入的headers
        if user_headers:
            for key, value in user_headers.items():
                if key.lower() in ['user-agent', 'cookie', 'accept', 'referer']:
                    normalized_key = '-'.join([word.capitalize()
                                              for word in key.lower().split('-')])
                    headers[normalized_key] = value

        # 根据URL添加特定header[可选]
        if url:
            parsed = urlparse(url)
            host = parsed.netloc

            # 针对 baike.baidu.com 的反爬策略
            if 'baike.baidu.com' in host:
                # headers = user_headers
                headers["Cookie"] = headers.get(
                    "Cookie", "") + "; BAIDUID=9B4BEA99EDD0815C9A39D81CE9B8C50A:SL=0:NR=10:FG=1"

            # 针对 movie.douban.com 的反爬策略
            if 'movie.douban.com' in host:
                headers["Cookie"] = headers.get(
                    "Cookie", "") + "; __yadk_uid=MFsoFyM8BOiB4lv8QUXoZ9wlEBVWDPrR"

            # 针对 360搜索 (www.so.com) 的反爬策略
            if 'www.so.com' in host:
                headers.update({
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Priority': 'u=0, i'
                })

            # 针对百度系站点的 cookie 处理
            if 'baidu.com' in host:
                headers.setdefault('Cookie', '')
                if 'BAIDUID' not in headers['Cookie']:
                    headers['Cookie'] += '; BAIDUID=FAKE_ID_FOR_ANTI_SPIDER'

            # 针对豆瓣 (douban.com) 的反爬机制
            if 'douban.com' in host:
                headers.setdefault('Cookie', '')
                if 'bid' not in headers['Cookie']:
                    headers['Cookie'] += '; bid="FAKE_BID_STRING"'

            # 针对 Bing 搜索 (bing.com) 的反爬策略
            if 'bing.com' in host:
                headers.update({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.bing.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                })
                headers.setdefault('Cookie', '')
                if '_EDGE_V' not in headers['Cookie']:
                    headers['Cookie'] += '; _EDGE_V=1; MUID=1234567890ABCDEF1234567890ABCDEF'

            # 针对 Google 搜索 (google.com) 的反爬策略
            if 'google.com' in host:
                # headers = user_headers
                headers.update({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.google.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                })
                headers.setdefault('Cookie', '')
                if 'NID' not in headers['Cookie']:
                    headers['Cookie'] += '; NID=123=ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefg'

            # 处理搜狗搜索
            if 'sogou.com' in host:
                headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Referer': 'https://www.sogou.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Connection': 'keep-alive'
                })

            # 针对 DuckDuckGo 搜索 (duckduckgo.com) 的反爬策略
            if 'duckduckgo.com' in host:
                headers.update({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://duckduckgo.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                })
                headers.setdefault('Cookie', '')
                if 'dcm' not in headers['Cookie']:
                    headers['Cookie'] += '; dcm=1; __ddg1_=1234567890ABCDEF1234567890ABCDEF'

        return headers