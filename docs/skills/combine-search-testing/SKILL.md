---
name: combine-search-testing
description: >-
  Write and run tests for Combine-Search (pytest, mock search/LLM, TestClient).
  Use when adding tests, fixing CI, test_combine_pipeline, or verifying
  combine API without real API keys or external search.
---

# Combine-Search 测试 Skill

## 默认命令

```bash
pytest tests/ -q
```

当前 14 项：应用冒烟 + v1 API + 流水线 mock + prompt_loader。

## 测试分层

| 层 | 文件 | 策略 |
|----|------|------|
| 全应用 | `test_app_smoke.py` | `from app.main import app` + `TestClient` |
| 轻量路由 | `test_combine_api.py` | 仅挂载 `combine_router`，避免拉全栈副作用 |
| 流水线 | `test_combine_pipeline.py` | `asyncio.run(run_combine(...))` + monkeypatch |
| 提示词 | `test_prompt_loader.py` | 直接调 loader，无 HTTP |

## Mock 模式（combine 流水线）

```python
def _fake_get_service(cls, service_name, http_tool="default", force_new=False):
    return _FakeSearch()  # search_web 返回固定 code=200 + data

monkeypatch.setattr(
    combine_pipeline.DefaultSearchEngineFactory,
    "get_service",
    classmethod(_fake_get_service),
)
monkeypatch.setattr(combine_pipeline, "chat_complete", lambda **kw: "SUMMARY_OK")
```

提示词失败测试 mock `load_scenario_prompt` 签名须为 `(scenario, locale=None)`。

## 上传接口测试

```python
monkeypatch.setattr(config.settings, "PROMPTS_DIR", str(tmp_path))
monkeypatch.setattr(config.settings, "PROMPTS_ADMIN_KEY", "secret-key")
# POST with header X-Prompts-Admin-Key: secret-key
```

## 不要做的

- 在默认 `tests/` 里打真实 Bing / OpenAI（不稳定、需密钥）
- 依赖 `import app.main` 时未 mock 的重网络调用

## 改代码后

1. `pytest tests/ -q`
2. 若动路由/模型：`python3 -c "from app.main import app; print(len(app.routes))"`

## 手工 E2E（可选，需 Key）

```bash
uvicorn app.main:app --port 8002
python examples/demo_combine.py
```
