# Combine-Search Agent Skills（给其他大模型）

本目录存放**与实现同步**的开发指引，供 Cursor、Claude、GPT、Gemini 等任意助手继续维护本仓库时使用。

## 推荐阅读顺序

1. [../SPEC.md](../SPEC.md) — 功能规格（事实来源）
2. [../总体设计.md](../总体设计.md) — 架构与边界
3. 按任务选下方 Skill 全文阅读

## Skill 索引

| Skill | 文件 | 适用任务 |
|-------|------|----------|
| **combine-search-dev** | [combine-search-dev/SKILL.md](combine-search-dev/SKILL.md) | combine 流水线、搜索引擎、LLM、路由、配置 |
| | [combine-search-dev/reference.md](combine-search-dev/reference.md) | 环境变量、API、引擎速查 |
| **combine-search-prompts** | [combine-search-prompts/SKILL.md](combine-search-prompts/SKILL.md) | 场景 YAML、locale、上传、占位符 |
| **combine-search-testing** | [combine-search-testing/SKILL.md](combine-search-testing/SKILL.md) | pytest、mock、勿打真实外网 |

## 给其他模型的用法

**方式 A（推荐）**：在对话开头说明：

> 你正在开发 combine-search 仓库。请先阅读仓库内 `docs/SPEC.md`，再阅读 `docs/skills/combine-search-dev/SKILL.md`，并遵守其中约定。

**方式 B**：将对应 `SKILL.md` 全文复制到系统提示 / Project Instructions。

**方式 C（Cursor）**：仓库根目录 [AGENTS.md](../../AGENTS.md) 指向本目录；也可在 `.cursor/rules` 中引用 `docs/skills/` 路径。

## 维护约定

- 改 API、流水线、提示词行为时，**同步更新** `docs/SPEC.md` 与相关 Skill。
- Skill 内链接均相对于 `docs/skills/` 或仓库根，避免写绝对路径。
