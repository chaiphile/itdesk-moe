from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, has_permission
from app.db.session import get_db
from app.core import tickets as ticket_service
from app.core.dependencies import require_org_scope
from app.models.models import Ticket, User
from app.core.audit import write_audit

router = APIRouter()


@router.post("/tickets", status_code=201)
def create_ticket(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create ticket for current user. owner_org_unit_id is taken from profile."""
    title = payload.get("title")
    description = payload.get("description")
    priority = payload.get("priority")
    if not title or not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title and description are required")

    ticket = ticket_service.create_ticket(db, title=title, description=description, created_by_user=current_user, priority=priority)
    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "owner_org_unit_id": ticket.owner_org_unit_id,
        "created_by": ticket.created_by,
        "priority": ticket.priority,
        "status": ticket.status,
    }


@router.get("/tickets/mine")
def list_my_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List tickets visible to current user according to org scope."""
    rows: List[Ticket] = ticket_service.list_tickets_in_scope(db, current_user)
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "owner_org_unit_id": r.owner_org_unit_id,
            "created_by": r.created_by,
            "priority": r.priority,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/tickets/{ticket_id}")
def get_ticket_by_id(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    """Return ticket if within current user's org scope."""
    ticket = ticket_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Confidential tickets: if user lacks permission, pretend it does not exist and audit the denial
    if ticket.sensitivity_level == "CONFIDENTIAL" and not has_permission(current_user, "CONFIDENTIAL_VIEW"):
        try:
            ip = None
            user_agent = None
            if request is not None:
                try:
                    ip = request.client.host if request.client else None
                except Exception:
                    ip = None
                user_agent = request.headers.get("user-agent")

            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ticket_confidential",
                entity_id=ticket.id,
                meta={"path": request.url.path if request is not None else None, "method": request.method if request is not None else None},
                ip=ip,
                user_agent=user_agent,
            )
        except Exception:
            # Audit failure should not change response behavior
            pass
        # Return 404 to avoid leaking existence
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Enforce org scope using require_org_scope logic by calling the dependency factory
    # If ticket.owner_org_unit_id is None, deny access
    target_org_id = ticket.owner_org_unit_id
    if target_org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope")

    # call the inner dependency to validate scope; pass `request` so audit metadata is available
    dep = require_org_scope(target_org_id)
    dep(current_user=current_user, db=db, request=request)

    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "owner_org_unit_id": ticket.owner_org_unit_id,
        "created_by": ticket.created_by,
        "priority": ticket.priority,
        "status": ticket.status,
    }
