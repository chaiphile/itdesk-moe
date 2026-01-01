from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

from app.core import tickets as ticket_service
from app.core.audit import write_audit
from app.core.auth import get_current_user, has_permission
from app.core.org_scope import is_orgunit_in_scope
from app.db.session import get_db
from app.models.models import Ticket, User, TicketMessage

router = APIRouter()


@router.post("/tickets", status_code=201)
def create_ticket(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create ticket for current user. owner_org_unit_id is taken from profile."""
    title = payload.get("title")
    description = payload.get("description")
    priority = payload.get("priority")
    if not title or not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title and description are required",
        )

    ticket = ticket_service.create_ticket(
        db,
        title=title,
        description=description,
        created_by_user=current_user,
        priority=priority,
    )
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
def list_my_tickets(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
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
def get_ticket_by_id(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Return ticket if within current user's org scope."""
    # Load ticket and messages; for portal we must only load PUBLIC messages at DB level
    ticket = (
        db.query(Ticket)
        .options(
            selectinload(Ticket.messages),
            # apply loader criteria to ensure only PUBLIC messages are loaded
            with_loader_criteria(TicketMessage, TicketMessage.type == "PUBLIC", include_aliases=True),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    # Confidential tickets: if user lacks permission, pretend it does not exist and audit the denial
    if ticket.sensitivity_level == "CONFIDENTIAL" and not has_permission(
        current_user, "CONFIDENTIAL_VIEW"
    ):
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
                meta={
                    "path": request.url.path if request is not None else None,
                    "method": request.method if request is not None else None,
                },
                ip=ip,
                user_agent=user_agent,
            )
        except Exception:
            # Audit failure should not change response behavior
            pass
        # Return 404 to avoid leaking existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    # Org scope enforcement (audit as ticket_view when denied to avoid leaking)
    target_org_id = ticket.owner_org_unit_id
    if target_org_id is None:
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="org_unit_access",
                entity_id=target_org_id,
                meta={
                    "path": request.url.path if request is not None else None,
                    "method": request.method if request is not None else None,
                },
                ip=(request.client.host if request and request.client else None),
                user_agent=(request.headers.get("user-agent") if request is not None else None),
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope"
        )

    viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
    scope_level = getattr(current_user, "scope_level", "SELF")
    if not is_orgunit_in_scope(db, viewer_org_unit_id, scope_level, target_org_id):
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="org_unit_access",
                entity_id=target_org_id,
                meta={
                    "path": request.url.path if request is not None else None,
                    "method": request.method if request is not None else None,
                },
                ip=(request.client.host if request and request.client else None),
                user_agent=(request.headers.get("user-agent") if request is not None else None),
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope"
        )

    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "owner_org_unit_id": ticket.owner_org_unit_id,
        "created_by": ticket.created_by,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at is not None else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at is not None else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at is not None else None,
        "sensitivity_level": ticket.sensitivity_level,
        "messages": [
            {
                "id": m.id,
                "author_id": m.author_id,
                "type": m.type,
                "body": m.body,
                "created_at": m.created_at.isoformat() if m.created_at is not None else None,
            }
            for m in sorted(ticket.messages, key=lambda x: x.created_at or 0)
        ],
    }
