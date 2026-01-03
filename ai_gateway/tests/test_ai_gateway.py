import os
import json
import shutil
from fastapi.testclient import TestClient
import pytest
import importlib

from ai_gateway.main import app
from ai_gateway.clients import EmbeddingClient, OpenRouterClient
import ai_gateway.db as agdb


@pytest.fixture(autouse=True)
def ensure_db_tmp(tmp_path, monkeypatch):
    # Use a temporary sqlite file for tests
    db_file = tmp_path / "test_ai_gateway.db"
    monkeypatch.setenv("AI_GATEWAY_DB", f"sqlite:///{db_file}")
    # Ensure stale files are removed so schema reflects current models
    try:
        if db_file.exists():
            db_file.unlink()
    except Exception:
        pass
    # set internal token for auth guard
    monkeypatch.setenv("AI_GATEWAY_INTERNAL_TOKEN", "test-token")
    # Re-import/init DB: reload module so ENGINE picks up the new env
    importlib.reload(agdb)
    try:
        agdb.Base.metadata.drop_all(bind=agdb.ENGINE)
    except Exception:
        pass
    agdb.init_db()
    yield


def test_embedding_deterministic():
    c = EmbeddingClient(dim=64)
    v1 = c.embed("hello world")
    v2 = c.embed("hello world")
    assert len(v1) == 64
    # deterministic equality
    assert v1 == v2


def test_summarize_flow(monkeypatch):
    # monkeypatch OpenRouterClient.summarize to avoid network
    def fake_summarize(self, text):
        return {
            "summary": "This is a summary.",
            "action_items": ["action 1"],
            "timeline": ["step1"],
            "confidence": 0.9,
            "warnings": []
        }

    monkeypatch.setattr(OpenRouterClient, "summarize", fake_summarize)

    client = TestClient(app)

    payload = {
        "ticket_id": "TKT-1",
        "title": "Test",
        "description": "Contains email me@test.com and phone +123456789",
        "messages": [{"type": "note", "body": "Hello me@test.com"}, {"type": "attachment", "body": "should not be sent"}],
        "metadata": {"org_unit_id": "42", "sensitivity_level": "low"}
    }

    headers = {"x-org-unit": "42", "x-ai-gateway-token": "test-token"}
    r = client.post("/ai/summarize", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"] == "This is a summary."

    # check persistence
    db = agdb.SessionLocal()
    sug = db.query(agdb.AISuggestion).filter(agdb.AISuggestion.ticket_id == "TKT-1").first()
    assert sug is not None
    audit = db.query(agdb.AuditEvent).filter(agdb.AuditEvent.ticket_id == "TKT-1").order_by(agdb.AuditEvent.id).all()
    assert any(a.event_type == "AI_REQUESTED" for a in audit)
    assert any(a.event_type == "AI_SUGGESTION_CREATED" for a in audit)


def test_summarize_invalid_model_output(monkeypatch):
    # model returns non-json content -> should be 502 and audit AI_OUTPUT_INVALID
    def fake_bad(self, text):
        return {"__raw": "I refuse to output JSON"}

    monkeypatch.setattr(OpenRouterClient, "summarize", fake_bad)
    client = TestClient(app)
    payload = {
        "ticket_id": "TKT-2",
        "title": "Bad",
        "description": "desc",
        "messages": [{"type": "note", "body": "hello"}],
        "metadata": {"org_unit_id": "42", "sensitivity_level": "low"}
    }
    headers = {"x-org-unit": "42", "x-ai-gateway-token": "test-token"}
    r = client.post("/ai/summarize", json=payload, headers=headers)
    assert r.status_code == 502
    db = agdb.SessionLocal()
    audit = db.query(agdb.AuditEvent).filter(agdb.AuditEvent.ticket_id == "TKT-2").all()
    assert any(a.event_type == "AI_OUTPUT_INVALID" for a in audit)


def test_summarize_unauthorized(monkeypatch):
    # without correct token results in 401 and no writes
    def fake_ok(self, text):
        return {
            "summary": "ok",
            "action_items": [],
            "timeline": [],
            "confidence": 0.5,
            "warnings": []
        }

    monkeypatch.setattr(OpenRouterClient, "summarize", fake_ok)
    client = TestClient(app)
    payload = {
        "ticket_id": "TKT-3",
        "title": "Auth",
        "description": "desc",
        "messages": [{"type": "note", "body": "hello"}],
        "metadata": {"org_unit_id": "42", "sensitivity_level": "low"}
    }
    headers = {"x-org-unit": "42", "x-ai-gateway-token": "wrong"}
    r = client.post("/ai/summarize", json=payload, headers=headers)
    assert r.status_code == 401
    db = agdb.SessionLocal()
    assert db.query(agdb.AISuggestion).filter(agdb.AISuggestion.ticket_id == "TKT-3").first() is None

