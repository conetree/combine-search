# Combine Search简介

基于多种搜索引擎和爬虫工具，抓取搜索结果相关网页，再组装提示词，最后调用大型模型进行分析，返回生成结果。适用于各种想抓取网页再用大模型分析的情形。
<img width="1499" alt="image" src="https://github.com/user-attachments/assets/5648d0e4-addb-46e6-ad3e-e321d3975637" />


## 功能

- 搜索流行的搜索引擎
- 多种HTTP抓取工具，绕过反爬
- 支持提示词修改和上下文记忆
- 调用大模型进行内容分析和内容生成

## 应用场景
- 股票分析：搜索词（股票号码 东方财富 同花顺 新浪财经 搜狐财经) -> 搜索bing -> 根据搜索结果获取抓取链接 -> 抓取内容提取文本   ->  组装提示词(请给我分析${股票名}，参考内容如下：${抓取的内容}$ ，返回今天走势、明天估计、未来走势三种情况) -> 大模型API -> 返回结果。

- 电影推荐语：搜索词（电影名称 豆瓣电影 百科  IMDB 猫眼) -> 搜索bing -> 根据搜索结果获取抓取链接 -> 抓取内容提取文本   ->  组装提示词(请给分析${电影名}，参考内容如下：${抓取的内容} ，返回电影票房 出品方 主演 故事梗概 20-30字的推荐语) -> 大模型API -> 返回结果。

- 热点事件分析：搜索词（热点事件 百度新闻 微博 知乎 抖音) -> 搜索bing -> 根据搜索结果获取抓取链接 -> 抓取内容提取文本   ->  组装提示词(请给分析${热点事件}，参考内容如下：${抓取的内容} ，返回事件的起因、基本经过、造成影响等) -> 大模型API -> 返回结果。

- 商品分析：搜索词（产品名称 亚马逊 淘宝 京东 拼多多) -> 搜索bing -> 根据搜索结果获取抓取链接 -> 抓取内容提取文本   ->  组装提示词(请给分析${产品名}，参考内容如下：${抓取的内容} ，返回产品的价格、评价、优势等) -> 大模型API -> 返回结果。

## 项目结构

```c
combine-search/
├── README.md
├── requirements.txt
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logging.py
│   ├── routes
│   │   ├── search_routes.py
│   ├── controllers
│   │   ├── search_controller.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── search_service.py
│   │   ├── google_service.py
│   │   └── llm.py
│   ├── models
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── utils
│       ├── __init__.py
│       └── helpers.py
└── tests
    └── __init__.py
```

## 安装指南

```bash
# 创建虚拟环境，依赖python3
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# Python 3.11虚拟环境
# python3.11 -m venv venv-3.11
# source venv-3.11/bin/activate  # Linux/Mac

# 或
.\venv-3.11\Scripts\activate  # Windows

# 安装依赖
# pip install -r requirements.txt
# 使用pip3
pip3 install -r requirements.txt

# 基于虚拟环境安装依赖
# venv/bin/pip install -r requirements.txt
# venv-3.11/bin/pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置必要的环境变量
```

## 启动服务

```bash
# 开发环境启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# 或启动脚本
sh startup.sh

# 关闭脚本
sh shutdown.sh

# 基于3.11启动命令
# nohup venv-3.11/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 生产环境启动
uvicorn app.main:app --host 0.0.0.0 --port 8088
```

## API 文档

启动服务后访问:
- Swagger UI: http://localhost:8088/docs
- ReDoc: http://localhost:8088/redoc

## 开发指南

1. API定义在 `app/routes` 目录下
2. 业务逻辑在 `app/services` 目录下
3. 数据模型和验证在 `app/models` 目录下
4. 配置管理在 `app/core/config.py` 中集中管理
5. 日志配置在 `app/core/logging.py` 中
6. 抓取工具类在 `app/tools` 目录下
7. 常用工具类在 `app/utils` 目录下
8. 单元测试在 `tests` 目录下
