from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.auth import get_current_user, has_permission
from app.core.org_scope import is_orgunit_in_scope
from app.core.ai_classifier import mask_pii, rules_v1_classify
from app.db.session import get_db
from app.models.models import AiSuggestion, Ticket, TeamMember
from app.models.models import User

router = APIRouter()


class ClassifyRequest(BaseModel):
    ticket_id: int
    title: str
    description: str
    language: Optional[str] = "fa"


class ClassifyResponse(BaseModel):
    category: str
    subcategory: Optional[str]
    priority: str
    route_to_team_id: Optional[int]
    confidence: float
    rationale_short: str


@router.post("/ai/classify", response_model=ClassifyResponse)
def classify_ticket(
    payload: ClassifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Require agent-like privileges: membership in at least one team OR role name 'agent'
    user_id = getattr(current_user, "id", None)
    team_count = db.query(TeamMember).filter(TeamMember.user_id == user_id).count()
    role_name = getattr(getattr(current_user, "role", None), "name", None)
    if team_count == 0 and role_name != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Agent access required"
        )

    ticket: Ticket = db.query(Ticket).filter(Ticket.id == payload.ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Confidential tickets: deny if no CONFIDENTIAL_VIEW
    if ticket.sensitivity_level == "CONFIDENTIAL" and not has_permission(
        current_user, "CONFIDENTIAL_VIEW"
    ):
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ai_classify",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Org scope check
    viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
    scope_level = getattr(current_user, "scope_level", "SELF")
    if not is_orgunit_in_scope(db, viewer_org_unit_id, scope_level, ticket.owner_org_unit_id):
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ai_classify",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope")

    # Actor team membership validation (must be member of ticket team unless admin)
    actor_team_ids = [r[0] for r in db.query(TeamMember.team_id).filter(TeamMember.user_id == user_id).all()]
    is_admin = has_permission(current_user, "admin")
    if ticket.current_team_id not in actor_team_ids and not is_admin:
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ai_classify",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not permitted to view this ticket")

    # Mask PII before classifying
    masked_title = mask_pii(payload.title)
    masked_description = mask_pii(payload.description)

    # Run baseline classifier
    result = rules_v1_classify(masked_title, masked_description, db=db)

    # Build response strictly matching contract
    response = {
        "category": result["category"],
        "subcategory": result.get("subcategory"),
        "priority": result["priority"],
        "route_to_team_id": result.get("route_to_team_id"),
        "confidence": float(result.get("confidence", 0.0)),
        "rationale_short": result.get("rationale_short", ""),
    }

    # Persist suggestion
    suggestion = AiSuggestion(
        ticket_id=payload.ticket_id,
        kind="TRIAGE",
        payload_json=response,
        model_version="rules-v1",
        created_by=getattr(current_user, "id", None),
    )
    db.add(suggestion)
    try:
        db.commit()
        db.refresh(suggestion)
    except Exception:
        db.rollback()
        raise

    # Audit creation
    try:
        write_audit(
            db,
            actor_id=getattr(current_user, "id", None),
            action="AI_SUGGESTION_CREATED",
            entity_type="ai_suggestion",
            entity_id=suggestion.id,
            diff={"ticket_id": payload.ticket_id, "kind": "TRIAGE", "model_version": "rules-v1"},
            ip=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        pass

    return response


class FeedbackPayload(BaseModel):
    accepted: bool
    feedback_note: Optional[str] = None


@router.post("/ai/suggestions/{suggestion_id}/feedback")
def suggestion_feedback(
    suggestion_id: int,
    payload: FeedbackPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suggestion: AiSuggestion = db.query(AiSuggestion).filter(AiSuggestion.id == suggestion_id).first()
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    # Fetch ticket and ensure visibility
    ticket: Ticket = db.query(Ticket).filter(Ticket.id == suggestion.ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Confidential check
    if ticket.sensitivity_level == "CONFIDENTIAL" and not has_permission(current_user, "CONFIDENTIAL_VIEW"):
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ai_classify",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Org scope
    viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
    scope_level = getattr(current_user, "scope_level", "SELF")
    if not is_orgunit_in_scope(db, viewer_org_unit_id, scope_level, ticket.owner_org_unit_id):
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ai_classify",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope")

    # Update suggestion
    suggestion.accepted = payload.accepted
    suggestion.feedback_note = payload.feedback_note
    suggestion.decided_by = getattr(current_user, "id", None)
    suggestion.decided_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(suggestion)
    except Exception:
        db.rollback()
        raise

    # Audit feedback
    try:
        write_audit(
            db,
            actor_id=getattr(current_user, "id", None),
            action="AI_SUGGESTION_FEEDBACK",
            entity_type="ai_suggestion",
            entity_id=suggestion.id,
            diff={"accepted": payload.accepted},
            ip=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        pass

    return {"ok": True}
