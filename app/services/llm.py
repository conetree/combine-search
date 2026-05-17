from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from pydantic import PrivateAttr

from app.core.config import settings

class InternalLLM(LLM):
    """封装内部网关大模型 API（可选）。"""

    _session_id: str = PrivateAttr()

    def __init__(self, session_id: str | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._session_id = session_id or "default_session"

    @property
    def _llm_type(self) -> str:
        return "internal_llm"

    def _call(
        self,
        prompt: str,
        stop: List[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        if not settings.INTERNAL_AI_API_URL or not settings.INTERNAL_AI_API_URL.strip():
            raise RuntimeError(
                "INTERNAL_AI_API_URL 未配置。请在 .env 中设置，或留空以使用 OpenAI 兼容路由。"
            )

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if settings.INTERNAL_AI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_AI_API_KEY}"

        try:
            prompt_obj = json.loads(prompt)
            inner_raw = prompt_obj.get("input")
            if isinstance(inner_raw, str):
                inner = json.loads(inner_raw)
            else:
                inner = inner_raw or {}
        except (json.JSONDecodeError, TypeError, AttributeError):
            inner = {"input": prompt, "promptList": []}

        data = {
            "service_name": "text-copilot-generate",
            "prompt_id": "123",
            "prompt_version": "latest",
            "prompt_token": settings.INTERNAL_AI_API_KEY or "unset",
            "prompt_list": inner.get("promptList", []),
            "job_id": self._session_id,
            "response_mode": 1,
            "prompt_variable": json.dumps({"input": inner.get("input", prompt)}),
        }

        base = settings.INTERNAL_AI_API_URL.rstrip("/")
        url = f"{base}/prompt/api/completions?job_id={self._session_id}"

        response = requests.post(url, headers=headers, json=data, timeout=120)

        if response.status_code != 200:
            raise RuntimeError(f"AI API调用失败: {response.text}")

        return response.json().get("data", [""])[0]

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": "internal_llm",
            "api_url": settings.INTERNAL_AI_API_URL,
        }


class OpenAICompatibleLLM(LLM):
    """使用 OpenAI Chat Completions 兼容 HTTP 接口（DeepSeek / GLM / 千问 / OpenAI 等）。"""

    _provider: str = PrivateAttr()

    def __init__(self, provider: str | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._provider = provider or settings.LLM_DEFAULT_PROVIDER

    @property
    def _llm_type(self) -> str:
        return "openai_compatible"

    def _call(
        self,
        prompt: str,
        stop: List[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        from app.services.llm_router import chat_complete

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer in the same language as the user when possible.",
            },
            {"role": "user", "content": prompt},
        ]
        return chat_complete(
            provider=self._provider,
            messages=messages,
            temperature=0.3,
        )

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"model_name": self._provider}
