---
name: combine-search-prompts
description: >-
  Manage Combine-Search scenario prompt YAML templates (film/stock/news/product),
  PROMPTS_DIR overrides, locale files, render_prompt placeholders, and
  POST /api/v1/prompts/upload. Use when editing app/prompts, prompt_loader,
  system_prompt_override, or prompt catalog API.
---

# Combine-Search 提示词 Skill

## 规格来源

[SPEC.md](../../SPEC.md) §6 · [总体设计.md](../../总体设计.md) §5

## 文件与 API

| 项 | 位置 |
|----|------|
| 内置模板 | `app/prompts/{scenario}.yaml` |
| 多语言 | `app/prompts/{scenario}.{locale}.yaml` 或 `PROMPTS_DIR` 下同名 |
| 加载/渲染 | `app/services/prompt_loader.py` |
| 目录查询 | `GET /api/v1/prompts/scenarios?locale=` |
| 上传覆盖 | `POST /api/v1/prompts/upload` + `X-Prompts-Admin-Key` |

## YAML 最小结构

```yaml
system: |
  角色与输出格式约束…
user: |
  用户任务。主题：{{ query }}
  检索摘录：{{ retrieved_context }}
  日期：{{ current_date }}
```

缺少 `system` 或 `user` → `ValueError` → combine 中 `prompt_invalid:`。

## 优先级（高 → 低）

1. `PROMPTS_DIR/{scenario}.{locale}.yaml`
2. `PROMPTS_DIR/{scenario}.yaml`
3. `app/prompts/{scenario}.{locale}.yaml`
4. `app/prompts/{scenario}.yaml`

请求级 `system_prompt_override` 只替换 **system**；**user** 仍 `render_prompt`。

## 修改场景时的同步项

1. `app/prompts/*.yaml`
2. `prompt_loader.STANDARD_SCENARIOS`（若为新场景 id）
3. `app/models/schemas.py` → `ScenarioLiteral`
4. `tests/test_prompt_loader.py` 或 `test_combine_api.test_prompts_catalog`
5. `docs/SPEC.md` §6.1 表

## 上传接口

- 需配置 `PROMPTS_DIR` 与 `PROMPTS_ADMIN_KEY`
- 成功后调用 `invalidate_prompt_cache()`
- 校验：`validate_prompt_yaml_bytes(raw)`

## 测试

```bash
pytest tests/test_prompt_loader.py tests/test_combine_api.py -q
```

## 反模式

- 在 combine 里静默 fallback 到通用 prompt（应写 `errors` 并跳过 LLM）
- 在 YAML 里写未实现的 `{{ foo }}` 占位符（当前仅支持 query / retrieved_context / current_date）
