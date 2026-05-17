"""API v1: combine search + LLM."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile

from app.core.config import settings
from app.models.schemas import (
    CombineRequest,
    CombineResponse,
    PromptCatalogResponse,
    PromptScenarioInfo,
)

ALLOWED_ENGINES = frozenset(
    {"duckduckgo", "bing", "baidu", "google", "sogou", "douban", "so"}
)

router = APIRouter(tags=["combine"])


@router.get("/health")
def health_v1():
    return {"status": "ok", "service": settings.PROJECT_NAME, "api": "v1"}


@router.get("/prompts/scenarios", response_model=PromptCatalogResponse)
def list_prompt_scenarios(
    locale: Optional[str] = Query(
        None, description="可选语言码（如 zh），参与 film.zh.yaml 解析顺序"
    ),
):
    """列出场景模板及来源（builtin / external / missing），见总体设计 §5。"""
    from app.services.prompt_loader import list_prompt_catalog

    data = list_prompt_catalog(locale=locale)
    return PromptCatalogResponse(
        prompts_dir=data["prompts_dir"],
        locale=data.get("locale"),
        scenarios=[PromptScenarioInfo(**row) for row in data["scenarios"]],
    )


@router.post("/prompts/upload")
async def upload_prompt_template(
    request: Request,
    scenario: str = Form(..., description="场景标识，如 film"),
    locale: Optional[str] = Form(None, description="可选，如 zh → 写入 film.zh.yaml"),
    file: UploadFile = File(..., description="YAML，需含 system 与 user"),
) -> Dict[str, Any]:
    """上传或覆盖 PROMPTS_DIR 下模板（需配置 PROMPTS_ADMIN_KEY 与 PROMPTS_DIR）。"""
    from app.services.prompt_loader import invalidate_prompt_cache, validate_prompt_yaml_bytes

    got = (request.headers.get("X-Prompts-Admin-Key") or "").strip()
    if not settings.PROMPTS_ADMIN_KEY or got != settings.PROMPTS_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="missing or invalid X-Prompts-Admin-Key")
    base = (settings.PROMPTS_DIR or "").strip()
    if not base:
        raise HTTPException(status_code=400, detail="PROMPTS_DIR is not set")

    scen = scenario.lower().strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", scen):
        raise HTTPException(status_code=400, detail="invalid scenario slug")
    loc = (locale or "").strip().lower()
    if loc and not re.fullmatch(r"[a-z]{2,12}", loc):
        raise HTTPException(status_code=400, detail="invalid locale")

    raw = await file.read()
    if len(raw) > 256_000:
        raise HTTPException(status_code=400, detail="file too large")
    try:
        validate_prompt_yaml_bytes(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    name = f"{scen}.{loc}.yaml" if loc else f"{scen}.yaml"
    dest = Path(base) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    invalidate_prompt_cache()
    return {
        "code": 200,
        "path": str(dest.resolve()),
        "scenario": scen,
        "locale": loc or None,
    }


@router.post("/combine", response_model=CombineResponse)
async def combine_post(body: CombineRequest, request: Request):
    eng = body.search_engine.lower().strip()
    if eng not in ALLOWED_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"search_engine must be one of: {sorted(ALLOWED_ENGINES)}",
        )
    from app.services.combine_pipeline import run_combine

    headers = {k: v for k, v in request.headers.items() if isinstance(v, str)}
    data = await run_combine(
        query=body.query,
        scenario=body.scenario,
        search_engine=eng,
        links_num=body.links_num,
        http_tool=body.http_tool,
        fetch_fallback_chain=body.fetch_fallback_chain,
        llm_provider=body.llm_provider,
        model=body.model,
        temperature=body.temperature,
        system_prompt_override=body.system_prompt_override,
        include_raw_excerpts=body.include_raw_excerpts,
        max_context_chars=body.max_context_chars,
        request_headers=headers,
        locale=body.locale,
    )
    return CombineResponse(**data)
