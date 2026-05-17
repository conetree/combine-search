"""Integration-style tests for combine pipeline with mocks (no real search/LLM)."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.combine_routes import router as combine_router
from app.services import combine_pipeline
from app.services.combine_pipeline import run_combine


class _FakeSearch:
    def search_web(self, query, mode, n, headers):
        body = "x" * 500
        return {
            "code": 200,
            "data": [
                {"url": "https://example.com/a", "title": "A", "content": body},
            ],
        }


def _patch_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get_service(cls, service_name, http_tool="default", force_new=False):
        return _FakeSearch()

    monkeypatch.setattr(
        combine_pipeline.DefaultSearchEngineFactory,
        "get_service",
        classmethod(_fake_get_service),
    )


def test_run_combine_happy_path(monkeypatch: pytest.MonkeyPatch):
    _patch_search(monkeypatch)
    monkeypatch.setattr(combine_pipeline, "chat_complete", lambda **kw: "SUMMARY_OK")

    out = asyncio.run(
        run_combine(
            query="topic",
            scenario="news",
            search_engine="bing",
            links_num=2,
            http_tool="request",
            fetch_fallback_chain=["request"],
            llm_provider="openai",
            model=None,
            temperature=0.1,
            system_prompt_override=None,
            include_raw_excerpts=False,
            max_context_chars=10_000,
            request_headers={},
        )
    )
    assert out["llm_output"] == "SUMMARY_OK"
    assert out["scenario"] == "news"
    assert not out["errors"]
    assert out["timings"].get("llm_ms", 0) >= 0


def test_run_combine_prompt_invalid_skips_llm(monkeypatch: pytest.MonkeyPatch):
    _patch_search(monkeypatch)

    def _no_llm(**kw):
        raise AssertionError("LLM should not run when prompt is invalid")

    monkeypatch.setattr(combine_pipeline, "chat_complete", _no_llm)
    monkeypatch.setattr(
        combine_pipeline,
        "load_scenario_prompt",
        lambda s, locale=None: (_ for _ in ()).throw(ValueError("need system and user")),
    )

    out = asyncio.run(
        run_combine(
            query="q",
            scenario="news",
            search_engine="bing",
            links_num=1,
            http_tool="request",
            fetch_fallback_chain=["request"],
            llm_provider="openai",
            model=None,
            temperature=0.0,
            system_prompt_override=None,
            include_raw_excerpts=False,
            max_context_chars=10_000,
            request_headers={},
        )
    )
    assert out["llm_output"] == ""
    assert any(e.startswith("prompt_invalid:") for e in out["errors"])


def test_run_combine_prompt_missing_skips_llm(monkeypatch: pytest.MonkeyPatch):
    _patch_search(monkeypatch)
    called: list[bool] = []

    def _no_llm(**kw):
        called.append(True)
        return "should_not"

    monkeypatch.setattr(combine_pipeline, "chat_complete", _no_llm)
    monkeypatch.setattr(
        combine_pipeline,
        "load_scenario_prompt",
        lambda s, locale=None: (_ for _ in ()).throw(FileNotFoundError("no template")),
    )

    out = asyncio.run(
        run_combine(
            query="q",
            scenario="news",
            search_engine="bing",
            links_num=1,
            http_tool="request",
            fetch_fallback_chain=["request"],
            llm_provider="openai",
            model=None,
            temperature=0.0,
            system_prompt_override=None,
            include_raw_excerpts=False,
            max_context_chars=10_000,
            request_headers={},
        )
    )
    assert out["llm_output"] == ""
    assert not called
    assert any(e.startswith("prompt_missing:") for e in out["errors"])


def test_combine_post_via_api_patched(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(combine_router, prefix="/api/v1")
    _patch_search(monkeypatch)
    monkeypatch.setattr(combine_pipeline, "chat_complete", lambda **kw: "API_OK")

    client = TestClient(app)
    r = client.post(
        "/api/v1/combine",
        json={
            "query": "hello",
            "scenario": "film",
            "search_engine": "bing",
            "links_num": 2,
            "http_tool": "request",
            "fetch_fallback_chain": ["request"],
            "llm_provider": "openai",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["llm_output"] == "API_OK"
    assert body["search_engine"] == "bing"
