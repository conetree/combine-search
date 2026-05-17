"""
Search / fetch runtime config. Values come from environment variables with safe defaults.
Do not commit API keys; set FIRECRAWL_API_KEY and AGENT_PROXY_BASE in .env
"""
from __future__ import annotations

import os
from typing import Any, Dict, List


def _int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _allowed_domains() -> List[str]:
    raw = os.getenv(
        "ALLOWED_DOMAIN",
        "baidu.com,www.baidu.com,baike.baidu.com,movie.douban.com,"
        "zh.wikipedia.org,wikipedia.org,zhihu.com,bing.com,sogou.com,so.com,baike.com",
    )
    return [d.strip() for d in raw.split(",") if d.strip()]


def build_search_config() -> Dict[str, Any]:
    return {
        "MAX_RESULTS": _int("MAX_RESULTS", 60),
        "MAX_CONTENT_LENGTH": _int("MAX_CONTENT_LENGTH", 1_000_000_000),
        "DEFAULT_RETRIES": _int("DEFAULT_RETRIES", 3),
        "DEFAULT_TIMEOUT": _int("DEFAULT_TIMEOUT", 10),
        "AGENT_URL": os.getenv("AGENT_PROXY_BASE", os.getenv("AGENT_URL", "")).rstrip("/"),
        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", ""),
        "DUCKDUCKGO_URL": os.getenv("DUCKDUCKGO_URL", "https://duckduckgo.com/html/"),
        "LITE_DUCKDUCKGO_URL": os.getenv(
            "LITE_DUCKDUCKGO_URL", "https://lite.duckduckgo.com/lite/"
        ),
        "BAIDU_URL": os.getenv("BAIDU_URL", "https://www.baidu.com/s"),
        "SOGOU_URL": os.getenv("SOGOU_URL", "https://sogou.com/web"),
        "DOUBAN_SEARCH_URL": os.getenv(
            "DOUBAN_SEARCH_URL", "https://search.douban.com/movie/subject_search"
        ),
        "SO_URL": os.getenv("SO_URL", "https://www.so.com/s"),
        "BING_URL": os.getenv("BING_URL", "https://www.bing.com/search"),
        "GOOGLE_URL": os.getenv("GOOGLE_URL", "https://www.google.com/search"),
        "DUCKDUCKGO_API": os.getenv("DUCKDUCKGO_API", "https://duckduckgo.com/ac/"),
        "ALLOWED_DOMAIN": _allowed_domains(),
    }


config: Dict[str, Any] = build_search_config()
