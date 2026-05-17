# Combine-Search 开发参考

## 环境变量（`app/core/config.py`）

| 变量 | 用途 |
|------|------|
| `OPENAI_API_KEY` / `OPENAI_API_BASE` | openai provider |
| `DEEPSEEK_*` / `ZHIPU_*` / `DASHSCOPE_*` | 其它 LLM |
| `LLM_DEFAULT_PROVIDER` | catalog chat 无内部网关时的默认厂商 |
| `INTERNAL_AI_API_URL` / `INTERNAL_AI_API_KEY` | 遗留内部网关（可选） |
| `PROMPTS_DIR` | 外置提示词根目录 |
| `PROMPTS_CACHE_ENABLED` | 按 mtime 缓存模板 |
| `PROMPTS_ADMIN_KEY` | 上传接口 `X-Prompts-Admin-Key` |
| `DEFAULT_SEARCH_ENGINE` | 默认 bing |
| `DEFAULT_FETCH_CHAIN` | 如 `cloudscraper,request,curl` |
| `MAX_CONTEXT_CHARS` | 注入 LLM 前截断 |
| `CLOUDSCRAPER_INTERPRETER` | 空或 `nodejs` |
| `FIRECRAWL_API_KEY` | firecrawl 客户端 |
| `AGENT_PROXY_BASE` | `?url=` 代理抓取 |

搜索侧见 `app/core/search_config.py`（`ALLOWED_DOMAIN` 等）。

## v1 API 速查

| 方法 | 路径 |
|------|------|
| GET | `/api/v1/health` |
| GET | `/api/v1/prompts/scenarios?locale=` |
| POST | `/api/v1/prompts/upload` |
| POST | `/api/v1/combine` |

## CombineRequest 核心字段

`query`, `scenario` (film|stock|news|product), `search_engine`, `links_num`, `http_tool`, `fetch_fallback_chain`, `llm_provider`, `model`, `temperature`, `system_prompt_override`, `include_raw_excerpts`, `max_context_chars`, `locale`

## CombineResponse 核心字段

`llm_output`, `sources`, `errors`, `timings`, `search_engine`, `scenario`, `locale`, 可选 `raw_excerpts`

## 提示词解析顺序（`locale=zh`, `scenario=film`）

1. `{PROMPTS_DIR}/film.zh.yaml`
2. `{PROMPTS_DIR}/film.yaml`
3. `app/prompts/film.zh.yaml`
4. `app/prompts/film.yaml`

占位符：`{{ query }}`, `{{ retrieved_context }}`, `{{ current_date }}`（有无空格均可）。

## 已注册搜索引擎

`duckduckgo`, `bing`, `baidu`, `google`, `sogou`, `douban`, `so`

## 常见 http_tool

`request`, `curl`, `cloudscraper`, `playwright`, `selenium`, `firecrawl`, `agent`, `scrapy`

## 示例与 Demo

- `examples/demo_combine.py` — HTTP 调 combine
- `examples/gradio_combine_demo.py` — 需 requirements-extra

## 不在范围内

- 保证绕过所有反爬 / 登录墙
- 证券实时权威行情 API
- CI 内真实 Bing+OpenAI E2E（需密钥）
