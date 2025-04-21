# utils/web_utils.py
"""
工具方法模块：
    提供生成随机 Cookie、获取默认请求头以及增强请求头的方法
"""

import random
import string
import secrets
from urllib.parse import urlparse
from fake_useragent import UserAgent
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
            # f"__uid={random.randint(100000, 999999)}",
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
        ua = UserAgent()
        return {
            # "User-Agent": random.choice(RANDOM_USER_AGENTS),
            "User-Agent": ua.random, # 从fake_useragent库里随机选择UA
            "Accept": "text/html,application/xhtml+xml,application/xml;application/json;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Accept-Language": random.choice(['zh-CN,zh;q=0.8', "zh-CN,zh;q=0.9,en;q=0.8"]),
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
        例子：9B4BEA99EDD0815C9A39D81CE9B8C50A
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

            # 针对 baidu.com 的反爬策略
            if 'baidu.com' in host or 'baike.baidu.com' in host:
                headers.update({
                    'Referer': 'https://www.baidu.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })
                if 'BAIDUID' not in headers['Cookie']:
                    baiduid = WebUtils.generate_BAIDUID_value()
                    headers["Cookie"] = headers.get(
                        "Cookie", "") + "; BAIDUID={baiduid}:SL=0:NR=10:FG=1"

            # 针对 360搜索 (www.so.com) 的反爬策略
            if 'www.so.com' in host:
                headers.update({
		    #'Host': 'www.so.com',
		    'Referer': 'https://www.so.com/',
		    'Sec-Fetch-Dest': 'document',
		    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
		    'Connection': 'keep-alive',
                    'Sec-Fetch-User': '?1',
		    'Priority': 'u=0, i'
                })
                if 'QiHooGUID' not in headers['Cookie']:
                    headers["Cookie"] = headers.get(
                        "Cookie", "") + "; QiHooGUID=68676EB9A427AAEA16C4C1E8899D6209.1744163253954; __guid=15484592.58638361683777900.1744163254047.47; _S=11KMTkrjcvB4r9r54yEmpMUcRuub9JfSBnh+Cq00aekeo=; so_huid=11KMTkrjcvB4r9r54yEmpMUcRuub9JfSBnh%2BCq00aekeo%3D"

            # 针对豆瓣 (douban.com) 的反爬机制
            if 'douban.com' in host:
                if 'bid' not in headers['Cookie']:
                    headers["Cookie"] = headers.get(
                    "Cookie", "") +  '; bid="4mTU3-etpfY"'
                headers.update({
                    'Referer': 'https://www.douban.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })


            # 针对 movie.douban.com 的反爬策略
            if 'movie.douban.com' in host:
                if '__yadk_uid' not in headers['Cookie']:
                    headers["Cookie"] = headers.get(
                        "Cookie", "") + "; __yadk_uid=xhp8umkXwrifRJee6NIEDFwyPscmNndJ"
                headers.update({
                    'Referer': 'https://movie.douban.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })

            # 针对 Bing 搜索 (bing.com) 的反爬策略
            if 'bing.com' in host:
                headers.update({
                    'Referer': 'https://www.bing.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })
                if '_EDGE_V' not in headers['Cookie']:
                    headers["Cookie"] = headers.get(
                    "Cookie", "") +  '; _EDGE_V=1; MUID=1234567890ABCDEF1234567890ABCDEF'

            # 针对 Google 搜索 (google.com) 的反爬策略
            if 'google.com' in host:
                headers.update({
                    'Referer': 'https://www.google.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })
                if 'NID' not in headers['Cookie']:
                    headers["Cookie"] = headers.get(
                    "Cookie", "") +  '; NID=523=cSSZeP4PeHRWwPuhk9JSem7HG7OfonlOFFJJuCfhuZ2PuuPQKXg5SG55P8SznFb92XS_U4f59uZmv6uNeZZgxgK4UFAuLXvgwt-GnKuvP1na1sEVgu4gqv-mx7AGpnWtQgxLsfd2LMhLGbrR2nRsLWeA7PHI4bjqnEYW1hDMePC2tOd9Ru_wg-9n1Q5T9vAzsS8B4U-FUYiglWh6pBHj75EZx7kUEAF2WlTx58JvQTtf0Mr4PYMR43eGluSEZjtNvcv6bq-PYXFI1bWtWnaJNDfhes-YMALuAY7cGwi4DSth6ZRXEmUipYPbtX3l15gRi3dhKDKMwcZcHimLbMB8eXbxu4AQV9N9XeE5hlZhTiMVlzPWsk2FC7tm9nTVhF6T8aWVy1MDQJQ'

            # 处理搜狗搜索
            if 'sogou.com' in host:
                headers.update({
                    'Referer': 'https://www.sogou.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Connection': 'keep-alive'
                })

            # 针对 DuckDuckGo 搜索 (duckduckgo.com) 的反爬策略
            if 'duckduckgo.com' in host:
                headers.update({
                    'Referer': 'https://duckduckgo.com/',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })
                if 'dcm' not in headers['Cookie']:
                    headers["Cookie"] = headers.get(
                    "Cookie", "") +  '; dcm=1; __ddg1_=1234567890ABCDEF1234567890ABCDEF'
        logger.info("get_enhanced_headers():%s", headers)
        return headers
