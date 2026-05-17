"""Smoke tests: full FastAPI app imports and core routes respond."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_homepage():
    r = client.get("/")
    assert r.status_code == 200
    assert "combine" in r.json()


def test_v1_health_on_full_app():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_prompts_catalog_on_full_app():
    r = client.get("/api/v1/prompts/scenarios")
    assert r.status_code == 200
    assert "film" in {s["scenario"] for s in r.json()["scenarios"]}
