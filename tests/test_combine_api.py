from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import config
from app.routes.combine_routes import router as combine_router

app = FastAPI()
app.include_router(combine_router, prefix="/api/v1")
client = TestClient(app)


def test_v1_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_prompts_catalog():
    r = client.get("/api/v1/prompts/scenarios")
    assert r.status_code == 200
    body = r.json()
    assert "scenarios" in body
    ids = {s["scenario"] for s in body["scenarios"]}
    assert "film" in ids and "news" in ids


def test_combine_invalid_engine():
    r = client.post(
        "/api/v1/combine",
        json={
            "query": "test",
            "scenario": "news",
            "search_engine": "not-a-real-engine",
            "links_num": 1,
            "http_tool": "request",
            "llm_provider": "openai",
        },
    )
    assert r.status_code == 400


def test_prompts_catalog_locale_query():
    r = client.get("/api/v1/prompts/scenarios", params={"locale": "zh"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("locale") == "zh"
    assert "scenarios" in body


def test_prompt_upload_unauthorized():
    r = client.post(
        "/api/v1/prompts/upload",
        data={"scenario": "news"},
        files={"file": ("n.yaml", b"system: s\nuser: u\n", "application/x-yaml")},
    )
    assert r.status_code == 401


def test_prompt_upload_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "PROMPTS_DIR", str(tmp_path))
    monkeypatch.setattr(config.settings, "PROMPTS_ADMIN_KEY", "secret-key")
    body = b'system: You are a test.\nuser: "Hello {{ query }} {{ retrieved_context }}"\n'
    r = client.post(
        "/api/v1/prompts/upload",
        headers={"X-Prompts-Admin-Key": "secret-key"},
        data={"scenario": "news", "locale": "zh"},
        files={"file": ("n.yaml", body, "application/x-yaml")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["code"] == 200
    assert data["scenario"] == "news"
    assert data["locale"] == "zh"
    uploaded = tmp_path / "news.zh.yaml"
    assert uploaded.is_file()
    assert b"You are a test" in uploaded.read_bytes()
