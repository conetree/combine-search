# Combine Search Agent

基于 **Python / FastAPI** 的组合搜索 Agent：用关键词在多搜索引擎上取结果 → 抓取网页正文 → 按 **场景化提示词** 调用 **OpenAI 兼容接口** 的大模型（OpenAI / DeepSeek / 智谱 GLM / 通义千问等）生成推荐语、精炼总结与结构化分析。

```mermaid
flowchart LR
  Q[Query] --> S[SearchEngine]
  S --> F[FetchClients]
  F --> P[ScenarioPrompts]
  P --> L[LLM_ChatCompletions]
  L --> O[Markdown_or_JSON]
```

更完整的架构、需求边界与约束说明见 **[docs/总体设计.md](docs/总体设计.md)**；功能规格见 **[docs/SPEC.md](docs/SPEC.md)**。  
给其他大模型 / AI 助手继续开发：**[AGENTS.md](AGENTS.md)** → **[docs/skills/](docs/skills/)**。

## 能力概览

| 能力 | 说明 |
|------|------|
| 依赖安装 | **全量**：`pip install -r requirements.txt`（core + torch/gradio/streamlit 等）。**仅 API/搜索/combine**：`pip install -r requirements-core.txt` |
| 搜索引擎 | Bing、Baidu、DuckDuckGo、Google、搜狗、360、豆瓣（见工厂注册） |
| 抓取客户端 | `request` / `curl` / `cloudscraper` / `playwright` / `selenium` / `firecrawl` / `agent` 等 |
| 组合接口 | `POST /api/v1/combine`：一次请求完成搜索 + 提炼 |
| 提示词管理 | `GET /api/v1/prompts/scenarios`（可选 `?locale=`）；`POST /api/v1/prompts/upload`（需 `PROMPTS_DIR` + `X-Prompts-Admin-Key`）；`PROMPTS_DIR` 外部覆盖（见 [docs/总体设计.md](docs/总体设计.md) §5） |
| 场景模板 | `film` / `stock` / `news` / `product`，内置 YAML，可用 `PROMPTS_DIR` 覆盖 |
| 大模型 | 统一 **Chat Completions** HTTP，切换 `llm_provider` 与可选 `model` |

## 合规与边界

- 无法保证绕过所有反爬（验证码、登录墙、强 WAF）。生产环境请优先 **官方 API**、**授权数据**、**Firecrawl** 或合规代理。
- 请遵守目标站 **robots.txt** 与服务条款；控制频率；密钥与抓取责任由部署方承担。
- **股票等金融场景**：本仓库输出仅供信息整理，**非投资建议**；权威行情请使用持牌数据接口。

## 快速开始

推荐使用 **Python 3.11+** 的虚拟环境；全量依赖里含 pandas / 可选爬虫栈，在部分系统上直接 `import app.main` 可能较慢或触发与本机二进制包不兼容的问题，组合接口单测使用轻量 FastAPI 子应用规避重依赖。

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# 至少配置一个 LLM 的 API Key（如 OPENAI_API_KEY），以及可选 FIRECRAWL_API_KEY、AGENT_PROXY_BASE

uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

- Swagger：`http://localhost:8002/docs`
- 健康检查：`GET http://localhost:8002/api/v1/health`

### 一键组合示例

```bash
curl -s -X POST "http://localhost:8002/api/v1/combine" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "某电影 豆瓣 票房",
    "scenario": "film",
    "search_engine": "bing",
    "links_num": 2,
    "http_tool": "cloudscraper",
    "llm_provider": "openai",
    "temperature": 0.3
  }'
```

或使用脚本：`python examples/demo_combine.py`（需先启动服务）。可选 Gradio：`pip install -r requirements-extra.txt` 后 `python examples/gradio_combine_demo.py`。

## 主要环境变量

| 变量 | 含义 |
|------|------|
| `OPENAI_API_KEY` / `OPENAI_API_BASE` | OpenAI 兼容密钥与 Base URL |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `ZHIPU_API_KEY` | 智谱 GLM |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope（千问兼容模式） |
| `LLM_DEFAULT_PROVIDER` | 旧版 `/catalog-agent/chat` 无内部网关时默认厂商，默认 `openai` |
| `INTERNAL_AI_API_URL` | 可选：内部旧网关；留空则走 OpenAI 兼容客户端 |
| `FIRECRAWL_API_KEY` | Firecrawl 抓取（可选） |
| `AGENT_PROXY_BASE` | 可选：`?url=` 转发抓取代理根地址 |
| `ALLOWED_DOMAIN` | 逗号分隔，搜索结果域名过滤 |
| `DEFAULT_FETCH_CHAIN` | 组合检索正文过短时，`link` 模式后的抓取降级链，如 `cloudscraper,request,curl` |
| `PROMPTS_DIR` | 覆盖内置提示词目录（同名 `film.yaml` 等） |
| `PROMPTS_CACHE_ENABLED` | `true` 时按文件 mtime 缓存模板加载结果 |
| `PROMPTS_ADMIN_KEY` | 与请求头 `X-Prompts-Admin-Key` 一致时允许 `POST /api/v1/prompts/upload` |
| `CLOUDSCRAPER_INTERPRETER` | 若需 Node 解 JS 挑战可设为 `nodejs`（需本机安装 Node） |

完整占位见 [.env.example](.env.example)。

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/combine` | 组合搜索 + LLM（推荐主入口） |
| GET | `/api/v1/prompts/scenarios` | 列出场景模板及来源；可选查询参数 `locale` |
| POST | `/api/v1/prompts/upload` | 上传场景 YAML（需 `PROMPTS_ADMIN_KEY` 与 `PROMPTS_DIR`） |
| GET | `/api/v1/health` | 服务健康 |
| GET | `/api/search/...` | 各搜索引擎与 `fetch-*` 抓取端点（遗留/调试） |
| POST | `/api/catalog-agent/chat` | 表单多模对话；若 params 含 **`scenario`**（及可选 `locale`），则与 combine 共用 YAML 模板 + 默认 LLM（无 LangChain 多轮） |

## 项目结构（核心）

```
app/
├── main.py                 # FastAPI 入口
├── routes/
│   ├── combine_routes.py   # /api/v1/*
│   └── search_routes.py
├── services/
│   ├── combine_pipeline.py # 编排
│   ├── fetch_orchestrator.py
│   ├── llm_router.py       # OpenAI 兼容 chat.completions
│   ├── prompt_loader.py
│   └── ...
├── prompts/                # film / stock / news / product YAML
├── tools/http_clients.py   # 多抓取实现
└── core/config.py          # pydantic-settings
```

## Playwright（可选）

若使用 `http_tool=playwright`，需安装浏览器内核：

```bash
playwright install chromium
```

## 开发说明

- 业务配置：`app/core/search_config.py`（多数项可由环境变量覆盖）。
- 单测：`pytest tests/ -q`（`tests/test_combine_pipeline.py` 对 `/api/v1/combine` 与 `run_combine` 使用 mock，无需外网与 API Key）。
- 遗留 `POST /chat` 的浏览器调试片段见 [examples/chat_fetch_browser_example.js](examples/chat_fetch_browser_example.js)。

## License

以仓库原有许可证为准。
