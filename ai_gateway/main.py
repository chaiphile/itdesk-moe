from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import os
import json
from ai_gateway.clients import OpenRouterClient
from ai_gateway.masking import mask_pii, filter_attachments
from ai_gateway.db import init_db, get_db_session, AISuggestion, AuditEvent
from jsonschema import validate, ValidationError
from datetime import datetime

app = FastAPI(title="ai-gateway")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4o")
AI_GATEWAY_INTERNAL_TOKEN = os.getenv("AI_GATEWAY_INTERNAL_TOKEN", "")
AI_JSON_SCHEMA_STRICT = os.getenv("AI_JSON_SCHEMA_STRICT", "true").lower() in ("1", "true", "yes")
PII_MASKING = os.getenv("PII_MASKING", "true").lower() in ("1", "true", "yes")

with open(os.path.join(os.path.dirname(__file__), "schema.json"), "r", encoding="utf-8") as f:
    OUTPUT_SCHEMA = json.load(f)


class Message(BaseModel):
    type: str
    body: str


class SummarizeInput(BaseModel):
    ticket_id: str
    title: str
    description: str
    messages: List[Message]
    metadata: Dict[str, Any]


class SummarizeOutput(BaseModel):
    summary: str
    action_items: List[str]
    timeline: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: List[str]
    class Config:
        extra = "forbid"


AI_GATEWAY_INIT_DB = os.getenv("AI_GATEWAY_INIT_DB", "true").lower() in ("1", "true", "yes")


@app.on_event("startup")
def startup():
    # Initialize DB tables only when explicitly enabled. In production prefer running migrations
    # and disable auto-creation by setting AI_GATEWAY_INIT_DB=false.
    if AI_GATEWAY_INIT_DB:
        init_db()


def enforce_scope(metadata: Dict[str, Any], request: Request):
    header_org = request.headers.get("x-org-unit")
    if header_org and metadata.get("org_unit_id") and str(header_org) != str(metadata.get("org_unit_id")):
        raise HTTPException(status_code=403, detail="org_unit scope mismatch")


def require_internal_token(request: Request):
    token = request.headers.get("x-ai-gateway-token")
    configured = os.getenv("AI_GATEWAY_INTERNAL_TOKEN", "")
    if not configured:
        return
    if not token or token != configured:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.post("/ai/summarize")
def summarize(payload: SummarizeInput, request: Request, db=Depends(get_db_session)):
    # auth - service-to-service
    require_internal_token(request)

    enforce_scope(payload.metadata, request)

    # Confidential gating (defensive): return 404 to avoid leaking existence
    sensitivity = payload.metadata.get("sensitivity_level")
    requester_perms = payload.metadata.get("requester_permissions") or []
    if str(sensitivity).upper() == "CONFIDENTIAL" and "CONFIDENTIAL_VIEW" not in requester_perms:
        # audit permission denied
        db.add(AuditEvent(event_type="PERMISSION_DENIED", ticket_id=payload.ticket_id, payload_json={"reason": "confidential_without_permission"}, created_at=datetime.utcnow()))
        db.commit()
        raise HTTPException(status_code=404, detail="not found")

    # Prepare messages: remove attachments and mask PII if enabled
    filtered_msgs = filter_attachments([m.dict() for m in payload.messages])
    # Only include text fields (title, description, message bodies)
    parts = [payload.title or "", payload.description or ""]
    parts += [m.get("body", "") for m in filtered_msgs]
    raw_text = "\n".join([p for p in parts if p])
    if PII_MASKING:
        masked_text = mask_pii(raw_text)
    else:
        masked_text = raw_text

    # Audit: AI_REQUESTED
    db.add(AuditEvent(event_type="AI_REQUESTED", ticket_id=payload.ticket_id, payload_json={"kind": "summarize", "model": OPENROUTER_MODEL}, created_at=datetime.utcnow()))
    db.commit()

    # Call OpenRouter (mockable in tests)
    client = OpenRouterClient(api_key=OPENROUTER_API_KEY, model=OPENROUTER_MODEL)
    try:
        model_response = client.summarize(masked_text)
    except Exception as e:
        db.add(AuditEvent(event_type="AI_REQUEST_FAILED", ticket_id=payload.ticket_id, payload_json={"error_class": e.__class__.__name__, "message_short": str(e)[:200]}, created_at=datetime.utcnow()))
        db.commit()
        raise HTTPException(status_code=502, detail="ai request failed")

    # If the client returned a raw marker, treat as invalid
    if not isinstance(model_response, dict) or model_response.get("__raw") is not None:
        db.add(AuditEvent(event_type="AI_OUTPUT_INVALID", ticket_id=payload.ticket_id, payload_json={"raw": model_response.get("__raw") if isinstance(model_response, dict) else str(model_response)}, created_at=datetime.utcnow()))
        db.commit()
        raise HTTPException(status_code=502, detail="ai returned invalid output")

    # Validate/normalize via Pydantic
    try:
        output = SummarizeOutput.parse_obj(model_response)
    except Exception as e:
        db.add(AuditEvent(event_type="AI_OUTPUT_INVALID", ticket_id=payload.ticket_id, payload_json={"error": str(e)[:200], "raw": model_response}, created_at=datetime.utcnow()))
        db.commit()
        raise HTTPException(status_code=502, detail="ai output invalid")

    out = output.dict()

    # jsonschema strict validation as extra safety
    if AI_JSON_SCHEMA_STRICT:
        try:
            validate(instance=out, schema=OUTPUT_SCHEMA)
        except ValidationError as e:
            db.add(AuditEvent(event_type="AI_OUTPUT_INVALID", ticket_id=payload.ticket_id, payload_json={"error": e.message}, created_at=datetime.utcnow()))
            db.commit()
            raise HTTPException(status_code=502, detail="ai output failed schema validation")

    # Persist suggestion and audit creation
    suggestion = AISuggestion(ticket_id=payload.ticket_id, kind="summarize", payload_json=out, model_version=OPENROUTER_MODEL, accepted=None, rejected=None, created_at=datetime.utcnow())
    db.add(suggestion)
    db.commit()

    db.add(AuditEvent(event_type="AI_SUGGESTION_CREATED", ticket_id=payload.ticket_id, payload_json={"suggestion_id": suggestion.id, "kind": "summarize"}, created_at=datetime.utcnow()))
    db.commit()

    return out
