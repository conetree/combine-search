# tools/http_clients.py
"""
工具层 - HTTP 客户端模块：
    定义了各种抓取客户端，统一继承 BaseWebClient
    包括：
      - AgentClient：通过代理服务抓取
      - CurlClient：利用 curl 命令抓取
      - SimpleHTTPClient：基于 requests 库抓取
      - FirecrawlClient：利用 Firecrawl API 抓取
      - ScrapyClient：使用 Scrapy 框架抓取
      - SeleniumClient：使用 Selenium WebDriver 抓取
      - CloudscraperClient：使用 Cloudscraper 框架抓取
      - PlaywrightClient： 使用 Playwright 框架抓取
"""
import shutil
import subprocess
import time
import random
from time import sleep
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from fastapi import HTTPException
from firecrawl import FirecrawlApp
import scrapy
from bs4 import BeautifulSoup
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from multiprocessing import Process, Queue
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
import cloudscraper
import chrome_version
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from app.core.logging import logger
from app.utils.web_utils import WebUtils


class BaseWebClient:
    """
    基础 Web 客户端（可继承扩展）
    提供统一的重试逻辑和超时设置
    """

    def __init__(self, retries=3, timeout=5):
        self.DEFAULT_RETRIES = retries      # 最大重试次数
        self.DEFAULT_TIMEOUT = timeout      # 请求超时时间（单位：秒）
        self.requestsSession = requests.Session()  # 创建会话保持持久的连接和 Cookie
        self.ERROR_MESSAGE = {
            "anti-crawler": "抓取遭遇反爬虫机制，请打开地址查看，通过人工解除封禁。"
        }

    def fetch(self, url: str, headers: dict = None):
        logger.info(f"fetch {url}")

    def _wrap_error_detail(self, client_name: str, url: str, error_detail: str) -> str:
        return f"{client_name} 请求:[{url}]失败，原因:[{error_detail}]"

    def _check_anti_crawler(self, attempt: int, status_code: int, retry_statuses=None) -> tuple[bool, str]:
        """
        检查是否触发反爬虫策略，返回是否应重试以及错误信息
        """
        if retry_statuses is None:
            # 状态码是403、429、503表示被反爬虫命中
            retry_statuses = [403, 429, 503]

        if status_code in retry_statuses:
            error_detail = self.ERROR_MESSAGE.get(
                "anti-crawler", "Blocked by anti-crawler strategy")
            logger.warning(
                f"Received anti-crawler status code %s, retrying...{attempt+1}/{self.DEFAULT_RETRIES}", status_code)
            sleep(2 ** attempt + random.uniform(0, 1))
            return True, error_detail

        return False, ""

    def _handle_retry(self, attempt: int, error: Exception):
        """
        重试逻辑：
            - 记录警告日志
            - 根据尝试次数等待后重试
        """
        delay_time = 2 ** attempt + random.uniform(1, 2)
        retry_tips = f"{delay_time:.1f}s 后重试" if attempt + \
            1 < self.DEFAULT_RETRIES else " 重试结束 "
        logger.warning(
            f"{self.__class__.__name__}: 尝试 {attempt + 1}/{self.DEFAULT_RETRIES} 失败，{retry_tips}，错误：{error}")
        if attempt + 1 < self.DEFAULT_RETRIES:
            time.sleep(delay_time)


class AgentClient(BaseWebClient):
    """
    通过代理服务抓取页面的客户端
    """

    def __init__(self, agent_url: str, **kwargs):
        super().__init__(**kwargs)
        self.agent_url = agent_url  # 代理服务基础 URL

    def fetch(self, url: str, headers: dict = None):
        """
        使用代理服务抓取目标 URL 内容
        """
        logger.info("AgentClient fetch url: %s", url)
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            try:
                # 构造代理请求 URL，例如：http://代理服务?url=目标URL
                proxy_url = f"{self.agent_url}?url={url}"
                logger.info(f"Agent模式抓取: {proxy_url}")
                response = self.requestsSession.get(
                    proxy_url,
                    # 使用传递头或增强请求头（含随机 Cookie）
                    headers=WebUtils.get_enhanced_headers(url, headers),
                    timeout=self.DEFAULT_TIMEOUT,
                    verify=False
                )

                should_retry, error_detail = self._check_anti_crawler(
                    attempt, response.status_code)
                if should_retry:
                    logger.warning(
                        "request url: %s error_detail:%s", url, error_detail)
                    continue  # 进入下一轮 retry

                response.raise_for_status()
                return response.text
            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
        error_detail = self._wrap_error_detail(
            "AgentClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class CurlClient(BaseWebClient):
    """
    基于 curl 命令抓取页面内容的客户端
    """

    def fetch(self, url: str, headers: dict = None) -> str:
        logger.info("CurlClient fetch url: %s", url)
        headers = WebUtils.get_enhanced_headers(url, headers)
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            # 构造 curl 命令，包括自动重定向、超时参数和状态码输出
            curl_command = [
                "curl",
                "-L",
                "--insecure",
                "-m", str(self.DEFAULT_TIMEOUT),
                "-w", "\n%{http_code}",  # 在输出末尾添加状态码
                url
            ]

            # 添加 headers 参数
            for key, value in headers.items():
                curl_command.extend(["-H", f"{key}: {value}"])

            try:
                result = subprocess.run(
                    curl_command,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self.DEFAULT_TIMEOUT + 3,  # 额外延时防止超时未捕获
                )

                output = result.stdout or ''
                # 解析状态码和内容
                lines = output.split('\n')
                status_code_line = lines[-1].strip() if lines else ''
                if not status_code_line.isdigit():
                    raise ValueError(
                        f"Invalid status code: {status_code_line}")
                status_code = int(status_code_line)
                content = '\n'.join(lines[:-1])  # 去除最后一行状态码

                # 检查是否为反爬状态码
                should_retry, error_detail = self._check_anti_crawler(
                    attempt, status_code)
                if should_retry:
                    logger.warning(
                        "request url: %s error_detail:%s", url, error_detail)
                    continue  # 进入下一轮 retry

                # 状态码正常，返回内容
                return content

            except subprocess.CalledProcessError as e:
                error_detail = f"子进程错误: {e.stderr}"
                self._handle_retry(attempt, e)
            except subprocess.TimeoutExpired as e:
                error_detail = "请求超时"
                self._handle_retry(attempt, e)
            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
            finally:
                # 确保子进程被终止（即使出现异常）
                pass  # 若子进程未自动终止，可添加强制终止逻辑

        # 重试次数用尽后抛出异常
        error_detail = self._wrap_error_detail("CurlClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class SimpleHTTPClient(BaseWebClient):
    """
    基于 requests 库抓取页面内容的客户端
    """

    def fetch(self, url: str, headers: dict = None):
        logger.info("SimpleHTTPClient fetch url: %s", url)
        try:
            # 添加连接池配置
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=50,
                max_retries=3
            )
            self.requestsSession.mount('https://', adapter)
            self.requestsSession.mount('http://', adapter)
        except Exception as e:
            logger.warning(f"连接池配置失败: {str(e)}")
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            try:
                response = self.requestsSession.get(
                    url,
                    headers=WebUtils.get_enhanced_headers(url, headers),
                    timeout=self.DEFAULT_TIMEOUT,
                    verify=False
                )
                responseText = response.text
                # 可根据返回码判断是否命中反爬规则（例如 403、503）
                should_retry, error_detail = self._check_anti_crawler(
                    attempt, response.status_code)
                if should_retry:
                    logger.warning(
                        "request url: %s error_detail:%s", url, error_detail)
                    continue  # 进入下一轮 retry
                response.raise_for_status()
                return responseText
            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
        error_detail = self._wrap_error_detail(
            "SimpleHTTPClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class FirecrawlClient(BaseWebClient):
    """
    基于 Firecrawl API 抓取页面内容的客户端
    """

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key  # Firecrawl API Key

    def _extract_content(self, result):
        if isinstance(result, dict):
            return result.get('html', '')
        elif isinstance(result, list):
            return "\n".join(res.get('html', '') for res in result)
        elif isinstance(result, str):
            return result
        return 'unknown type.'

    def fetch(self, url: str, headers: dict = None):
        logger.info("FirecrawlClient fetch url: %s", url)
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            try:
                fc_app = FirecrawlApp(api_key=self.api_key)
                enhanced_headers = WebUtils.get_enhanced_headers(url, headers)
                crawl_result = fc_app.scrape_url(
                    url,
                    params={
                        "headers": enhanced_headers,
                        # 其他可选参数：formats、waitFor、timeout 等
                        'formats': ['html'],
                        # 'formats': ['markdown', 'html'],
                        # 'waitFor': 1000,
                        # 'timeout': 6000
                        'metadata': True
                    }
                )

                # 情况1：从API响应字典中获取状态码
                if isinstance(crawl_result, dict):
                    status_code = crawl_result.get(
                        'metadata', {}).get('statusCode', 200)

                    should_retry, error_detail = self._check_anti_crawler(
                        attempt, status_code)
                    if should_retry:
                        logger.warning(
                            "request url: %s error_detail:%s", url, error_detail)
                        continue  # 进入下一轮 retry

                # 情况2：处理空内容（可能是反爬导致的假空页面）
                content = self._extract_content(crawl_result)
                if not content.strip():
                    logger.warning("Empty content detected, retrying...")
                    sleep(2 ** attempt + random.uniform(0, 1))
                    continue

                return content
            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
        error_detail = self._wrap_error_detail(
            "FirecrawlClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class BeautifulSoupClient(BaseWebClient):
    """
    使用 requests 和 BeautifulSoup 抓取页面的客户端
    """

    def fetch(self, url: str, headers: dict = None):
        logger.info("BeautifulSoupClient fetch url: %s", url)
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            try:
                response = self.requestsSession.get(
                    url,
                    headers=WebUtils.get_enhanced_headers(url, headers),
                    timeout=self.DEFAULT_TIMEOUT,
                    verify=False
                )
                # 可根据返回码判断是否命中反爬规则（例如 403、503）
                should_retry, error_detail = self._check_anti_crawler(
                    attempt, response.status_code)
                if should_retry:
                    logger.warning(
                        "request url: %s error_detail:%s", url, error_detail)
                    continue  # 进入下一轮 retry

                response.raise_for_status()
                # 解析 HTML 内容 提取 文本
                soup = BeautifulSoup(response.text, "html.parser")
                """
                body_tag = soup.find("body")
                if body_tag:
                    results = body_tag.get_text(strip=True)
                    return results
                """
                return soup.get_text()
            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
        error_detail = self._wrap_error_detail("BeautifulSoupClient",
                                               url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class ScrapyClient(BaseWebClient):
    """
    使用 Scrapy 框架抓取页面内容的客户端
    """

    class SimpleSpider(scrapy.Spider):
        name = "simplespider"
        custom_settings = {
            'DOWNLOAD_DELAY': 1,
            'LOG_LEVEL': 'ERROR',
            'COOKIES_ENABLED': False,
            # === 反防爬设置 ===
            'RETRY_TIMES': 3,  # Scrapy内置重试
            'RETRY_HTTP_CODES': [503, 504, 403, 429],
            'DOWNLOAD_TIMEOUT': 30,  # 增加超时
            'USER_AGENT_ROTATION': True  # 需要配合中间件
        }

        def __init__(self, queue, target_url, custom_headers=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.queue = queue
            self.target_url = target_url
            self.custom_headers = custom_headers
            self.retry_count = 0

        def start_requests(self):
            headers = WebUtils.get_enhanced_headers(
                self.target_url, self.custom_headers)

            yield scrapy.Request(
                url=self.target_url,
                headers=headers,
                callback=self.parse,
                errback=self.errback,  # 错误回调
                meta={'attempt': 0}  # 记录原始请求尝试次数
            )

        def parse(self, response):
            if response.status in [403, 503]:
                logger.warning(f"触发反爬状态码 {response.status}")
                self.queue.put({"status": response.status,
                               "error_detail": "触发反爬状态码，需要人工解除。"})
                return

            # 检测验证页面
            if "antibot-challenge" in response.text:
                logger.warning("检测到验证页面")
                self.queue.put({"status": response.status,
                               "error_detail": "验证页面触发反爬策略，需要人工解除。"})
                return
            # 正常响应
            self.queue.put({"status": response.status, "text": response.text})

        def errback(self, failure):
            # 处理超时等网络错误
            logger.warning("请求异常：%s", failure.getErrorMessage())
            self.queue.put(
                {"status": 0, "error_detail": f"请求失败：{failure.getErrorMessage()}"})

        def _retry_request(self, request):
            """自定义重试逻辑（突破Scrapy默认重试限制）"""
            attempt = request.meta.get('attempt', 0) + 1
            if attempt <= self.DEFAULT_RETRIES:  # 额外重试次数
                # 指数退避 + 随机抖动
                delay = 2 ** attempt + random.uniform(0, 2)
                logger.info(f"第{attempt}次重试，延迟{delay:.1f}s")
                new_request = request.copy()
                new_request.meta['attempt'] = attempt
                new_request.dont_filter = True  # 避免被过滤
                return new_request.replace(delay=delay)
            else:
                logger.error("重试次数耗尽")
                self.queue.put("")  # 防止主进程卡死

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.queue = Queue()

    def run_crawler(self, url, headers):
        process = CrawlerProcess(settings=get_project_settings())
        process.crawl(self.SimpleSpider, target_url=url,
                      queue=self.queue, custom_headers=headers)
        process.start()

    def fetch(self, url: str, headers: dict = None):
        logger.info("ScrapyClient fetch url: %s", url)
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            try:
                proc = Process(target=self.run_crawler, args=(url, headers))
                proc.start()
                result = self.queue.get(timeout=self.DEFAULT_TIMEOUT)

                # 判断返回的数据类型，如果是字典，提取相应的数据
                if isinstance(result, dict):
                    # 如果存在 error_detail，则说明遇到了反爬错误或验证页面
                    if "error_detail" in result:
                        error_detail = result["error_detail"]
                        should_retry, _ = self._check_anti_crawler(
                            attempt, result.get("status", 503))
                        if should_retry:
                            logger.warning(
                                "request url: %s error_detail:%s", url, error_detail)
                            continue
                        raise Exception(error_detail)
                    result_text = result.get("text", "").strip()
                else:
                    result_text = result.strip()

                if not result_text:
                    # 如果文本为空，调用 _check_anti_crawler 来判断是否触发反爬
                    should_retry, error_detail = self._check_anti_crawler(
                        attempt, 503)
                    if should_retry:
                        logger.warning(
                            "request url: %s error_detail:%s", url, error_detail)
                        continue

                proc.join()
                logger.info(f"Scrapy抓取完成: {url}")
                return result_text
            except Exception as e:
                error_detail = str(e)
                # 如果异常信息中包含反爬关键词，则先尝试检查反爬，如果不需要重试就立即抛出
                if any(keyword in error_detail for keyword in ['403', '503', '验证']):
                    should_retry, _ = self._check_anti_crawler(attempt, 503)
                    if not should_retry:
                        raise e
                self._handle_retry(attempt, e)
            finally:
                proc.join(timeout=self.DEFAULT_TIMEOUT)
                if proc.is_alive():
                    proc.terminate()
                    proc.join()  # 确保资源被回收
        error_detail = self._wrap_error_detail(
            "ScrapyClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class ScrapyClient_simple(BaseWebClient):
    """
    使用 Scrapy 框架抓取页面内容的客户端简版[可选]
    """
    class SimpleSpider(scrapy.Spider):
        name = "simplespider"
        custom_settings = {
            'DOWNLOAD_DELAY': 1,
            'LOG_LEVEL': 'ERROR',
            'COOKIES_ENABLED': False,
        }

        def __init__(self, queue, target_url, custom_headers=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.queue = queue
            self.target_url = target_url
            self.custom_headers = custom_headers

        def start_requests(self):
            headers = WebUtils.get_enhanced_headers(
                self.target_url, self.custom_headers)
            yield scrapy.Request(url=self.target_url, headers=headers, callback=self.parse)

        def parse(self, response):
            self.queue.put(response.text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.queue = Queue()

    def run_crawler(self, url, headers):
        process = CrawlerProcess(settings=get_project_settings())
        process.crawl(self.SimpleSpider, target_url=url,
                      queue=self.queue, custom_headers=headers)
        process.start()

    def fetch(self, url: str, headers: dict = None):
        logger.info("ScrapyClient fetch url: %s", url)
        error_detail = ""
        for attempt in range(self.DEFAULT_RETRIES):
            try:
                proc = Process(target=self.run_crawler, args=(url, headers))
                proc.start()
                result = self.queue.get(timeout=self.DEFAULT_TIMEOUT)
                proc.join()
                logger.info(f"Scrapy抓取完成: {url}")
                return result
            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
        error_detail = self._wrap_error_detail("ScrapyClient_simple",
                                               url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class SeleniumClient(BaseWebClient):
    """Selenium客户端(反防爬虫)"""

    def __init__(self, headless=True, **kwargs):
        super().__init__(**kwargs)
        self.headless = headless
        self.timeout = self.DEFAULT_TIMEOUT * 3
        self.webdriver_options = None
        self.webdriver_service = None
        self.chrome_path = self._detect_chrome_binary()
        self.driver_version = self._detect_chrome_version()

    def _detect_chrome_binary(self) -> str:
        """检测Chrome安装路径"""
        common_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        ]

        for path in common_paths:
            if Path(path).exists():
                logger.info(f"检测到Chrome路径: {path}")
                return str(path)

        # 尝试环境变量查找
        env_path = shutil.which("google-chrome") or shutil.which("chrome")
        if env_path:
            logger.info(f"检测到Chrome路径: {env_path}")
            return env_path

        """
        $ wget http://dist.control.lth.se/public/CentOS-7/x86_64/google.x86_64/google-chrome-stable-124.0.6367.118-1.x86_64.rpm
        $ sudo yum install google-chrome-stable-124.0.6367.118-1.x86_64.rpm
        $ google-chrome --version
        $ Google Chrome 124.0.6367.118 
        $ google-chrome --headless --no-sandbox --dump-dom https://www.baidu.com
        """
        logger.info("Chrome未安装，请参考：https://www.google.com/chrome/")
        raise RuntimeError("Chrome未安装，请安装后重试。")

    def _detect_chrome_version(self):
        """检测Chrome版本"""
        chrome_ver = chrome_version.get_chrome_version()
        if chrome_ver:
            logger.info(f"已安装 Chrome，version:{chrome_ver}")
            return chrome_ver
        else:
            logger.info("Chrome未安装，请安装。")
            raise RuntimeError("Chrome未安装，请安装后重试。")

    def _get_driver_options(self):
        if self.webdriver_options is None:
            self.webdriver_options = self._create_driver_options()
        return self.webdriver_options

    def _create_driver_options(self):
        """创建浏览器选项配置"""
        options = ChromeOptions()

        # 无头模式增强配置
        if self.headless:
            # 设置无头版本为new某些情况因版本不对则渲染不成功
            options.add_argument("--headless=new")
            # options.add_argument("--headless=old")
            options.add_argument("--disable-gpu")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--disable-dev-shm-usage")

        # 通用防检测配置
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # 性能优化参数
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")

        return options

    def _get_webdriver_service(self):
        if self.webdriver_service is None:
            self.webdriver_service = self._create_webdriver_service()
        return self.webdriver_service

    def _create_webdriver_service(self) -> Service:
        """创建驱动服务（国内镜像加速+智能错误处理）"""
        # 配置国内镜像源（外网有可能加载不成功）
        mirror_url = "https://registry.npmmirror.com/binary.html?path=chromedriver/"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                service = Service(
                    ChromeDriverManager(
                        url=mirror_url  # 镜像路径可选
                    ).install()
                )

                # Linux/Mac系统需要添加执行权限[可选]
                # if os.name != 'nt':
                #     os.chmod(service.path, 0o755)
                #     logger.info(f"设置驱动可执行权限: {service.path}")

                logger.info(f"驱动安装成功 | 路径: {service.path}")
                return service

            except WebDriverException as e:
                error_msg = str(e)
                logger.error(
                    f"WebDriver异常 ({attempt+1}/{max_retries}): {error_msg}")

                # 处理特定错误
                if "session not created" in error_msg:
                    logger.warning("浏览器/驱动版本不匹配，请修复...")
                    self._handle_driver_mismatch()
                    sleep(2)
                else:
                    raise

            except Exception as e:
                logger.error(f"未知错误 ({attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                sleep(3)

        raise WebDriverException("无法创建驱动服务")

    def _handle_driver_mismatch(self):
        """处理驱动版本不匹配"""
        logger.error(f"Chrome版本冲突: {self.driver_version}")
        latest_driver = ChromeDriverManager().get_browser_version_from_os()
        raise RuntimeError(
            f"请执行以下操作之一：\n"
            f"1. 升级Chrome: yum install -y google-chrome-stable\n"
            f"2. 手动下载驱动: https://chromedriver.chromium.org/downloads (需版本≥{latest_driver})"
        )

    def _apply_headers(self, driver, headers: dict):
        """通过CDP设置请求头"""
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd(
                "Network.setExtraHTTPHeaders",
                {"headers": {k: str(v) for k, v in headers.items()}}
            )
        except Exception as e:
            logger.warning(f"设置Header失败: {str(e)}")

    def _get_response_code(self, driver):
        """通过JavaScript获取响应状态码"""
        try:
            response_code = driver.execute_script(
                "return window.performance.getEntries()[0].responseStatus"
            )
            return response_code
        except Exception:
            return None

    def fetch(self, url: str, headers: dict = None):
        logger.info(f"SeleniumClient fetch url: {url}")
        error_detail = ""
        headers = WebUtils.get_enhanced_headers(url, headers)
        options = self._get_driver_options()
        service = self._get_webdriver_service()
        for key, value in headers.items():
            options.add_argument(f'--header={key}:{value}')

        for attempt in range(self.DEFAULT_RETRIES):
            driver = None
            try:
                driver = webdriver.Chrome(
                    service=service,
                    options=options,
                    keep_alive=True  # 保持连接复用
                )
                driver.set_page_load_timeout(self.timeout)
                # 也可通过 DevTools 协议（CDP）来设置headers
                # self._apply_headers(driver, headers)
                driver.get(url)

                # 检查是否被封禁（通过状态码或页面内容）
                response_code = self._get_response_code(driver)
                should_retry, error_detail = self._check_anti_crawler(
                    attempt, response_code)
                if should_retry:
                    logger.warning(
                        "request url: %s error_detail:%s", url, error_detail)
                    continue  # 进入下一轮 retry

                # 等待渲染[可选]
                wait = WebDriverWait(driver, 10)
                # 显式等待关键元素加载（示例：等待<body>渲染）
                # WebDriverWait(driver, self.timeout).until(
                #     EC.presence_of_element_located((By.TAG_NAME, "body"))
                # )
                # 也可以等待整个页面的 JavaScript 执行完成（使用 document.readyState）
                wait.until(lambda d: d.execute_script(
                    "return document.readyState") == "complete")

                return driver.page_source

            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
            finally:
                if driver:
                    driver.quit()

        error_detail = self._wrap_error_detail(
            "SeleniumClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class SeleniumClient_simple(BaseWebClient):
    """Selenium客户端简版[可选]"""

    def __init__(self, headless=True, **kwargs):
        super().__init__(**kwargs)
        self.headless = headless
        self.timeout = self.DEFAULT_TIMEOUT * 2
        self.chrome_path = self._detect_chrome_binary()
        self.driver_version = self._detect_chrome_version()

    def _detect_chrome_binary(self) -> str:
        """检测Chrome安装路径"""
        common_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        ]

        for path in common_paths:
            if Path(path).exists():
                logger.info(f"检测到Chrome路径: {path}")
                return str(path)

        # 尝试环境变量查找
        env_path = shutil.which("google-chrome") or shutil.which("chrome")
        if env_path:
            print(f"检测到Chrome路径: {env_path}")
            return env_path

        """
        $ wget http://dist.control.lth.se/public/CentOS-7/x86_64/google.x86_64/google-chrome-stable-124.0.6367.118-1.x86_64.rpm
        $ sudo yum install google-chrome-stable-124.0.6367.118-1.x86_64.rpm
        $ google-chrome --version
        $ Google Chrome 124.0.6367.118 
        $ google-chrome --headless --no-sandbox --dump-dom https://www.baidu.com
        """
        logger.info("Chrome未安装，请参考：https://www.google.com/chrome/")

    def _detect_chrome_version(self):
        """检测Chrome"""
        chrome_ver = chrome_version.get_chrome_version()
        if chrome_ver:
            print(f"已安装 Chrome，version:{chrome_ver}")
            return chrome_ver
        else:
            logger.info("Chrome未安装，请安装。")

    def _create_driver_options(self):
        """创建浏览器选项配置"""
        options = ChromeOptions()

        # 无头模式增强配置
        if self.headless:
            options.add_argument("--headless=new")
            # options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('lang=zh_CN.UTF-8')

        # 通用防检测配置
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # 性能优化参数
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")

        return options

    def _create_webdriver_service(self) -> Service:
        """镜像地址，可选"""
        mirror_url = "https://registry.npmmirror.com/binary.html?path=chromedriver/"
        try:
            print(f"ChromeDriverManager install: {mirror_url}")
            service = Service(ChromeDriverManager(
                url=mirror_url
            ).install())
            print(f"ChromeDriverManager install done: {service}")
            return service
        except WebDriverException as e:
            if "WebDriverException error:" in str(e):
                self._handle_driver_mismatch()
            raise
        except Exception as e:
            logger.error(f"ChromeDriverManager 驱动服务创建失败: {str(e)}")
            raise

    def _handle_driver_mismatch(self):
        """处理驱动版本不匹配"""
        logger.error(f"Chrome版本冲突: {self.driver_version}")
        latest_driver = ChromeDriverManager().get_browser_version_from_os()
        raise RuntimeError(
            f"请执行以下操作之一：\n"
            f"1. 升级Chrome: yum install -y google-chrome-stable\n"
            f"2. 手动下载驱动: https://chromedriver.chromium.org/downloads (需版本≥{latest_driver})"
        )

    def fetch(self, url: str, headers: dict = None):
        logger.info(f"SeleniumClient fetch url: {url}")
        error_detail = ""
        headers = WebUtils.get_enhanced_headers(url, headers)
        options = self._create_driver_options()
        service = self._create_webdriver_service()
        # 添加 headers 到 ChromeOptions
        for key, value in headers.items():
            options.add_argument(f'--header={key}:{value}')

        for attempt in range(self.DEFAULT_RETRIES):
            driver = None
            try:
                driver = webdriver.Chrome(
                    service=service,
                    options=options,
                    keep_alive=True  # 保持连接复用
                )
                driver.set_page_load_timeout(self.timeout)
                driver.get(url)
                return driver.page_source

            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)
            finally:
                if driver:
                    driver.quit()
        error_detail = self._wrap_error_detail(
            "SeleniumClient_simple_client", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class CloudscraperClient(BaseWebClient):
    """
    增强版 cloudscraper 客户端（支持深度反爬穿透）
    新增能力：
    1. 动态请求头伪装
    2. 浏览器指纹模拟
    3. 智能代理轮询
    4. 验证页面自动识别
    5. 随机化请求参数
    6. 挑战解决方案增强
    """

    def __init__(self,
                 proxy_pool: List[str] = None,  # 新增代理池支持
                 browser_fingerprint: Dict = None,  # 自定义浏览器指纹
                 **kwargs):
        super().__init__(**kwargs)

        # === 新增反爬配置 ===
        self.proxy_pool = proxy_pool or []
        self.browser_fingerprint = browser_fingerprint or {
            'browser': 'chrome',
            'mobile': False,
            'platform': 'windows'
        }

        # === 强化 cloudscraper 配置 ===
        self.scraperSession = cloudscraper.create_scraper(
            interpreter='nodejs',  # 使用NodeJS解析JS
            delay=random.uniform(1, 3),  # 随机化请求延迟
            browser=self.browser_fingerprint
        )

    def _handle_anti_crawl_retry(self, attempt: int, status_code: int):
        """专用反爬重试策略"""
        logger.warning(
            "CloudscraperClient Received status code %s, retrying...", status_code)
        # sleep(2 ** attempt + random.uniform(0, 1))
        # 每3次重试切换一次指纹
        if (attempt + 1) % 3 == 0:
            self._rotate_fingerprint()

    def _rotate_fingerprint(self):
        """动态切换浏览器指纹"""
        new_fingerprint = {
            'browser': random.choice(['chrome', 'firefox', 'edge']),
            'mobile': random.choice([True, False]),
            'platform': random.choice(['windows', 'macos', 'linux'])
        }
        self.scraperSession.browser = new_fingerprint
        logger.debug(f"切换浏览器指纹: {new_fingerprint}")

    def fetch(self, url: str, headers: dict = None) -> str:
        logger.info("CloudscraperClient fetch url: %s", url)
        error_detail = ""

        # === 生成动态增强请求头 ===
        enhanced_headers = WebUtils.get_enhanced_headers(url, headers)
        enhanced_headers.update({
            'Sec-Fetch-Mode': 'navigate' if random.random() > 0.5 else 'cors'
        })

        for attempt in range(self.DEFAULT_RETRIES):
            try:
                # === 新增请求参数随机化 ===
                request_params = {
                    'headers': enhanced_headers,
                    'timeout': self.DEFAULT_TIMEOUT + random.randint(1, 5),
                    # 'allow_redirects': random.choice([True, False]),
                    'allow_redirects': True,  # 默认启用重定向
                    'params': {'_t': int(time.time())}  # 添加随机时间戳参数
                }

                # === 代理轮询逻辑 ===
                if self.proxy_pool:
                    proxy = random.choice(self.proxy_pool)
                    request_params['proxies'] = {'http': proxy, 'https': proxy}
                    logger.debug(f"Using proxy: {proxy}")

                response = self.scraperSession.get(url, **request_params)

                # 第一层：根据状态码判断是否命中反爬规则（例如 403、503）
                should_retry, error_detail = self._check_anti_crawler(
                    attempt, response.status_code)
                if should_retry:
                    logger.warning(
                        "request url: %s error_detail:%s", url, error_detail)
                    self._handle_anti_crawl_retry(
                        attempt, response.status_code)
                    continue  # 进入下一轮 retry

                # 第二层：软性内容特征检测[可选]
                # anti_crawl_conditions = [
                #     "cloudflare" in response.text.lower(),
                #     "access denied" in response.text.lower(),
                #     "请输入验证码" in response.text,
                #     len(response.text) < 1024  # 小页面可能是验证页
                # ]
                # if any(anti_crawl_conditions):
                #     # self._handle_anti_crawl_retry(attempt, response.status_code)
                #     continue

                response.raise_for_status()

                return response.text

            except Exception as e:
                error_detail = str(e)
                self._handle_retry(attempt, e)

        error_detail = self._wrap_error_detail(
            "CloudscraperClient", url, error_detail)
        raise HTTPException(status_code=502, detail=error_detail)


class PlaywrightClient(BaseWebClient):
    """
    基于Playwright的浏览器客户端，具备高级反爬绕过能力
    """

    # 默认浏览器配置
    BROWSER_CONFIG = {
        'headless': True,                   # 是否无头
        'slow_mo': random.randint(150, 450),  # 操作延迟，模拟人速
        'proxy': None,                      # 代理服务器
        'user_agent': None,                 # 自定义UA
        'viewport': {'width': 1366, 'height': 768},
        'bypass_csp': True,                 # 绕过内容安全策略
        'stealth_mode': True,               # 启用反检测脚本
        'user_data_dir': None,              # 可选用户数据目录
    }

    def __init__(self, config: Dict = None, **kwargs):
        super().__init__(**kwargs)
        # 合并外部配置
        if config:
            self.BROWSER_CONFIG.update(config)
        # UA 生成
        if not self.BROWSER_CONFIG['user_agent']:
            self.BROWSER_CONFIG['user_agent'] = self._generate_realistic_ua()
        self.chrome_path = self._detect_chrome_binary()

    def _detect_chrome_binary(self) -> str:
        """检测Chrome安装路径"""
        common_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        ]

        for path in common_paths:
            if Path(path).exists():
                logger.info(f"检测到Chrome路径: {path}")
                return str(path)

        # 尝试环境变量查找
        env_path = shutil.which("google-chrome") or shutil.which("chrome")
        if env_path:
            logger.info(f"检测到Chrome路径: {env_path}")
            return env_path

        # 如果没有找到Chrome路径，返回None
        logger.warning("未能检测到Chrome路径，Playwright将使用默认的Chromium浏览器。")
        return None

    def _generate_realistic_ua(self) -> str:
        """随机生成 Chrome UA"""
        versions = ['120.0.6099.224', '121.0.6167.140',
                    '122.0.6261.112', '123.0.6312.88']
        return (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{random.choice(versions)} Safari/537.36"
        )

    def _rotate_fingerprint(self):
        """每次重试时随机轮换 UA 和视窗大小"""
        logger.info("PlaywrightClient: 轮换浏览器指纹")
        self.BROWSER_CONFIG['user_agent'] = self._generate_realistic_ua()
        self.BROWSER_CONFIG['viewport'] = {
            'width': random.choice([1366, 1440, 1536, 1600]),
            'height': random.choice([768, 900, 1024, 1080])
        }

    def _anti_detection_actions(self, page):
        """模拟鼠标移动和滚动，反检测行为"""
        for _ in range(random.randint(3, 7)):
            x = random.randint(0, self.BROWSER_CONFIG['viewport']['width'])
            y = random.randint(0, self.BROWSER_CONFIG['viewport']['height'])
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))
        page.evaluate(f"window.scrollBy(0, {random.randint(200, 800)})")
        time.sleep(random.uniform(0.5, 1.2))

    def _check_denied_crawler(self, page) -> bool:
        """检测反爬机制触发状态"""
        # 检查常见反爬特征
        detection_indicators = [
            ('验证码', '//div[contains(@class, "captcha-container")]'),
            ('访问限制', 'text=Access Denied'),
            ('流量异常', 'text=Unusual Traffic')
        ]

        for text, xpath in detection_indicators:
            if page.query_selector(xpath) is not None:
                logger.warning(f"检测到反爬特征: {text}")
                return True
        return False

    def fetch(self, url: str, headers: Dict[str, str] = None) -> str:
        """
        1. 将所有 sync_playwright 调用放入同一上下文，确保不跨线程/Greenlet
        2. 保留重试、指纹轮换、反爬检测逻辑
        """
        error_detail = ""
        # 在同一 Greenlet/线程中启动 Playwright
        with sync_playwright() as pw:
            for attempt in range(self.DEFAULT_RETRIES):
                browser = context = page = None
                # 在 for 循环内 每轮尝试都用 try/finally 管理，
                # 确保当轮的 browser、context、page 在结束时被立即关闭
                try:
                    browser = pw.chromium.launch(
                        headless=self.BROWSER_CONFIG['headless'],
                        slow_mo=self.BROWSER_CONFIG['slow_mo'],
                        executable_path=self.chrome_path,  # 优先使用检测到的Chrome路径
                        proxy={'server': self.BROWSER_CONFIG['proxy']}
                        if self.BROWSER_CONFIG['proxy'] else None,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-infobars',
                            '--no-sandbox',
                            f"--window-size={self.BROWSER_CONFIG['viewport']['width']},"
                            f"{self.BROWSER_CONFIG['viewport']['height']}",
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process'
                        ]
                    )
                    context = browser.new_context(
                        user_agent=self.BROWSER_CONFIG['user_agent'],
                        viewport=self.BROWSER_CONFIG['viewport'],
                        bypass_csp=self.BROWSER_CONFIG['bypass_csp']
                    )
                    # 注入反检测脚本
                    if self.BROWSER_CONFIG['stealth_mode']:
                        context.add_init_script("""
                            delete navigator.__proto__.webdriver;
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => [1,2,3]
                            });
                        """)
                    # 地理位置模拟
                    context.grant_permissions(['geolocation'])
                    context.set_geolocation({
                        'latitude': random.uniform(-90, 90),
                        'longitude': random.uniform(-180, 180)
                    })

                    page = context.new_page()
                    # 增强请求头
                    enhanced = WebUtils.get_enhanced_headers(url, headers)
                    page.set_extra_http_headers(enhanced)

                    # 导航并获取响应状态
                    response = page.goto(
                        url, timeout=self.DEFAULT_TIMEOUT * 500)
                    status_code = response.status
                    should_retry, error_detail = self._check_anti_crawler(
                        attempt, status_code)
                    if should_retry or self._check_denied_crawler(page):
                        error_detail = error_detail if error_detail == '' else "页面中含有验证码或拒绝访问"
                        logger.warning(
                            "检测到反爬机制：request url: %s error_detail:%s", url, error_detail)
                        # 执行反检测行为
                        self._anti_detection_actions(page)
                        self._rotate_fingerprint()
                        continue

                    # 获取渲染后内容并检查反爬
                    content = page.content()
                    return content

                except PlaywrightTimeoutError as e:
                    error_detail = f"页面加载超时：{e}"
                    self._handle_retry(attempt, e)
                except Exception as e:
                    error_detail = str(e)
                    self._handle_retry(attempt, e)
                finally:
                    # 显式 close，确保不留残余 transport
                    try:
                        if page:
                            page.close()
                        if context:
                            context.close()
                        if browser:
                            browser.close()
                    except Exception as e:
                        logger.error(f"PlaywrightClient 资源释放时发生异常: {e}")
                        pass

        # 所有重试用尽，抛出异常
        raise HTTPException(
            status_code=503,
            detail=self._wrap_error_detail(
                "PlaywrightClient", url, error_detail)
        )

