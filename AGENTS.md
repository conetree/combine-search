# Agent 开发指引（Combine-Search）

本仓库为 **组合搜索 + 场景提示词 + 多厂商 LLM** 的 FastAPI 服务。

## 给其他大模型：请先读这些

| 顺序 | 文档 |
|------|------|
| 1 | [docs/SPEC.md](docs/SPEC.md) — 功能规格（事实来源） |
| 2 | [docs/skills/README.md](docs/skills/README.md) — Skill 索引与用法 |
| 3 | 按任务阅读 `docs/skills/*/SKILL.md`（见下表） |

## Skill 目录（`docs/skills/`）

| Skill | 路径 | 何时用 |
|-------|------|--------|
| **combine-search-dev** | [docs/skills/combine-search-dev/SKILL.md](docs/skills/combine-search-dev/SKILL.md) | combine 流水线、搜索引擎、LLM、路由、配置 |
| | [reference.md](docs/skills/combine-search-dev/reference.md) | 环境变量与 API 速查 |
| **combine-search-prompts** | [docs/skills/combine-search-prompts/SKILL.md](docs/skills/combine-search-prompts/SKILL.md) | 场景 YAML、PROMPTS_DIR、locale、上传 |
| **combine-search-testing** | [docs/skills/combine-search-testing/SKILL.md](docs/skills/combine-search-testing/SKILL.md) | pytest、mock 策略 |

## 其它文档

- [docs/总体设计.md](docs/总体设计.md) — 架构与边界
- [README.md](README.md) — 安装与运行

## 快速验证

```bash
pytest tests/ -q
uvicorn app.main:app --port 8002
curl http://127.0.0.1:8002/api/v1/health
```

## 主入口

`POST /api/v1/combine` → `app/services/combine_pipeline.py`
