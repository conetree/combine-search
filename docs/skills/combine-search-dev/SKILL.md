---
name: combine-search-dev
description: >-
  Develop and extend the Combine-Search FastAPI agent (search → fetch → scenario
  prompts → OpenAI-compatible LLM). Use when working in combine-search repo,
  POST /api/v1/combine, combine_pipeline, llm_router, search engines, http_clients,
  fetch_orchestrator, or continuing features from docs/SPEC.md.
---

# Combine-Search 开发 Skill

## 先读文档（按顺序）

1. [SPEC.md](../../SPEC.md) — 功能规格、API、验收标准（**事实来源**）
2. [总体设计.md](../../总体设计.md) — 架构与边界
3. [README.md](../../../README.md) — 运行与环境变量

## 架构一图

```
POST /api/v1/combine
  → combine_routes.combine_post
  → combine_pipeline.run_combine
       → SearchEngineFactory.get_service → search_web(text|link)
       → [正文过短] FetchOrchestrator.fetch_url_as_text
       → prompt_loader.load_scenario_prompt + render_prompt
       → llm_router.chat_complete
```

遗留：`POST /api/catalog-agent/chat` — 带 `params.scenario` 时走同一套 prompt + `chat_complete`（见 `app/api/api.py`）。

## 改功能时去哪改

| 目标 | 文件 |
|------|------|
| 组合编排逻辑 | `app/services/combine_pipeline.py` |
| 单 URL 抓取降级链 | `app/services/fetch_orchestrator.py` |
| v1 路由 / 校验 | `app/routes/combine_routes.py` |
| 请求/响应模型 | `app/models/schemas.py` |
| 多 LLM | `app/services/llm_router.py` |
| 提示词加载 | `app/services/prompt_loader.py` |
| 内置场景 YAML | `app/prompts/{film,stock,news,product}.yaml` |
| 新搜索引擎 | `app/services/{name}_service.py` + `search_engine_factory.py` |
| HTTP/浏览器客户端 | `app/tools/http_clients.py` |
| 全局配置 | `app/core/config.py`、`app/core/search_config.py` |
| 应用入口 | `app/main.py` |

## 编码约定

- **同步 I/O 在 async 路由里**：用 `asyncio.to_thread(...)`（见 `combine_pipeline`、`api.py`）。
- **重依赖懒加载**：Scrapy 在函数内 import；`api.py` 的 pandas/docx/pdf 在 `process_file` 内 import；搜索客户端在 `base_search` / `scraper` 懒创建。
- **Python 3.9+**：模块顶使用 `from __future__ import annotations`，或 `Optional[T]`，避免 `Foo | None` 在 3.9 模块级求值报错。
- **密钥**：只走环境变量 / `Settings`，禁止硬编码进仓库。
- **combine 业务错误**：多数仍 HTTP 200，`errors[]` + 空 `llm_output`；参数错误用 HTTP 400。
- **提示词失败**：前缀 `prompt_missing:` / `prompt_invalid:` / `prompt_load:`，**不调用 LLM**。

## 测试（改完必跑）

```bash
pytest tests/ -q
```

| 测试文件 | 用途 |
|----------|------|
| `tests/test_app_smoke.py` | 完整 `app.main` 导入与健康 |
| `tests/test_combine_api.py` | v1 路由、上传鉴权 |
| `tests/test_combine_pipeline.py` | mock 搜索/LLM 的流水线 |
| `tests/test_prompt_loader.py` | 内置 YAML 加载 |

新 combine 逻辑优先 **mock** `DefaultSearchEngineFactory.get_service` 与 `chat_complete`，勿在单测里打真实外网。

## 依赖

- 仅 API：`pip install -r requirements-core.txt`
- 全量（Gradio/torch）：`pip install -r requirements.txt`

## 扩展检查清单

**新搜索引擎**

1. 实现 `BaseSearch` 子类（参考 `bing_service.py`）
2. 在 `DefaultSearchEngineFactory.register_default_services` 注册
3. 将引擎名加入 `combine_routes.ALLOWED_ENGINES`
4. 更新 `docs/SPEC.md` §5.2 与 README API 表

**新 LLM 厂商**

1. 在 `llm_router.resolve_provider_endpoint` 增加分支
2. 在 `app/core/config.py` + `.env.example` 增加 `*_API_KEY` / `*_API_BASE` / 默认模型

**新场景 scenario**

1. 新增 `app/prompts/{scenario}.yaml`（`system` + `user` + 占位符）
2. 更新 `prompt_loader.STANDARD_SCENARIOS` 与 `schemas.ScenarioLiteral`
3. 补充 `test_prompt_loader` 或 catalog 断言

## 详细参考

- 环境变量、API 字段、错误前缀表：[reference.md](reference.md)
