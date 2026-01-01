from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.core import agent_queues as agent_service
from app.models.models import User, TeamMember
from typing import Optional
from pydantic import BaseModel
from fastapi import Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Ticket, Team, TeamMember as TM, AuditLog, User as UserModel
from app.core.auth import has_permission
from app.core.org_scope import is_orgunit_in_scope
from app.core.audit import write_audit

router = APIRouter()


@router.get("/agent/queues")
def get_agent_queues(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return tickets for teams the current user is a member of, within org scope."""
    # Require agent-like privileges: membership in at least one team OR role name 'agent'
    user_id = getattr(current_user, "id", None)
    team_count = db.query(TeamMember).filter(TeamMember.user_id == user_id).count()
    role_name = getattr(getattr(current_user, "role", None), "name", None)
    if team_count == 0 and role_name != "agent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent access required")

    rows = agent_service.list_agent_queues(db, current_user)
    # Minimal fields only
    return [
        {
            "id": r.id,
            "title": r.title,
            "status": r.status,
            "priority": r.priority,
            "owner_org_unit_id": r.owner_org_unit_id,
            "current_team_id": r.current_team_id,
            "assignee_id": r.assignee_id,
            "created_at": r.created_at.isoformat() if r.created_at is not None else None,
            "sensitivity_level": r.sensitivity_level,
        }
        for r in rows
    ]



class AssignPayload(BaseModel):
    assignee_id: Optional[int] = None
    current_team_id: Optional[int] = None


@router.post("/agent/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    payload: AssignPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch ticket
    ticket: Ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Confidential tickets: follow existing policy -> audit and 404
    if ticket.sensitivity_level == "CONFIDENTIAL" and not has_permission(current_user, "CONFIDENTIAL_VIEW"):
        try:
            ip = request.client.host if request.client else None
        except Exception:
            ip = None
        user_agent = request.headers.get("user-agent")
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ticket_confidential",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=ip,
                user_agent=user_agent,
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Org scope check
    viewer_org_unit_id = getattr(current_user, "org_unit_id", None)
    scope_level = getattr(current_user, "scope_level", "SELF")
    if not is_orgunit_in_scope(db, viewer_org_unit_id, scope_level, ticket.owner_org_unit_id):
        # audit permission denied
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ticket_assign",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org unit out of scope")

    # Determine actor team membership
    actor_team_ids = [r[0] for r in db.query(TM.team_id).filter(TM.user_id == getattr(current_user, "id", None)).all()]
    is_admin = has_permission(current_user, "admin")

    if ticket.current_team_id not in actor_team_ids and not is_admin:
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ticket_assign",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not permitted to act on this team")

    # Begin validation for assignee/team changes
    old_assignee = ticket.assignee_id
    old_team = ticket.current_team_id

    new_assignee = payload.assignee_id if payload.assignee_id is not None else getattr(current_user, "id", None)
    new_team = payload.current_team_id if payload.current_team_id is not None else ticket.current_team_id

    # If team change requested, validate actor belongs to that team (or admin)
    if payload.current_team_id is not None:
        # actor must be member of new team or admin
        if payload.current_team_id not in actor_team_ids and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot move ticket to a team you are not a member of")

    # Validate assignee existence
    assignee_obj = None
    if new_assignee is not None:
        assignee_obj = db.query(UserModel).filter(UserModel.id == new_assignee).first()
        if assignee_obj is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee not found")

    # Validate assignee membership in team
    if new_assignee is not None:
        target_team_id_for_validation = new_team
        membership = db.query(TM).filter(TM.team_id == target_team_id_for_validation, TM.user_id == new_assignee).first()
        if membership is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee is not a member of the target team")

    # Enforce assignment policy: non-admins may only self-assign
    if not is_admin and new_assignee != getattr(current_user, "id", None):
        try:
            write_audit(
                db,
                actor_id=getattr(current_user, "id", None),
                action="PERMISSION_DENIED",
                entity_type="ticket_assign",
                entity_id=ticket.id,
                meta={"path": request.url.path, "method": request.method},
                ip=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins may assign to other users")

    # Perform update
    ticket.assignee_id = new_assignee
    ticket.current_team_id = new_team
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Write audit for assignment
    try:
        ip = request.client.host if request.client else None
    except Exception:
        ip = None
    user_agent = request.headers.get("user-agent")
    diff = {
        "assignee_id": {"from": old_assignee, "to": ticket.assignee_id},
        "current_team_id": {"from": old_team, "to": ticket.current_team_id},
    }
    try:
        write_audit(
            db,
            actor_id=getattr(current_user, "id", None),
            action="TICKET_ASSIGNED",
            entity_type="ticket",
            entity_id=ticket.id,
            diff=diff,
            meta={"path": request.url.path, "method": request.method},
            ip=ip,
            user_agent=user_agent,
        )
    except Exception:
        pass

    return {
        "id": ticket.id,
        "current_team_id": ticket.current_team_id,
        "assignee_id": ticket.assignee_id,
        "status": ticket.status,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at is not None else None,
    }
