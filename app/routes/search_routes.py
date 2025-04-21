# 搜索路由
import urllib.parse
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from app.controllers.search_controller import SearchController
from app.controllers.search_controller import validate_url
from app.views.search_view import render_page as render_search_page
from app.utils.response_utils import response_success, response_error

router = APIRouter()
controller = SearchController()


def _search_response_error(request: Request):
    return response_error(400, "缺少搜索关键词q", request.url)


@router.get("/fetch-agent")
def fetch_agent(request: Request, url: list = Depends(validate_url),
                mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_agent(url, dict(request.headers), mode)


@router.get("/fetch-curl")
def fetch_curl(request: Request, url: list = Depends(validate_url),
               mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_curl(url, dict(request.headers), mode)


@router.get("/fetch-request")
def fetch_request(request: Request, url: list = Depends(validate_url),
                  mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_request(url, dict(request.headers), mode)


@router.get("/fetch-firecrawl")
def fetch_firecrawl(request: Request, url: list = Depends(validate_url),
                    mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_firecrawl(url, dict(request.headers), mode)


@router.get("/fetch-scrapy")
def fetch_scrapy(request: Request, url: list = Depends(validate_url),
                 mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_scrapy(url, dict(request.headers), mode)


@router.get("/fetch-selenium")
def fetch_selenium(request: Request, url: list = Depends(validate_url),
                   mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_selenium(url, dict(request.headers), mode)


@router.get("/fetch-beautifulsoup")
def fetch_beautifulsoup(request: Request, url: list = Depends(validate_url),
                        mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_beautifulsoup(url, dict(request.headers), mode)

@router.get("/fetch-cloudscraper")
def fetch_cloudscraper(request: Request, url: list = Depends(validate_url),
                       mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_cloudscraper(url, dict(request.headers), mode)

@router.get("/fetch-playwright")
def fetch_playwright(request: Request, url: list = Depends(validate_url),
                       mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch_playwright(url, dict(request.headers), mode)

@router.get("/fetch")
def fetch(request: Request, url: list = Depends(validate_url),
          mode: str = Query("html", description="返回内容类型:html,text")):
    return controller.fetch(url, dict(request.headers), mode)


@router.get("/duckduckgo")
def search_duckduckgo(request: Request, q: str = Query(None, description="搜索关键词"),
                      mode: str = Query(
                          "text", description="返回内容类型:link,text,html"),
                      links_num: int = Query(2, description="链接数量"),
                      http_tool: str = Query("firecrawl", description="抓取工具")):
    return search_duckduckgo_web(request, q, mode, links_num, http_tool)


@router.get("/duckduckgo-api")
def search_duckduckgo_api(request: Request, q: str = Query(None, description="搜索关键词"),
                          mode: str = Query(
                              "text", description="返回内容类型:link,text,html"),
                          links_num: int = Query(2, description="链接数量"),
                          http_tool: str = Query("firecrawl", description="抓取工具")):
    if q:
        result = controller.search_duckduckgo_api(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/duckduckgo-web")
def search_duckduckgo_web(request: Request, q: str = Query(None, description="搜索关键词"),
                          mode: str = Query(
                              "text", description="返回内容类型:link,text,html"),
                          links_num: int = Query(2, description="链接数量"),
                          http_tool: str = Query("firecrawl", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_duckduckgo_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/bing-web")
def search_bing_web(request: Request, q: str = Query(None, description="搜索关键词"),
                    mode: str = Query("text", description="返回内容类型:link,text,html"),
                    links_num: int = Query(2, description="链接数量"),
                    http_tool: str = Query("request", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_bing_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/baidu-web")
def search_baidu_web(request: Request, q: str = Query(None, description="搜索关键词"),
                     mode: str = Query("text", description="返回内容类型:link,text,html"),
                     links_num: int = Query(2, description="链接数量"),
                     http_tool: str = Query("request", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_baidu_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/google-web")
def search_google_web(request: Request, q: str = Query(None, description="搜索关键词"),
                      mode: str = Query(
                          "text", description="返回内容类型:link,text,html"),
                      links_num: int = Query(2, description="链接数量"),
                      http_tool: str = Query("firecrawl", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_google_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/sogou-web")
def search_sogou_web(request: Request, q: str = Query(None, description="搜索关键词"),
                     mode: str = Query("text", description="返回内容类型:link,text,html"),
                     links_num: int = Query(2, description="链接数量"),
                     http_tool: str = Query("request", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_sogou_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/so-web")
def search_so_web(request: Request, q: str = Query(None, description="搜索关键词"),
                  mode: str = Query("text", description="返回内容类型:link,text,html"),
                  links_num: int = Query(2, description="链接数量"),
                  http_tool: str = Query("request", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_so_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)

@router.get("/douban-web")
def search_douban_web(request: Request, q: str = Query(None, description="搜索关键词"),
                  mode: str = Query("text", description="返回内容类型:link,text,html"),
                  links_num: int = Query(2, description="链接数量"),
                  http_tool: str = Query("request", description="抓取工具")):
    if q:
        q = urllib.parse.quote(q)
        result = controller.search_douban_web(
            q, mode, links_num, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("/duckduckgo-suggest")
def search_duckduckgo_suggest(request: Request, q: str = Query(None, description="搜索关键词"),
                              http_tool: str = Query("firecrawl", description="抓取工具")):
    if q:
        result = controller.search_duckduckgo_suggest(
            q, dict(request.headers), http_tool)
        return result
    return _search_response_error(request)


@router.get("")
def index():
    result = controller.index()
    html_content = render_search_page(result)
    return HTMLResponse(content=html_content)
