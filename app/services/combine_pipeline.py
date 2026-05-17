"""End-to-end: search -> (optional refetch) -> prompt -> LLM."""
from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.services.fetch_orchestrator import FetchOrchestrator
from app.services.llm_router import chat_complete
from app.services.prompt_loader import load_scenario_prompt, render_prompt
from app.services.search_engine_factory import DefaultSearchEngineFactory


def _parse_fetch_chain(chain: Optional[List[str]]) -> List[str]:
    if chain:
        return chain
    return [
        t.strip()
        for t in settings.DEFAULT_FETCH_CHAIN.split(",")
        if t.strip()
    ]


def _extract_from_search_payload(
    payload: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], str, List[str]]:
    """Return (sources, combined_context, errors)."""
    errors: List[str] = []
    if not payload or payload.get("code") not in (200,):
        msg = (payload or {}).get("message") or "search failed"
        errors.append(str(msg))
        return [], "", errors

    data = payload.get("data")
    if data is None:
        errors.append("empty search data")
        return [], "", errors
    if isinstance(data, str):
        return [], data, errors

    sources: List[Dict[str, Any]] = []
    parts: List[str] = []
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            u = row.get("url") or row.get("href") or ""
            title = row.get("title", "")
            c = (row.get("content") or "").strip()
            if u:
                sources.append({"url": u, "title": title})
            if c:
                parts.append(f"### {u or title}\n{c}")
    ctx = "\n\n".join(parts).strip()
    return sources, ctx, errors


def _urls_from_link_payload(payload: Dict[str, Any], limit: int) -> List[str]:
    if payload.get("code") != 200:
        return []
    data = payload.get("data") or []
    if not isinstance(data, list):
        return []
    out: List[str] = []
    for row in data:
        if isinstance(row, dict):
            href = row.get("href") or row.get("url")
            if href:
                out.append(href)
        if len(out) >= limit:
            break
    return out


async def run_combine(
    *,
    query: str,
    scenario: str,
    search_engine: str,
    links_num: int,
    http_tool: str,
    fetch_fallback_chain: Optional[List[str]],
    llm_provider: str,
    model: Optional[str],
    temperature: float,
    system_prompt_override: Optional[str],
    include_raw_excerpts: bool,
    max_context_chars: int,
    request_headers: Dict[str, Any],
    locale: Optional[str] = None,
    min_chars_refetch: int = 400,
) -> Dict[str, Any]:
    timings: Dict[str, int] = {}
    errors: List[str] = []
    t_all = time.perf_counter()

    engine = (search_engine or settings.DEFAULT_SEARCH_ENGINE).lower().strip()
    tool = http_tool or "cloudscraper"
    chain = _parse_fetch_chain(fetch_fallback_chain)

    service = DefaultSearchEngineFactory.get_service(engine, tool)

    t0 = time.perf_counter()
    search_payload = await asyncio.to_thread(
        service.search_web, query, "text", links_num, request_headers
    )
    timings["search_ms"] = int((time.perf_counter() - t0) * 1000)

    sources, context, err_list = _extract_from_search_payload(search_payload)
    errors.extend(err_list)

    if len(context) < min_chars_refetch and chain:
        t1 = time.perf_counter()
        link_payload = await asyncio.to_thread(
            service.search_web, query, "link", links_num, request_headers
        )
        timings["search_link_ms"] = int((time.perf_counter() - t1) * 1000)
        urls = _urls_from_link_payload(link_payload, links_num)
        orch = FetchOrchestrator(service, chain)
        refetched: List[str] = []
        for u in urls:
            try:
                txt = await asyncio.to_thread(
                    orch.fetch_url_as_text, u, request_headers
                )
                refetched.append(f"### {u}\n{txt}")
                sources.append({"url": u, "title": "", "refetched": True})
            except Exception as e:
                errors.append(f"refetch {u}: {e}")
        if refetched:
            context = (context + "\n\n" + "\n\n".join(refetched)).strip()

    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n…(truncated)"

    today = date.today().isoformat()
    system_msg = ""
    user_msg = ""
    prompt_ok = False
    try:
        sp = load_scenario_prompt(scenario, locale=locale)
        system_msg = system_prompt_override or sp.system
        user_msg = render_prompt(
            sp.user,
            query=query,
            retrieved_context=context or "(无检索正文，请明确说明信息不足)",
            current_date=today,
        )
        prompt_ok = True
    except FileNotFoundError as e:
        errors.append(f"prompt_missing: {e}")
    except ValueError as e:
        errors.append(f"prompt_invalid: {e}")
    except Exception as e:
        logger.exception("prompt load failed")
        errors.append(f"prompt_load: {e}")

    t2 = time.perf_counter()
    llm_out = ""
    if prompt_ok:
        try:
            llm_out = await asyncio.to_thread(
                chat_complete,
                **{
                    "provider": llm_provider,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "model": model,
                    "temperature": temperature,
                },
            )
        except Exception as e:
            logger.exception("LLM failed")
            errors.append(f"llm: {e}")
            llm_out = ""
    timings["llm_ms"] = int((time.perf_counter() - t2) * 1000)
    timings["total_ms"] = int((time.perf_counter() - t_all) * 1000)

    out: Dict[str, Any] = {
        "llm_output": llm_out,
        "sources": sources,
        "errors": errors,
        "timings": timings,
        "search_engine": engine,
        "scenario": scenario.lower().strip(),
        "locale": (locale or "").strip().lower() or None,
    }
    if include_raw_excerpts:
        out["raw_excerpts"] = context
    return out
