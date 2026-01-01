from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.core import agent_queues as agent_service
from app.models.models import User, TeamMember

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
