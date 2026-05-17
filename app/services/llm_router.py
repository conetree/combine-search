"""
OpenAI Chat Completions-compatible HTTP client for multiple providers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.core.logging import logger


def resolve_provider_endpoint(
    provider: str,
) -> Tuple[str, str, str]:
    """Return (api_base_without_trailing_slash, api_key, default_model)."""
    p = (provider or "openai").lower().strip()
    if p in ("openai", "chatgpt"):
        return (
            settings.OPENAI_API_BASE.rstrip("/"),
            settings.OPENAI_API_KEY,
            settings.OPENAI_DEFAULT_MODEL,
        )
    if p in ("deepseek",):
        return (
            settings.DEEPSEEK_API_BASE.rstrip("/"),
            settings.DEEPSEEK_API_KEY,
            settings.DEEPSEEK_DEFAULT_MODEL,
        )
    if p in ("zhipu", "glm", "chatglm"):
        return (
            settings.ZHIPU_API_BASE.rstrip("/"),
            settings.ZHIPU_API_KEY,
            settings.ZHIPU_DEFAULT_MODEL,
        )
    if p in ("dashscope", "qwen", "tongyi"):
        return (
            settings.DASHSCOPE_API_BASE.rstrip("/"),
            settings.DASHSCOPE_API_KEY,
            settings.DASHSCOPE_DEFAULT_MODEL,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


def chat_complete(
    *,
    provider: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    timeout: float = 120.0,
) -> str:
    base, api_key, default_model = resolve_provider_endpoint(provider)
    if not api_key:
        raise ValueError(
            f"No API key configured for provider '{provider}'. "
            "Set the matching env var in .env (see .env.example)."
        )
    mdl = model or default_model
    url = f"{base}/chat/completions"
    payload: Dict[str, Any] = {
        "model": mdl,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    logger.info("LLM request provider=%s model=%s", provider, mdl)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM response missing choices: {data}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if content is None:
        raise RuntimeError(f"LLM response missing content: {data}")
    return str(content).strip()
