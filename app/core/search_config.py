config = {
    # 配置常量
    "MAX_RESULTS": 60,  # 总搜索条数（原3页×20条）
    "MAX_CONTENT_LENGTH": 1000000000,  # 内容截断长度
    "DEFAULT_RETRIES": 3,  # 重试次数
    "DEFAULT_TIMEOUT": 10,  # 超时时间（单位：秒）
    "AGENT_URL": "http://api-qui.qiyi.domain/services/agent",  # 代理服务地址
    # Firecrawl API Key（从https://www.firecrawl.dev/获取）
    "FIRECRAWL_API_KEY": "fc-938f767537f44797bf7b9d96140b6531",
    "DUCKDUCKGO_URL": "https://duckduckgo.com/html/",
    "LITE_DUCKDUCKGO_URL": "https://lite.duckduckgo.com/lite/",
    "BAIDU_URL": "https://www.baidu.com/s",
    "SOGOU_URL": "https://sogou.com/web",
    "DOUBAN_SEARCH_URL": "https://search.douban.com/movie/subject_search",
    "SO_URL": "https://www.so.com/s",
    "BING_URL": "https://www.bing.com/search",
    "GOOGLE_URL": "https://www.google.com/search",
    "DUCKDUCKGO_API": "https://duckduckgo.com/ac/",
    "ALLOWED_DOMAIN": ["baidu.com", "www.baidu.com", "baike.baidu.com", "movie.douban.com", "zh.wikipedia.org", "wikipedia.org", "zhihu.com", "bing.com", "sogou.com", "so.com", "baike.com"]
    # "ALLOWED_DOMAIN": ["baidu.com", "douban.com", "wikipedia.org"]
}