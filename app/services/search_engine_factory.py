from typing import Dict, Any
from app.services.search_service import BaseSearch
from app.services.duckduckgo_service import DuckduckgoService
from app.services.bing_service import BingService
from app.services.baidu_service import BaiduService
from app.services.google_service import GoogleService
from app.services.sogou_service import SogouService
from app.services.douban_service import DoubanService
from app.services.so_service import SoService

from typing import Dict, Type


import threading
from typing import Dict, Type
from app.services.search_service import BaseSearch
from app.services.duckduckgo_service import DuckduckgoService
from app.services.bing_service import BingService
from app.services.baidu_service import BaiduService
from app.services.google_service import GoogleService
from app.services.sogou_service import SogouService
from app.services.so_service import SoService

class SearchEngineFactory:
    """搜索引擎服务工厂（线程安全单例模式）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SearchEngineFactory, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._service_cache: Dict[str, BaseSearch] = {}
        self._service_registry: Dict[str, Type[BaseSearch]] = {}

    def register_service(self, name: str, service_cls: Type[BaseSearch]) -> None:
        self._service_registry[name.lower()] = service_cls

    def _generate_cache_key(self, service_name: str, http_tool: str) -> str:
        return f"{service_name.lower()}_{http_tool}"

    def get_service(self, service_name: str, http_tool: str = "default", force_new: bool = False) -> BaseSearch:
        cache_key = self._generate_cache_key(service_name, http_tool)

        if not force_new and cache_key in self._service_cache:
            return self._service_cache[cache_key]

        service_cls = self._service_registry.get(service_name.lower())
        if not service_cls:
            raise ValueError(f"未注册的搜索服务: {service_name}")

        instance = service_cls(http_tool=http_tool)
        self._service_cache[cache_key] = instance
        return instance

class DefaultSearchEngineFactory:
    """默认的搜索引擎工厂，使用 SearchEngineFactory 获取搜索服务实例"""

    _factory = SearchEngineFactory()

    @classmethod
    def register_default_services(cls):
        """注册默认的搜索引擎服务"""
        default_services = {
            "duckduckgo": DuckduckgoService,
            "bing": BingService,
            "baidu": BaiduService,
            "google": GoogleService,
            "sogou": SogouService,
            "douban": DoubanService,
            "so": SoService
        }
        for name, service_cls in default_services.items():
            cls._factory.register_service(name, service_cls)

    @classmethod
    def get_service(cls, service_name: str, http_tool: str = "default", force_new: bool = False) -> BaseSearch:
        return cls._factory.get_service(service_name, http_tool, force_new)

# 在模块初始化时注册默认服务
DefaultSearchEngineFactory.register_default_services()

