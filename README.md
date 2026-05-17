# Combine Search

🚀本项目是基于搜索引擎（抓取内容）+大模型（生成内容）的实际应用，主打一个简单好用。可广泛应用于各种Agent、RAG、Agentic构建。

核心思路是用一条 API 把「搜网页 → 读正文 → 按场景写总结」串起来：多搜索引擎、多种抓取方式、四套业务提示词模板，再接各家 OpenAI 兼容大模型（OpenAI、DeepSeek、智谱、通义等）。

```mermaid
flowchart LR
  classDef stepQuery fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a
  classDef stepSearch fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#9a3412
  classDef stepFetch fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534
  classDef stepPrompt fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8
  classDef stepLlm fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#9d174d
  classDef stepOut fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#854d0e

  Q([检索词]):::stepQuery
  S[搜索引擎]:::stepSearch
  F[网页抓取]:::stepFetch
  P[场景提示词]:::stepPrompt
  L[大模型]:::stepLlm
  O([结构化输出]):::stepOut

  Q --> S --> F --> P --> L --> O
```

## 这个仓库解决什么问题

运营、编辑、内容类产品里常见一类需求：先根据剧名/商品/新闻主题去网上找材料，再按固定格式写出推荐语、摘要或简报。手工做要反复打开搜索、复制链接、粘贴进对话，格式也不统一。

本仓库把这条链路做成可部署的服务：

- **搜索与抓取可换**：Bing、百度、DuckDuckGo 等引擎，配合 request、cloudscraper、Playwright 等客户端，按站点情况降级重试。
- **输出按场景约束**：影视、资讯、股票、商品四套 YAML 模板，占位符注入检索正文；也可用 `PROMPTS_DIR` 在部署侧覆盖，不必改代码。
- **模型可切换**：同一套 Chat Completions 协议，换环境变量即可换厂商。

适合当作内部「检索 + 提炼」微服务，或在此基础上接自己的前端与权限体系。更细的边界与合规说明见下文「合规与边界」。

## 延伸阅读：AI 编程知识库

若你在用 AI 辅助写代码、维护提示词或扩展本仓库，可参考 [MicroWind | AI 编程核心知识库](https://microwind.github.io/)：算法与设计模式、Prompt Engineering、Skills 体系等，和「怎么指挥 AI 改工程」相关，与本项目的 `docs/skills/` 文档可以对照着看。

## 文档与协作开发

| 文档 | 内容 |
|------|------|
| [docs/SPEC.md](docs/SPEC.md) | 功能规格、API 字段、验收方式 |
| [docs/总体设计.md](docs/总体设计.md) | 架构、模块划分、设计取舍 |
| [AGENTS.md](AGENTS.md) → [docs/skills/](docs/skills/) | 给其他模型/协作者看的开发约定 |

## 能力一览

| 能力 | 说明 |
|------|------|
| 依赖 | 只要 API：`pip install -r requirements-core.txt`；含 Gradio/torch 等：`pip install -r requirements.txt` |
| 搜索 | Bing、Baidu、DuckDuckGo、Google、搜狗、360、豆瓣 |
| 抓取 | request、curl、cloudscraper、playwright、selenium、firecrawl、agent 等 |
| 主接口 | `POST /api/v1/combine`：一次请求完成搜索 + 提炼 |
| 提示词 | 内置四场景；`GET /api/v1/prompts/scenarios`；外置目录 `PROMPTS_DIR`；可选上传接口 |
| 大模型 | `llm_provider` 指定厂商，可选 `model` 覆盖默认模型名 |

## 合规与边界

- 不保证能过所有验证码、登录墙或强 WAF；线上建议优先用官方 API、授权数据源，或 Firecrawl 等合规通道。
- 请遵守目标站的 robots.txt 与服务条款，控制访问频率；密钥与抓取后果由部署方负责。
- **股票场景**：输出仅供信息整理，不构成投资建议；行情请以持牌数据源为准。

## 快速开始

建议 Python 3.11+ 虚拟环境。若本机 `import app.main` 较慢，多半是 pandas/爬虫栈较重；跑单测会用轻量子应用，不影响日常开发。

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-core.txt   # 或 requirements.txt 全量

cp .env.example .env
# 至少填一个 LLM Key，例如 OPENAI_API_KEY

uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

- 接口文档：`http://localhost:8002/docs`
- 健康检查：`GET http://localhost:8002/api/v1/health`

### 调用示例

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

也可运行 `python examples/demo_combine.py`（需先启动服务）。需要简单页面时：`pip install -r requirements-extra.txt` 后执行 `python examples/gradio_combine_demo.py`。

## 环境变量（常用）

| 变量 | 含义 |
|------|------|
| `OPENAI_API_KEY` / `OPENAI_API_BASE` | OpenAI 及兼容端点 |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `ZHIPU_API_KEY` | 智谱 GLM |
| `DASHSCOPE_API_KEY` | 通义（DashScope 兼容模式） |
| `LLM_DEFAULT_PROVIDER` | 遗留 `/catalog-agent/chat` 默认厂商 |
| `INTERNAL_AI_API_URL` | 可选内部旧网关 |
| `FIRECRAWL_API_KEY` | Firecrawl |
| `AGENT_PROXY_BASE` | `?url=` 代理抓取根地址 |
| `ALLOWED_DOMAIN` | 搜索结果域名白名单 |
| `DEFAULT_FETCH_CHAIN` | 正文过短时的抓取降级链，如 `cloudscraper,request,curl` |
| `PROMPTS_DIR` | 外置提示词目录 |
| `PROMPTS_CACHE_ENABLED` | 是否按文件修改时间缓存模板 |
| `PROMPTS_ADMIN_KEY` | 与 `X-Prompts-Admin-Key` 配合，允许上传模板 |

完整列表见 [.env.example](.env.example)。

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/combine` | 组合搜索 + 大模型（主入口） |
| GET | `/api/v1/prompts/scenarios` | 场景模板列表，可选 `?locale=` |
| POST | `/api/v1/prompts/upload` | 上传 YAML（需 `PROMPTS_ADMIN_KEY` 与 `PROMPTS_DIR`） |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/search/...` | 单引擎搜索与抓取（调试、遗留） |
| POST | `/api/catalog-agent/chat` | 表单对话；`params` 里带 `scenario` 时与 combine 共用模板 |

## 目录结构（核心）

```
app/
├── main.py
├── routes/combine_routes.py    # /api/v1/*
├── services/combine_pipeline.py
├── services/llm_router.py
├── services/prompt_loader.py
├── prompts/                    # film / stock / news / product
└── tools/http_clients.py
```

## Playwright（可选）

使用 `http_tool=playwright` 时需安装浏览器：

```bash
playwright install chromium
```

## 开发

- 配置：`app/core/search_config.py`（多数项可用环境变量覆盖）
- 测试：`pytest tests/ -q`
- 遗留 `POST /chat` 浏览器示例：[examples/chat_fetch_browser_example.js](examples/chat_fetch_browser_example.js)

## License

以仓库原有许可证为准。
