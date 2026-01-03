import os
import json
import shutil
from fastapi.testclient import TestClient
import pytest
import importlib
from datetime import datetime

from ai_gateway.main import app
import ai_gateway.db as agdb
from ai_gateway.db import AISuggestion, AuditEvent


@pytest.fixture(autouse=True)
def ensure_db_tmp(tmp_path, monkeypatch):
    db_file = tmp_path / "test_ai_gateway.db"
    monkeypatch.setenv("AI_GATEWAY_DB", f"sqlite:///{db_file}")
    try:
        if db_file.exists():
            db_file.unlink()
    except Exception:
        pass
    monkeypatch.setenv("AI_GATEWAY_INTERNAL_TOKEN", "test-token")
    importlib.reload(agdb)
    try:
        agdb.Base.metadata.drop_all(bind=agdb.ENGINE)
    except Exception:
        pass
    agdb.init_db()
    yield


def test_accept_success():
    db = agdb.SessionLocal()
    # create suggestion with metadata
    out = {"summary": "ok"}
    sug = AISuggestion(ticket_id="TKT-A", kind="summarize", payload_json={"out": out, "metadata": {"sensitivity_level": "low", "org_unit_id": "42"}}, model_version="v1")
    db.add(sug)
    db.commit()

    client = TestClient(app)
    headers = {"x-ai-gateway-token": "test-token", "x-org-unit": "42"}
    payload = {"ticket_id": "TKT-A", "comment": "Looks good", "edited_payload_json": None}
    r = client.post(f"/ai/suggestions/{sug.id}/accept", json=payload, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"status": "ACCEPTED"}

    db2 = agdb.SessionLocal()
    s2 = db2.query(AISuggestion).filter(AISuggestion.id == sug.id).first()
    assert s2.accepted is True
    assert s2.decided_at is not None
    audit = db2.query(AuditEvent).filter(AuditEvent.ticket_id == "TKT-A").all()
    assert any(a.event_type == "AI_SUGGESTION_ACCEPTED" for a in audit)


def test_reject_success():
    db = agdb.SessionLocal()
    out = {"summary": "ok"}
    sug = AISuggestion(ticket_id="TKT-R", kind="summarize", payload_json={"out": out, "metadata": {"sensitivity_level": "low"}}, model_version="v1")
    db.add(sug)
    db.commit()

    client = TestClient(app)
    headers = {"x-ai-gateway-token": "test-token"}
    payload = {"ticket_id": "TKT-R", "reason_code": "WRONG", "comment": "Incorrect"}
    r = client.post(f"/ai/suggestions/{sug.id}/reject", json=payload, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"status": "REJECTED"}

    db2 = agdb.SessionLocal()
    s2 = db2.query(AISuggestion).filter(AISuggestion.id == sug.id).first()
    assert s2.rejected is True
    assert s2.decided_at is not None
    audit = db2.query(AuditEvent).filter(AuditEvent.ticket_id == "TKT-R").all()
    assert any(a.event_type == "AI_SUGGESTION_REJECTED" for a in audit)


def test_idor_binding():
    db = agdb.SessionLocal()
    out = {"summary": "ok"}
    sug = AISuggestion(ticket_id="TKT-1", kind="summarize", payload_json={"out": out, "metadata": {"sensitivity_level": "low"}}, model_version="v1")
    db.add(sug)
    db.commit()

    client = TestClient(app)
    headers = {"x-ai-gateway-token": "test-token"}
    # wrong ticket_id in payload
    payload = {"ticket_id": "TKT-OTHER", "comment": "x"}
    r = client.post(f"/ai/suggestions/{sug.id}/accept", json=payload, headers=headers)
    assert r.status_code == 404


def test_state_conflict():
    db = agdb.SessionLocal()
    out = {"summary": "ok"}
    sug = AISuggestion(ticket_id="TKT-2", kind="summarize", payload_json={"out": out, "metadata": {"sensitivity_level": "low"}}, model_version="v1", rejected=True)
    db.add(sug)
    db.commit()

    client = TestClient(app)
    headers = {"x-ai-gateway-token": "test-token"}
    payload = {"ticket_id": "TKT-2", "comment": "x"}
    r = client.post(f"/ai/suggestions/{sug.id}/accept", json=payload, headers=headers)
    assert r.status_code == 409


def test_confidential_without_permission():
    db = agdb.SessionLocal()
    out = {"summary": "ok"}
    sug = AISuggestion(ticket_id="TKT-3", kind="summarize", payload_json={"out": out, "metadata": {"sensitivity_level": "CONFIDENTIAL"}}, model_version="v1")
    db.add(sug)
    db.commit()

    client = TestClient(app)
    headers = {"x-ai-gateway-token": "test-token"}
    payload = {"ticket_id": "TKT-3", "comment": "x"}
    r = client.post(f"/ai/suggestions/{sug.id}/accept", json=payload, headers=headers)
    assert r.status_code == 404
    db2 = agdb.SessionLocal()
    audit = db2.query(AuditEvent).filter(AuditEvent.ticket_id == "TKT-3").all()
    assert any(a.event_type == "PERMISSION_DENIED" for a in audit)


def test_missing_token():
    db = agdb.SessionLocal()
    out = {"summary": "ok"}
    sug = AISuggestion(ticket_id="TKT-4", kind="summarize", payload_json={"out": out, "metadata": {"sensitivity_level": "low"}}, model_version="v1")
    db.add(sug)
    db.commit()

    client = TestClient(app)
    # no token header
    payload = {"ticket_id": "TKT-4", "comment": "x"}
    r = client.post(f"/ai/suggestions/{sug.id}/accept", json=payload)
    assert r.status_code == 401
